"""Read supplied electronic STEP models without changing either model."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, '/Applications/FreeCAD.app/Contents/Resources/lib')
sys.modules['flatmesh'] = None
import FreeCAD as App
import Part

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'mechanical/v8_2'
FILES = {
    'usb2can': ROOT / 'references/dm-tools/USB2CANFD_Dual/模型/usb2canfd_v2_1-double.stp',
    'distribution_pcb': ROOT / 'references/user_supplied/3D_PCB1_2026-09-28.step',
}


def vec(v):
    return [round(a, 6) for a in (v.x, v.y, v.z)]


def bounds(shape):
    b = shape.BoundBox
    return {'min': [round(v, 6) for v in (b.XMin, b.YMin, b.ZMin)],
            'max': [round(v, 6) for v in (b.XMax, b.YMax, b.ZMax)],
            'size': [round(v, 6) for v in (b.XLength, b.YLength, b.ZLength)]}


def cylinders(shape):
    found = []
    for i, f in enumerate(shape.Faces):
        s = f.Surface
        if isinstance(s, Part.Cylinder):
            found.append({'face': i + 1, 'radius': round(s.Radius, 6),
                          'center': vec(s.Center), 'axis': vec(s.Axis),
                          'bounds': bounds(f), 'area': round(f.Area, 5),
                          'orientation': f.Orientation})
    return found


def inspect():
    data = {}
    for key, path in FILES.items():
        shape = Part.read(str(path))
        solids = []
        for i, solid in enumerate(shape.Solids):
            solids.append({'index': i, 'volume': round(solid.Volume, 6),
                           'bounds': bounds(solid), 'cylinders': cylinders(solid)})
        data[key] = {'source': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                     'bounds': bounds(shape), 'volume': round(shape.Volume, 6),
                     'valid': shape.isValid(), 'solid_count': len(shape.Solids), 'solids': solids}
        print(key, data[key]['bounds'], 'solids', len(solids), flush=True)
        if key == 'usb2can':
            bare = Part.makeCompound(shape.Solids[1:12])
            data[key]['bare_board'] = {
                'included_solid_indices_zero_based': list(range(1, 12)),
                'removed_housing_indices': [0, 12],
                'removed_housing_screw_indices': [13, 14, 15, 16],
                'removed_light_pipe_indices': [17, 18, 19],
                'bounds': bounds(bare), 'valid': bare.isValid(),
                'mounting_holes_diameter': 2.0,
                'mounting_holes_xy': [[x, y] for x in [-13.05, 13.95] for y in [-9.0, 9.0]],
                'mounting_hole_pitch_xy': [27.0, 18.0],
                'pcb_z_bottom_top': [2.0, 3.6],
                'usb_mating_direction': [-1, 0, 0],
                'can_uart_mating_direction': [1, 0, 0],
                'note': 'Bare assembly extracted from supplied manufacturer STEP; no housing, screws or light pipes. Small underside solder joints not necessarily represented.'}
            target = OUT / 'source/board_model_inspection_usb2can_bare.step'
            target.parent.mkdir(parents=True, exist_ok=True)
            bare.exportStep(str(target))
            data[key]['bare_board']['exported_step'] = str(target)
            print('usb2can_bare', bounds(bare), flush=True)
    target = OUT / 'source/board_model_inspection_raw.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    write_summary(data)
    return data


def write_summary(data):
    """Keep actionable measured interfaces apart from every cylinder face."""
    pcb = data['distribution_pcb']
    summary = {
        'units': 'mm', 'coordinates': 'Unmodified source STEP coordinate systems',
        'usb2can_bare': data['usb2can']['bare_board'],
        'usb2can_source': {k: data['usb2can'][k] for k in ('source', 'sha256')},
        'distribution_pcb': {
            'source': pcb['source'], 'sha256': pcb['sha256'],
            'bounds': pcb['bounds'], 'valid': pcb['valid'],
            'pcb_bounds': pcb['solids'][0]['bounds'],
            'pcb_z_bottom_top': [0.0, 1.600051],
            'mounting_holes_diameter': 3.000005,
            'mounting_holes_xy': [[x, y] for x in [2.413005, 29.464059]
                                  for y in [-36.576073, -2.540005]],
            'mounting_hole_pitch_xy': [27.051054, 34.036068],
            'mounting_hole_array_center_xy': [15.938532, -19.558039],
            'connectors': [
                {'reference': 'CN5', 'model_name': 'XT30PW-M 2P',
                 'solid_indices': [1, 2, 3], 'mating_outward': [0, -1, 0],
                 'bounds': pcb['solids'][2]['bounds']},
                {'reference': 'U2', 'model_name': '4P XT30PW-M',
                 'solid_indices': [4], 'mating_outward': [1, 0, 0],
                 'bounds': pcb['solids'][4]['bounds']},
                {'reference': 'U1', 'model_name': '4P XT30PW-M',
                 'solid_indices': [5], 'mating_outward': [-1, 0, 0],
                 'bounds': pcb['solids'][5]['bounds']},
                {'reference': 'CN4', 'model_name': 'WAFER-GH1.25-2PWB',
                 'solid_indices': list(range(6, 11)), 'mating_outward': [1, 0, 0],
                 'housing_bounds': pcb['solids'][10]['bounds']},
                {'reference': 'CN3', 'model_name': 'WAFER-GH1.25-2PWB',
                 'solid_indices': list(range(11, 16)), 'mating_outward': [1, 0, 0],
                 'housing_bounds': pcb['solids'][15]['bounds']},
            ],
            'limits': [
                'STEP contains no electrical netlist, pin assignment or current rating.',
                'Connector assignments to left/right legs must be confirmed electrically.',
                '3.0 mm holes are not guaranteed M3 clearance holes; M2.5 insulated fixing is an option.',
                'Minimum model solder tail Z=-0.399949; provide additional solder/insulation clearance.'
            ]
        },
        'manual_confirmed': {
            'source': str(ROOT / 'references/dm-tools/USB2CANFD_Dual/DM-USB2CANFD_Dual 模块使用说明书 V1.0.pdf'),
            'manual_revision': '2026-03-23 V1.0', 'pages': [3, 4],
            'USB_TypeC': 'Module power and host communication; do not connect battery 24V.',
            'CAN': 'Two independent channels, GH1.25 2P each.',
            'UART': 'GH1.25 3P.',
            'termination': '120 ohm on-board termination enabled by corresponding switch ON.'
        },
    }
    (OUT / 'source/board_model_inspection.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    (OUT / 'source/board_model_inspection.md').write_text('''# V8.2 新增转接板模型核对

## USB2CANFD Dual 裸板

- 采用用户指定的无外壳版本。由官方 STEP 删除壳体、壳体螺钉和导光柱，保留电路板及电子器件；不是用长方体代替。
- 导出文件：`board_model_inspection_usb2can_bare.step`，11 个有效实体。原始 0 基实体索引保留 1..11；删除 0、12..19。
- 包络 48.1 × 22 × 5.999 mm；原点不动：X=±24.05，Y=±11，Z=2.000001..7.999027。
- 板厚约 1.6 mm；4 个 Ø2 mm 安装孔，孔阵列 27 × 18 mm，中心 X=-13.05/+13.95、Y=±9。原模型孔径名义值不足以规定螺钉配合公差，实物安装前确认。
- Type-C 朝 −X 插拔；两个 CAN 及 UART 朝 +X 插拔；拆壳后应预留底部焊点/绝缘间隙，不把模型未显示的焊锡当作不存在。
- 使用手册第 3–4 页：Type-C 同时供电及通信；CAN 为两路独立 GH1.25 2P；UART 为 GH1.25 3P；两路可通过拨码接入 120 Ω 终端。**不得把电池 24 V 接入该模块 CAN 或 USB 供电端。**

## 用户自制转接板

- STEP 整体包络 32.0734 × 39.0907 × 7.1703 mm；裸 PCB 31.9787 × 39.0907 × 1.60005 mm。
- 源坐标 X=-0.081991..31.991364，Y=-39.103378..-0.0127，Z=-0.399949..6.770393；元件朝 +Z，焊脚低于 PCB 约 0.4 mm。
- 4 个 Ø3.000005 mm 孔：X=2.413005/29.464059，Y=-36.576073/-2.540005；孔距 27.051054 × 34.036068 mm。可以用 M2.5 配绝缘支承，不能默认孔已是 M3 的 3.2 mm 间隙孔。
- CN5：双芯 XT30PW-M，插拔朝 −Y；U1/U2：四芯 XT30PW-M，分别朝 −X/+X；CN3/CN4：GH1.25 2P，朝 +X。
- STEP 能确认连接器外形和位置，**不能确认铜箔网络、极性、电流能力、左右 CAN 是否隔离**。需要原理图或实物通断检查后定义接线表针脚。

## 数据边界

尺寸来自输入 STEP 的实体包络和圆柱孔面，不是照片比例估计。USB2CAN 工程 PDF 是带壳版本，50 × 26 × 9.5 mm 及单个 Ø4 孔仅记录来源，不用于本版裸板固定。文件和孔位详见同名 JSON。
''')


def render():
    """Render tessellated supplied geometry with Agg; no GUI document edits."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    previews = OUT / 'previews'
    previews.mkdir(parents=True, exist_ok=True)
    for key, path in FILES.items():
        shape = Part.read(str(path))
        if key == 'usb2can':
            shape = Part.makeCompound(shape.Solids[1:12])
            key = 'usb2can_bare'
        bb = shape.BoundBox
        for label, elev, azim in [('iso', 38, -60), ('top', 90, -90), ('front', 10, -90)]:
            fig = plt.figure(figsize=(13, 10), dpi=130)
            ax = fig.add_subplot(111, projection='3d')
            all_polys, all_colors = [], []
            for i, solid in enumerate(shape.Solids):
                vertices, faces = solid.tessellate(0.15)
                vertices = [tuple(v) for v in vertices]
                polys = [[vertices[n] for n in face] for face in faces]
                color = '#397C52' if key == 'distribution_pcb' and i == 0 else ('#D7BA57' if key == 'distribution_pcb' else '#718186')
                all_polys.extend(polys)
                all_colors.extend([color] * len(polys))
            collection = Poly3DCollection(all_polys, facecolors=all_colors, edgecolors=None, shade=True,
                                         linewidth=0, zsort='average')
            ax.add_collection3d(collection)
            ax.set_xlim(bb.XMin - 2, bb.XMax + 2)
            ax.set_ylim(bb.YMin - 2, bb.YMax + 2)
            ax.set_zlim(-2, max(bb.ZMax + 2, 10))
            ax.set_box_aspect((bb.XLength + 4, bb.YLength + 4, max(bb.ZMax + 4, 12)))
            ax.view_init(elev=elev, azim=azim)
            ax.set_xlabel('source X (mm)'); ax.set_ylabel('source Y (mm)'); ax.set_zlabel('source Z (mm)')
            if label == 'top':
                ax.zaxis.set_visible(False)
                ax.set_zticks([])
                ax.set_zlabel('')
            ax.set_title(key + ' / supplied STEP geometry / ' + label)
            fig.tight_layout()
            fig.savefig(previews / ('board_%s_%s.png' % (key, label)), facecolor='white')
            plt.close(fig)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--render', action='store_true')
    args = p.parse_args()
    inspect()
    if args.render:
        render()
