"""WHEELTEC drawing envelope and one-piece removable narrow battery tray.

The purchased item is represented by one conservative rectangular envelope,
including its magnetic mounting base. No inferred DC hole position, magnetic
contact, inner cells or undocumented case contours are manufactured here.
Dimensions are millimetres; the V8 chassis mounting datums remain unchanged.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import build_printable_robot as cad
import cad_chassis as primitive

App, Part, V = cad.App, cad.Part, cad.V
SIZE = (85.6, 44.5, 61.6)
MINIMUM = (-42.8, -22.25, -43.8)
MAXIMUM = (42.8, 22.25, 17.8)
TRAY_BOTTOM, SUPPORT_Z = -46.2, -43.8
MOUNT_XY = tuple((x, y) for x in (-70., 70.) for y in (-20., 20.))
STRAP_X = (-24., 24.)
MASS_G = 400.
DRAWING = cad.ROOT / 'references/user_supplied/WHEELTEC_battery_user_drawing.png'


def box(x, y, z, dx, dy, dz):
    return cad.box(x, y, z, dx, dy, dz)


def cyl(radius, height, point, direction=(0, 0, 1)):
    return Part.makeCylinder(radius, height, V(*point), V(*direction))


def envelope():
    """Drawing's complete 44.5 mm thickness, including magnetic base."""
    return box(*MINIMUM, *SIZE)


def tray():
    floor = primitive._rounded_prism(91.6, 49.5, 2.4, TRAY_BOTTOM, 2.)
    pieces = [floor]
    for side in (-1, 1):
        y0 = 22.75 if side > 0 else -24.75
        pieces.append(box(-45.8, y0, SUPPORT_Z, 91.6, 2., 9.6))
        x0 = 43.3 if side > 0 else -45.8
        pieces.append(box(x0, -22.75, SUPPORT_Z, 2.5, 45.5, 12.))
        for y in (-20., 20.):
            # Integral bridges keep the four original Z-39 pad datums.
            x0 = 45.2 if side > 0 else -70.
            pieces.extend((box(x0, y - 7., -39., 24.8, 14., 3.),
                           cyl(7., 3., (70. * side, y, -39.))))
    tools = [cyl(1.7, 3.4, (x, y, -39.2)) for x, y in MOUNT_XY]
    for x in STRAP_X:
        for side in (-1, 1):
            y0 = 22.25 if side > 0 else -25.0
            # Side windows guide one unbroken strap loop beneath the tray.
            # A 4 mm integral upper bridge remains; overlap/buckles stay above.
            tools.append(box(x - 6., y0, -46.3, 12., 2.75, 8.1))
    return cad.cut(cad.union(*pieces), *tools)


def connector_keepout():
    """Design allowance across the entire top face, not a vendor plug model.

    Port position is undimensioned, so no precise hole is invented. The
    available height to the unchanged electronics tray is12.2mm; reserve11mm.
    A selected right-angle plug and cable must be measured inside this space.
    """
    return box(-42.8, -22.25, 17.8, 85.6, 44.5, 11.)


def strap_underfloor_allowance():
    """Two1mm-thick single-layer strap corridors, no buckle/overlap allowed."""
    return Part.makeCompound([box(x - 5., -25.75, -47.2, 10., 51.5, 1.)
                              for x in STRAP_X])


def module_vertical_sweep(height=100.):
    """Conservative continuous envelope for a complete module lowered in Z.

    The wider mounting ears occur outside X45.2, beyond the hip motor discs.
    Keeping them separate avoids turning the whole tray into a fictitious
    54 mm-wide box. No connector, buckle or cable geometry is claimed here.
    """
    pieces = [box(-45.8, -24.75, TRAY_BOTTOM, 91.6, 49.5,
                  17.8 - TRAY_BOTTOM + height)]
    for side in (-1, 1):
        for y in (-20., 20.):
            x0 = 45.2 if side > 0 else -77.
            pieces.append(box(x0, y - 7., -39., 31.8, 14., 3. + height))
    # Underfloor single-layer straps travel with the preassembled module.
    pieces.extend(box(x - 5., -25.75, -47.2, 10., 51.5, 1. + height)
                  for x in STRAP_X)
    return Part.makeCompound(pieces)


