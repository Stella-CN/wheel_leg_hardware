"""User-dimensioned 7 inch display and adjustable, removable rear carriers.

The purchased display is a dimensional envelope, not supplier CAD. Only its
outer size, mass, hole diameter/pitch and rear connector direction are known.
The assumed centred hole array is adjustable ±2 mm independently in Y/Z.
"""
from __future__ import annotations

import json
import build_printable_robot as cad
import cad_v5_payload as primitive

V, Part = cad.V, cad.Part
WIDTH, HEIGHT, DEPTH = 165., 110., 20.
FACE_X, REAR_X, CENTER_Z = 119., 99., 8.
PITCH_Y, PITCH_Z = 150.6377, 93.3845
HOLES = tuple((sy * PITCH_Y / 2, CENTER_Z + sz * PITCH_Z / 2)
              for sy in (-1, 1) for sz in (-1, 1))
FRAME_HOLES = tuple((sy * 89., z) for sy in (-1, 1) for z in (-38., 8., 54.))
xcyl, xhex = primitive.xcyl, primitive.xhex


def display():
    shape = cad.box(REAR_X, -WIDTH/2, CENTER_Z-HEIGHT/2, DEPTH, WIDTH, HEIGHT)
    # Through-holes here are reference axes in a clearance envelope. Actual
    # screen mounting-lug thickness is unknown and is NOT assumed to be20mm.
    return cad.cut(shape, *(xcyl(1.5, REAR_X-.1, DEPTH+.2, y, z) for y,z in HOLES))


def _carrier(positive=True):
    parts = [cad.box(94,84.5,-46,22,9,108)]
    for z in (CENTER_Z-PITCH_Z/2, CENTER_Z+PITCH_Z/2):
        parts += [
            xcyl(7,94,3,PITCH_Y/2,z),cad.box(94,PITCH_Y/2,z-4,3,18.2,8)]
    shape = cad.union(*parts)
    cuts = []
    for z in (CENTER_Z-PITCH_Z/2, CENTER_Z+PITCH_Z/2):
        # A6.8square window and14square metal washer permit±2mm independently
        # in both coordinates with aM2.5 screw (corner clearance included).
        cuts.append(cad.box(93.8,PITCH_Y/2-3.4,z-3.4,3.4,6.8,6.8))
    for z in (-38.,8.,54.):
        cuts += [xcyl(1.7,93.8,22.4,89,z),xhex(93.8,16.2,89,z,5.8)]
    # Open side webs rather than a solid block; remaining edge rails are4mm.
    for z0,z1 in ((-30.,0.),(16.,46.)):
        cuts.append(cad.box(98,84.3,z0,14,9.4,z1-z0))
    shape = cad.cut(shape,*cuts)
    return shape if positive else cad.mirror(shape)


def designs():
    return {'display_carrier_right':_carrier(), 'display_carrier_left':_carrier(False)}


def hardware():
    result=[]
    for i,(y,z) in enumerate(FRAME_HOLES):
        screw=cad.union(xcyl(1.5,106,16,y,z),xcyl(2.75,122,3,y,z))
        nut=cad.cut(xhex(107.6,2.4,y,z,5.5),xcyl(1.5,107.5,2.6,y,z))
        result += [(f'display_frame_M3x16_{i}',screw,'fixed'),
                   (f'display_frame_M3_nut_{i}',nut,'fixed')]
    for i,(y,z) in enumerate(HOLES):
        washer=cad.cut(cad.box(93,y-7,z-7,1,14,14),xcyl(1.4,92.9,1.2,y,z))
        spacer=cad.cut(xcyl(4,97,2,y,z),xcyl(1.5,96.9,2.2,y,z))
        result += [(f'display_adjustable_washer_{i}',washer,'fixed'),
                   (f'display_spacer_D8_d3_t2_{i}',spacer,'fixed')]
    return result


def payload():
    return ('Display_7in_user_envelope',display(),265.,
            'User drawings165x110x20mm/265g,1024x600; holesD3 confirmed by user. '
            'Pitch150.6377x93.3845 is from screenshot, not certified tolerance. '
            'Centred array assumed; independent±2mm mounting adjustment. '
            'HDMI/USB face rear(-X); exact connectors/lug thickness unprovided.')


