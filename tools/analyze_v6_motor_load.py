"""V6 CAD mass, constrained gravity and 24 V motor load screening.

Run with FreeCAD Python after wheel_leg_v6.FCStd exists.  --formula-only runs
without FreeCAD; --plot-only uses an ordinary Python with matplotlib.  This
script writes V6 reports only and never saves the opened FreeCAD document.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

from analyze_v6_proportions import BASELINE, G, Geometry, RECOMMENDED, validate

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "mechanical/v6"
ROLES = {"fixed", "hip", "oa", "ac", "output", "wheel"}
WHEEL_RADIUS = .050
RATED_TORQUE = 3.
PEAK_TORQUE = 7.


def write_json(name, value):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def com(shape, app):
    solids = shape.Solids
    volume = sum(s.Volume for s in solids)
    if volume <= 0:
        raise ValueError("Mass item is not a positive-volume solid")
    center = sum((s.CenterOfMass * s.Volume for s in solids), app.Vector()) / volume
    return center, volume


def read_mass_budget(doc, app, allowance_g=200.):
    rows = []
    for obj in doc.Objects:
        if obj.TypeId != "Part::Feature":
            continue
        material = getattr(obj, "Material", "")
        role = getattr(obj, "KinematicRole", "")
        if role not in ROLES:
            raise ValueError(f"Unknown kinematic role for {obj.Name}: {role}")
        center, volume = com(obj.Shape, app)
        if material == "motor":
            if "H6215" in obj.Name:
                mass_g = 360.
            elif "J4310" in obj.Name:
                mass_g = 300.
            else:
                raise ValueError(f"Unknown motor mass: {obj.Name}")
            method = "Manufacturer motor mass; CAD uniform-volume centre approximates unknown internal mass distribution"
        elif material == "payload":
            mass_g = obj.BudgetMassGrams
            method = obj.ManufacturingNote
        else:
            density = {"CNC": .0027, "PETG": .00127, "rubber": .0011,
                       "steel": .00785}.get(material)
            if density is None:
                raise ValueError(f"Unbudgeted material: {obj.Name} / {material}")
            if "bronze" in obj.Name:
                density = .0088
            mass_g = volume * density
            method = f"CAD nominal solid volume × {density} g/mm³"
        if not math.isfinite(mass_g) or mass_g <= 0:
            raise ValueError(f"Invalid mass: {obj.Name}")
        local = obj.Placement.inverse().multVec(center)
        rows.append(dict(part=obj.Name, material=material, mass_g=round(mass_g, 3),
                         center_mm=[center.x, center.y, center.z],
                         local_center_mm=[local.x, local.y, local.z],
                         role=role, method=method))
    rows.append(dict(part="unmodelled_installation_allowance", material="allowance",
                     mass_g=allowance_g, center_mm=[0., 0., 5.],
                     local_center_mm=[0., 0., 5.], role="fixed",
                     method="Engineering allowance for cables, DC/DC, connectors, retainers and unmodelled fasteners; 100–300 g indicative"))
    total = sum(row["mass_g"] for row in rows) / 1000
    categories = {}
    for row in rows:
        material = row["material"]
        categories[material] = categories.get(material, 0.) + row["mass_g"] / 1000
    center = [sum(row["mass_g"] * row["center_mm"][axis] for row in rows) / (1000 * total)
              for axis in range(3)]
    return dict(total_kg=total, indicative_range_kg=[total - .2, total + .3],
                range_method="Engineering installation/device/printing allowance, not a statistical confidence interval",
                by_material_kg=categories, nominal_center_from_hip_mm=center, parts=rows,
                notes=["PETG uses full CAD volume, not a slicer mass estimate",
                       "Bearing/hardware reference envelopes may overestimate real internal solid volume",
                       "Motor mass comes from manufacturer data; internal centre of mass remains approximate",
                       "V6 CAD mass is separate from the fixed V5 comparison mass used in proportion_study.json"])


def transformed_center(row, geometry, hip, knee):
    """Independent role transforms in the XZ plane, returning metres."""
    x, y, z = [v / 1000 for v in row["local_center_mm"]]
    role = row["role"]
    if role == "fixed":
        return x, y, z
    oa, output = hip + knee, hip + knee + math.pi
    angle = {"hip": hip, "oa": oa, "ac": hip,
             "output": output, "wheel": output}[role]
    px, pz = x * math.cos(angle) - z * math.sin(angle), x * math.sin(angle) + z * math.cos(angle)
    if role == "ac":
        px += geometry.crank * math.sin(oa)
        pz -= geometry.crank * math.cos(oa)
    elif role == "output":
        px += geometry.upper * math.sin(hip)
        pz -= geometry.upper * math.cos(hip)
    elif role == "wheel":
        wx, wz = geometry.forward(hip, knee)
        px += wx
        pz += wz
    return px, y, pz


def potential(budget, geometry, hip, knee):
    """Ground-fixed wheels, chassis pitch fixed; both legs vary together.

    The chassis origin translates by -W.  This is a constrained virtual-work
    calculation, not the free body's equilibrium or balance-control solution.
    """
    _, wheel_z = geometry.forward(hip, knee)
    return sum(row["mass_g"] / 1000 * G *
               (transformed_center(row, geometry, hip, knee)[2] - wheel_z)
               for row in budget["parts"])


def distributed_row(budget, geometry, height):
    hip, knee, bend = geometry.vertical(height)
    efforts, convergence = [], []
    for joint in (0, 1):
        derivatives = []
        for eps in (1e-5, 1e-6):
            plus, minus = [hip, knee], [hip, knee]
            plus[joint] += eps
            minus[joint] -= eps
            # Divide common left/right work equally between the two drives.
            derivatives.append((potential(budget, geometry, *plus) -
                                potential(budget, geometry, *minus)) / (4 * eps))
        efforts.append(derivatives[-1])
        convergence.append(abs(derivatives[1] - derivatives[0]))
    return dict(leg_length_mm=height * 1000, bend_deg=math.degrees(bend),
                hip_deg=math.degrees(hip), knee_relative_deg=math.degrees(knee),
                hip_gravity_Nm=efforts[0], knee_gravity_Nm=efforts[1],
                hip_magnitude_Nm=abs(efforts[0]), knee_magnitude_Nm=abs(efforts[1]),
                knee_rated_utilization=abs(efforts[1]) / RATED_TORQUE,
                knee_with_25_percent_allowance_Nm=1.25 * abs(efforts[1]),
                finite_difference_convergence_Nm=max(convergence))


def native_validation(doc, app, budget, geometry, heights):
    """Check native expressions against independent COM and gravity models."""
    params = doc.Parameters
    saved = float(params.LegLength.Value), float(params.Beta.Value)
    bodies = [(doc.getObject(row["part"]), row) for row in budget["parts"]
              if row["material"] != "allowance"]
    local_vectors = {row["part"]: app.Vector(*row["local_center_mm"]) for _, row in bodies}
    max_position_error = max_angle_error = 0.
    gravity_rows = []

    def set_pose(height, beta=0.):
        params.LegLength = height * 1000
        params.Beta = math.degrees(beta)
        doc.recompute()

    def native_potential(height, beta=0.):
        set_pose(height, beta)
        # The downward leg vector is rotated through beta at fixed length.
        wz = -height * math.cos(beta)
        # Native Placement includes the recomputed FreeCAD expressions.
        # Rigid-body centroid invariance avoids repeatedly integrating the
        # full motor B-reps at every small derivative perturbation. The CAD
        # centroid was obtained from the actual solids in read_mass_budget.
        result = sum(row["mass_g"] / 1000 * G *
                     (obj.Placement.multVec(local_vectors[row["part"]]).z / 1000 - wz)
                     for obj, row in bodies)
        result += sum(row["mass_g"] / 1000 * G *
                      (row["local_center_mm"][2] / 1000 - wz)
                      for row in budget["parts"] if row["material"] == "allowance")
        return result

    try:
        for height in heights:
            hip, knee, _ = geometry.vertical(height)
            for beta in (0., math.radians(10), math.radians(-10)):
                set_pose(height, beta)
                native_angles = [float(params.Hip.Value), float(params.OA.Value), float(params.Output.Value)]
                expected_angles = [math.degrees(hip + beta), math.degrees(hip + knee + beta),
                                   math.degrees(hip + knee + math.pi + beta)]
                max_angle_error = max(max_angle_error,
                                      *(abs(a - b) for a, b in zip(native_angles, expected_angles)))
                for obj, row in bodies:
                    actual = obj.Placement.multVec(local_vectors[row["part"]])
                    expected = transformed_center(row, geometry, hip + beta, knee)
                    error = math.sqrt(sum((actual[i] - expected[i] * 1000)**2 for i in range(3)))
                    max_position_error = max(max_position_error, error)
            # Beta varies h only. Length varies both h and k. These two
            # independent native-parameter derivatives recover motor efforts.
            eps_beta, eps_height = 1e-5, 1e-6
            tau_hip = (native_potential(height, eps_beta) - native_potential(height, -eps_beta)) / (4 * eps_beta)
            du_dheight_per_side = (native_potential(height + eps_height) -
                                  native_potential(height - eps_height)) / (4 * eps_height)
            jac = geometry.jacobian(hip, knee)
            dk_dheight = -1 / jac[1][1]
            dh_dheight = jac[1][0] / (height * jac[1][1])
            tau_knee = (du_dheight_per_side - tau_hip * dh_dheight) / dk_dheight
            independent = distributed_row(budget, geometry, height)
            error = max(abs(tau_hip - independent["hip_gravity_Nm"]),
                        abs(tau_knee - independent["knee_gravity_Nm"]))
            gravity_rows.append(dict(height_mm=height * 1000, native_hip_Nm=tau_hip,
                                     native_knee_Nm=tau_knee, effort_error_Nm=error))
    finally:
        params.LegLength, params.Beta = saved
        doc.recompute()
    max_effort_error = max(row["effort_error_Nm"] for row in gravity_rows)
    if max_position_error > .001 or max_angle_error > 1e-6 or max_effort_error > 2e-5:
        raise ValueError(f"Native expression mismatch: {max_position_error=}, {max_angle_error=}, {max_effort_error=}")
    return dict(heights_mm=[h * 1000 for h in heights], beta_deg=[-10, 0, 10],
                maximum_COM_error_mm=max_position_error, maximum_angle_error_deg=max_angle_error,
                maximum_gravity_effort_error_Nm=max_effort_error, gravity_checks=gravity_rows,
                saved_document_modified=False,
                scope="FreeCAD native Placement expressions applied to actual CAD-derived local centres, checked against independent analytic transforms and constrained gravity; does not establish collision clearance at beta ±10 degrees")


def formula_tests():
    result = validate([BASELINE, RECOMMENDED])
    baseline_budget = json.loads((ROOT / "mechanical/v5/mass_budget.json").read_text())
    old_report = json.loads((ROOT / "mechanical/v5/motor_load_analysis.json").read_text())
    comparisons = []
    for old in old_report["distributed_gravity"]["rows"]:
        new = distributed_row(baseline_budget, BASELINE, old["leg_length_mm"] / 1000)
        error = max(abs(new[key] - old[key]) for key in ("hip_gravity_Nm", "knee_gravity_Nm"))
        comparisons.append(dict(height_mm=old["leg_length_mm"], effort_error_Nm=error))
    if max(row["effort_error_Nm"] for row in comparisons) > 1e-6:
        raise ValueError("V5 same-method gravity regression failed")
    result["V5_same_method_regression"] = comparisons
    # A point payload fixed at O has potential Mg(-zW).  Its gravity gradient
    # must equal minus J^T times Mg/2 at each symmetric constrained leg.
    point = dict(parts=[dict(mass_g=1000., local_center_mm=[0., 0., 0.], role="fixed")])
    errors = []
    for height in (.1, .12, .18, .2, .215):
        h, k, _ = RECOMMENDED.vertical(height)
        expected = [-G / 2 * col[1] for col in RECOMMENDED.jacobian(h, k)]
        measured = distributed_row(point, RECOMMENDED, height)
        errors.extend(abs(measured[key] - expected[j])
                      for j, key in enumerate(("hip_gravity_Nm", "knee_gravity_Nm")))
    result["point_payload_virtual_work_max_error_Nm"] = max(errors)
    assert max(errors) < 1e-8
    return result


def analyze(budget, geometry, heights, nominal):
    mass = budget["total_kg"]
    rows = [distributed_row(budget, geometry, height) for height in heights]
    concentrated = [geometry.pose_metrics(height, mass) for height in heights]
    baseline_budget = json.loads((ROOT / "mechanical/v5/mass_budget.json").read_text())
    comparison = []
    for height, current in zip(heights, rows):
        old = distributed_row(baseline_budget, BASELINE, height)
        comparison.append(dict(height_mm=height * 1000,
                               V5_knee_Nm=old["knee_magnitude_Nm"],
                               V6_knee_Nm=current["knee_magnitude_Nm"],
                               knee_change_percent=(current["knee_magnitude_Nm"] / old["knee_magnitude_Nm"] - 1) * 100,
                               V5_hip_Nm=old["hip_magnitude_Nm"], V6_hip_Nm=current["hip_magnitude_Nm"]))
    standing = distributed_row(budget, geometry, nominal)
    hip, knee, _ = geometry.vertical(nominal)
    jac = geometry.jacobian(hip, knee)
    driving = []
    for acceleration in (0., .5, 1.):
        force_x = mass * (acceleration + .02 * G) / 2
        wheel_torque = WHEEL_RADIUS * force_x
        driving.append(dict(acceleration_m_s2=acceleration, Crr_assumption=.02,
                            height_mm=nominal * 1000, wheel_torque_Nm=wheel_torque,
                            hip_absolute_sum_Nm=standing["hip_magnitude_Nm"] + abs(jac[0][0] * force_x) + abs(wheel_torque),
                            knee_absolute_sum_Nm=standing["knee_magnitude_Nm"] + abs(jac[1][0] * force_x) + abs(wheel_torque),
                            method="Distributed static gravity plus conservative total-mass horizontal demand and wheel-housing couple; omits wheel/link inertias"))
    jumps = []
    for height in (.16, nominal, .2, .215):
        metrics = geometry.pose_metrics(height, mass)
        for ballistic_height in (.05, .10, .15):
            speed = math.sqrt(2 * G * ballistic_height)
            knee_rpm = metrics["knee_rpm_for_1_m_s"] * speed
            hip_rpm = metrics["hip_rpm_for_1_m_s"] * speed
            jumps.append(dict(takeoff_leg_length_mm=height * 1000,
                              ideal_ballistic_rise_mm=ballistic_height * 1000,
                              required_vertical_speed_m_s=speed, knee_rpm=knee_rpm,
                              hip_rpm=hip_rpm, exceeds_200rpm_no_load_limit=max(knee_rpm, hip_rpm) > 200,
                              below_no_load_does_not_establish_loaded_torque=True))
    landings = []
    for fall in (.05, .10, .20):
        for stroke in (.03, .05, .08):
            end_height = heights[-1] - stroke
            factor = 1 + fall / stroke
            force_z = mass * G * factor / 2
            h, k, _ = geometry.vertical(end_height)
            arm = geometry.jacobian(h, k)[1][1]
            ac_force = force_z * geometry.upper * geometry.lower / (geometry.crank * end_height)
            b_force = math.hypot(ac_force * math.sin(h), force_z + ac_force * math.cos(h))
            landings.append(dict(fall_height_mm=fall * 1000, stopping_stroke_mm=stroke * 1000,
                                 end_leg_length_mm=end_height * 1000,
                                 displacement_average_load_multiple=factor,
                                 knee_torque_at_average_force_Nm=force_z * arm,
                                 AC_force_at_average_N=ac_force, B_force_at_average_N=b_force,
                                 note="Displacement-average force times end-stroke arm; not a peak impact or time-average torque"))
    return dict(geometry_mm=dict(OB=geometry.upper * 1000, AC=geometry.upper * 1000,
                                BW=geometry.lower * 1000, OA=geometry.crank * 1000, BC=geometry.crank * 1000),
                nominal_leg_length_mm=nominal * 1000, mass_kg=mass,
                motor_specs=dict(J4310=dict(voltage_V=24, driver_version="V1.1 confirmed by user",
                                           rated_Nm=3, peak_Nm=7, rated_rpm=120, no_load_rpm=200),
                                 H6215=dict(voltage_V=24, rated_Nm=1, peak_Nm=2,
                                            rated_rpm=120, no_load_rpm=320)),
                distributed_gravity=dict(rows=rows,
                    constraint="Wheels fixed to ground, left/right coordinates varied together, chassis pitch fixed; requires corresponding external constraint reaction and is not a free static balance solution"),
                concentrated_mass_screen=concentrated, V5_same_height_same_method=comparison,
                flat_driving=driving, takeoff_speed_scenarios=jumps, landing_scenarios=landings,
                wheel_rated_speed_m_s=120 * 2 * math.pi / 60 * WHEEL_RADIUS,
                wheel_no_load_speed_m_s=320 * 2 * math.pi / 60 * WHEEL_RADIUS,
                limitations=["The supplied 24 V performance image is not a full 7 Nm torque-speed-duration envelope",
                             "Motor rotor and stator are treated as one rigid envelope for gravity; internal inertias are not modelled",
                             "Uniform-volume motor centres approximate unknown internal mass distribution",
                             "No thermal, peak-current-duration, voltage-sag, battery-discharge or free-balance verification",
                             "r=45 mm reduces linkage axial force; it does not itself reduce the motor-to-CW angular ratio",
                             "Wheel-housing torque acts on the CW body and therefore contributes to both motor coordinates",
                             "CAD beta-pose validation is kinematic only and does not establish its collision-free operating range"])


def write_markdown(budget, report):
    rows = report["distributed_gravity"]["rows"]
    nominal = next(row for row in rows if abs(row["leg_length_mm"] - report["nominal_leg_length_mm"]) < .01)
    worst = max(rows, key=lambda row: row["knee_magnitude_Nm"])
    mass = budget["total_kg"]
    lines = ["# V6 质量与24V电机负载初算", "",
        f'本版CAD与设备合计约 **{mass:.3f} kg**，工程估计区间{budget["indicative_range_kg"][0]:.2f}～{budget["indicative_range_kg"][1]:.2f}kg。采用OB=AC=130、BW=105、OA=BC=45mm，名义髋轮距{report["nominal_leg_length_mm"]:.0f}mm。', "",
        f'名义姿态每侧膝分布重力负载约 **{nominal["knee_magnitude_Nm"]:.2f}N·m**；报告采样中最大约 **{worst["knee_magnitude_Nm"]:.2f}N·m**，出现在{worst["leg_length_mm"]:.0f}mm。对照J4310额定3N·m、峰值7N·m。该结果仅用于低速调试的力矩筛查，不能证明任意姿态连续工作或完成跳跃。', "",
        "用户确认J4310采用 **24V、V1.1版本驱动**。额定120rpm、空载200rpm；本报告不采用48V的400rpm，也不将输出轴转矩再乘10:1。200rpm与7N·m不能视作可同时实现的工作点。", "",
        "## 质量", "", "| 类别 | kg |", "|---|---:|"]
    lines += [f'| {key} | {value:.3f} |' for key, value in budget["by_material_kg"].items()]
    lines += ["", "四台4310按1.20kg、两台H6215按0.72kg；Orin套件175g、D435按75g、电池400g、IMU暂20g。另留200g安装附件预算。打印件按CAD实体体积计算，实际切片和实称应替换；硬件包络也不等同于精确内部实体质量。", "",
        "## 分布重力与V5同方法比较", "",
        "每件零件使用本版CAD体积/设备质量及局部重心，通过KinematicRole恢复运动；固定轮心于地面、固定机身俯仰，同时扰动左右同名关节，将势能导数均分到两台电机。**这是有外部俯仰约束的虚功计算，不是自由机器人平衡解。** 真实机器人必须用轮端接触力和姿态控制维持平衡。", "",
        "| 髋轮距 mm | V6髋 N·m/侧 | V6膝 N·m/侧 | V5膝同方法 N·m/侧 | V6膝×1.25 |", "|---|---:|---:|---:|---:|"]
    for row, comparison in zip(rows, report["V5_same_height_same_method"]):
        lines.append(f'| {row["leg_length_mm"]:.2f} | {row["hip_magnitude_Nm"]:.3f} | {row["knee_magnitude_Nm"]:.3f} | {comparison["V5_knee_Nm"]:.3f} | {row["knee_with_25_percent_allowance_Nm"]:.3f} |')
    lines += ["", "V5与V6各使用自身CAD质量，统一高度及同一势能方法；比值同时包含几何与质量变化。V5在100mm等位置的列只是数学重算，并不表示V5已通过这些位置的实体干涉检查。25%是设计留量示例，不能代替电机热模型。", "",
        "另在JSON保留全质量集中于机身的粗筛。该粗筛包含轮端非簧载质量，不应和分布质量列混用；也不应因粗筛单列超过3N·m就直接断言实机必然失效。", "",
        "## 平地低速行驶", "", "| 加速度 m/s² | 髋绝对和包络 N·m/侧 | 膝绝对和包络 N·m/侧 | 轮转矩 N·m/侧 |", "|---:|---:|---:|---:|"]
    for row in report["flat_driving"]:
        lines.append(f'| {row["acceleration_m_s2"]:.1f} | {row["hip_absolute_sum_Nm"]:.3f} | {row["knee_absolute_sum_Nm"]:.3f} | {row["wheel_torque_Nm"]:.3f} |')
    lines += ["", "名义姿态、滚阻系数0.02假设。以分布静态负载为基础，叠加全质量水平加速/滚阻的雅可比项，并按不利方向叠加CW上的轮电机外壳反力矩；未包含车轮转动惯量、连杆惯性和姿态纠偏峰值。轮毂电机额定1、峰值2N·m。", "",
        f'轮半径50mm，额定120rpm对应约{report["wheel_rated_speed_m_s"]:.2f}m/s；320rpm对应约{report["wheel_no_load_speed_m_s"]:.2f}m/s空载轮缘速度。', "",
        "## 跳跃速度", "", "| 离地髋轮距 mm | 理想抛升 mm | 膝相对转速 rpm | 髋转速 rpm | 超出200rpm空载 |", "|---:|---:|---:|---:|---|"]
    for row in report["takeoff_speed_scenarios"]:
        if row["ideal_ballistic_rise_mm"] in (50, 100):
            lines.append(f'| {row["takeoff_leg_length_mm"]:.0f} | {row["ideal_ballistic_rise_mm"]:.0f} | {row["knee_rpm"]:.1f} | {row["hip_rpm"]:.1f} | {"是" if row["exceeds_200rpm_no_load_limit"] else "否"} |')
    lines += ["", "速度由v=√(2gh)与V6不等长雅可比计算，同时检查髋和膝。**低于空载200rpm不等于电机在该速度有足够转矩**。缩短BW降低力矩需求，也降低相同关节转速的竖直速度；加长OA/BC主要降低AC杆内力，不改变平行四杆的角传动比。需要较早离地与真实转矩—转速—时间曲线共同评估，当前仍不能确认跳跃能力。", "",
        "## 落地平均载荷筛查", "", "| 落差 mm | 缓冲 mm | 位移平均力/Mg | 终点膝 N·m/侧 | AC平均力 N | B平均反力 N |", "|---:|---:|---:|---:|---:|---:|"]
    for row in report["landing_scenarios"]:
        lines.append(f'| {row["fall_height_mm"]:.0f} | {row["stopping_stroke_mm"]:.0f} | {row["displacement_average_load_multiple"]:.2f} | {row["knee_torque_at_average_force_Nm"]:.2f} | {row["AC_force_at_average_N"]:.0f} | {row["B_force_at_average_N"]:.0f} |')
    lines += ["", f'以{rows[-1]["leg_length_mm"]:.0f}mm开始缓冲，F平均=Mg(1+h/s)，转矩采用缓冲终点力臂。这里是**位移平均力乘终点力臂**，不是冲击峰值或时间平均转矩。单腿先着地、结构弹性、控制延迟和动态惯量可能增大峰值；该表不属于跳跃验收。', "",
        "## 公式、原生FreeCAD复核与供电", "",
        "U=Σmi·g·(zi−zW)，τj=(∂U/∂qj)/2。a=130mm、b=105mm、r=45mm；xW=a·sin(h)−b·sin(h+k)，zW=−a·cos(h)+b·cos(h+k)。轮在髋正下方时φ=acos((ℓ²−a²−b²)/(2ab))、h=−atan2(b·sinφ,a+b·cosφ)、k=φ−π。膝垂向力臂ab·sinφ/ℓ，AC纯竖直轴力/Fz=ab/(rℓ)。", "",
        f'独立数学模型与FreeCAD原生表达式核对的最大重心位置误差 **{report["native_validation"]["maximum_COM_error_mm"]:.3g}mm**，重力力矩误差 **{report["native_validation"]["maximum_gravity_effort_error_Nm"]:.3g}N·m**。原生校验包含Beta±10°，只是公式验证，不代表这些姿态的无干涉范围。', "",
        "四台4310同时在3N·m/120rpm、两台H6215在1N·m/120rpm的机械功率合计约176W，对应24V至少7.3A，实际还需加驱动损耗和电子设备功耗。这是指定工作点的算术预算，不是常态耗电预测；静态保持机械功为0也有铜耗发热。", "",
        "4310手册的额定/峰值相电流不能直接相加当电池母线电流。400g只确定电池质量，容量、放电倍率、BMS限流、压降仍未知，供电与续航不能据此确认。", "",
        "- [逐件质量与重心](mass_budget.json)、[全部负载数据](motor_load_analysis.json)、[比例研究](proportion_study.md)、[原生校验](motor_native_validation.json)。", "- [4310 V1.1原厂手册](../../references/DM-J4310-2EC/说明书/DM-J4310-2EC%20V1.1%20Geared%20Motor%20User%20Manual%20V1.2%202026-09-08.pdf)第7页；[H6215原厂教程](../../references/DM-H6215/说明书/DM-H6215轮毂电机使用教程V2.pdf)第1页。", "- 雅可比与虚功依据：[Modern Robotics 5.1.1](https://modernrobotics.northwestern.edu/nu-gm-book-resource/5-1-1-space-jacobian/)、[5.2](https://modernrobotics.northwestern.edu/nu-gm-book-resource/5-2-statics-of-open-chains/)。具体闭环公式按本版拓扑推导。", "", "本报告未修改MuJoCo模型、质量惯量、控制器或热模型；旧仿真结果不是V6实机运行或跳跃证明。"]
    (OUT / "MOTOR_LOAD.md").write_text("\n".join(lines) + "\n")
    mass_lines = ["# V6 质量预算", "", f'合计约 **{mass:.3f}kg**，工程估计{budget["indicative_range_kg"][0]:.2f}～{budget["indicative_range_kg"][1]:.2f}kg。', "", "| 类别 | kg |", "|---|---:|"]
    mass_lines += [f'| {key} | {value:.3f} |' for key, value in budget["by_material_kg"].items()]
    mass_lines += ["", "设备按厂商质量、金属和打印件按CAD名义体积计；另留200g未建模安装附件。质量区间是工程假设，不是统计置信区间。", "", "[逐项质量、重心和计算依据](mass_budget.json) · [电机负载报告](MOTOR_LOAD.md)"]
    (OUT / "MASS.md").write_text("\n".join(mass_lines) + "\n")


def plot():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    report = json.loads((OUT / "motor_load_analysis.json").read_text())
    rows = report["V5_same_height_same_method"]
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.6), constrained_layout=True)
    x = [row["height_mm"] for row in rows]
    axes[0].plot(x, [row["V5_knee_Nm"] for row in rows], "o--", label="V5 distributed gravity", color="#9096a0")
    axes[0].plot(x, [row["V6_knee_Nm"] for row in rows], "o-", label="V6 distributed gravity", color="#137b83")
    axes[0].axhline(3, color="#b26d26", linestyle=":", label="J4310 rated: 3 Nm")
    axes[0].set(xlabel="Hip-to-wheel distance (mm)", ylabel="Knee torque per side (Nm)",
                title=f'Gravity screening | V6 mass {report["mass_kg"]:.3f} kg')
    axes[0].legend(fontsize=9)
    selected = [row for row in report["takeoff_speed_scenarios"] if row["ideal_ballistic_rise_mm"] == 100]
    for key, label, color in (("knee_rpm", "Knee relative speed", "#7254a2"),
                              ("hip_rpm", "Hip speed", "#137b83")):
        axes[1].plot([row["takeoff_leg_length_mm"] for row in selected],
                     [row[key] for row in selected], "o-", label=label, color=color)
    axes[1].axhline(200, color="#bb483b", linestyle="--", label="24 V no-load limit: 200 rpm")
    axes[1].axhline(120, color="#b26d26", linestyle=":", label="Rated speed: 120 rpm")
    axes[1].set(xlabel="Takeoff hip-to-wheel distance (mm)", ylabel="Required motor speed (rpm)",
                title="Ideal 100 mm ballistic rise | torque-speed unverified")
    axes[1].legend(fontsize=9)
    for axis in axes:
        axis.grid(alpha=.2)
        axis.spines[["top", "right"]].set_visible(False)
    fig.suptitle("V6 130 / 105 / 45 mm | 24 V J4310 V1.1", fontsize=14)
    destination = OUT / "previews"
    destination.mkdir(exist_ok=True)
    fig.savefig(destination / "motor_load_comparison.png", dpi=170)
    fig.savefig(destination / "motor_load_comparison.svg")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--formula-only", action="store_true")
    group.add_argument("--plot-only", action="store_true")
    args = parser.parse_args()
    if args.plot_only:
        plot()
        return
    formulas = formula_tests()
    write_json("motor_formula_validation.json", formulas)
    if args.formula_only:
        print(json.dumps(formulas, indent=2))
        return
    path = OUT / "wheel_leg_v6.FCStd"
    if not path.exists():
        raise FileNotFoundError(f"Build V6 first: {path}; --formula-only is available without CAD")
    sys.path.insert(0, "/Applications/FreeCAD.app/Contents/Resources/lib")
    import FreeCAD as App
    import Part  # noqa: F401 - registers document shape properties
    doc = App.openDocument(str(path))
    try:
        params = doc.Parameters
        geometry = Geometry("V6 actual CAD", params.RodLength.Value / 1000,
                            params.LowerLength.Value / 1000, params.CrankLength.Value / 1000)
        if max(abs(geometry.upper - .13), abs(geometry.lower - .105), abs(geometry.crank - .045)) > 1e-9:
            raise ValueError("Unexpected V6 link dimensions; review reports before changing the selected proportion")
        nominal = params.LegLength.Value / 1000
        heights = sorted(set((.1, .12, .16, nominal, math.sqrt(2) * .13, .2, .215)))
        budget = read_mass_budget(doc, App)
        # The root build may save visibility and the vendor camera mesh after
        # exporting the physical Parts. Stable geometry-source hashes and
        # actual motion parameters identify this calculation without treating
        # a later view-only FCStd save as a different mechanical design.
        source_files = ("build_sleeved_robot.py", "build_printable_robot.py", "cad_v6_chassis.py",
                        "cad_v6_leg.py", "cad_v6_payload.py", "cad_v6_jetson_mount.py",
                        "cad_v5_coupling.py")
        budget["source_CAD"] = dict(file=path.name,
            geometry_source_sha256={name: hashlib.sha256((ROOT / "tools" / name).read_bytes()).hexdigest()
                                    for name in source_files},
            kinematic_parameters_mm=dict(OB=geometry.upper * 1000, BW=geometry.lower * 1000,
                                         OA=geometry.crank * 1000, nominal_hip_to_wheel=nominal * 1000),
            visual_save_note="Later addition of the official D435 Mesh::Feature and view changes does not add mass;75g is counted in the existing camera proxy once")
        native = native_validation(doc, App, budget, geometry, (.1, nominal, .215))
        report = analyze(budget, geometry, heights, nominal)
        report["native_validation"] = native
        report["formula_validation"] = formulas
        write_json("mass_budget.json", budget)
        write_json("motor_native_validation.json", native)
        write_json("motor_load_analysis.json", report)
        write_markdown(budget, report)
        print(json.dumps(dict(mass_kg=budget["total_kg"],
                              nominal=distributed_row(budget, geometry, nominal),
                              native_validation=native), indent=2))
    finally:
        App.closeDocument(doc.Name)


if __name__ == "__main__":
    main()
