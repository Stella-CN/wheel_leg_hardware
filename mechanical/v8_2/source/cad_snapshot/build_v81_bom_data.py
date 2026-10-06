"""Reconcile the prototype BOM with every physical V8.1 CAD instance."""
from __future__ import annotations

import collections
import json
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'mechanical/v8_1'


def read(name):
    return json.loads((OUT / name).read_text())


def main():
    manifest = read('part_manifest.json')
    modules = read('module_manifest.json')['modules']
    module_of = {name: m['id'] for m in modules for name in m['objects']}
    module_labels = {m['id']: m['name'] for m in modules}
    with zipfile.ZipFile(OUT / 'wheel_leg_v8_1.FCStd') as archive:
        doc = ET.fromstring(archive.read('Document.xml'))
    physical = {o.get('name') for o in doc.find('Objects')
                if o.get('type') in ('Part::Feature', 'Mesh::Feature')}
    label_map = {}
    for obj in doc.find('ObjectData'):
        prop = obj.find("Properties/Property[@name='Label']/String")
        if prop is not None:
            label_map[prop.get('value')] = obj.get('name')

    def resolve(raw):
        if raw in physical:
            return raw
        name = label_map.get(raw.replace('_', ' '))
        if name not in physical:
            raise ValueError(f'BOM instance absent from native CAD: {raw}')
        return name

    aliases = {r['part']: r['part'] for r in manifest}
    for group in read('manufacturing_aliases.json')['aliases']:
        assert group['passed']
        for name in group['instances']:
            aliases[name] = group['canonical']
    for group in read('leg_mirror_equivalence.json')['results']:
        if group['shared_manufacturing_sku'] and group['part'] != 'wheel_rim':
            aliases[group['part'] + '_left'] = group['part']
    grouped = collections.defaultdict(list)
    for row in manifest:
        grouped[aliases[row['part']]].append(row)

    names = {
        'chassis_belly_plate': '机架底板', 'chassis_hip_frame_right': '右承力侧框',
        'chassis_hip_frame_left': '左承力侧框', 'chassis_front_crossframe': '前后通用横框',
        'chassis_front_shell': '前主壳', 'chassis_rear_cover': '后检修壳',
        'display_front_bezel': '屏幕相机前脸板', 'shoulder_fairing_right': '左右通用肩罩',
        'battery_tray': '电池托', 'electronics_tray': '电器托盘',
        'Jetson_base_retainer_right': 'Jetson右夹座', 'Jetson_base_retainer_left': 'Jetson左夹座',
        'D435_embedded_bracket': 'D435一体后座', 'HI13R2_rigid_bridge': 'IMU刚性安装桥',
        'display_case_cradle_right': '屏幕右托夹', 'display_case_cradle_left': '屏幕左托夹',
        'hip_stator_mount': '左右通用髋定子座', 'hip_rotor_cnc': '左右通用髋转子法兰',
        'knee_stator_cnc': '右膝定子套杯', 'knee_stator_cnc_left': '左膝定子套杯',
        'OB_inner_carrier': '右OB内框', 'OB_inner_carrier_left': '左OB内框',
        'OB_outer_shell': '右OB外包主臂', 'OB_outer_shell_left': '左OB外包主臂',
        'OA_one_piece': '左右通用OA曲柄', 'AC_bearing_link': '左右通用AC轴承连杆',
        'CW_one_piece': '右CW下臂', 'CW_one_piece_left': '左CW下臂', 'wheel_rim': '通用轮辋',
    }
    rows = []
    for number, (canonical, members) in enumerate(grouped.items(), 1):
        process = members[0]['process']
        instances = []
        for member in members:
            name = member['part']
            if name == 'wheel_rim':
                instances += ['wheel_rim_left', 'wheel_rim_right']
            elif name in physical:
                instances.append(name)
            else:
                instances.append(resolve(name + '_right'))
        quantity = sum(m['quantity'] for m in members)
        assert len(instances) == quantity
        ident = f'P{number:02}'
        directory = 'print' if process == 'PETG' else 'metal'
        target = OUT / 'manufacturing' / directory
        target.mkdir(parents=True, exist_ok=True)
        filename = f'{ident}_{canonical}'
        source_dir = 'step' if process == 'PETG' else 'cnc'
        shutil.copy2(OUT / source_dir / f'{canonical}.step', target / f'{filename}.step')
        if process == 'PETG':
            shutil.copy2(OUT / 'print' / f'{canonical}.stl', target / f'{filename}.stl')
        notes = ('0.4喷嘴PETG；先打印孔/螺母槽试片，参见公差与装配说明。'
                 if process == 'PETG' else
                 '承力或刚性定位件；6061-T6 CNC，螺纹/轴承座/薄耳需精加工；不可直接替换普通钣金或PETG。')
        if quantity == 2:
            notes += '同一制造型号加工2件，按装配方向翻转；等形证据见别名审查。'
        if canonical == 'D435_embedded_bracket':
            notes += '默认25.05深相机；26.05深相机用alternates替代，二选一，仅计1件。'
        if canonical == 'battery_tray':
            notes += '按WHEELTEC电池85.6×61.6×42、含磁底44.5设计；装拆及穿带见BATTERY.md。'
        if canonical == 'display_front_bezel':
            notes += '5寸GK-HD屏，装机前核实四角接触金属外框。'
        rows.append(dict(id=ident, module='、'.join(sorted({module_of[n] for n in instances})),
            name=names[canonical], spec=' × '.join(str(v) for v in members[0]['dimensions_mm'])+' mm 包络；详见STEP',
            quantity=quantity, unit='件', material='PETG' if process == 'PETG' else '6061-T6铝合金',
            process='FDM 3D打印' if process == 'PETG' else 'CNC铣削/车铣',
            supply_type='3D打印件' if process == 'PETG' else '定制金属件',
            source=f'manufacturing/{directory}/{filename}.step', status='样机首件；按公差说明验收',
            notes=notes, manufacturing_notes=notes, model_instances=instances,
            assembly_part_aliases=[m['part'] for m in members]))

    standards = {}
    for item in read('leg_hardware_bom.json')['bom']:
        row = dict(item)
        row['supply_type'] = {'standard': '标准件', 'catalog': '厂家目录件', 'custom': '定制金属件'}[row['supply_type']]
        row['model_instances'] = [resolve(n) for n in row['model_instances']]
        if row['standard_key']:
            standards[row['standard_key']] = row
        else:
            row['process'] = '精密薄板切割/整平' if row['id'] in ('LC01', 'LC05') else 'CNC车削/精磨/二次加工'
            source = OUT / row['source']
            destination = OUT / 'manufacturing/metal' / f"{row['id']}_{source.name}"
            shutil.copy2(source, destination)
            row['source'] = str(destination.relative_to(OUT))
            rows.append(row)
    body = read('body_hardware_bom.json')
    for number, item in enumerate(body['standard_rows'], 1):
        key = item['key']
        family = key.split('|')[0]
        names_std = {'DIN7991': '沉头内六角螺钉', 'ISO4762': '内六角圆柱头螺钉',
                     'ISO4032': '六角螺母', 'ISO7089': '普通平垫圈'}
        usage = [dict(module=u['module'], connection=u['location'], quantity=u['quantity'], notes=u['note']) for u in item['usages']]
        instances = [resolve(n) for u in item['usages'] for n in u['cad_names']]
        if key in standards:
            row = standards[key]
            row['quantity'] += item['quantity']
            row['usage'] += usage
            row['model_instances'] += instances
            row['notes'] += ' 机身用法见BODY_ASSEMBLY.md。'
        else:
            row = dict(id=f'BH{number:02}', module='', name=names_std[family],
                spec=f"{family} {item['size']}", quantity=item['quantity'], unit='件',
                material=f"钢{item['grade']}；"+('发黑' if item['finish']=='black' else '镀锌'),
                process='采购', supply_type='标准件', source='BODY_ASSEMBLY.md；body_hardware_bom.json',
                status='按列明头径/强度等级采购', notes=item['notes'], standard_key=key,
                usage=usage, model_instances=instances)
            standards[key] = row
    for row in standards.values():
        assert sum(u['quantity'] for u in row['usage']) == row['quantity'], row['id']
        assert len(row['model_instances']) == row['quantity'], row['id']
        row['module'] = '、'.join(sorted({module_of[n] for n in row['model_instances']}))
        rows.append(row)
    for row in rows:
        row['module'] = '、'.join(sorted({module_of[n] for n in row['model_instances']}))

    devices = [
        ('E01','J4310关节电机','DM-J4310-2EC，24V，V1.1驱动',4,'原厂总成','source/hardware/j4310_drawing.txt',
         ['J4310_hip_left','J4310_hip_right','J4310_knee_left','J4310_knee_right'],'电机内部零件与紧固件不拆计。'),
        ('E02','轮毂电机','DM-H6215',2,'原厂总成','source/hardware/h6215_drawing.txt',['H6215_left','H6215_right'],'轮辋紧固螺钉已计入LH01。'),
        ('E03','开发套件','Jetson Orin Nano官方开发套件',1,'原厂总成','payload_interfaces.json',['Jetson_Orin_Nano_official'],'含原厂底座/散热器；按实际版本核对接口。'),
        ('E04','深度相机','RealSense D435',1,'原厂总成','payload_interfaces.json',['D435_clearance_envelope','D435_official_ROS_mesh'],'一个设备，两种CAD表达；后座深度按实物25.05/26.05二选一。'),
        ('E05','惯性测量单元','超核HI13R2 USB版',1,'原厂总成','https://www.hipnuc.com/hi13.html',['HI13R2_official'],'俯视名义原点在机体中心；安装后标定轴向。'),
        ('E06','5寸显示器','GK-HD V3，122×78×14.5 mm',1,'原厂总成','source/display/显示器规格书.pdf，第2页',['Display_GK_HD_5in_supplier_envelope'],'采用外壳托夹；供应商未给5寸安装孔。200g为质量估计。'),
        ('E07','E626S电池包及磁吸底座','用户确认24V等级E626S；本体85.6×61.6×42 mm，含磁底44.5 mm',1,'原厂封装电池/磁吸底座','source/battery/WHEELTEC_battery_user_drawing.png；source/battery/WHEELTEC_24V_manual.pdf',
         ['Battery_WHEELTEC_drawing_envelope'],'用户确认选E626S；官方337g/22.2V/2550mAh/6A持续/13A瞬时。337g是否含底座未明，安装仍按400g预算。DC5.5-2.1充放共口，插头及脉冲时长需复核。'),
        ('E08','弹性轮胎','外径100/内径86/宽32 mm',2,'橡胶/弹性体待选','design_parameters.json',['elastic_tyre_left','elastic_tyre_right'],'按轮辋匹配；硬度、摩擦、固定方式和跳跃耐久需样件确认。'),
    ]
    for ident, name, spec, qty, material, source, instances, note in devices:
        rows.append(dict(id=ident,module='、'.join(sorted({module_of[n] for n in instances})),name=name,spec=spec,
            quantity=qty,unit='件',material=material,process='整件采购',supply_type='外购设备',source=source,
            status=('型号用户已确认；含底质量/插头待测' if ident=='E07' else '规格待选定' if ident=='E08' else '按指定版本采购并测量'),notes=note,model_instances=instances))
    for ident, name, spec, qty, module, material, note in [
        ('C01','屏幕后软垫','4×8×0.5 mm，4块',4,'M05','薄弹性自粘片','0.5为最终压缩厚度目标；仅支撑金属外框，不挤压屏幕玻璃。'),
        ('C02','电池束带','10×300 mm；底部单层厚≤1.0 mm',2,'M04','绝缘魔术贴束带','机外穿带固定；保守绕行231mm加顶部搭接≥50mm；扣头/搭接避DC口并核实真实厚度。'),
    ]:
        rows.append(dict(id=ident,module=module,name=name,spec=spec,quantity=qty,unit='件',material=material,
            process='采购/裁切',supply_type='外购耗材',source='body_hardware_bom.json',status='装机实配',notes=note,model_instances=[]))
    for number, (name, note) in enumerate([
        ('电源转换与配电','需按Jetson/屏幕/相机实际供电确定DC-DC、配电板与安装空间。'),
        ('保险丝、开关与急停','按电池最大电流、导线及驱动器电压电流规格选择。'),
        ('线束、插头与绝缘护线件','CAN/USB/HDMI/电源线长度、弯曲半径、腿线活动余量及电池绝缘垫材需实物布线确认。'),
        ('螺纹防松与标记耗材','选与铝、钢及邻近塑料兼容的可拆防松工艺；扭矩经样件验证。'),
    ],1):
        rows.append(dict(id=f'T{number:02}',module='整机',name=name,spec='待电气方案与实物确认',quantity=None,unit='待定',
            material='待定',process='选型/采购',supply_type='待选型附件',source='本次设计待定项',status='未选型，不计入已定数量',notes=note,model_instances=[]))

    coverage = collections.defaultdict(list)
    for row in rows:
        for name in row['model_instances']:
            coverage[name].append(row['id'])
    missing = sorted(physical - coverage.keys())
    duplicate = {name: ids for name, ids in coverage.items() if len(ids) != 1}
    assert not missing and not duplicate, (missing, duplicate)
    totals = {kind: dict(types=sum(r['supply_type']==kind for r in rows),
              pieces=sum(r['quantity'] or 0 for r in rows if r['supply_type']==kind))
              for kind in sorted({r['supply_type'] for r in rows})}
    result = dict(ready_for_workbook=True,revision='V8.1',date='2026-09-28',
        scope_note='1台样机净用量。标准件与厂家目录件合计238件；备件默认0%。电池选E626S；插头/线束待实物确认。',
        modules=module_labels,totals=totals,rows=rows)
    (OUT/'bom_master.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    (OUT/'bom_cad_audit.json').write_text(json.dumps(dict(physical_cad_objects=len(physical),
        covered_objects=len(coverage),missing=missing,duplicate=duplicate,totals=totals,
        note='D435 mesh and analysis solid are one purchased camera, not two. Vendor-internal components are not counted separately.'),ensure_ascii=False,indent=2)+'\n')
    lines=['# V8.1 制造与采购分类清单','','数量按一台样机净用量。制造目录中的共用件只保留一份几何，按BOM数量制造，勿重复计算左右装配导出。','',
           '|类别|型号数|件数|','|---|---:|---:|']
    order=('3D打印件','定制金属件','标准件','厂家目录件','外购设备','外购耗材','待选型附件')
    for kind in order:
        t=totals[kind]
        lines.append(f"|{kind}|{t['types']}|{t['pieces'] if kind!='待选型附件' else '待定'}|")
    lines+=['','电池按用户确认的24V等级E626S及新图纸；接口核对见BATTERY_SOURCE_REVIEW.md。未知附件数量不伪记为零。','']
    for kind in order:
        lines += [f'## {kind}','','|编号|零件|数量|规格/工艺|','|---|---|---:|---|']
        for r in rows:
            if r['supply_type']!=kind:
                continue
            name=f"[{r['name']}]({r['source']})" if kind in ('3D打印件','定制金属件') else r['name']
            spec=(r['process']+'；'+r['material']) if kind=='定制金属件' else r['spec']
            lines.append(f"|{r['id']}|{name}|{r['quantity'] if r['quantity'] is not None else '待定'}|{spec.replace('|','／')}|")
        lines.append('')
    lines += ['## 加工分工','','- 承力杆、法兰、髋座、轮辋、机架和IMU桥使用6061-T6 CNC。轴承台阶、薄叉耳及包夹结构不能用普通板件下料直接代替。',
        '- LC02轴销、LC03/LC04青铜带肩套、LC06限位肩销采用车削、精磨/钻攻及必要的二次铣削。',
        '- LC01压盖和LC05薄防脱片适合精密薄板切割、去毛刺和整平；LC05仅0.20mm，需确认工艺能力。',
        '- PETG文件已摆正并校核220×220×250mm包络；先做孔槽试片，壳体及托盘局部需可拆支撑。新电池托仍1件，保留4颗M3×8及2条束带。',
        '- D435的26.05mm深备选后座位于alternates，只替换默认件，不增加单机数量。','',
        '配合见[腿部公差](LEG_FITS.md)、[机身细节](BODY_ASSEMBLY.md)和[电池安装](BATTERY.md)。装配顺序见[模块总装](MODULE_ASSEMBLY.md)。STEP单位mm，螺纹主要以底孔表达，必须按书面规格完成钻攻。','']
    (OUT/'MANUFACTURING_LIST.md').write_text('\n'.join(lines))
    print(json.dumps(totals,ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
