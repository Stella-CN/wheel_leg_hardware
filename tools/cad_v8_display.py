"""GK-HD 5-inch supplier envelope and external metal-case cradle.

Only the 122 x 78 x 14.5 mm outside dimensions are supplier-confirmed.
No device hole pattern or active display boundary is invented. The separate
chassis front panel retains the case at four small outer-edge stops; verify
those stops land on metal, never glass, before manufacturing that panel.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import build_printable_robot as cad
import cad_v5_payload as primitive

V, Part = cad.V, cad.Part
WIDTH, HEIGHT, DEPTH = 122., 78., 14.5
FACE_X, REAR_X, CENTER_Z = 114., 99.5, -4.
FRAME_HOLES = tuple((sy * 67., z) for sy in (-1, 1) for z in (-34., 26.))
MASS_G = 200.
MASS_RANGE_G = (100., 350.)
xcyl, xhex = primitive.xcyl, primitive.xhex


def display():
    """Supplier outside envelope, intentionally without undocumented holes."""
    return cad.box(REAR_X, -WIDTH / 2, CENTER_Z - HEIGHT / 2,
                   DEPTH, WIDTH, HEIGHT)


def _carrier(positive=True):
    # Rear spine joins only the upper/lower corner supports. The side wall
    # between them stays completely open at the device's axial depth.
    parts = [cad.box(96.5, 65., -34., 2.5, 4., 60.)]
    for z in (-34., 26.):
        parts.extend((xcyl(5., 96.5, 17.5, 67., z),
                      cad.box(96.5, 56., z - 4., 2.5, 11., 8.)))
    # 0.5 mm clearance beside the metal side walls. Rear contact uses
    # four adhesive 4 x 8 x 0.5 mm compliant pads, specified separately.
    parts.extend((cad.box(99., 61.5, -44.5, 15., 3., 14.5),
                  cad.box(99., 61.5, 22., 15., 3., 15.),
                  cad.box(99., 56., -44.5, 14.8, 8.5, 1.5),
                  cad.box(99., 56., 35.5, 14.8, 8.5, 1.5)))
    shape = cad.union(*parts)
    tools = [xcyl(4.8, 96.3, 18., 68., -44.),
             xcyl(3.1, 96.3, 1., 62., -40.)]
    for z in (-34., 26.):
        tools.extend((xcyl(1.7, 96.3, 18., 67., z),
                      xhex(96.3, 2.7, 67., z, 5.8)))
    shape = cad.cut(shape, *tools)
    return shape if positive else cad.mirror(shape)


def designs():
    return {'display_case_cradle_right': _carrier(),
            'display_case_cradle_left': _carrier(False)}


def hardware():
    rows = []
    for i, (y, z) in enumerate(FRAME_HOLES):
        # M3x22: 3 mm front panel + 17.5 mm cradle; 1.5 mm projects
        # behind the cradle. Its captive nut is accessible from the rear.
        screw = cad.union(xcyl(1.5, 95., 22., y, z),
                          xcyl(2.75, 117., 3., y, z))
        nut = cad.cut(xhex(96.6, 2.4, y, z, 5.5),
                      xcyl(1.5, 96.5, 2.6, y, z))
        rows.extend(((f'display_case_M3x22_{i}', screw, 'fixed'),
                     (f'display_case_M3_nut_{i}', nut, 'fixed')))
    return rows


def payload():
    return ('Display_GK_HD_5in_supplier_envelope', display(), MASS_G,
            'User GK-HD V3 specification PDF p2 confirms 122x78x14.5 mm. '
            'No 5-inch device mounting holes, active display area, exact '
            'connector envelope or mass provided. 200 g is an engineering '
            'scenario only, range100..350 g; not manufacturer mass. '
            'External case cradle, no holes drilled in purchased device.')


def export_notes(out):
    source = cad.ROOT / 'mechanical/v8/source/display/显示器规格书.pdf'
    report = dict(
        units='mm', source=str(source.relative_to(cad.ROOT / 'mechanical/v8')),
        source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        dimension_page_pdf=2, model_family='GK-HD', specification_revision='V3',
        cover_date='20240428', selected_variant_inches=5,
        outer_width_height_depth=[WIDTH, HEIGHT, DEPTH],
        active_display_area=None, active_display_window='Not specified; no inferred AA cutout.',
        manufacturer_device_mounting_holes=None,
        face_x=FACE_X, rear_x=REAR_X, center_z=CENTER_Z,
        mass_g=MASS_G, mass_is_assumed=True, mass_scenario_range_g=MASS_RANGE_G,
        panel_clear_opening_width_height=[123., 79.],
        cradle_fasteners='4xM3x22 screws + 4xM3 nuts, cradle front datumX114, panelX114..117',
        cradle_holes_yz=FRAME_HOLES, cradle_hole_diameter=3.4,
        case_side_clearance_each_mm=.5,
        front_stops='Provided by chassis front panel at four corners; formed length4mm, nominal case contact3.5x0.5mm each. Actual metal rim must be confirmed.',
        rear_pads='4x4x8x0.5 mm compliant adhesive pads at X99..99.5, Y±(56..60), Z[-38,-30]/[22,30]; not separate CAD solids.',
        device_bottom_support_z=-43., device_top_retention_z=35.5,
        connectors='Rear-left recessed family illustration; no dimensioned connector coordinates/direction. Cradle leaves rear central area and side central height open.',
        unresolved=['Actual mass and centre of mass.',
                    'Front corner contact must be metal case, not LCD/glass; replace stop pads after measuring if necessary.',
                    'Case dimensional tolerances and front glass extent.',
                    'Actual rear/side plug clearances and cable bending.',
                    'Unknown purchased-device case load limits; not jump-qualified.'],
        supplier_interface_not_reused='7/10-inch75x75 M4 and all former7-inch data excluded.')
    (out / 'display_interface.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    lines = [
        '# GK-HD 5寸屏与外壳托架', '',
        '用户选定新规格书中的5寸版本。厂家只确认外形 **122×78×14.5 mm**；'
        'PDF第2页给出尺寸，封面为GK-HD / V3 / 20240428。源文件与6页渲染保存在source/display。', '',
        '| 项目 | 本版采用值与依据 |', '|---|---|',
        '| 屏幕前面 / 后面 / 中心高 | X114 / X99.5 / Z−4 mm |',
        '| 前壳通窗 | 123×79 mm，按完整外廓留每侧0.5 mm；不假定有效显示区 |',
        '| 厂家安装孔 | 未给出；不使用机壳角螺钉、不借用7/10寸75 mm M4孔 |',
        '| 托架固定 | 4×M3×22+M3捕获螺母，孔轴Y±67、Z−34/26 mm，孔Ø3.4 |',
        '| 质量 | 200 g工程情景；100～350 g敏感性范围，非厂家参数 |', '',
        '两件PETG角托以金属外壳作为支撑对象。下部托唇在Z−43接触外壳底面，'
        '上部挡唇在Z35.5防止向上脱离，顶面保留0.5 mm装配间隙，左右各留0.5 mm；中段侧面和背面敞开。'
        '后面四个支承区与设备之间留0.5 mm，粘贴4×8×0.5 mm柔性垫片后承压。'
        '垫片坐标为X99..99.5，Y正侧56..60/负侧−60..−56，Z−38..−30及22..30；'
        '这些软垫未作为独立CAD实体，计入装配杂件。', '',
        '前面板四个小止挡只覆盖外廓最边缘0.5 mm、每处4 mm长，'
        '**前缘是否有可受力的金属边必须实物确认，禁止以玻璃或液晶层承受螺钉夹紧力。**'
        '未知玻璃范围时不能把本版前止挡当作已获厂家认可的夹持位置。', '',
        '装配顺序：把M3螺母从托架背面压入六角孔；贴后部软垫；'
        '将左右托架从两侧扣合在屏的金属外壳上下角；把屏与托架整体置于拆下的前面板后面，'
        '确认止挡与金属边接触，再从前面装4颗M3×22，先手拧至托架平面与面板接触，'
        '不得用螺钉把未知玻璃边缘强行夹紧。螺杆在托架背面露出1.5 mm；可将M3×25裁短至22 mm并倒角。'
        '最后将完整前面板模块装到机壳并连接HDMI与USB供电/数据。', '',
        '背面接口区采用敞开结构；规格书示意AUDIO/USB5V/HDMI位于背视左侧凹区，'
        '接口准确方向和插头尺寸未给出，不绘制虚构接头。需用实物核对弯头、插拔通道和线束弯曲半径。'
        '屏幕分辨率、有效区、质量、公差、外壳承载极限均没有5寸单独确证。'
        '本托架提供可审查机械接口，未进行跌落、振动、跳跃或玻璃应力认证。'
    ]
    (out / 'DISPLAY.md').write_text('\n'.join(lines) + '\n')
