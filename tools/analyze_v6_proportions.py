"""Compare V6 link proportions with explicit unequal-link kinematics.

This independent screening uses Python's standard library only.  Dimensions
are metres inside the model; reports use millimetres.  It does not modify CAD,
MuJoCo, controller parameters, or the V5 mass budget.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "mechanical/v6"
G = 9.81
RPM_TO_RAD = 2 * math.pi / 60


@dataclass(frozen=True)
class Geometry:
    name: str
    upper: float
    lower: float
    crank: float

    @classmethod
    def mm(cls, name: str, upper: float, lower: float, crank: float):
        return cls(name, upper / 1000, lower / 1000, crank / 1000)

    def forward(self, hip: float, knee: float) -> tuple[float, float]:
        """O-to-W coordinates; knee is rotor relative to its moving stator."""
        oa = hip + knee
        return (self.upper * math.sin(hip) - self.lower * math.sin(oa),
                -self.upper * math.cos(hip) + self.lower * math.cos(oa))

    def jacobian(self, hip: float, knee: float):
        """Columns d(x,z)/d(q_hip,q_knee), each in m/rad."""
        oa = hip + knee
        return ((self.upper * math.cos(hip) - self.lower * math.cos(oa),
                 self.upper * math.sin(hip) - self.lower * math.sin(oa)),
                (-self.lower * math.cos(oa), -self.lower * math.sin(oa)))

    def vertical(self, height: float):
        if not abs(self.upper - self.lower) < height < self.upper + self.lower:
            raise ValueError("Height lies at/outside a theoretical singular boundary")
        cosine = (height**2 - self.upper**2 - self.lower**2) / (2 * self.upper * self.lower)
        bend = math.acos(max(-1., min(1., cosine)))
        hip = -math.atan2(self.lower * math.sin(bend),
                         self.upper + self.lower * math.cos(bend))
        return hip, bend - math.pi, bend

    def height_at_bend(self, bend: float):
        return math.sqrt(self.upper**2 + self.lower**2 +
                         2 * self.upper * self.lower * math.cos(bend))

    def pose_metrics(self, height: float, mass: float):
        hip, knee, bend = self.vertical(height)
        jac = self.jacobian(hip, knee)
        arm = jac[1][1]
        # Holding x_W=0 needs both actuators.  At very deep flexion the hip
        # can become the tighter speed constraint even with equal motors.
        hip_over_knee_rate = -jac[1][0] / height
        speed_factor = max(1., abs(hip_over_knee_rate))
        force = mass * G / 2
        ac_force_factor = self.upper * self.lower / (self.crank * height)
        rpm_per_m_s = 1 / arm / RPM_TO_RAD
        return dict(height_mm=height * 1000, bend_deg=math.degrees(bend),
                    hip_deg=math.degrees(hip), knee_relative_deg=math.degrees(knee),
                    oa_absolute_deg=math.degrees(hip + knee),
                    knee_vertical_arm_mm=arm * 1000,
                    hip_horizontal_arm_mm=jac[0][0] * 1000,
                    knee_horizontal_arm_mm=jac[1][0] * 1000,
                    static_knee_Nm=force * arm,
                    static_hip_Nm=0.,
                    AC_force_per_vertical_wheel_force=ac_force_factor,
                    AC_force_N=force * ac_force_factor,
                    hip_over_knee_rate=hip_over_knee_rate,
                    vertical_speed_at_120rpm_m_s=arm * 120 * RPM_TO_RAD / speed_factor,
                    vertical_speed_at_200rpm_m_s=arm * 200 * RPM_TO_RAD / speed_factor,
                    knee_rpm_for_1_m_s=abs(rpm_per_m_s),
                    hip_rpm_for_1_m_s=abs(hip_over_knee_rate * rpm_per_m_s),
                    knee_rpm_for_100mm_ballistic_jump=math.sqrt(2 * G * .1) * rpm_per_m_s,
                    hip_rpm_for_100mm_ballistic_jump=abs(hip_over_knee_rate) * math.sqrt(2 * G * .1) * rpm_per_m_s)


BASELINE = Geometry.mm("V5 baseline", 130, 130, 35)
RECOMMENDED = Geometry.mm("V6 recommended", 130, 105, 45)
ALTERNATIVES = (Geometry.mm("longer reach candidate", 130, 110, 45),
                Geometry.mm("short compact candidate", 120, 100, 45))


def validate(candidates):
    """Independent FK finite differences and four-bar vector closure."""
    max_jacobian_error = max_inverse_error = max_closure_error = 0.
    max_power_error = max_vertical_rate_error = 0.
    samples = 0
    eps = 1e-6
    for geom in candidates:
        for bend_deg in (5, 30, 60, 90, 120, 150, 170, 175):
            bend = math.radians(bend_deg)
            height = geom.height_at_bend(bend)
            hip, knee, _ = geom.vertical(height)
            fk = geom.forward(hip, knee)
            max_inverse_error = max(max_inverse_error, abs(fk[0]), abs(fk[1] + height))
            jac = geom.jacobian(hip, knee)
            q = (hip, knee)
            for column in range(2):
                plus, minus = list(q), list(q)
                plus[column] += eps
                minus[column] -= eps
                fp, fm = geom.forward(*plus), geom.forward(*minus)
                for axis in range(2):
                    max_jacobian_error = max(max_jacobian_error,
                        abs((fp[axis] - fm[axis]) / (2 * eps) - jac[column][axis]))
            # Independently recover C by intersecting the AC and BC circles.
            # Select the parallelogram assembly branch, then compare with the
            # direct vector closure used for the kinematic reduction.
            oa = (geom.crank * math.sin(hip + knee), -geom.crank * math.cos(hip + knee))
            ob = (geom.upper * math.sin(hip), -geom.upper * math.cos(hip))
            c_from_a = (oa[0] + ob[0], oa[1] + ob[1])
            delta = (ob[0] - oa[0], ob[1] - oa[1])
            distance = math.hypot(*delta)
            along = (geom.upper**2 - geom.crank**2 + distance**2) / (2 * distance)
            perpendicular = math.sqrt(max(0., geom.upper**2 - along**2))
            unit = (delta[0] / distance, delta[1] / distance)
            middle = (oa[0] + along * unit[0], oa[1] + along * unit[1])
            circle_solutions = [(middle[0] - sign * perpendicular * unit[1],
                                 middle[1] + sign * perpendicular * unit[0])
                                for sign in (-1, 1)]
            c_from_b = min(circle_solutions,
                           key=lambda c: math.hypot(c[0] - c_from_a[0], c[1] - c_from_a[1]))
            for axis in range(2):
                max_closure_error = max(max_closure_error, abs(c_from_a[axis] - c_from_b[axis]))
            # Power equality checked with an arbitrary force and rates,
            # using FK finite differences rather than J qdot for velocity.
            rates, force = (.37, -.81), (13., 27.)
            fp = geom.forward(hip + eps * rates[0], knee + eps * rates[1])
            fm = geom.forward(hip - eps * rates[0], knee - eps * rates[1])
            velocity = [(fp[i] - fm[i]) / (2 * eps) for i in range(2)]
            torque = [sum(jac[j][i] * force[i] for i in range(2)) for j in range(2)]
            max_power_error = max(max_power_error, abs(sum(torque[j] * rates[j] for j in range(2)) -
                                                      sum(force[i] * velocity[i] for i in range(2))))
            # Independent derivative of the IK path for fixed wheel x.
            dh = min(1e-7, (height - abs(geom.upper - geom.lower)) / 10,
                     (geom.upper + geom.lower - height) / 10)
            qp, qm = geom.vertical(height + dh), geom.vertical(height - dh)
            analytic = (jac[1][0] / (height * jac[1][1]), -1 / jac[1][1])
            max_vertical_rate_error = max(max_vertical_rate_error,
                *(abs((qp[j] - qm[j]) / (2 * dh) - analytic[j]) for j in range(2)))
            samples += 1
    assert max_jacobian_error < 1e-8
    assert max_inverse_error < 1e-10
    assert max_closure_error < 1e-10
    assert max_power_error < 1e-7
    assert max_vertical_rate_error < 2e-3  # Near-singular 175 degree cases included.
    return dict(samples=samples, fk_central_difference_max_error_m_per_rad=max_jacobian_error,
                inverse_kinematics_max_error_m=max_inverse_error,
                parallelogram_vector_closure_error_m=max_closure_error,
                virtual_work_max_error_W=max_power_error,
                vertical_ik_derivative_max_error_rad_per_m=max_vertical_rate_error,
                note="Vector closure validates the chosen parallelogram algebra, not CAD tolerances or assembly accessibility.")


def candidate_report(geom, mass):
    heights = (.1, .12, .16, math.sqrt(2) * .13, .2, .21, .215, .225)
    return dict(name=geom.name, OB_AC_mm=geom.upper * 1000,
                BW_mm=geom.lower * 1000, OA_BC_mm=geom.crank * 1000,
                theoretical_height_bounds_mm=[abs(geom.upper - geom.lower) * 1000,
                                              (geom.upper + geom.lower) * 1000],
                same_height=[geom.pose_metrics(h, mass) for h in heights
                             if abs(geom.upper - geom.lower) < h < geom.upper + geom.lower],
                same_bend=[geom.pose_metrics(geom.height_at_bend(math.radians(angle)), mass)
                           for angle in (60, 90, 120, 135, 150)],
                practical_clearance_range="Must be established from V6 CAD collision and joint-stop checks; theoretical bounds are not operating limits.")


def write_markdown(report):
    selected = report["selected_candidates"]
    mass = report["comparison_mass_kg"]
    lines = ["# V6 杆长比例独立研究", "",
        "推荐 **OB=AC=130 mm，BW=105 mm，OA=BC=45 mm**。保留平行四杆拓扑，将轮端长臂缩短19.2%，曲柄延长28.6%；需要同时重算姿态和限位槽。备选为130/110/45（多保留5 mm伸展）与120/100/45（更紧凑、竖直速度损失更大）。这里三组数字依次为OB=AC、BW、OA=BC。", "",
        "**加长OA/BC会降低AC杆轴力，不会改变平行四杆的角传动比。缩短BW会同时降低相同姿态下的转矩和同转速下的竖直速度；不能把它当作跳跃能力必然提高。** 可用屈膝角度须由OB包壳、OA槽和CW/轮端的干涉检查确认。", "",
        "## 模型和公式", "",
        "令a=OB=AC、b=BW、r=OA=BC；h为髋电机角，k为膝转子相对膝定子的角，φ=k+π为腿的弯曲角（伸直时φ=0）。OA绝对角为h+k，BW绝对角为h+φ。坐标x向前、z向上，轮心相对髋中心：", "",
        "```text", "x = a sin(h) - b sin(h+k)", "z = -a cos(h) + b cos(h+k)",
        "ℓ² = a² + b² + 2ab cos(φ)",
        "φ = acos((ℓ²-a²-b²)/(2ab))", "h = -atan2(b sin(φ), a+b cos(φ))", "k = φ-π", "```", "",
        "其中后四式为轮心在髋正下方的分支；b≠a时不再使用V5的h=−φ/2。雅可比按电机实际相对角坐标求导：", "",
        "```text", "J_h = (a cos(h)-b cos(h+k), a sin(h)-b sin(h+k))", "J_k = (-b cos(h+k), -b sin(h+k))", "轮心正下方时：", "J_h = (ℓ, 0)", "J_k = (b(b+a cosφ)/ℓ, ab sinφ/ℓ)",
        "垂向膝力臂 d = ab sinφ/ℓ", "纯竖直支承：|τ_k| = Fz·d；|τ_h| = 0（不含杆自重/偏心/车轮反力矩）", "固定轮心x的伸腿：k_dot = -ℓ_dot/d；h_dot = -J_k,x/ℓ · k_dot", "AC轴力：|T|/Fz = ab/(rℓ)（纯竖直、忽略杆自重/轮电机反力矩）", "```", "",
        "自由CW刚体关于B取矩得到T·r·sinφ=Fz·b·sin(h+φ)，代入竖直姿态可得最后一式。矩臂d和运动学均不含r，因此r从42增至45或48mm只改变杆件内力、局部接触载荷和几何空间。", "",
        "## 同一髋轮高度比较", "",
        f"所有候选统一采用V5质量 **{mass:.5f} kg** 做比例隔离比较；每侧Fz=Mg/2。该集中质量表不等于V6的分布自重计算，也不能与V5报告的分布质量1.96N·m列直接比较。", "",
        "| a/b/r mm | 高度 mm | 弯曲角 φ | 膝垂向力臂 mm | 膝静态 N·m/侧 | AC/Fz | 200rpm理想竖直速度 m/s |", "|---|---:|---:|---:|---:|---:|---:|"]
    for row in selected:
        label = f'{row["OB_AC_mm"]:.0f}/{row["BW_mm"]:.0f}/{row["OA_BC_mm"]:.0f}'
        for pose in row["same_height"]:
            if abs(pose["height_mm"] - 183.8477631085) < .01 or pose["height_mm"] in (120, 200):
                lines.append(f'| {label} | {pose["height_mm"]:.2f} | {pose["bend_deg"]:.2f}° | {pose["knee_vertical_arm_mm"]:.2f} | {pose["static_knee_Nm"]:.3f} | {pose["AC_force_per_vertical_wheel_force"]:.3f} | {pose["vertical_speed_at_200rpm_m_s"]:.3f} |')
    lines += ["", "同183.85mm髋轮距，推荐方案较V5垂向力臂约下降21.1%，AC内力约下降37.2%，200rpm理想竖直速度亦下降21.1%。同高度时推荐方案弯曲角为77.57°，V5为90°；短BW本身没有让该高度下的屈膝角变大。", "",
        "## 同弯曲角比较", "", "| a/b/r mm | φ=90°时高度 mm | 膝静态 N·m/侧 | 膝垂向力臂 mm | 200rpm理想速度 m/s |", "|---|---:|---:|---:|---:|"]
    for row in selected:
        pose = next(p for p in row["same_bend"] if abs(p["bend_deg"] - 90) < .01)
        label = f'{row["OB_AC_mm"]:.0f}/{row["BW_mm"]:.0f}/{row["OA_BC_mm"]:.0f}'
        lines.append(f'| {label} | {pose["height_mm"]:.2f} | {pose["static_knee_Nm"]:.3f} | {pose["knee_vertical_arm_mm"]:.2f} | {pose["vertical_speed_at_200rpm_m_s"]:.3f} |')
    lines += ["", "推荐方案同90°弯曲角下垂向力臂由91.92降至81.68mm，约下降11.1%；同高和同角必须分别比较。", "",
        "## 行程、死点和屈膝", "", "| a/b/r mm | 理论髋轮距 mm | 120mm时 φ | 100mm时 φ |", "|---|---:|---:|---:|"]
    for row in selected:
        label = f'{row["OB_AC_mm"]:.0f}/{row["BW_mm"]:.0f}/{row["OA_BC_mm"]:.0f}'
        bounds = row["theoretical_height_bounds_mm"]
        poses = {round(p["height_mm"]): p for p in row["same_height"]}
        lines.append(f'| {label} | {bounds[0]:.0f}～{bounds[1]:.0f} | {poses[120]["bend_deg"]:.2f}° | {poses[100]["bend_deg"]:.2f}° |')
    lines += ["", "上述仅为理想杆中心运动学。φ=0或180°时det(J)=ab·sinφ=0，四杆亦进入共线变位；应避免到达或越过，限位需要预留实体间隙和控制裕量。a=b且完全折叠时ℓ=0，竖直朝向分支本身也退化。", "",
        "推荐方案先在120～215mm范围做实体干涉扫描，再尝试扩展至100mm，不能提前把25～235mm理论范围写成允许行程。增大r使A/C承载耳与O/B头部距离增大，可能帮助清除某些局部干涉，但OA扫掠外径也随之变大；必须以实际槽形检查为准。", "",
        "## 24V V1.1电机的离地速度约束", "",
        "统一采用J4310额定120rpm、24V空载200rpm。表中速度同时限制髋与膝；200rpm对应无载运动学天花板，绝不是在该速度还能同时提供7N·m。不同姿态的重力功、关节惯量、峰值时间和热约束需另算。", "",
        "| a/b/r mm | 离地髋轮距 mm | 100mm理想抛升需膝rpm | 需髋rpm |", "|---|---:|---:|---:|"]
    for row in selected:
        label = f'{row["OB_AC_mm"]:.0f}/{row["BW_mm"]:.0f}/{row["OA_BC_mm"]:.0f}'
        for pose in row["same_height"]:
            if pose["height_mm"] in (200, 215, 225):
                lines.append(f'| {label} | {pose["height_mm"]:.0f} | {pose["knee_rpm_for_100mm_ballistic_jump"]:.1f} | {pose["hip_rpm_for_100mm_ballistic_jump"]:.1f} |')
    lines += ["", "因此V6若追求跳跃，应在较早的伸腿姿态评估离地，而不能简单沿用V5的225mm离地：推荐方案225mm距235mm全伸直更近，速度能力显著下降。相同电机与相同质量下，几何减力和提速存在权衡。", "",
        "## 数值验证和证据", "", f'中心差分FK雅可比最大误差 {report["validation"]["fk_central_difference_max_error_m_per_rad"]:.3g} m/rad；IK位置最大误差 {report["validation"]["inverse_kinematics_max_error_m"]:.3g} m。另核对固定轮心的IK角速度导数、平行四杆向量闭环和虚功功率一致性。', "",
        "- [完整24组比例扫描、3个选择与V5基准](proportion_study.json)。", "- [可复现脚本](../../tools/analyze_v6_proportions.py)：`python3 tools/analyze_v6_proportions.py`。脚本只写本研究报告，不改CAD/仿真。", "- [Lynch/Park《Modern Robotics》5.1.1](https://modernrobotics.northwestern.edu/nu-gm-book-resource/5-1-1-space-jacobian/)给出关节速度与末端速度的雅可比关系；[5.2](https://modernrobotics.northwestern.edu/nu-gm-book-resource/5-2-statics-of-open-chains/)由功率守恒推导雅可比转置与关节力矩的关系。本机构的具体公式为本报告依实际拓扑重新推导。", "- [本地4310 V1.1手册](../../references/DM-J4310-2EC/说明书/DM-J4310-2EC%20V1.1%20Geared%20Motor%20User%20Manual%20V1.2%202026-09-08.pdf)第7页：额定3N·m、峰值7N·m、额定120rpm；24V空载200rpm。用户已确认24V V1.1驱动。", "", "本研究不证明结构强度、轴承冲击寿命、电池供电、机器人平衡或跳跃性能；这些必须结合最终V6质量与实体运动检查继续核对。"]
    (OUT / "proportion_study.md").write_text("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mass-kg", type=float, default=None,
                        help="Common comparison mass; defaults to the V5 mass budget")
    args = parser.parse_args()
    mass = args.mass_kg
    if mass is None:
        mass = json.loads((ROOT / "mechanical/v5/mass_budget.json").read_text())["total_kg"]
    if not math.isfinite(mass) or mass <= 0:
        raise ValueError("Mass must be finite and positive")
    grid = [Geometry.mm(f"grid_{a}_{b}_{r}", a, b, r)
            for a in (120, 130) for b in (95, 100, 105, 110) for r in (42, 45, 48)]
    selected = [BASELINE, RECOMMENDED, *ALTERNATIVES]
    report = dict(comparison_mass_kg=mass,
                  mass_method="Common V5 reference mass, intentionally unchanged to isolate geometry; not a final V6 mass estimate",
                  recommended_dimensions_mm=dict(OB=130, AC=130, BW=105, OA=45, BC=45),
                  selected_candidates=[candidate_report(g, mass) for g in selected],
                  grid=[candidate_report(g, mass) for g in grid],
                  validation=validate(selected + grid),
                  sources=dict(jacobian="https://modernrobotics.northwestern.edu/nu-gm-book-resource/5-1-1-space-jacobian/",
                               statics="https://modernrobotics.northwestern.edu/nu-gm-book-resource/5-2-statics-of-open-chains/"),
                  critical_findings=["r changes link forces, not the 1:1 angular transmission or endpoint Jacobian of the parallelogram",
                                     "At identical height shorter BW reduces vertical torque arm and speed equally",
                                     "Geometrical height bounds exclude mechanical collision and stops",
                                     "Hip rate is not generally half the knee relative rate when OB differs from BW",
                                     "Both hip and knee speed caps are applied; 200rpm is an unloaded bound, not a peak torque working point"])
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "proportion_study.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    write_markdown(report)
    print(json.dumps(dict(recommended=report["recommended_dimensions_mm"], validation=report["validation"]), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