def payload():
    return ('Battery_WHEELTEC_drawing_envelope', envelope(), MASS_G,
            'User WHEELTEC drawing: case85.6x61.6x42mm;44.5mm including '
            'magnetic mechanical base. Installed85.6X x44.5Y x61.6Z,DC face+Z. '
            'One conservative envelope, not vendor CAD.400g assembly mass '
            'budget retained. OfficialE626S dimensions match and list337g '
            'battery, but purchasedSKU and complete-base mass unconfirmed. '
            'DC hole coordinates, plug envelope and discharge suitability '
            'are not inferred from the drawing.')


def interface_data():
    return dict(
        units='mm', model='WHEELTEC user drawing; candidateE626S, SKU unconfirmed',
        representation='One conservative box including the magnetic base; not detailed vendor CAD',
        drawing_case_dimensions=[85.6, 61.6, 42.], drawing_with_base_thickness=44.5,
        robot_dimensions_xyz=SIZE, robot_min_xyz=MINIMUM, robot_max_xyz=MAXIMUM,
        mass_budget_g=MASS_G, mass_is_measured=False,
        candidate_official=dict(model='E626S', source='https://wheeltec.net/24-DC.pdf',
            page=12, battery_mass_g=337, battery_mass_scope='Candidate battery only; exact selectedSKU/base-inclusive mass unconfirmed',
            nominal_voltage_V=22.2, full_voltage_V=25.2, cutoff_voltage_V=18.,
            capacity_mAh=2550, continuous_current_A=6., instant_current_A=13.,
            instant_duration_s=None,
            note='Matching dimensions do not establish purchased SKU. Values do not certify whole-robot motor power suitability.'),
        magnetic_base=dict(included_in_envelope=True,
            role='Mechanical magnetic attachment/flux plate; not an electrical contact; no jump load credit',
            source='Official24-DC.pdf page9, selectedSKU must be confirmed'),
        mounting=dict(part='battery_tray', process='one-piecePETG',
            mounting_centres_xy=MOUNT_XY, mounting_pad_z=[-39., -36.],
            mounting_screws='4xISO4762 M3x8 unchanged;3mm grip/5mm nominal metal insertion',
            clearance_hole_diameter=3.4, floor_bottom_z=TRAY_BOTTOM,
            support_z=SUPPORT_Z, floor_thickness=2.4,
            inner_opening_xy=[86.6, 45.5], nominal_side_clearance_each=.5,
            main_outer_width_y=49.5, long_sidewall_thickness=2.,
            long_sidewall_top_z=-34.2, endstop_top_z=-31.8,
            actual_belly_central_pocket_top_z=-48., tray_belly_clearance_mm=1.8),
        retention=dict(straps=2, maximum_width=10., strap_x=STRAP_X,
            suggested_purchase_size_mm=[10., 300.],
            conservative_centreline_loop_mm=231., minimum_top_overlap_mm=50.,
            selection='300mm cut-to-fit straps; straight single layer<=1mm, no bulky buckle; overlap only above battery, away from actual DC plug and cable',
            side_guide_window_width_x=12., side_guide_window_z=[-46.3, -38.2],
            upper_guide_bridge_height=4., underfloor_single_layer_thickness_max=1.,
            underfloor_remaining_nominal_clearance=.8,
            instruction='Mechanical straps and integral stops carry restraint; no magnetic holding-force assumption. Keep buckles/overlaps on top outside actualDC port.'),
        dc=dict(drawing_label='2.1DC', exact_port_coordinates=None,
            candidate_interface='DC5.5x2.1, shared charging/discharging per official candidate datasheet; SKU not confirmed',
            port_face_robot_normal=[0, 0, 1], available_height_to_electronics_tray=12.2,
            design_keepout_height=11., design_keepout_bounds=[-42.8,-22.25,17.8,42.8,22.25,28.8],
            clearance_keepout_to_tray=1.2,
            qualification='Only the declared keepout can be checked. Select and measure a compact right-angle plug/cable; no exact socket/plug geometry modeled.'),
        manufacturing='Print floor flat with support under raised integral ears, clear the12mm strap windows/4mm bridges; calibrateØ3.4 holes and0.5mm side clearance. No scaling of source battery dimensions.',
        unresolved=['PurchasedSKU and whether base is included in the order.',
                    'Measured complete assembly mass.',
                    'DC socket coordinates, right-angle plug height and cable bend radius.',
                    'Actual strap single-layer thickness<=1mm and buckle/overlap placement.',
                    'Electrical peak duration, BMS/connector rating and motor operating compatibility.',
                    'Restraint performance under jump/impact; no physical qualification.'])


