"""V8.1 read-only mass, constrained motor-load and battery-power screening.

Run after the updated V8.1 native CAD and manifest have finished exporting.
The source document is opened, recomputed for verification, and never saved.
Only reports inside mechanical/v8_1 are written; earlier versions are read-only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import analyze_v8_motor_load as prior
from analyze_v6_motor_load import native_validation, read_mass_budget
from analyze_v6_proportions import G, Geometry

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'mechanical/v8_1'
CAD_PATH = OUT / 'wheel_leg_v8_1.FCStd'
BATTERY_SOURCE = 'https://wheeltec.net/24-DC.pdf'
SOURCE_NAMES = tuple(dict.fromkeys(prior.SOURCE_FILES + (
    'analyze_v81_motor_load.py', 'cad_v81_chassis.py', 'cad_v81_payload.py',
    'cad_v81_display.py', 'cad_v81_leg.py', 'cad_v81_coupling.py',
    'cad_v81_battery.py', 'update_v81_battery.py',
)))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(name, data):
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def adjusted_mass_budget(doc, app):
    """Retain V8's method, but identify new bronze parts explicitly."""
    actual = read_mass_budget(doc, app)
    corrected = []
    for row in actual['parts']:
        if row['part'].startswith('flanged_bush_'):
            old_mass = row['mass_g']
            row['mass_g'] = round(doc.getObject(row['part']).Shape.Volume * .0088, 3)
            row['material'] = 'bronze'
            row['method'] = 'One-piece bearing-bronze bush: nominal CAD volume ×0.0088 g/mm³'
            corrected.append(dict(part=row['part'], previous_generic_steel_mass_g=old_mass,
                                  bronze_mass_g=row['mass_g']))
        elif row['part'] == 'unmodelled_installation_allowance':
            row['method'] = ('200 g engineering allowance retained for cables, DC/DC, connectors, '
                             'soft pads/straps and unrepresented details; not a verified weight allowance. '
                             'Counted CAD screws are not added again as separate hardware rows.')
    if len(corrected) != 12:
        raise ValueError(f'Expected 12 integrated bronze bushes, found {len(corrected)}')
    actual['bronze_density_corrections'] = corrected
    screen_part = prior.find_screen_part(actual)
    budget = prior.screen_scenario_budget(actual, screen_part, 200.)
    batteries = [row for row in budget['parts'] if row['part'].startswith('Battery_')]
    if len(batteries) != 1 or abs(batteries[0]['mass_g'] - 400.) > 1e-6:
        raise ValueError('Battery including base must retain the unweighed 400 g estimate')
    batteries[0]['method'] = ('User-confirmed E626S24V class, drawing envelope including magnetic base; '
                              'installed assembly400g engineering estimate; official listing337g does not establish base-inclusive scope. '
                              'Supersedes the pre-confirmation candidate wording retained in CAD provenance.')
    budget['battery_part'] = batteries[0]['part']
    old_rows = {row['part']: row for row in prior.load_baseline('v8')['parts']}
    current_rows = {row['part']: row for row in budget['parts']}
    added_screw_prefixes = ('belly_frame_DIN7991_', 'crossframe_DIN7991_',
                           'battery_tray_M3x8_', 'electronics_tray_M3x8_',
                           'wheel_rim_ISO4762_M3x8_')
    newly_modeled_screws = [row for name, row in current_rows.items()
                           if name.startswith(added_screw_prefixes) and name not in old_rows]
    if len(newly_modeled_screws) != 36:
        raise ValueError(f'Expected36 previously unmodeled frame/tray/rim screws, found{len(newly_modeled_screws)}')
    budget['v8_mass_change_audit'] = dict(
        V8_total_kg=prior.load_baseline('v8')['total_kg'],
        V81_minus_V8_kg=budget['total_kg'] - prior.load_baseline('v8')['total_kg'],
        added_feature_names=sorted(set(current_rows) - set(old_rows)),
        removed_feature_names=sorted(set(old_rows) - set(current_rows)),
        newly_modeled_screws_count=len(newly_modeled_screws),
        newly_modeled_screws_CAD_mass_g=sum(row['mass_g'] for row in newly_modeled_screws),
        note='Mass change includes geometry, standard-screw lengths, consolidated bushes and current battery tray. '
             'A renamed part appears in both added/removed lists; the complete total difference is the relevant net value.')
    budget['notes'] = [
        'V8.1 CAD volumes; 5-inch display200g and battery+base400g remain engineering estimates.',
        'User confirmed E626S24V class; official337g listing leaves base-inclusive mass scope unconfirmed, so battery+base400g remains assumed.',
        'Screen100/200/350g values are sensitivity scenarios, not manufacturer tolerances.',
        'Bronze bush density is explicitly0.0088g/mm³, not inherited generic steel density.',
        'Steel fasteners/bearings are nominal CAD-envelope volume estimates; simplified bearing interiors and '
        'omitted screw engagement/threads bias these estimates in different directions.',
        'PETG uses full CAD solid volume; the final slicer mass, material data and weighing must replace this estimate.',
        '200g installation allowance retained; soft pads, straps, wires, power conversion and details are not exact CAD mass.',
        'Payload/motor centres use uniform-volume proxies, not measured internal mass distribution.',
        'Visible mesh overlays are excluded to avoid counting D435 twice.',
    ]
    return budget, screen_part