def export_notes(out):
    report=dict(units='mm',source='User dimensional screenshots and clarification',
        product_url='https://detail.tmall.com/item.htm?id=639709410089&skuId=4607086052833',
        product_page_access='Web fetch unavailable; no additional unverified dimensions inferred',
        display_inches=7,resolution_px=[1024,600],mass_g=265,
        outer_width_height_depth=[WIDTH,HEIGHT,DEPTH],active_width_height=[155,87],
        face_x=FACE_X,rear_x=REAR_X,center_z=CENTER_Z,
        mounting_hole_diameter=3.,nominal_hole_pitch_yz=[PITCH_Y,PITCH_Z],
        nominal_hole_centres_yz=HOLES,centred_array_is_assumption=True,
        nominal_edge_offsets=[(WIDTH-PITCH_Y)/2,(HEIGHT-PITCH_Z)/2],
        carrier_adjustment_mm_each_axis=2.,carrier_square_windows=6.8,
        adjustment_washers=[14,14,1],rear_spacer=[8,3,2],
        screen_fasteners='4xM2.5 through screws with metal washers and locknuts. Length selected after measuring mounting-lug thickness; not modelled.',
        carrier_fasteners='6xM3x16 with captiveM3 nuts; all modelled',
        connectors='HDMI/USB/power face rear(-X); exact positions/plug dimensions unknown',
        limits=['Measure hole-array offset and mounting-lug plane before fabrication.',
                'The screenshot precision is not a machining tolerance.',
                'Do not tighten through glass/LCD; fasten the actual mounting tabs only.',
                '2mm spacers are an initial packaging assumption, replace to match the lug datum.'])
    (out/'display_interface.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    lines=['# 7寸屏接口与可调支架','',
        '| 项目 | 数值 / 依据 |','|---|---|',
        '| 外形 | 165×110×20 mm，用户图 |',
        '| 有效显示区 | 155×87 mm，1024×600，用户图 |',
        '| 质量 | 约265 g，用户图 |',
        '| 安装孔 | 4×Ø3 mm，用户确认 |',
        '| 孔中心距 | 150.6377×93.3845 mm，截图标注；小数位不代表加工精度 |',
        '| 接口 | HDMI/USB朝后−X，用户确认；电源及实际插头包络未提供 |','',
        '装配中屏幕中心位于Y0/Z8，玻璃前面X119、后包络X99；前壳面X122，屏幕内嵌3mm。'
        '孔阵列暂按外框居中，距左右边7.18115、距上下边8.30775mm；这是可调设计基准，尚非供应商确认孔偏移。','',
        '左右两件PETG托架使用6.8mm方形调节窗和14×14×1mm金属平垫板，允许各方向±2mm位置修正。'
        '每孔前端暂放D8/d3/t2金属隔柱，四颗M2.5穿过实际Ø3安装孔，以锁紧螺母固定；'
        '屏幕安装耳厚度和接触面未知，因此螺钉长度不虚设，模型不绘出这四颗未定长度螺钉。'
        'M2.5在Ø3孔留装配间隙；不能对玻璃/液晶层施加夹紧载荷。','',
        '两件托架通过6颗M3×16及捕获式螺母固定在前壳。承重链为设备安装耳→金属垫板/隔柱→PETG托架→前壳→金属横框。'
        '前壳先固定到骨架；拆下独立前屏框，从166×111mm主壳通孔前方放入165×110mm屏幕，'
        '内部安装耳固定后再装前屏框。屏固定耳工具通道及最终螺钉方向须结合实物核对，'
        '连续入窗检查只覆盖设备包络平移，不包含未知安装耳和线束。屏/相机均为连续前脸的一部分。','',
        '商品页未能读取；尺寸以用户图及确认内容为准。下单加工前需核对孔阵列偏移、安装耳面、实际后接头位置。'
        '当前提供可审查的安装方案，不能把设备包络当作完整供应商三维模型。']
    (out/'DISPLAY.md').write_text('\n'.join(lines)+'\n')