def export_notes(out):
    out=Path(out)
    source=out/'source/battery';source.mkdir(parents=True,exist_ok=True)
    drawing_copy=source/'WHEELTEC_battery_user_drawing.png'
    if DRAWING.exists():
        shutil.copy2(DRAWING,drawing_copy)
    data=interface_data()
    if drawing_copy.exists():
        data['user_drawing_source']='source/battery/'+drawing_copy.name
        data['user_drawing_sha256']=hashlib.sha256(drawing_copy.read_bytes()).hexdigest()
    data['cad_source_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    (out/'battery_interface.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    (out/'BATTERY.md').write_text('''# WHEELTEC电池与一体托盘

按用户图纸采用本体85.6×61.6×42 mm、含磁吸底座总厚44.5 mm。CAD仅建立包含底座的保守长方体外廓，不推断磁铁、内部电芯或未标注的DC孔位。官方资料中的E626S外形吻合，但购买SKU尚未核实；整包含底座质量继续用400 g预算，337 g仅是候选电池规格，不能当作本次装配实测重量。

安装为85.6沿X、44.5沿Y、61.6沿Z；范围X±42.8、Y±22.25、Z−43.8～17.8 mm。DC所在窄侧面朝上。腿部、电机、金属机架、机壳、Jetson位置不变。

托盘为一个PETG零件，保留原4个X±70/Y±20的M3×8固定点，耳座Z−39～−36，底厚2.4 mm；承托面Z−43.8。主托宽49.5 mm，长侧壁2 mm，电池每侧留0.5 mm装配间隙。底板现有中央凹台上表面是Z−48，托底Z−46.2，实际名义间隙1.8 mm，不按外围底板高度误判。

两条现有宽≤10 mm束带在X±24穿过一体侧窗口，再绕托盘底部和电池形成完整闭环。按厚1 mm带材、保守外接矩形中心线，闭环长231 mm；再留至少50 mm顶部搭接，建议采购两条10×300 mm无厚大扣头的可修整束带，试装后裁剪。侧窗宽12 mm、上方保留4 mm桥；下方只允许厚≤1.0 mm的单层带材，折返和搭接置于电池上方，且不可占用实物DC插头与线材位置。底部1 mm带材之后剩0.8 mm名义间隙。普通厚魔术贴或扣头未必适用，实际DC位置也可能要求调整穿带位置；本版不虚构二者兼容性。机械止挡与束带承担约束，磁吸只辅助定位，不能凭磁吸宣称承受跳跃冲击。

电池顶到电器盘底共12.2 mm。因为DC孔没有定位尺寸，本版对整个顶面保留11 mm高的设计检查区，最高Z28.8，离电器盘底Z30为1.2 mm；这不是已选插头模型。必须实测弯头外伸、线径和弯曲半径，并确认束带不会压在插头上。超出该高度的插头不能直接宣称适配。

保留单托盘、两条束带、4颗M3×8，BOM件数不增加。托底朝下打印，一体抬高耳座下方使用可清除支撑；12 mm侧窗口及4 mm桥打印后应清理、通带，避免锐边割带。是否能在两腿装好后整体装拆，由battery_local_review.json与模块装配审查约束；装电池前应断开所有输出，避免金属工具搭接端口。工艺间隙是样机起点，打印试装、束带拉拔、振动和跳跃保持力仍需试验。

[官方24-DC规格书](https://wheeltec.net/24-DC.pdf)第12页候选E626S：22.2 V、2550 mAh、337 g、持续6 A、瞬时13 A，瞬时时间未给；满电25.2 V、截止18 V。第9页磁吸座用于机械固定。候选DC5.5×2.1为充放同口。资料尚未映射实际购买SKU，不能据外形吻合就确定供电能力，也不能把DC口的瞬时参数当作所有电机可持续使用的电流。
''',encoding='utf-8')
    return data


def export_review(out):
    """Check new local geometry against the frozen native assembly read-only."""
    out = Path(out)
    doc = App.openDocument(str(out / 'wheel_leg_v8_1.FCStd'))
    doc.Parameters.LegLength = 180
    doc.Parameters.Beta = 0
    doc.recompute()
    old_battery = {o.Name for o in doc.Objects if o.Name.startswith('Battery_')}
    targets = {o.Name: o.Shape for o in doc.Objects if o.TypeId == 'Part::Feature'
               and o.Name not in old_battery | {'battery_tray'}}
    report = dict(units='mm', threshold_mm3=.001, checks=[], failures=[],
                  source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  background_fcstd_sha256=hashlib.sha256((out / 'wheel_leg_v8_1.FCStd').read_bytes()).hexdigest())

    def hits(shape, obstacles):
        result = []
        for name, obstacle in obstacles.items():
            if not shape.BoundBox.intersect(obstacle.BoundBox):
                continue
            volume = cad.interference_volume(shape, obstacle)
            if volume > .001:
                result.append(dict(part=name, overlap_mm3=volume))
        return result

    def record(name, passed, **kwargs):
        report['checks'].append(dict(name=name, passed=bool(passed), **kwargs))
        if not passed:
            report['failures'].append(name)

    parts = {'battery_tray': tray(), 'battery_envelope': envelope()}
    record('valid_single_solids', all(s.isValid() and len(s.Solids) == 1 for s in parts.values()),
           rows=[dict(name=n, valid=s.isValid(), solids=len(s.Solids), volume_mm3=s.Volume)
                 for n, s in parts.items()])
    overlap = cad.interference_volume(parts['battery_tray'], parts['battery_envelope'])
    record('battery_seated_in_tray', overlap < .001, overlap_mm3=overlap)
    for name, shape in parts.items():
        collisions = hits(shape, targets)
        record(name + '_to_native_assembly', not collisions, hits=collisions)
    for name, shape in [('declared_connector_design_allowance', connector_keepout()),
                        ('single_layer_underfloor_straps', strap_underfloor_allowance())]:
        collisions = hits(shape, {**targets, **parts})
        record(name, not collisions, hits=collisions)
    # Exact face gap checks avoid mistaking the belly's outer ledge for the
    # recessed central floor under this tray.
    floor = primitive._rounded_prism(91.6, 49.5, .001, TRAY_BOTTOM, 2.)
    gaps = dict(tray_bottom_to_belly=floor.distToShape(targets['chassis_belly_plate'])[0],
                underfloor_strap_to_belly=strap_underfloor_allowance().distToShape(targets['chassis_belly_plate'])[0],
                battery_to_electronics_tray=envelope().distToShape(targets['electronics_tray'])[0],
                connector_allowance_to_electronics_tray=connector_keepout().distToShape(targets['electronics_tray'])[0])
    for side in ('left', 'right'):
        gaps['tray_to_hip_motor_' + side] = parts['battery_tray'].distToShape(targets['J4310_hip_' + side])[0]
    record('nominal_clearances', all(v > .1 for v in gaps.values()), values_mm=gaps,
           note='Rigid nominal solids only; manufacturing tolerances, warpage, straps and plug variations require trial fitting.')
    # Frame and both complete legs present, but upper electronics/front/body
    # covers absent. A continuous conservative swept envelope is stronger than
    # isolated sampled placements for this simple straight insertion route.
    stage = {o.Name: o.Shape for o in doc.Objects if o.TypeId == 'Part::Feature'
             and getattr(o, 'AssemblyModule', '').startswith(('M01', 'M02', 'M03'))}
    sweep_hits = hits(module_vertical_sweep(), stage)
    record('complete_battery_module_vertical_insertion', not sweep_hits, hits=sweep_hits,
           continuous_vertical_travel_mm=100., background_objects=len(stage),
           assembly_state='Metal frame and complete legs installed at180mm,beta0; electronics tray/Jetson,IMU,front face and outer shells absent; four tray screws installed after lowering.',
           route_contents='Tray+battery+single-layer underfloor strap allowance; no unselected plug,buckle or cable geometry.')
    access = []
    for x, y in MOUNT_XY:
        tool = cyl(1.5, 120., (x, y, -33.))
        collisions = hits(tool, {**stage, **parts})
        access.append(dict(x=x, y=y, hits=collisions))
    record('four_M3x8_top_driver_access_after_module_insertion', not any(r['hits'] for r in access),
           tool_diameter_mm=3., tip_z=-33., rows=access, assembly_state='Same open-body state as vertical insertion.')
    record('unchanged_four_mounting_datums', all(
        cad.interference_volume(cyl(1.6, 3., (x, y, -39.)), parts['battery_tray']) < .001
        for x, y in MOUNT_XY), centres_xy=MOUNT_XY, screw='ISO4762M3x8',
        grip_mm=3., nominal_metal_engagement_mm=5.)
    report['all_pass'] = not report['failures']
    report['limitations'] = ['No strength, impact or strap load certification.',
        'DC location and plug not dimensioned; only declared11mm top design allowance checked.',
        'Full assembly motion sweep is recorded separately by parent integration script.',
        'Body electronics must be removed before reversing the battery-module insertion path.']
    (out / 'battery_local_review.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    App.closeDocument(doc.Name)
    return report