def power_screen(mass):
    """Battery-side limits, not sums of motor phase current ratings."""
    voltage_rows = []
    for voltage, label in ((18., 'cutoff/low-SOC arithmetic case'),
                           (22.2, 'nominal'), (25.2, 'full charge')):
        voltage_rows.append(dict(voltage_V=voltage, state=label,
            continuous_current_A=6., continuous_battery_terminal_power_W=voltage * 6.,
            published_instantaneous_current_A=13., instantaneous_VI_W=voltage * 13.,
            instantaneous_duration_s=None))
    auxiliary_rows = [dict(voltage_V=voltage, assumed_battery_side_electronics_W=aux,
                          drive_bus_power_available_W=voltage * 6. - aux)
                      for voltage in (18., 22.2) for aux in (20., 35., 50.)]
    jumps = []
    rise = .100
    speed = math.sqrt(2 * G * rise)
    for start, end in ((.100, .180), (.130, .180)):
        stroke = end - start
        acceleration = speed * speed / (2 * stroke)
        time = 2 * stroke / speed
        force = mass * (G + acceleration)
        jumps.append(dict(start_hip_wheel_mm=start * 1000, takeoff_hip_wheel_mm=end * 1000,
            assumed_COM_stroke_mm=stroke * 1000, target_ballistic_rise_mm=100.,
            takeoff_speed_m_s=speed, constant_upward_acceleration_m_s2=acceleration,
            push_duration_s=time, force_over_static_weight=force / (mass * G),
            ideal_total_positive_work_J=mass * G * (stroke + rise),
            ideal_mean_mechanical_power_W=mass * G * (stroke + rise) / time,
            ideal_end_push_mechanical_power_W=force * speed))
    return dict(source_url=BATTERY_SOURCE, source_pdf_page=12,
        selected_model='E626S24V class, nominal22.2V/full25.2V: confirmed by user; actual base-inclusive mass and plug remain unmeasured',
        rated_capacity_Ah=2.55, nominal_energy_Wh=22.2 * 2.55,
        official_listed_battery_mass_g=337., official_mass_includes_base=None, modeled_battery_and_base_mass_estimate_g=400.,
        connector='DC5.5-2.1 shared charging/discharging socket; connector rating and actual mating plug unverified',
        rows=voltage_rows, auxiliary_power_scenarios=auxiliary_rows,
        four_J4310_at_each_3Nm_120rpm_mechanical_W=4 * 3 * 120 * 2 * math.pi / 60,
        lumped_mass_jump_screen=jumps,
        scope='V×I terminal-power bounds and stated illustrative scenarios. Not a motor-current, thermal, BMS-trip or jump simulation.',
        limitations=[
            '13A instantaneous rating has no duration/duty specified; cannot treat its V×I value as a qualified push-off budget.',
            '6A bus current is not directly comparable with a sum of controlled motor phase currents.',
            'Standstill mechanical power is zero but copper/driver losses still draw power and create heat.',
            'Electronics power scenarios are battery-side assumptions including their conversion losses; drivetrain losses are additional.',
            'Four concurrent rated J4310 operating points exceed nominal continuous battery power before wheels, electronics and losses.',
            'Lumped jump uses the whole robot mass as one point with COM stroke equal to hip-wheel stroke and constant acceleration; '
            'actual distributed inertia, force trajectory, link energy, landing and control are excluded.',
            '18V is the published cutoff, not a recommended commanded discharge target. Sag and protection can cut power earlier.',
            '24V motor torque-speed data are not guaranteed at 18/22.2/25.2V; input range and regen/BMS compatibility remain to be checked.',
        ])


