"""Publish the V8.3 static fit-trial print kit after CAD and BOM QA."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'mechanical/v8_3_print_trial'
CAD = ROOT/'mechanical/v8_3'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def verify_document_links():
    checked = []
    for path in OUT.rglob('*.md'):
        for target in re.findall(r'\]\(([^)\n]+)\)', path.read_text()):
            if target.startswith('#') or re.match(r'^[A-Za-z][A-Za-z0-9+.-]*:', target):
                continue
            target = target.strip('<>').split('#', 1)[0]
            resolved = (path.parent / target).resolve()
            assert resolved.is_relative_to(OUT.resolve()), (path, target)
            assert resolved.exists(), (path, target)
            checked.append(dict(document=str(path.relative_to(OUT)), target=target))
    (OUT/'source/document_link_validation.json').write_text(
        json.dumps(dict(all_passed=True, links=checked), ensure_ascii=False, indent=2)+'\n')


def calibration_diagram(manifest):
    coupon = manifest['calibration']
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="900" height="850" viewBox="0 0 900 850">',
           '<rect width="900" height="850" fill="white"/>',
           '<g font-family="Arial, sans-serif" fill="#173444">',
           '<text x="60" y="45" font-size="26">Optional hole-fit coupon / mm / 100% scale</text>',
           '<text x="60" y="78" font-size="18">Notch at upper left. This illustration is not a cutting template.</text>',
           '<path d="M90 740 L846 740 L846 96 L125 96 L125 131 L90 131 Z" fill="#ebf0f3" stroke="#173444" stroke-width="2"/>']
    for row in coupon['holes']:
        x, y, r = 90+7*row['x_mm'], 740-7*row['y_mm'], 3.5*row['diameter_mm']
        svg.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="white" stroke="#237c88" stroke-width="2"/>')
        label = f"D{row['diameter_mm']:.2f}"
        svg.append(f'<text x="{x}" y="{y+r+24}" text-anchor="middle" font-size="18">{label}</text>')
    svg += ['<text x="60" y="788" font-size="18">Bottom row: nominal; middle: +0.15 diameter; top: +0.30 diameter.</text>',
            '<text x="60" y="821" font-size="18">Use results for measured local fitting; never scale the whole robot.</text>', '</g></svg>']
    (OUT/'00_optional_calibration/孔位图.svg').write_text('\n'.join(svg)+'\n')


def docs(manifest):
    rows = manifest['rows']
    body = ['# V8.3 打印试装清单', '',
            f"共 **{len(rows)} 种、{sum(r['quantity'] for r in rows)} 件**定制零件。每种只提供一个STL；文件名`_x02`表示打印2件。左右不同件已分开编号，禁止自行镜像代替。", '',
            '全部STL均为毫米、100%名义尺寸，已摆到Z=0；不是预切片G-code。下列参数是试装起点，支撑仍须在切片器中检查。', '',
            '|编号|名称|单机数量|模块|摆放后X×Y×Z mm|层高/首层 mm|周壁/填充|STL|',
            '|---|---|---:|---|---|---|---|---|']
    for r in rows:
        p = r['print_profile']
        size = '×'.join(f'{v:.2f}' for v in r['validation']['dimensions_mm'])
        body.append(f"|{r['id']}|{r['name']}|{r['quantity']}|{r['module']}|{size}|{p['layer_mm']}/{p['first_layer_mm']}|{p['perimeters']}道/{p['infill_percent']}%|[下载]({r['stl']})|")
    body += ['', '## 薄件与支撑', '',
             '- LC05总厚0.20 mm，按0.20 mm首层单独切片。不得加厚成普通垫圈；若无法完整取下，用同厚片材按原轮廓裁切。',
             '- LC01～LC06为精细形状样件。模型中螺纹主要用底孔/外圆表达，打印后不能直接假定已有可用螺纹。',
             '- 前壳/后壳按维修分缝落床，内腔、固定小手和悬空耳片使用可移除支撑。不要把支撑封在不可达的腔内。',
             '- 小销和衬套建议多件分散同时打印，使用打印机既有最小层时间；不另给未经设备验证的速度或温度。',
             '- [逐件后处理及精配限制](FIT_NOTES.md)优先于外观上的“装得上”；支撑残留、翘曲和缩孔可能造成假干涉。', '']
    (OUT/'打印清单.md').write_text('\n'.join(body))
    manufacturing = ['# 原设计材料与制造工艺', '',
        '本次38类定制件全部提供PETG形状试装STL。下表保留原设计材料，供试装完成后安排金属加工；不代表强度或跳跃性能已经验证。原金属件不能凭塑料样件装得上就改为长期打印承力件。', '',
        '|编号|零件|数量|原设计材料|原设计工艺|',
        '|---|---|---:|---|---|']
    for row in rows:
        manufacturing.append(f"|{row['id']}|{row['name']}|{row['quantity']}|{row['material']}|{row['process']}|")
    (OUT/'制造工艺分类.md').write_text('\n'.join(manufacturing)+'\n')
    native_hash = manifest['native_sha256']
    guide = f'''# V8.3 全定制件打印试装包

用途：先用PETG验证零件分块、孔位、嵌套关系和装配顺序，之后再加工原金属承力件。电机和电子模块使用您已有的实物；螺钉、螺母、标准垫片、轴承、定位销使用真实标准件。

本包包含 **{len(rows)} 种定制零件、共 {sum(r['quantity'] for r in rows)} 件**的单件STL，包含原24种金属加工件。另附一个可选孔径校准板，不计入77件。每个文件只放一种零件，数量按文件名`_xNN`及清单；不要把所有STL导入同一打印盘直接开打。

## 快速入口

- [打印清单](打印清单.md)：编号、数量、模块、尺寸和建议层高。
- [原设计材料与工艺分类](制造工艺分类.md)：区分后续金属加工件与原本的打印件。
- `STL/`：左右腿、双腿通用件、机架、电器仓、前脸、外壳等分组。
- [标准件采购表](采购BOM.xlsx)及[采购CSV](采购清单.csv)：已有电机和电子模块不重复采购。标准件按完整单机需求列出，填已有库存后扣减；轮胎/耗材和待选型件另行核实。
- [精细零件与试装注意事项](FIT_NOTES.md)：0.20mm挡片、小销、衬套和螺纹的限制。
- [模块装配顺序](MODULE_ASSEMBLY.md)：优先机外预装，再整体组合。
- `STEP_reference/`：同一版名义实体，用于核对尺寸；不是另一个需要再打印的零件集合。
- [可选孔径校准板孔位图](00_optional_calibration/孔位图.svg)：4/6/8/19mm四列，直径附加0/.15/.30mm三排。

## 外观变化

白色圆角包边、黑色前脸、低矮胶囊形相机边框、橙色浅槽涂装区。主体棱边进一步增大圆角，两只加大的小机械手与前主壳一体，不增加运动机构。最终圆角和手部尺寸见[外观修改记录](DESIGN_CHANGES.md)，打印包络见打印清单。腿部、机架、内部设备和已布置的开关/USB/充电接口位置沿用V8.2。

STL不含颜色，白/黑/橙效果通过不同零件颜色和局部涂装实现；浅槽不是灯具。固定小手不能用于提起整机或支承机体。

## 打印与试装

1. 打印机沿用220×220×250mm、0.4mm喷嘴、PETG。导入单位为mm、比例100%，STL已置于打印床上；支撑、温度和速度采用您机器验证过的配置。
2. 先打印校准板、一个关节的小件及一对髋膝法兰，核对实物轴承/销/电机。不要用整件缩放去消除局部配合误差。
3. 再打印单腿、机架与电子支架，最后打印机壳和另一条腿。必要的扩孔、轻磨和攻牙逐项记录，避免将打印误差当作设计错误。
   可准备游标卡尺、小锉、手钻、与对应底孔匹配的M2/M3丝锥及M3板牙；已有工具不需重复购买。螺纹底孔不可当通孔任意扩钻。
4. LC05为实际0.20mm薄挡片；同厚片材替代属于可选措施，不能加厚或用普通M2平垫改变轴向堆叠。
5. 全塑料样机仅用于断电、由桌面/治具独立支承的手动试装；不能让打印腿承受整机重量，也不进行通电行走或跳跃。FDM样件不能验证原金属件的微米级配合和强度。

## 检查范围

所有单件STL已检查封闭、非流形、自交、法向、落床及打印包络；只做刚体旋转平移，未放缩、扩孔或更改定制件名义尺寸。切片器支撑和薄层成形仍须预览确认；没有提供未经实机验证的G-code。

STL导出按毫米约定，参见[FreeCAD官方导出说明](https://github.com/FreeCAD/FreeCAD-documentation/blob/main/wiki/Export_to_STL_or_OBJ.md)；FDM配合需实测工艺，参见[Prusa原厂设计指南](https://help.prusa3d.com/article/modeling-with-3d-printing-in-mind_164135)。

源CAD SHA256：`{native_hash}`。`print_manifest.json`保存逐件源文件和STL哈希、摆放变换、打印参数及检查结果。V8.2原文件保持不变。
'''
    (OUT/'README.md').write_text(guide)


def main():
    manifest = read(OUT/'print_manifest.json')
    validation = read(OUT/'print_validation.json')
    assert validation['all_passed'] and manifest['part_types'] == len(manifest['rows'])
    assert sha(Path(manifest['source_native'])) == manifest['native_sha256']
    assert read(CAD/'shell_validation.json')['all_pass'], 'Exterior validation must pass'
    bom_qa=read(OUT/'verification/bom/workbook_qa.json')
    assert not bom_qa['formula_errors'] and bom_qa['visual_review']['all_worksheets_reviewed']
    source_rows = {r['id']: r for r in read(CAD/'bom_master.json')['rows']}
    purchase = read(OUT/'bom_purchase.json')
    expected_standard = {r['id'] for r in source_rows.values()
                         if r['supply_type'] in ('标准件', '厂家目录件')}
    assert {r['id'] for r in purchase['standard_purchase']} == expected_standard
    for row in purchase['standard_purchase']:
        for key in ('name', 'spec', 'quantity', 'material'):
            assert row[key] == source_rows[row['id']][key], (row['id'], key)
    assert sum(r['quantity'] for r in purchase['standard_purchase']) == bom_qa['standard_pieces']
    for r in manifest['rows']:
        assert sha(OUT/r['stl']) == r['stl_sha256']
        assert sha(OUT/r['reference_step']) == r['source_step_sha256']
    for required in ('采购BOM.xlsx', '采购清单.csv', 'FIT_NOTES.md', 'bom_purchase.json',
                     'MODULE_ASSEMBLY.md', 'source/assembly_reference_index.json'):
        assert (OUT/required).is_file(), required
    docs(manifest)
    calibration_diagram(manifest)
    shutil.copy2(CAD/'DESIGN_CHANGES.md', OUT/'DESIGN_CHANGES.md')
    previews = OUT/'previews'
    previews.mkdir(exist_ok=True)
    if (CAD/'previews').exists():
        for p in (CAD/'previews').glob('*.png'):
            shutil.copy2(p, previews/p.name)
    snapshot = OUT/'source/builders'
    snapshot.mkdir(parents=True, exist_ok=True)
    for name in ('export_v83_print_trial.py', 'package_v83_print_trial.py'):
        shutil.copy2(ROOT/'tools'/name, snapshot/name)
    (OUT/'source/source_bom.json').write_text((CAD/'bom_master.json').read_text())
    shutil.copy2(CAD/'shell_validation.json', OUT/'source/shell_validation.json')
    verify_document_links()
    files = sorted(p for p in OUT.rglob('*') if p.is_file()
                   and p.suffix not in ('.FCBak', '.pyc') and p.name != 'package_manifest.json')
    release = dict(native_sha256=manifest['native_sha256'], print_skus=manifest['part_types'],
                   print_pieces=manifest['required_pieces'], optional_calibration=1,
                   files=[dict(path=str(p.relative_to(OUT)), bytes=p.stat().st_size, sha256=sha(p)) for p in files])
    (OUT/'package_manifest.json').write_text(json.dumps(release, ensure_ascii=False, indent=2)+'\n')
    archive = ROOT/'mechanical/wheel_leg_v8_3_print_trial.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for p in files+[OUT/'package_manifest.json']:
            z.write(p, Path('v8_3_print_trial')/p.relative_to(OUT))
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        assert len([n for n in z.namelist() if n.endswith('.stl') and '/STL/' in n]) == manifest['part_types']
    digest = sha(archive)
    archive.with_suffix('.sha256').write_text(digest+'  '+archive.name+'\n')
    print(json.dumps(dict(archive=str(archive), bytes=archive.stat().st_size, sha256=digest,
                          print_types=manifest['part_types'], print_pieces=manifest['required_pieces']), indent=2))


if __name__ == '__main__':
    main()
