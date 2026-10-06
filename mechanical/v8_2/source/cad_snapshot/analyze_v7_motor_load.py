"""V7 CAD mass, constrained joint loads and sagittal balance screening.

Run with FreeCAD Python only after wheel_leg_v7.FCStd is complete. The opened
document is never saved. --formula-only needs no V7 CAD; --plot-only needs
matplotlib. All outputs go to mechanical/v7; V6 is a read-only baseline.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

from analyze_v6_proportions import G, Geometry, RECOMMENDED, validate
from analyze_v6_motor_load import (
    distributed_row, native_validation, read_mass_budget, transformed_center,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "mechanical/v7"
BASELINE = ROOT / "mechanical/v6"
RATED_TORQUE = 3.0
PEAK_TORQUE = 7.0
WHEEL_RADIUS = 0.050
NOMINAL_HEIGHT = 0.180
SCAN_HEIGHTS = tuple(mm / 1000 for mm in range(100, 216))
SOURCE_FILES = (
    "build_faceted_robot.py", "cad_v7_chassis.py", "cad_v7_payload.py",
    "cad_v7_display.py", "cad_v7_imu.py", "cad_v6_leg.py",
    "cad_v6_jetson_mount.py", "cad_v5_coupling.py", "build_printable_robot.py",
    "analyze_v7_motor_load.py", "analyze_v6_motor_load.py",
    "analyze_v6_proportions.py",
)


def write_json(name, data):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def load_baseline():
    return json.loads((BASELINE / "mass_budget.json").read_text())


def center_at_pose(budget, geometry, height, beta=0.0):
    """Mass-weighted actual-CAD centres in metres from the hip frame."""
    hip, knee, _ = geometry.vertical(height)
    weighted = [0.0, 0.0, 0.0]
    total_g = sum(row["mass_g"] for row in budget["parts"])
    for row in budget["parts"]:
        point = transformed_center(row, geometry, hip + beta, knee)
        for axis in range(3):
            weighted[axis] += row["mass_g"] * point[axis]
    return tuple(value / total_g for value in weighted)


def level_body_offset(budget, geometry, height, beta):
    hip, knee, _ = geometry.vertical(height)
    wheel_x, _ = geometry.forward(hip + beta, knee)
    return center_at_pose(budget, geometry, height, beta)[0] - wheel_x


def level_body_balance_angle(budget, geometry, height, bound_deg=30.0):
    """Nearest root of COM_x - wheel_x with chassis pitch held at zero.

    Beta tilts both legs, not the body. This is a static geometric candidate;
    the searched range is not a certified collision-free operating range.
    """
    roots = []
    previous = math.radians(-bound_deg)
    previous_value = level_body_offset(budget, geometry, height, previous)
    for index in range(1, 241):
        current = math.radians(-bound_deg + 2 * bound_deg * index / 240)
        value = level_body_offset(budget, geometry, height, current)
        if abs(previous_value) < 1e-12:
            roots.append(previous)
        elif previous_value * value < 0:
            lo, hi, flo = previous, current, previous_value
            for _ in range(45):
                mid = (lo + hi) / 2
                fm = level_body_offset(budget, geometry, height, mid)
                if flo * fm <= 0:
                    hi = mid
                else:
                    lo, flo = mid, fm
            roots.append((lo + hi) / 2)
        if abs(value) < 1e-12:
            roots.append(current)
        previous, previous_value = current, value
    if not roots:
        return dict(angle_deg=None, search_bound_deg=bound_deg,
                    note="No root within the geometric search range")
    root = min(roots, key=abs)
    hip, knee, _ = geometry.vertical(height)
    wheel = geometry.forward(hip + root, knee)
    return dict(angle_deg=math.degrees(root), search_bound_deg=bound_deg,
                residual_COM_to_contact_x_mm=1000 * level_body_offset(
                    budget, geometry, height, root),
                wheel_x_from_hip_mm=1000 * wheel[0],
                hip_height_above_axle_mm=-1000 * wheel[1],
                sign_convention="Positive Beta moves the wheel forwards (+X) relative to the level chassis",
                note="Static geometric balance candidate only; no collision, actuator, friction or control validation at this Beta")


def balance_row(budget, geometry, height, solve_level=True):
    center = center_at_pose(budget, geometry, height)
    hip, knee, _ = geometry.vertical(height)
    wheel_x, wheel_z = geometry.forward(hip, knee)
    dx, z_axle = center[0] - wheel_x, center[2] - wheel_z
    mass = sum(row["mass_g"] for row in budget["parts"]) / 1000
    # Circular wheels retain axle height. The simple locked-shape lean is
    # about their common axle, so the denominator excludes wheel radius.
    lean = math.atan2(dx, z_axle)
    result = dict(height_mm=1000 * height,
                  COM_from_hip_mm=[1000 * coordinate for coordinate in center],
                  COM_to_contact_x_mm=1000 * dx,
                  COM_height_above_ground_mm=1000 * (z_axle + WHEEL_RADIUS),
                  COM_height_above_axle_mm=1000 * z_axle,
                  gravity_pitch_moment_about_contact_Nm=mass * G * dx,
                  locked_shape_balance_lean_deg=math.degrees(lean),
                  locked_shape_lean_residual_x_mm=1000 * (dx * math.cos(lean) - z_axle * math.sin(lean)),
                  lean_sign_convention="Positive lean moves points above the axle towards -X (nose up); x'=x*cos(theta)-z*sin(theta)")
    if solve_level:
        result["level_chassis_leg_beta_candidate"] = level_body_balance_angle(budget, geometry, height)
    return result


def fixed_mass_sensitivity(baseline):
    rows = []
    for height in (0.100, NOMINAL_HEIGHT, 0.215):
        old = distributed_row(baseline, RECOMMENDED, height)
        h, k, _ = RECOMMENDED.vertical(height)
        per_kg = G * RECOMMENDED.jacobian(h, k)[1][1] / 2
        for extra in (0.3, 0.6):
            torque = old["knee_magnitude_Nm"] + extra * per_kg
            rows.append(dict(height_mm=height * 1000, added_fixed_mass_kg=extra,
                             added_knee_torque_Nm=extra * per_kg,
                             resulting_knee_torque_Nm=torque,
                             rated_margin_Nm=RATED_TORQUE - torque,
                             torque_with_25_percent_allowance_Nm=1.25 * torque))
    return dict(rows=rows, scope="V6 plus added chassis-fixed mass only, with chassis pitch constrained; not the actual V7 mass or free balance result")


def formula_tests():
    result = validate([RECOMMENDED])
    baseline = load_baseline()
    prior = json.loads((BASELINE / "motor_load_analysis.json").read_text())
    errors = []
    for old in prior["distributed_gravity"]["rows"]:
        measured = distributed_row(baseline, RECOMMENDED, old["leg_length_mm"] / 1000)
        errors.extend(abs(measured[key] - old[key])
                      for key in ("hip_gravity_Nm", "knee_gravity_Nm"))
    if max(errors) > 1e-6:
        raise ValueError("Read-only V6 gravity regression failed")
    result["V6_same_method_max_error_Nm"] = max(errors)
    synthetic = dict(parts=[dict(part="test_payload", mass_g=1000.0,
                                local_center_mm=[40.0, 0.0, 80.0], role="fixed")])
    balance = balance_row(synthetic, RECOMMENDED, NOMINAL_HEIGHT)
    expected_beta = math.degrees(math.asin(0.04 / NOMINAL_HEIGHT))
    expected_lean = math.degrees(math.atan2(0.04, NOMINAL_HEIGHT + 0.08))
    beta_error = abs(balance["level_chassis_leg_beta_candidate"]["angle_deg"] - expected_beta)
    lean_error = abs(balance["locked_shape_balance_lean_deg"] - expected_lean)
    if max(beta_error, lean_error) > 1e-8:
        raise ValueError("Analytical point-payload balance test failed")
    # Moving a fixed payload fore/aft leaves constrained joint gravity
    # unchanged while changing total-body pitch moment by m*g*delta_x.
    other = dict(parts=[dict(synthetic["parts"][0], local_center_mm=[-40.0, 0.0, 80.0])])
    first = distributed_row(synthetic, RECOMMENDED, NOMINAL_HEIGHT)
    second = distributed_row(other, RECOMMENDED, NOMINAL_HEIGHT)
    joint_error = max(abs(first[key] - second[key])
                      for key in ("hip_gravity_Nm", "knee_gravity_Nm"))
    moment_delta = balance["gravity_pitch_moment_about_contact_Nm"] - balance_row(
        other, RECOMMENDED, NOMINAL_HEIGHT, solve_level=False)["gravity_pitch_moment_about_contact_Nm"]
    if joint_error > 1e-8 or abs(moment_delta - G * 0.08) > 1e-10:
        raise ValueError("Constrained pitch / global balance distinction failed")
    result.update(point_payload_beta_error_deg=beta_error, point_payload_lean_error_deg=lean_error,
                  fixed_payload_fore_aft_joint_effort_change_Nm=joint_error,
                  fixed_payload_fore_aft_global_pitch_moment_change_Nm=moment_delta,
                  scope="Formula validation and V6 regression only; no V7 CAD has been read")
    return result


def analyze(budget, baseline, geometry, heights, nominal):
    current = [distributed_row(budget, geometry, height) for height in heights]
    previous = [distributed_row(baseline, geometry, height) for height in heights]
    nominal_v7 = distributed_row(budget, geometry, nominal)
    nominal_v6 = distributed_row(baseline, geometry, nominal)
    balance_v7 = balance_row(budget, geometry, nominal)
    balance_v6 = balance_row(baseline, geometry, nominal)
    balance_scan = [balance_row(budget, geometry, height, solve_level=False) for height in heights]
    mass = budget["total_kg"]
    hip, knee, _ = geometry.vertical(nominal)
    jac = geometry.jacobian(hip, knee)
    driving = []
    for acceleration in (0.0, 0.5, 1.0):
        force_x = mass * (acceleration + 0.02 * G) / 2
        wheel_torque = WHEEL_RADIUS * force_x
        driving.append(dict(acceleration_m_s2=acceleration, Crr_assumption=0.02,
                            wheel_torque_Nm=wheel_torque,
                            hip_absolute_sum_Nm=nominal_v7["hip_magnitude_Nm"] + abs(jac[0][0] * force_x) + abs(wheel_torque),
                            knee_absolute_sum_Nm=nominal_v7["knee_magnitude_Nm"] + abs(jac[1][0] * force_x) + abs(wheel_torque)))
    jump = []
    for height in (0.160, nominal, 0.200, 0.215):
        metrics = geometry.pose_metrics(height, mass)
        speed = math.sqrt(2 * G * 0.100)
        knee_rpm = metrics["knee_rpm_for_1_m_s"] * speed
        hip_rpm = metrics["hip_rpm_for_1_m_s"] * speed
        jump.append(dict(takeoff_leg_length_mm=height * 1000, ideal_ballistic_rise_mm=100,
                         knee_rpm=knee_rpm, hip_rpm=hip_rpm,
                         exceeds_200rpm_no_load=max(knee_rpm, hip_rpm) > 200))
    return dict(version="V7", geometry_mm=dict(OB=130, AC=130, BW=105, OA=45, BC=45),
                nominal_leg_length_mm=nominal * 1000, mass_kg=mass,
                motor_specs=dict(J4310=dict(voltage_V=24, driver_version="V1.1", rated_Nm=3,
                                           peak_Nm=7, rated_rpm=120, no_load_rpm=200),
                                 H6215=dict(voltage_V=24, rated_Nm=1, peak_Nm=2)),
                nominal=nominal_v7, worst_sample=max(current, key=lambda row: row["knee_magnitude_Nm"]),
                distributed_gravity=dict(rows=current, scan_step_mm=1,
                    constraint="Ground-fixed wheels; left/right coordinates varied together; fixed chassis pitch. Joint efforts omit the external pitch-constraint reaction and are not proof of free balance."),
                V6_comparison=dict(mass_kg=baseline["total_kg"], mass_delta_kg=mass - baseline["total_kg"],
                    nominal=nominal_v6, worst_sample=max(previous, key=lambda row: row["knee_magnitude_Nm"]),
                    nominal_balance=balance_v6,
                    COM_from_hip_delta_mm=[a - b for a, b in zip(balance_v7["COM_from_hip_mm"], balance_v6["COM_from_hip_mm"])],
                    same_height_rows=[dict(height_mm=a["leg_length_mm"], V7_knee_Nm=a["knee_magnitude_Nm"],
                                           V6_knee_Nm=b["knee_magnitude_Nm"]) for a, b in zip(current, previous)]),
                sagittal_balance=dict(nominal=balance_v7, rows=balance_scan,
                    assumptions="Circular wheels on level ground; contact points share the axle X. COM estimates use uniform CAD mass distribution. The locked-shape lean rotates geometry about the wheel axle; the level-body Beta candidate instead changes both hip angles. Neither is dynamic stability or collision validation."),
                flat_driving=driving, takeoff_speed_scenarios=jump,
                limitations=["Actual forward screen placement affects global pitch moment even when constrained hip effort changes little",
                             "Balance angles are reported estimates only; no changes are applied to leg geometry, saved joint pose, MuJoCo or control parameters",
                             "Motor mass is supplied mass with approximate CAD-volume centre; equipment internal COM is unknown",
                             "HI13R2 uses the 11 g upper mass bound, not a measurement; LCD assembly uses 265 g",
                             "No full torque-speed-duration, thermal, battery-sag, free-balance, landing or jump validation",
                             "200 rpm no-load and 7 Nm peak cannot be assumed simultaneous",
                             "Scan range is a force calculation; use the separate CAD interference report to determine permitted motion"])


def write_reports(budget, report):
    nominal, worst = report["nominal"], report["worst_sample"]
    old = report["V6_comparison"]
    balance = report["sagittal_balance"]["nominal"]
    beta = balance["level_chassis_leg_beta_candidate"]["angle_deg"]
    beta_text = f"{beta:.2f}°" if beta is not None else "±30°搜索内无解"
    mass_lines = ["# V7 质量预算", "",
                  f'CAD与设备预算 **{budget["total_kg"]:.3f} kg**；较V6 {old["mass_delta_kg"]:+.3f} kg。', "",
                  "| 类别 | kg |", "|---|---:|"]
    mass_lines += [f"| {key} | {value:.3f} |" for key, value in budget["by_material_kg"].items()]
    mass_lines += ["", "屏幕总成265g；HI13R2按11g上界；Jetson套件175g、D435 75g、电池400g；另有200g安装附件预算。显示网格不重复计质量。设备重心按CAD均匀体积近似，打印件按完整CAD体积估算。", "",
                   f'名义姿态相对髋中心的整机重心XYZ：{balance["COM_from_hip_mm"][0]:.2f} / {balance["COM_from_hip_mm"][1]:.2f} / {balance["COM_from_hip_mm"][2]:.2f} mm。', "",
                   "[逐件质量与重心](mass_budget.json) · [负载与配平估算](MOTOR_LOAD.md)"]
    (OUT / "MASS.md").write_text("\n".join(mass_lines) + "\n")
    lines = ["# V7 电机负载与重心初算", "",
             f'整机约 **{budget["total_kg"]:.3f} kg**。24V V1.1 J4310按额定3N·m、峰值7N·m、额定120rpm、空载200rpm；腿长130/105/45mm，名义髋轮距180mm。', "",
             "| 同方法比较 | V6 | V7 |", "|---|---:|---:|",
             f'| 质量 kg | {old["mass_kg"]:.3f} | {budget["total_kg"]:.3f} |',
             f'| 名义每膝静力矩 N·m | {old["nominal"]["knee_magnitude_Nm"]:.3f} | {nominal["knee_magnitude_Nm"]:.3f} |',
             f'| 100～215mm每1mm采样最大 N·m | {old["worst_sample"]["knee_magnitude_Nm"]:.3f} | {worst["knee_magnitude_Nm"]:.3f} |',
             f'| 名义COM相对接地点X偏差 mm | {old["nominal_balance"]["COM_to_contact_x_mm"]:.2f} | {balance["COM_to_contact_x_mm"]:.2f} |', "",
             f'V7最大采样在{worst["leg_length_mm"]:.0f}mm；加25%示例留量后为 **{worst["knee_with_25_percent_allowance_Nm"]:.3f}N·m**。此留量不代替电机热验证。', "",
             "## 前置屏幕与俯仰配平", "",
             f'名义COM距地面约{balance["COM_height_above_ground_mm"]:.1f}mm，接地点X偏差 **{balance["COM_to_contact_x_mm"]:+.2f}mm**；重力产生的全机俯仰力矩约 **{balance["gravity_pitch_moment_about_contact_Nm"]:+.3f}N·m**（正值使前侧下俯）。', "",
             f'锁定腿部形态、绕轮轴倾斜的理想配平角约 **{balance["locked_shape_balance_lean_deg"]:+.2f}°**（正值为上部向后、前端抬起）。若保持机身水平，则两腿Beta几何配平候选为 **{beta_text}**（正值使轮心前移）；该候选姿态尚需独立干涉和控制验证。', "",
             "以上角度只将重心投影移到理想轮端支承线上，是不稳定平衡位置的几何估算，不能证明动态稳定。轮轴倾角使用重心距轮轴高度；不把轮胎半径误加到该分母。", "",
             "**腿部结构与参数保持不变。上述配平角仅供评估，本次没有将其应用到腿部装配、保存姿态、MuJoCo模型或控制器。**", "",
             "关节静力矩采用U=Σmi·g·(zi−zW)、τ=(∂U/∂q)/2，并**固定机身俯仰**。前后移动同一机身载荷可不改变该约束下的髋静力矩，却改变整体Mg·Δx俯仰力矩。因此不能以髋力矩很小认定前置屏幕无需配平。", "",
             "## 名义平地行驶筛查", "", "| 加速度 m/s² | 髋 N·m/侧 | 膝 N·m/侧 | 轮 N·m/侧 |", "|---:|---:|---:|---:|"]
    for row in report["flat_driving"]:
        lines.append(f'| {row["acceleration_m_s2"]:.1f} | {row["hip_absolute_sum_Nm"]:.3f} | {row["knee_absolute_sum_Nm"]:.3f} | {row["wheel_torque_Nm"]:.3f} |')
    lines += ["", "假定滚阻系数0.02，重力项叠加水平力雅可比项和CW上的轮电机外壳反力矩的绝对和；未包含轮/杆转动惯量及平衡控制峰值。", "",
              "## 跳跃限制", "", "| 100mm理想跳高的离地髋轮距 mm | 膝 rpm | 髋 rpm |", "|---:|---:|---:|"]
    for row in report["takeoff_speed_scenarios"]:
        lines.append(f'| {row["takeoff_leg_length_mm"]:.0f} | {row["knee_rpm"]:.1f} | {row["hip_rpm"]:.1f} |')
    lines += ["", "几何不变，所以同高度的跳跃转速要求与V6一致；新增质量提高推蹬与落地载荷。低于200rpm空载不代表该速度有足够转矩，当前不能确认跳跃能力。", "",
              f'FreeCAD原生表达式与独立模型最大重心误差{report["native_validation"]["maximum_COM_error_mm"]:.3g}mm、重力力矩误差{report["native_validation"]["maximum_gravity_effort_error_Nm"]:.3g}N·m。该校验不是运动干涉或自由平衡验证。', "",
              "[全部数据](motor_load_analysis.json) · [质量](MASS.md) · [原生公式校验](motor_native_validation.json)。虚功/雅可比依据：[Modern Robotics 5.2](https://modernrobotics.northwestern.edu/nu-gm-book-resource/5-2-statics-of-open-chains/)。本报告未更新MuJoCo控制器、惯量或热模型。"]
    (OUT / "MOTOR_LOAD.md").write_text("\n".join(lines) + "\n")


def plot():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    report = json.loads((OUT / "motor_load_analysis.json").read_text())
    rows = report["V6_comparison"]["same_height_rows"]
    fig, axes = plt.subplots(1, 2, figsize=(12.0, 4.5), constrained_layout=True)
    x = [row["height_mm"] for row in rows]
    axes[0].plot(x, [row["V6_knee_Nm"] for row in rows], "--", label="V6", color="#9298a0")
    axes[0].plot(x, [row["V7_knee_Nm"] for row in rows], label="V7", color="#147d86")
    axes[0].axhline(3, linestyle=":", color="#b16c24", label="Rated 3 Nm")
    axes[0].set(xlabel="Hip-to-wheel distance (mm)", ylabel="Knee torque per side (Nm)",
                title="Constrained gravity, chassis pitch fixed")
    balance = report["sagittal_balance"]["rows"]
    axes[1].plot(x, [row["COM_to_contact_x_mm"] for row in balance], color="#7655a2", label="V7 COM - contact X")
    axes[1].axhline(0, linestyle=":", color="#888888", label="Ideal support line")
    axes[1].set(xlabel="Hip-to-wheel distance (mm)", ylabel="Forward COM offset (mm)",
                title="Level chassis, wheel directly below hip")
    for axis in axes:
        axis.grid(alpha=0.2)
        axis.legend(fontsize=9)
        axis.spines[["top", "right"]].set_visible(False)
    fig.suptitle(f'V7 {report["mass_kg"]:.3f} kg | 24 V J4310 V1.1 | static screening')
    destination = OUT / "previews"
    destination.mkdir(parents=True, exist_ok=True)
    fig.savefig(destination / "motor_load_comparison.png", dpi=170)
    fig.savefig(destination / "motor_load_comparison.svg")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--formula-only", action="store_true")
    mode.add_argument("--plot-only", action="store_true")
    args = parser.parse_args()
    if args.plot_only:
        plot()
        return
    tests = formula_tests()
    write_json("motor_formula_validation.json", tests)
    baseline = load_baseline()
    write_json("fixed_mass_sensitivity.json", fixed_mass_sensitivity(baseline))
    if args.formula_only:
        print(json.dumps(tests, indent=2))
        return
    path = OUT / "wheel_leg_v7.FCStd"
    if not path.exists():
        raise FileNotFoundError(f"Build final V7 first: {path}; use --formula-only during preparation")
    source_hashes = {name: hashlib.sha256((ROOT / "tools" / name).read_bytes()).hexdigest()
                     for name in SOURCE_FILES}
    sys.path.insert(0, "/Applications/FreeCAD.app/Contents/Resources/lib")
    import FreeCAD as App
    import Part  # noqa: F401 - registers native shape properties
    doc = App.openDocument(str(path))
    try:
        p = doc.Parameters
        geometry = Geometry("V7 actual CAD", p.RodLength.Value / 1000,
                            p.LowerLength.Value / 1000, p.CrankLength.Value / 1000)
        nominal = p.LegLength.Value / 1000
        if max(abs(geometry.upper - 0.130), abs(geometry.lower - 0.105),
               abs(geometry.crank - 0.045), abs(nominal - NOMINAL_HEIGHT), abs(p.Beta.Value)) > 1e-9:
            raise ValueError("Unexpected V7 link dimensions or saved pose; review the configured baseline")
        budget = read_mass_budget(doc, App)
        payloads = [row for row in budget["parts"] if row["material"] == "payload"]
        for expected in (265.0, 11.0, 175.0, 75.0, 400.0):
            if sum(abs(row["mass_g"] - expected) < 1e-6 for row in payloads) != 1:
                raise ValueError(f"Expected exactly one V7 payload budget of {expected} g")
        budget["notes"] = ["V7 actual CAD volume and BudgetMassGrams, not a V6 mass projection",
            "PETG uses full CAD solid volume; actual slicer mass may differ",
            "Motor and payload centres assume uniform CAD-volume density; internal real COM is unknown",
            "HI13R2 mass is the 11 g upper bound, screen assembly mass is 265 g",
            "Display-only Mesh::Feature objects are not counted; D435 has a single 75 g proxy",
            "Includes 200 g unmodelled installation allowance at hip-frame [0,0,5] mm"]
        budget["source_CAD"] = dict(file=path.name, geometry_source_sha256=source_hashes,
            kinematic_parameters_mm=dict(OB=130, BW=105, OA=45, nominal_hip_to_wheel=nominal * 1000),
            V6_baseline_mass_budget_sha256=hashlib.sha256((BASELINE / "mass_budget.json").read_bytes()).hexdigest(),
            visual_save_note="Subsequent visibility/view-only saves do not change geometry-source identity")
        native = native_validation(doc, App, budget, geometry, (0.100, nominal, 0.215))
        report = analyze(budget, baseline, geometry, SCAN_HEIGHTS, nominal)
        report["native_validation"] = native
        report["formula_validation"] = tests
        write_json("mass_budget.json", budget)
        write_json("motor_native_validation.json", native)
        write_json("motor_load_analysis.json", report)
        write_reports(budget, report)
        print(json.dumps(dict(mass_kg=budget["total_kg"], nominal=report["nominal"],
                              worst_sample=report["worst_sample"],
                              balance=report["sagittal_balance"]["nominal"]), ensure_ascii=False, indent=2))
    finally:
        App.closeDocument(doc.Name)


if __name__ == "__main__":
    main()
