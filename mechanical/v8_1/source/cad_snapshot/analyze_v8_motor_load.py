"""V8 CAD mass/load estimates with explicit, unweighed GK-HD screen scenarios.

Normal mode needs the completed wheel_leg_v8.FCStd and FreeCAD Python. The
opened CAD document is never saved. --formula-only needs no V8 CAD;
--plot-only needs matplotlib. V6/V7 sources and reports are read-only.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import sys

from analyze_v6_proportions import G, Geometry, RECOMMENDED
from analyze_v6_motor_load import distributed_row, native_validation, read_mass_budget
from analyze_v7_motor_load import balance_row, center_at_pose, formula_tests as prior_formula_tests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "mechanical/v8"
SCREEN_ESTIMATE_G = 200.0
SCREEN_SCENARIOS_G = (100.0, 200.0, 350.0)
NOMINAL_HEIGHT = 0.180
SCAN_HEIGHTS = tuple(mm / 1000 for mm in range(100, 216))
RATED_TORQUE = 3.0
WHEEL_RADIUS = 0.050
SOURCE_FILES = (
    "build_rounded_robot.py", "cad_v8_chassis.py", "cad_v8_payload.py",
    "cad_v8_display.py", "cad_v7_imu.py", "cad_v7_payload.py",
    "cad_v6_leg.py", "cad_v6_jetson_mount.py", "cad_v6_payload.py",
    "cad_v5_coupling.py", "build_printable_robot.py",
    "analyze_v8_motor_load.py", "analyze_v7_motor_load.py",
    "analyze_v6_motor_load.py", "analyze_v6_proportions.py",
)


def write_json(name, data):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def load_baseline(version):
    return json.loads((ROOT / "mechanical" / version / "mass_budget.json").read_text())


def find_screen_part(budget, requested=None):
    payloads = [row for row in budget["parts"] if row["material"] == "payload"]
    if requested:
        candidates = [row for row in payloads if row["part"] == requested]
    else:
        candidates = [row for row in payloads if any(
            token in row["part"].lower() for token in ("display", "screen", "lcd", "gk_hd", "gkhd"))]
    if len(candidates) != 1:
        raise ValueError("Expected one screen payload; use --screen-part to identify its CAD object")
    screen = candidates[0]
    if screen["role"] != "fixed" or abs(screen["mass_g"] - SCREEN_ESTIMATE_G) > 1e-6:
        raise ValueError("The V8 screen must be chassis-fixed with the explicit 200 g engineering estimate")
    return screen["part"]


def screen_scenario_budget(budget, screen_part, screen_mass_g):
    """Return an independent budget; change one mass, never CAD geometry."""
    result = deepcopy(budget)
    matches = [row for row in result["parts"] if row["part"] == screen_part]
    if len(matches) != 1 or screen_mass_g <= 0 or not math.isfinite(screen_mass_g):
        raise ValueError("Invalid screen mass scenario")
    matches[0]["mass_g"] = float(screen_mass_g)
    matches[0]["method"] = "Unweighed 5-inch GK-HD screen scenario; centre approximated by uniform CAD envelope"
    total_g = sum(row["mass_g"] for row in result["parts"])
    categories = {}
    for row in result["parts"]:
        key = row["material"]
        categories[key] = categories.get(key, 0.0) + row["mass_g"] / 1000
    result["total_kg"] = total_g / 1000
    result["by_material_kg"] = categories
    result["nominal_center_from_hip_mm"] = [
        sum(row["mass_g"] * row["center_mm"][axis] for row in result["parts"]) / total_g
        for axis in range(3)]
    result["assumed_screen_mass_g"] = screen_mass_g
    result["mass_status"] = "Estimate only: the selected screen mass is not supplied or measured"
    # The V6 reader's generic installation interval is not a screen interval.
    result.pop("indicative_range_kg", None)
    result.pop("range_method", None)
    return result


def version_summary(budget, geometry, heights=SCAN_HEIGHTS, nominal=NOMINAL_HEIGHT):
    rows = [distributed_row(budget, geometry, height) for height in heights]
    nominal_row = distributed_row(budget, geometry, nominal)
    maximum = max(rows, key=lambda row: row["knee_magnitude_Nm"])
    return dict(mass_kg=budget["total_kg"], nominal=nominal_row, worst_sample=maximum,
                nominal_rated_margin_Nm=RATED_TORQUE - nominal_row["knee_magnitude_Nm"],
                worst_sample_rated_margin_Nm=RATED_TORQUE - maximum["knee_magnitude_Nm"],
                nominal_with_25_percent_allowance_margin_Nm=RATED_TORQUE - nominal_row["knee_with_25_percent_allowance_Nm"],
                worst_with_25_percent_allowance_margin_Nm=RATED_TORQUE - maximum["knee_with_25_percent_allowance_Nm"],
                nominal_balance=balance_row(budget, geometry, nominal), rows=rows)


def formula_tests():
    result = prior_formula_tests()
    baseline = load_baseline("v7")
    previous = json.loads((ROOT / "mechanical/v7/motor_load_analysis.json").read_text())
    errors = []
    for old in previous["distributed_gravity"]["rows"]:
        measured = distributed_row(baseline, RECOMMENDED, old["leg_length_mm"] / 1000)
        errors.extend(abs(measured[key] - old[key])
                      for key in ("hip_gravity_Nm", "knee_gravity_Nm"))
    if max(errors) > 1e-6:
        raise ValueError("V7 same-method regression failed")
    synthetic = dict(parts=[
        dict(part="body", material="payload", mass_g=1000.0, role="fixed",
             center_mm=[0.0, 0.0, 0.0], local_center_mm=[0.0, 0.0, 0.0]),
        dict(part="screen", material="payload", mass_g=200.0, role="fixed",
             center_mm=[100.0, 0.0, 80.0], local_center_mm=[100.0, 0.0, 80.0])])
    original = deepcopy(synthetic)
    low = screen_scenario_budget(synthetic, "screen", 100.0)
    high = screen_scenario_budget(synthetic, "screen", 350.0)
    if synthetic != original:
        raise ValueError("Scenario calculation mutated the original budget")
    low_load = distributed_row(low, RECOMMENDED, NOMINAL_HEIGHT)
    high_load = distributed_row(high, RECOMMENDED, NOMINAL_HEIGHT)
    hip, knee, _ = RECOMMENDED.vertical(NOMINAL_HEIGHT)
    expected_delta = 0.250 * G * RECOMMENDED.jacobian(hip, knee)[1][1] / 2
    error = abs(high_load["knee_magnitude_Nm"] - low_load["knee_magnitude_Nm"] - expected_delta)
    centre = center_at_pose(high, RECOMMENDED, NOMINAL_HEIGHT)
    com_error = max(abs(centre[0] - 0.350 * 0.100 / 1.350),
                    abs(centre[2] - 0.350 * 0.080 / 1.350))
    if error > 1e-8 or com_error > 1e-12:
        raise ValueError("Independent mass sensitivity / barycentre test failed")
    result.update(V7_same_method_max_error_Nm=max(errors),
                  screen_mass_sensitivity_error_Nm=error,
                  screen_barycentre_error_m=com_error,
                  scenario_keeps_original_budget=True,
                  scope="Formula checks and read-only V6/V7 regressions; no V8 CAD is needed for these tests")
    return result


def analyze(budget, screen_part, geometry):
    current = version_summary(budget, geometry)
    comparisons = {version.upper(): version_summary(load_baseline(version), geometry)
                   for version in ("v6", "v7")}
    scenarios = []
    for mass_g in SCREEN_SCENARIOS_G:
        alternative = screen_scenario_budget(budget, screen_part, mass_g)
        summary = version_summary(alternative, geometry)
        summary.update(assumed_screen_mass_g=mass_g, mass_status="Unmeasured scenario",
                       COM_from_hip_delta_to_200g_mm=[a - b for a, b in zip(
                           summary["nominal_balance"]["COM_from_hip_mm"],
                           current["nominal_balance"]["COM_from_hip_mm"])])
        summary["COM_offset_rows"] = [balance_row(alternative, geometry, height, solve_level=False)
                                      for height in SCAN_HEIGHTS]
        scenarios.append(summary)
    mass = budget["total_kg"]
    hip, knee, _ = geometry.vertical(NOMINAL_HEIGHT)
    jac = geometry.jacobian(hip, knee)
    driving = []
    for acceleration in (0.0, 0.5, 1.0):
        force_x = mass * (acceleration + 0.02 * G) / 2
        wheel_torque = WHEEL_RADIUS * force_x
        driving.append(dict(acceleration_m_s2=acceleration, Crr_assumption=0.02,
                            wheel_torque_Nm=wheel_torque,
                            hip_absolute_sum_Nm=current["nominal"]["hip_magnitude_Nm"] + abs(jac[0][0] * force_x) + abs(wheel_torque),
                            knee_absolute_sum_Nm=current["nominal"]["knee_magnitude_Nm"] + abs(jac[1][0] * force_x) + abs(wheel_torque)))
    jumps = []
    for height in (0.160, NOMINAL_HEIGHT, 0.200, 0.215):
        metrics = geometry.pose_metrics(height, mass)
        speed = math.sqrt(2 * G * 0.100)
        jumps.append(dict(takeoff_leg_length_mm=height * 1000, ideal_ballistic_rise_mm=100,
                          knee_rpm=metrics["knee_rpm_for_1_m_s"] * speed,
                          hip_rpm=metrics["hip_rpm_for_1_m_s"] * speed))
    return dict(version="V8", mass_status="Engineering estimate, screen not weighed",
                assumed_screen_mass_g=SCREEN_ESTIMATE_G, screen_part=screen_part,
                screen_model="5-inch GK-HD, 122 x 78 x 14.5 mm; specification omits mass",
                mass_kg=mass, geometry_mm=dict(OB=130, AC=130, BW=105, OA=45, BC=45),
                saved_pose=dict(hip_to_wheel_mm=180, beta_deg=0),
                motor_specs=dict(J4310=dict(voltage_V=24, driver_version="V1.1", rated_Nm=3,
                                           peak_Nm=7, rated_rpm=120, no_load_rpm=200),
                                 H6215=dict(voltage_V=24, rated_Nm=1, peak_Nm=2)),
                nominal=current["nominal"], worst_sample=current["worst_sample"],
                selected_estimate=current, baseline_comparisons=comparisons,
                screen_mass_scenarios=scenarios, flat_driving=driving,
                takeoff_speed_scenarios=jumps,
                calculation_scope="Symmetric legs, wheels fixed to ground, chassis pitch constrained. Scan 100..215 mm in 1 mm steps is a force calculation, not a motion-clearance certificate.",
                limitations=["The selected screen has no supplied mass; 200 g and 100/350 g are engineering scenarios, not measurements or confidence bounds",
                             "The historical 265 g screen appears only in the read-only V7 baseline; it is not assigned to V8",
                             "Uniform CAD-envelope centres approximate unknown payload internal COM; scenario changes mass only, not its assumed centre",
                             "Screen fore/aft placement changes global pitch moment even when constrained hip gravity effort does not change",
                             "Balance angles are geometric estimates only and are not applied to legs, saved pose, MuJoCo or controls",
                             "No thermal, battery sag, torque-speed-duration, landing, free-balance or jumping verification",
                             "7 Nm peak and 200 rpm no-load cannot be assumed simultaneous"])


def write_reports(budget, report):
    selected = report["selected_estimate"]
    scenarios = report["screen_mass_scenarios"]
    balance = selected["nominal_balance"]
    mass_lines = ["# V8 质量估算与屏幕质量情景", "",
        f'**屏幕尚未称重。** 5寸GK-HD规格书只给出122×78×14.5mm，未给质量；暂按200g工程估计时，整机约 **{budget["total_kg"]:.3f}kg**。这不是实测定值。', "",
        "| 屏幕假定质量 g | 整机估算 kg |", "|---:|---:|"]
    mass_lines += [f'| {row["assumed_screen_mass_g"]:.0f} | {row["mass_kg"]:.3f} |' for row in scenarios]
    mass_lines += ["", "100～350g仅为屏幕质量敏感性情景，不是厂家公差或整机置信区间；其他零件误差、线材和附件误差仍存在。旧7寸屏265g只用于V7历史对比，不用于本版。", "",
                   "| 200g屏幕情景下类别 | kg |", "|---|---:|"]
    mass_lines += [f"| {key} | {value:.3f} |" for key, value in budget["by_material_kg"].items()]
    mass_lines += ["", "设备包括Jetson套件175g、D435 75g、电池400g、HI13R2按11g上界；另留200g未建模安装附件。打印件按完整CAD体积，设备重心按CAD包络均匀体积近似；显示网格不重复计质量。", "",
        f'200g屏幕情景下相对髋中心的整机重心XYZ约{balance["COM_from_hip_mm"][0]:.2f} / {balance["COM_from_hip_mm"][1]:.2f} / {balance["COM_from_hip_mm"][2]:.2f}mm；实称后应重算。', "",
        "[逐件估算](mass_budget.json) · [负载情景](MOTOR_LOAD.md) · [屏幕规格核对](source/display/READING.md)"]
    (OUT / "MASS.md").write_text("\n".join(mass_lines) + "\n")
    all_versions = {**report["baseline_comparisons"], "V8（屏幕200g暂估）": selected}
    lines = ["# V8 电机负载与重心估算", "",
        f'**以下V8主列采用未经称重的屏幕200g工程估计**，整机约{budget["total_kg"]:.3f}kg。24V V1.1 J4310按额定3N·m、峰值7N·m、额定120rpm、空载200rpm。', "",
        "腿部完全沿用130/105/45mm，保存姿态为髋轮距180mm、Beta=0°。配平角只计算、不应用到腿部装配、保存姿态、仿真或控制器。", "",
        "| 同方法比较 | 质量 kg | 名义每膝 N·m | 采样最大 N·m | 名义COM对接地线X mm |", "|---|---:|---:|---:|---:|"]
    for name, row in all_versions.items():
        lines.append(f'| {name} | {row["mass_kg"]:.3f} | {row["nominal"]["knee_magnitude_Nm"]:.3f} | {row["worst_sample"]["knee_magnitude_Nm"]:.3f} | {row["nominal_balance"]["COM_to_contact_x_mm"]:+.2f} |')
    lines += ["", "各版采用自己的CAD质量与重心，统一100～215mm、每1mm采样。质量列本身也是CAD和设备预算，不代表实机称重。", "",
        "## 屏幕质量敏感性", "",
        "| 屏幕 g（假定） | 整机 kg | 名义膝 N·m | 最大膝 N·m | 最大工况距3N·m余量 | 名义COM X mm |", "|---:|---:|---:|---:|---:|---:|"]
    for row in scenarios:
        lines.append(f'| {row["assumed_screen_mass_g"]:.0f} | {row["mass_kg"]:.3f} | {row["nominal"]["knee_magnitude_Nm"]:.3f} | {row["worst_sample"]["knee_magnitude_Nm"]:.3f} | {row["worst_sample_rated_margin_Nm"]:+.3f} | {row["nominal_balance"]["COM_to_contact_x_mm"]:+.2f} |')
    lines += ["", "本情景只改变实际CAD屏幕零件的质量，位置及内部均匀密度假设不变；完整XYZ重心、俯仰力矩与两种配平角均保存在JSON。", "",
        f'200g屏幕假设下，最大采样在{selected["worst_sample"]["leg_length_mm"]:.0f}mm。加25%示例留量后为 **{selected["worst_sample"]["knee_with_25_percent_allowance_Nm"]:.3f}N·m**，相对3N·m余量 **{selected["worst_with_25_percent_allowance_margin_Nm"]:+.3f}N·m**。留量不替代热验证。', "",
        "## 重心与俯仰", "",
        f'200g情景：重心距地面约{balance["COM_height_above_ground_mm"]:.1f}mm；对轮接地线前后偏差 **{balance["COM_to_contact_x_mm"]:+.2f}mm**，整体重力俯仰力矩 **{balance["gravity_pitch_moment_about_contact_Nm"]:+.3f}N·m**（正值前侧下俯）。', ""]
    beta = balance["level_chassis_leg_beta_candidate"]["angle_deg"]
    beta_text = f"{beta:+.2f}°" if beta is not None else "±30°搜索内无解"
    lines += [f'理想锁定关节、绕轮轴配平角 **{balance["locked_shape_balance_lean_deg"]:+.2f}°**（正值上部后倾）；机身保持水平时的两腿Beta几何候选 **{beta_text}**（正值轮心前移）。均未应用，不是动态稳定或该姿态无干涉的证明。', "",
        "静力矩以U=Σmi·g·(zi−zW)求势能导数并均分左右，同时固定机身俯仰。因此固定载荷前移可能不改变约束髋力矩，却改变全机MgΔx；不能用髋力矩小判定无需配平。", "",
        "## 200g屏幕情景的平地行驶筛查", "",
        "| 加速度 m/s² | 髋 N·m/侧 | 膝 N·m/侧 | 轮 N·m/侧 |", "|---:|---:|---:|---:|"]
    for row in report["flat_driving"]:
        lines.append(f'| {row["acceleration_m_s2"]:.1f} | {row["hip_absolute_sum_Nm"]:.3f} | {row["knee_absolute_sum_Nm"]:.3f} | {row["wheel_torque_Nm"]:.3f} |')
    lines += ["", "名义姿态、滚阻0.02；不利方向叠加水平力雅可比项和轮壳反力矩，未含轮/杆惯性及姿态纠偏峰值。", "",
        "腿几何未变：100mm理想抛升在180mm离地需膝178.8rpm，在200mm离地需218.5rpm，后者超过200rpm空载。实际推蹬与落地载荷仍取决于屏幕实重和转矩—转速—时间曲线，当前不能确认跳跃。", "",
        f'FreeCAD原生表达式校验最大重心误差{report["native_validation"]["maximum_COM_error_mm"]:.3g}mm，重力力矩误差{report["native_validation"]["maximum_gravity_effort_error_Nm"]:.3g}N·m；该校验不包含动态平衡。', "",
        "[全部数据](motor_load_analysis.json) · [质量来源与估算](MASS.md) · [原生校验](motor_native_validation.json)。虚功依据：[Modern Robotics 5.2](https://modernrobotics.northwestern.edu/nu-gm-book-resource/5-2-statics-of-open-chains/)。"]
    (OUT / "MOTOR_LOAD.md").write_text("\n".join(lines) + "\n")


def plot():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    report = json.loads((OUT / "motor_load_analysis.json").read_text())
    scenarios = report["screen_mass_scenarios"]
    x = [row["leg_length_mm"] for row in report["selected_estimate"]["rows"]]
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.7), constrained_layout=True)
    for version, colour in (("V6", "#aab0b7"), ("V7", "#72569b")):
        axes[0].plot(x, [row["knee_magnitude_Nm"] for row in report["baseline_comparisons"][version]["rows"]],
                     "--", label=version, color=colour)
    axes[0].fill_between(x, [row["knee_magnitude_Nm"] for row in scenarios[0]["rows"]],
                        [row["knee_magnitude_Nm"] for row in scenarios[-1]["rows"]],
                        color="#147d86", alpha=0.18, label="V8 screen 100–350 g scenario")
    axes[0].plot(x, [row["knee_magnitude_Nm"] for row in report["selected_estimate"]["rows"]],
                 color="#147d86", label="V8 screen assumed 200 g")
    axes[0].axhline(3, color="#b16c24", linestyle=":", label="Rated 3 Nm")
    axes[0].set(xlabel="Hip-to-wheel distance (mm)", ylabel="Knee torque per side (Nm)", title="Chassis pitch constrained")
    for row, style, colour in zip(scenarios, ("--", "-", ":"), ("#7b9295", "#147d86", "#78589b")):
        axes[1].plot(x, [entry["COM_to_contact_x_mm"] for entry in row["COM_offset_rows"]],
                     style, color=colour, label=f'Screen assumed {row["assumed_screen_mass_g"]:.0f} g')
    axes[1].axhline(0, color="#aaaaaa", linestyle=":")
    axes[1].set(xlabel="Hip-to-wheel distance (mm)", ylabel="Forward COM offset from contact (mm)",
                title="Unweighed screen mass sensitivity")
    for axis in axes:
        axis.grid(alpha=0.2)
        axis.legend(fontsize=8)
        axis.spines[["top", "right"]].set_visible(False)
    fig.suptitle(f'V8 mass estimate {report["mass_kg"]:.3f} kg at assumed screen 200 g | legs unchanged')
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
    parser.add_argument("--screen-part", help="Exact screen payload CAD object name if automatic identification is ambiguous")
    args = parser.parse_args()
    if args.plot_only:
        plot()
        return
    tests = formula_tests()
    write_json("motor_formula_validation.json", tests)
    if args.formula_only:
        print(json.dumps(tests, indent=2))
        return
    path = OUT / "wheel_leg_v8.FCStd"
    if not path.exists():
        raise FileNotFoundError(f"Wait for completed V8 CAD: {path}; --formula-only works without it")
    hashes = {name: hashlib.sha256((ROOT / "tools" / name).read_bytes()).hexdigest()
              for name in SOURCE_FILES}
    sys.path.insert(0, "/Applications/FreeCAD.app/Contents/Resources/lib")
    import FreeCAD as App
    import Part  # noqa: F401 - registers native shape properties
    doc = App.openDocument(str(path))
    try:
        p = doc.Parameters
        geometry = Geometry("V8 unchanged leg geometry", p.RodLength.Value / 1000,
                            p.LowerLength.Value / 1000, p.CrankLength.Value / 1000)
        if max(abs(geometry.upper - 0.130), abs(geometry.lower - 0.105),
               abs(geometry.crank - 0.045), abs(p.LegLength.Value / 1000 - NOMINAL_HEIGHT),
               abs(p.Beta.Value)) > 1e-9:
            raise ValueError("Unexpected V8 leg dimensions or pose; required 130/105/45,180 mm and Beta0")
        actual = read_mass_budget(doc, App)
        screen_part = find_screen_part(actual, args.screen_part)
        budget = screen_scenario_budget(actual, screen_part, SCREEN_ESTIMATE_G)
        payloads = [row for row in budget["parts"] if row["material"] == "payload"]
        for expected in (SCREEN_ESTIMATE_G, 11.0, 175.0, 75.0, 400.0):
            if sum(abs(row["mass_g"] - expected) < 1e-6 for row in payloads) != 1:
                raise ValueError(f"Expected exactly one payload budget of {expected} g")
        budget["notes"] = ["Actual V8 CAD volumes; GK-HD screen mass remains an unweighed engineering estimate",
            "Screen scenario values are 100/200/350 g; not manufacturer limits or statistical bounds",
            "The former V7 screen mass of 265 g is not used for V8",
            "Payload and motor centres are uniform CAD-envelope approximations",
            "PETG mass uses full nominal solid volume; compare with eventual slicer estimate and physical weighing",
            "Includes 200 g installation allowance at hip-frame [0,0,5] mm; distinct from screen mass",
            "Visual meshes have no added mass; D435 is counted once by its 75 g proxy"]
        budget["source_CAD"] = dict(file=path.name, geometry_source_sha256=hashes,
            kinematic_parameters_mm=dict(OB=130, BW=105, OA=45, nominal_hip_to_wheel=180, beta_deg=0),
            baseline_mass_budget_sha256={version: hashlib.sha256((ROOT / "mechanical" / version / "mass_budget.json").read_bytes()).hexdigest() for version in ("v6", "v7")},
            display_specification_sha256=hashlib.sha256((OUT / "source/display/显示器规格书.pdf").read_bytes()).hexdigest(),
            visual_save_note="Later visibility changes or vendor-mesh insertion do not alter counted part masses")
        native = native_validation(doc, App, budget, geometry, (0.100, NOMINAL_HEIGHT, 0.215))
        report = analyze(budget, screen_part, geometry)
        report["native_validation"] = native
        report["formula_validation"] = tests
        budget["screen_mass_scenario_total_range_kg"] = [report["screen_mass_scenarios"][index]["mass_kg"] for index in (0, -1)]
        write_json("mass_budget.json", budget)
        write_json("motor_native_validation.json", native)
        write_json("motor_load_analysis.json", report)
        write_reports(budget, report)
        print(json.dumps(dict(mass_estimate_kg=budget["total_kg"], screen_assumed_g=SCREEN_ESTIMATE_G,
                              nominal=report["nominal"], worst_sample=report["worst_sample"],
                              balance=report["selected_estimate"]["nominal_balance"]), ensure_ascii=False, indent=2))
    finally:
        App.closeDocument(doc.Name)


if __name__ == "__main__":
    main()