def write_reports(budget, report):
    selected = report['selected_estimate']
    balance = selected['nominal_balance']
    v8 = report['baseline_comparisons']['V8']
    delta = budget['total_kg'] - v8['mass_kg']
    mass = ['# V8.1 质量预算', '',
        f'当前 CAD 预算 **{budget["total_kg"]:.3f} kg**，比 V8 {delta:+.3f} kg。屏幕暂估200g；新电池含磁吸底座仍暂估400g，均未称重。', '',
        '| 类别 | kg |', '|---|---:|']
    mass += [f'| {key} | {value:.3f} |' for key, value in budget['by_material_kg'].items()]
    mass += ['', f'12件一体带肩铜套按8.8g/cm³单列，避免沿用钢密度。本次补建36颗机架/托盘/轮辋螺钉，CAD简化质量合计{budget["v8_mass_change_audit"]["newly_modeled_screws_CAD_mass_g"]:.1f}g，按对象只计一次；轴承和螺钉是简化体积估计，未画出的螺纹/入牙和轴承内部空隙会带来误差。200g未建模附件预算仍保留，用于线束、DC/DC、接头、软垫、绑带等，未据此保证总重上界。', '',
        '| 屏幕质量假设 g | 整机 kg |', '|---:|---:|']
    mass += [f'| {row["assumed_screen_mass_g"]:.0f} | {row["mass_kg"]:.3f} |' for row in report['screen_mass_scenarios']]
    mass += ['', '100～350g仅为屏幕敏感性情景。PETG按完整CAD实体体积，不等于切片耗材质量；设备内部重心采用均匀包络近似。', '',
        f'180mm名义姿态相对髋中心重心 XYZ约{balance["COM_from_hip_mm"][0]:.2f} / {balance["COM_from_hip_mm"][1]:.2f} / {balance["COM_from_hip_mm"][2]:.2f}mm。', '',
        '新电池图纸本体85.6×61.6×42mm，含底座厚44.5mm。用户已确认24V等级E626S；官方表列337g，是否包含磁吸底座未明确，含底座总重仍未实测，继续按400g预算。官方依据：[WHEELTEC手册第12页](https://wheeltec.net/24-DC.pdf)，[本地留档](source/battery/WHEELTEC_24V_manual.pdf)。', '',
        '[逐件质量和重心](mass_budget.json) · [电机及电池功率筛查](MOTOR_LOAD.md)']
    (OUT / 'MASS.md').write_text('\n'.join(mass) + '\n')

    lines = ['# V8.1 电机负载与电池功率筛查', '',
        f'整机暂估 **{budget["total_kg"]:.3f}kg**。名义180mm站姿每膝静力矩 **{report["nominal"]["knee_magnitude_Nm"]:.3f}N·m**；100～215mm采样最大 **{report["worst_sample"]["knee_magnitude_Nm"]:.3f}N·m**。这是约束姿态下的静力预算，不能确认动态平衡或跳跃。', '',
        '髋/膝J4310采用24V、V1.1驱动：额定3N·m/120rpm，峰值7N·m，空载200rpm；H6215额定1N·m、峰值2N·m。几何保持OB/AC130、BW105、OA/BC45mm，名义髋轮距180mm、Beta0°。', '',
        '| 同方法预算 | 质量 kg | 名义膝 N·m/侧 | 采样最大膝 N·m/侧 |', '|---|---:|---:|---:|']
    for name, row in (('V8', v8), ('V8.1', selected)):
        lines.append(f'| {name} | {row["mass_kg"]:.3f} | {row["nominal"]["knee_magnitude_Nm"]:.3f} | {row["worst_sample"]["knee_magnitude_Nm"]:.3f} |')
    lines += ['', f'最大采样点为{selected["worst_sample"]["leg_length_mm"]:.0f}mm，加25%示例留量后为{selected["worst_sample"]["knee_with_25_percent_allowance_Nm"]:.3f}N·m，对额定3N·m余量{selected["worst_with_25_percent_allowance_margin_Nm"]:+.3f}N·m。该留量不替代热试验、单腿支撑或落地冲击分析。', '',
        '| 平地加速度 m/s² | 髋 N·m/侧 | 膝 N·m/侧 | 轮 N·m/侧 |', '|---:|---:|---:|---:|']
    for row in report['flat_driving']:
        lines.append(f'| {row["acceleration_m_s2"]:.1f} | {row["hip_absolute_sum_Nm"]:.3f} | {row["knee_absolute_sum_Nm"]:.3f} | {row["wheel_torque_Nm"]:.3f} |')
    lines += ['', '上表采用滚阻0.02、不利方向叠加水平力项和轮壳反力矩；未含轮/杆惯性、斜坡、控制纠偏峰值。未指定行驶速度，表内力矩不等于完整工作点或输入功率。', '',
        f'名义整机COM对接地线X偏移{balance["COM_to_contact_x_mm"]:+.2f}mm，重心高度{balance["COM_height_above_ground_mm"]:.1f}mm，整体重力俯仰力矩{balance["gravity_pitch_moment_about_contact_Nm"]:+.3f}N·m。计算保持机身俯仰受约束；载荷前后移位仍可能改变自由平衡要求。', '',
        '## 电池是独立的约束', '',
        '用户已确认**24V等级E626S**。官方参数为22.2V、2550mAh、25.2V满充、18V截止、6A最大持续、13A瞬时放电；瞬时持续时间未给出，DC5.5-2.1为充放共口。实际接插件、含底座质量和短时放电能力仍需核对。[官方手册第12页](https://wheeltec.net/24-DC.pdf)', '',
        '| 电池端电压 | 6A持续功率算术上界 | 13A瞬时V×I（时间未知） |', '|---:|---:|---:|']
    for row in report['battery_power_screen']['rows']:
        lines.append(f'| {row["voltage_V"]:.1f}V | {row["continuous_battery_terminal_power_W"]:.1f}W | {row["instantaneous_VI_W"]:.1f}W |')
    lines += ['', 'E626S名义持续电池端功率约133W，18V低电压算术情景仅108W；18V是截止值，不应作为运行目标。电池压降、BMS、接插件、线路损耗和电子设备耗电都会压缩余量。电机相电流与母线电流不同，不能把6A与六台电机的相电流额定值直接相加比较。', '',
        '| 电池侧电子系统耗电假设 | 22.2V留给驱动母线 | 18V留给驱动母线 |', '|---:|---:|---:|']
    for aux in (20., 35., 50.):
        lines.append(f'| {aux:.0f}W | {133.2-aux:.1f}W | {108.-aux:.1f}W |')
    lines += ['', '这些电子功耗仅为情景，已视为电池侧耗电，实际Jetson模式、屏幕、相机和DC/DC需测量。上表剩余值还未扣电机及驱动损耗。四台J4310若同时达到3N·m与120rpm，机械输出合计约150.8W，已超过名义133.2W持续电池端上界，尚未算轮电机和电子设备；因此这块E626S不可能持续支持六电机的全部额定工况。站立时机械功率接近零仍有铜耗及驱动损耗，静态扭矩余量不能证明供电或热性能合格。', '',
        '## 跳跃尚未确认', '',
        '同一腿几何实现100mm理想抛升，180mm起跳需膝约178.8rpm；200mm起跳需约218.5rpm，已超过24V空载200rpm。7N·m峰值和200rpm空载不能同时使用，更不能把24V曲线直接套到低电量电压。', '',
        '| 简化推蹬行程 | 推蹬时长 s | 地面力/静重 | 理想平均机械功率 W | 推蹬末端机械功率 W |', '|---|---:|---:|---:|---:|']
    for row in report['battery_power_screen']['lumped_mass_jump_screen']:
        lines.append(f'| {row["start_hip_wheel_mm"]:.0f}→{row["takeoff_hip_wheel_mm"]:.0f}mm | {row["push_duration_s"]:.3f} | {row["force_over_static_weight"]:.2f} | {row["ideal_mean_mechanical_power_W"]:.1f} | {row["ideal_end_push_mechanical_power_W"]:.1f} |')
    lines += ['', '上表仅将整机视为单质点、假设重心行程等于腿伸长、匀加速推蹬并抛升100mm，忽略杆件分布惯量和传动损耗；不是完整跳跃仿真。其短时功率需结合电池13A允许时长、BMS响应、实际转矩—转速—时间曲线与落地冲击验证，不能据此宣称能跳。回馈制动与电池/BMS吸收能力也未验证。', '',
        f'原生FreeCAD表达式交叉检查：最大重心误差{report["native_validation"]["maximum_COM_error_mm"]:.3g}mm，重力力矩误差{report["native_validation"]["maximum_gravity_effort_error_Nm"]:.3g}N·m。验证的是计算和运动表达式一致，未验证实物质量、强度、热、动态平衡或跳跃；未修改MuJoCo惯量和控制器。', '',
        '[完整计算](motor_load_analysis.json) · [逐件质量](mass_budget.json) · [原生校验](motor_native_validation.json)。电机依据为工程内[4310 V1.1手册](../../../references/DM-J4310-2EC/说明书/DM-J4310-2EC%20V1.1%20Geared%20Motor%20User%20Manual%20V1.2%202026-09-08.pdf)第7页及[H6215教程](../../../references/DM-H6215/说明书/DM-H6215轮毂电机使用教程V2.pdf)第1页。虚功依据：[Modern Robotics 5.2](https://modernrobotics.northwestern.edu/nu-gm-book-resource/5-2-statics-of-open-chains/)。']
    (OUT / 'MOTOR_LOAD.md').write_text('\n'.join(lines) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--formula-only', action='store_true')
    args = parser.parse_args()
    tests = prior.formula_tests()
    tests['scope'] = 'V8.1 uses verified inherited formulas; native V8.1 CAD checked separately'
    power = power_screen(6.)
    assert abs(power['rows'][1]['continuous_battery_terminal_power_W'] - 133.2) < 1e-12
    assert power['rows'][0]['continuous_battery_terminal_power_W'] == 108.
    write_json('motor_formula_validation.json', tests)
    if args.formula_only:
        print(json.dumps(tests, indent=2))
        return
    hashes = {name: digest(ROOT / 'tools' / name) for name in SOURCE_NAMES}
    cad_hash = digest(CAD_PATH)
    sys.path.insert(0, '/Applications/FreeCAD.app/Contents/Resources/lib')
    import FreeCAD as App
    import Part  # noqa: F401 - registers Part::Feature native properties
    doc = App.openDocument(str(CAD_PATH))
    try:
        p = doc.Parameters
        geometry = Geometry('V8.1 unchanged kinematics', p.RodLength.Value/1000,
                            p.LowerLength.Value/1000, p.CrankLength.Value/1000)
        if max(abs(geometry.upper-.130), abs(geometry.lower-.105),
               abs(geometry.crank-.045), abs(p.LegLength.Value/1000-.180), abs(p.Beta.Value)) > 1e-9:
            raise ValueError('V8.1 requires130/105/45mm geometry,180mm pose,Beta0')
        budget, screen = adjusted_mass_budget(doc, App)
        native = native_validation(doc, App, budget, geometry, (.100, .180, .215))
        report = prior.analyze(budget, screen, geometry)
        report.update(version='V8.1', battery_power_screen=power_screen(budget['total_kg']),
                      native_validation=native, formula_validation=tests)
        report['baseline_comparisons']['V8'] = prior.version_summary(prior.load_baseline('v8'), geometry)
        report['limitations'].append('Battery6A continuous and unspecified13A instantaneous need actual power-system validation')
        budget['source_CAD'] = dict(file=CAD_PATH.name, file_sha256=cad_hash,
            geometry_source_sha256=hashes, part_manifest_sha256=digest(OUT/'part_manifest.json'),
            battery_manual_sha256=digest(OUT/'source/battery/WHEELTEC_24V_manual.pdf'),
            native_document_saved=False)
        budget['screen_mass_scenario_total_range_kg'] = [report['screen_mass_scenarios'][i]['mass_kg'] for i in (0, -1)]
        budget['source_unchanged_during_review'] = all(digest(ROOT/'tools'/name) == value for name,value in hashes.items())
        if not budget['source_unchanged_during_review']:
            raise ValueError('CAD source changed while analysis was running; rerun when export is stable')
        write_json('mass_budget.json', budget)
        write_json('motor_native_validation.json', native)
        write_json('motor_load_analysis.json', report)
        write_reports(budget, report)
        print(json.dumps(dict(mass_kg=budget['total_kg'], nominal=report['nominal'],
                              worst=report['worst_sample'], bronze_corrections=len(budget['bronze_density_corrections']),
                              native_validation=native), indent=2))
    finally:
        App.closeDocument(doc.Name)


if __name__ == '__main__':
    main()
