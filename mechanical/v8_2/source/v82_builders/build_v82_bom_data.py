"""Merge the V8.2 electronics into the frozen V8.1 BOM and audit native CAD.

Run only after V8.2 geometry and part_manifest.json are frozen.  V8.1 is read
only.  The per-instance hardware list is authoritative; unknown electrical
ratings and unselected parts are not silently counted as known zeroes.
"""
from __future__ import annotations

import collections
import copy
import hashlib
import json
from pathlib import Path
import re
import shutil
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "mechanical/v8_1"
OUT = ROOT / "mechanical/v8_2"
NEW_PARTS = {
    "electrical_service_carrier": ("配电通信一体安装架", "板卡和转换器先在机外预装；支柱下方保持绝缘与螺母净空，打印后清孔。"),
    "USB_hub_rear_clamp": ("背部USB扩展坞压托", "仅压持壳体；保留插口和上行线应力释放，不以连接器受力定位。"),
    "DC_charge_replaceable_plate": ("后充电口可换安装板", "预留导孔不等于DC母座安装孔；按所选母座图纸再扩孔或重打。"),
}
DEVICE_INFO = [
    ("E09", "Power_switch_M16_latching", "顶部自锁电源开关及插接座", "M16×1，法兰Ø17.8，AF19螺母；带插接座深47.5 mm", "用户开关尺寸图", "自锁型已确认；包含开关自带安装螺母、插接座及随件线，不重复计标准螺母。直流分断和LED电压待核实。"),
    ("E10", "USB_hub_104x30x10", "背部四口USB扩展坞", "104×30×10 mm；一体USB-A上行线150 mm，线径约4.8 mm", "用户扩展坞尺寸图", "四口向背部露出；接口速率、供电限制、型号待确认。上行线随件，不单独重复计。"),
    ("E11", "USB2CANFD_Dual_bare_official", "达妙双路USB2CANFD裸板", "DM-USB2CANFD Dual；使用提供模型中的裸板", "达妙USB2CANFD_Dual原始STEP及说明书V1.0", "壳体、原壳螺钉和导光柱不装入机器人；USB Type-C供电+数据，GH1.25 2P仅CAN。裸板可独立采购或由整机模块拆得，不双计。"),
    ("E12", "Distribution_PCB1_user_STEP", "用户配电转接板", "3D_PCB1_2026-09-28.step 对应板组件", "用户STEP，2026-09-28", "仅外形和孔位已建模；原理图、铜厚、网络、正负极及载流量未核实。板上连接器计入总成。"),
    ("E13", "DCDC_24_to_19_drawing_envelope", "24→19 V电源转换模块", "主体45×25×20 mm；总长58 mm；孔距51 mm，孔Ø4 mm", "用户DC/DC尺寸图", "按图示包络安装；功率、电流、输入范围、低压行为、耳片厚度均需实物核验。随件130 mm引线计入总成。"),
]


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def native_inventory(path):
    with zipfile.ZipFile(path) as archive:
        doc = ET.fromstring(archive.read("Document.xml"))
    types = {item.get("name"): item.get("type") for item in doc.find("Objects")}
    props = {}
    for item in doc.find("ObjectData"):
        values = {}
        for prop in item.findall("Properties/Property"):
            child = next(iter(prop), None)
            if child is not None:
                values[prop.get("name")] = child.get("value")
        props[item.get("name")] = values
    physical = {name for name, kind in types.items() if kind in ("Part::Feature", "Mesh::Feature")}
    excluded = {name for name in physical if any(props[name].get(key) == "routing_allowance"
                for key in ("Material", "KinematicRole", "GeometryKind"))}
    physical -= excluded
    module_of = {}
    for obj in doc.find("ObjectData"):
        if re.fullmatch(r"M\d\d", obj.get("name", "")):
            for child in obj.findall("Properties/Property[@name='Group']/LinkList/Link"):
                name = child.get("value")
                if name in physical:
                    if name in module_of:
                        raise ValueError(f"CAD object appears in multiple modules: {name}")
                    module_of[name] = obj.get("name")
    if physical - module_of.keys():
        raise ValueError(f"Physical objects outside assembly modules: {sorted(physical-module_of.keys())}")
    return physical, excluded, module_of, props


def standard_definition(family, size):
    """Procurement key includes the grade, finish and nondefault dimensions."""
    if family == "ISO4762":
        suffix = "|smooth_headD4.5" if size.startswith("M2.5x") else ""
        return (f"{family}|{size}|8.8|steel|black{suffix}", "内六角圆柱头螺钉",
                f"{family} {size.replace('x', '×')}", "钢8.8；发黑")
    if family == "ISO4032":
        dims = {"M3": ("AF5.5_t2.4", "AF5.5×2.4"), "M2.5": ("AF5_t2", "AF5×2"),
                "M1.6": ("AF3.2_t1.3", "AF3.2×1.3")}
        suffix, label = dims[size]
        return (f"{family}|{size}|8|steel|zinc|{suffix}", "六角螺母",
                f"{family} {size}；{label}", "钢8；镀锌")
    if family == "ISO7089":
        dims = {"M3": ("3.2x7x0.5", "Ø3.2/Ø7×0.5"), "M2.5": ("2.7x6x0.5", "Ø2.7/Ø6×0.5")}
        suffix, label = dims[size]
        return (f"{family}|{size}_{suffix}|200HV|steel|zinc", "普通平垫圈",
                f"{family} {size}；{label}", "钢200 HV；镀锌")
    raise ValueError(f"Unreviewed new hardware family: {family} {size}")


def refresh_manufactured(row, manifest):
    canonical = row["assembly_part_aliases"][0]
    member = manifest[canonical]
    source_dir = "step" if row["supply_type"] == "3D打印件" else "cnc"
    source = OUT / source_dir / f"{canonical}.step"
    target = OUT / row["source"]
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    if row["supply_type"] == "3D打印件":
        shutil.copy2(OUT / "print" / f"{canonical}.stl", target.with_suffix(".stl"))
    row["spec"] = " × ".join(str(v) for v in member["dimensions_mm"]) + " mm 包络；详见STEP"
    row["geometry_sha256"] = sha(target)


def write_manufacturing_list(rows, totals):
    kinds = ("3D打印件", "定制金属件", "标准件", "厂家目录件", "外购设备", "外购耗材", "待选型附件")
    lines = ["# V8.2 制造与采购清单", "", "一台样机净用量；采购备件比例在工作簿中默认0%。V8.1腿部制造件沿用。本版新增电气安装件并更新两片机壳及电器盘。", "",
             "|类别|型号数|已定义数量|", "|---|---:|---:|"]
    for kind in kinds:
        value = totals[kind]
        count = "部分待定" if kind == "待选型附件" else str(value["pieces"])
        lines.append(f"|{kind}|{value['types']}|{count}|")
    lines += ["", "新增设备质量为工程预算，不能替代称重。布线占位体不计为已采购线缆或实物质量。", ""]
    for kind in kinds:
        lines += [f"## {kind}", "", "|编号|名称|单机数量|规格/工艺|", "|---|---|---:|---|"]
        for row in rows:
            if row["supply_type"] != kind:
                continue
            name = f"[{row['name']}]({row['source']})" if kind in ("3D打印件", "定制金属件") else row["name"]
            spec = row["spec"] if kind != "定制金属件" else row["process"] + "；" + row["material"]
            lines.append(f"|{row['id']}|{name}|{row['quantity'] if row['quantity'] is not None else '待定'}|{spec.replace('|','／')}|")
        lines.append("")
    lines += ["## 制造分工与装配", "", "- 主承力杆、法兰、机架、轮辋与刚性IMU桥仍用金属加工；腿部销套及精密薄片沿用已审查V8.1工艺。", "- 电气安装架、扩展坞压托和充电接口板可PETG打印；安装架应力、转换器温升及打印孔公差需首件验收。", "- 前主壳增加顶部开关安装；后壳增加扩展坞窗口/托架与可换DC接口板；电器盘增加模块安装孔。使用本版更新导出，不从baseline_v81取旧件生产。", "- DC接口板导孔不能直接作为母座最终安装孔；主开关DC能力、转换器功率、分配板网络未确认，见ELECTRICAL_INTEGRATION.md。", "- 新增模块先在机外组装，再与电子盘/后盖装配；具体螺钉位置按装配体和模块说明。", ""]
    (OUT / "MANUFACTURING_LIST.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    baseline = read(BASE / "bom_master.json")
    build = read(OUT / "electrical_build.json")
    manifest = {row["part"]: row for row in read(OUT / "part_manifest.json")}
    native = OUT / "wheel_leg_v8_2.FCStd"
    physical, excluded, module_of, props = native_inventory(native)
    rows = copy.deepcopy(baseline["rows"])
    modules = dict(baseline["modules"], M07="前部配电通信服务模块", M08="后部USB扩展模块")

    # Retain references supporting unchanged legacy parts without presenting
    # those V8.1 reports as newly rerun V8.2 validation.
    baseline_dir = OUT / "baseline_v81"
    baseline_dir.mkdir(exist_ok=True)
    for filename in ("BODY_ASSEMBLY.md", "body_hardware_bom.json", "payload_interfaces.json"):
        shutil.copy2(BASE / filename, baseline_dir / filename)
        for row in rows:
            if filename in row["source"]:
                row["source"] = row["source"].replace(filename, "baseline_v81/" + filename)

    for row in rows:
        if row.get("assembly_part_aliases"):
            refresh_manufactured(row, manifest)
            changed = sorted(set(row["assembly_part_aliases"]) & set(build["changed_existing"]))
            if changed:
                row["notes"] += " V8.2已更新外形/接口，制造必须使用本版导出。"
                row["manufacturing_notes"] = row["notes"]

    next_part = 1 + max(int(row["id"][1:]) for row in rows if re.fullmatch(r"P\d+", row["id"]))
    for offset, (name, (label, note)) in enumerate(NEW_PARTS.items()):
        if name not in manifest:
            raise ValueError(f"V8.2 manufacturing export not frozen: {name}")
        ident = f"P{next_part+offset:02d}"
        row = dict(id=ident, module=module_of[name], name=label, spec="待读取STEP包络", quantity=1, unit="件",
                   material="PETG", process="FDM 3D打印", supply_type="3D打印件",
                   source=f"manufacturing/print/{ident}_{name}.step", status="样机首件；按接口与装配说明验收",
                   notes=note, manufacturing_notes=note, model_instances=[name], assembly_part_aliases=[name])
        refresh_manufactured(row, manifest)
        rows.append(row)

    standards = {row["standard_key"]: row for row in rows if row.get("standard_key")}
    next_hardware = 1
    for item in build["hardware"]:
        key, label, spec, material = standard_definition(item["family"], item["size"])
        if key not in standards:
            row = dict(id=f"EH{next_hardware:02d}", module=item["module"], name=label, spec=spec, quantity=0,
                       unit="件", material=material, process="采购", supply_type="标准件",
                       source="electrical_build.json；ELECTRICAL_INTEGRATION.md",
                       status="核对等级、头部包络及实物孔隙", notes="标准简化几何；首件确认工具空间和防松。",
                       standard_key=key, usage=[], model_instances=[])
            rows.append(row)
            standards[key] = row
            next_hardware += 1
        row = standards[key]
        row["quantity"] += 1
        row["model_instances"].append(item["name"])
        if "electrical_build.json" not in row["source"]:
            row["source"] += "；electrical_build.json"
        row.setdefault("usage", []).append(dict(module=item["module"], connection=item["name"], quantity=1,
                                                notes="V8.2电气模块新增连接"))
    for row in standards.values():
        assert sum(use["quantity"] for use in row["usage"]) == row["quantity"], row["id"]
        assert len(row["model_instances"]) == row["quantity"], row["id"]

    for ident, name, label, spec, source, note in DEVICE_INFO:
        mass = props[name].get("BudgetMassGrams")
        if mass is None:
            raise ValueError(f"New device lacks explicit mass budget: {name}")
        note += f" 工程质量预算{float(mass):g} g；未实测，不是厂家质量规格。"
        rows.append(dict(id=ident, module=module_of[name], name=label, spec=spec, quantity=1, unit="件",
                         material="外购电子/机电总成", process="整件采购", supply_type="外购设备",
                         source=source, status="机械包络已建模；电气/实物参数待核实", notes=note,
                         model_instances=[name], budget_mass_g=float(mass), mass_is_assumed=True))

    pending = {row["id"]: row for row in rows if row["supply_type"] == "待选型附件"}
    pending["T01"].update(name="电源保护与主回路分断器件", spec="依电气额定值选型，不能由AC开关标称替代",
                          notes="转换器/配电板/自锁开关已分别列E09、E12、E13；此项仅保留未确定的保护器件、必要的DC分断方案，不重复采购。")
    pending["T02"].update(name="后部充电DC母座", spec="插合DC5.5×2.1；面板安装孔/螺纹/载流待确定", quantity=1, unit="件",
                          notes="充电支路位于总开关前；背部右下可换板导孔待按母座图纸后加工。极性待核对。", status="已确定1件需求；型号未选定")
    pending["T03"]["notes"] = "USB/DP→HDMI/DC一分二及电源线、CAN/电机线、护线件长度规格待实配。扩展坞150mm上行线、开关随件线、转换器130mm引线及电机原配线包含于对应总成，不重复计。"
    for row in pending.values():
        row["source"] = "ELECTRICAL_INTEGRATION.md"
    rows.extend([
        dict(id="C03", module="M08", name="扩展坞防响软垫", spec="2×15×0.5 mm；两片，0.5为装配间隙目标",
             quantity=2, unit="片", material="薄弹性自粘片", process="采购/裁切", supply_type="外购耗材",
             source="MODULE_ASSEMBLY.md", status="装机实配压缩厚度", model_instances=[],
             notes="X−63..−61，Y中心±35，Z10..10.5；只压非端口壳边。未作为独立刚体建模，不由未压缩泡棉标称厚度替代实际间隙。"),
        dict(id="C04", module="M08", name="USB3数据延长线", spec="USB-A公→USB-A母；250 mm",
             quantity=1, unit="根", material="成品数据线", process="采购", supply_type="外购耗材",
             source="routing_allowances.json；ELECTRICAL_INTEGRATION.md", status="型号/接头包络待实配", model_instances=[],
             notes="与扩展坞原配150mm线组合绕过机内障碍；支持USB3数据，非仅充电线。长度含接头的定义与弯曲需实测；不重复计随坞原线。"),
        dict(id="T05", module="M04、M06", name="机壳及托盘护线套", spec="适用Ø10面板孔、3mm板厚；净孔≥7mm",
             quantity=3, unit="件", material="绝缘弹性体待定", process="选型/采购", supply_type="待选型附件",
             source="routing_allowances.json；MODULE_ASSEMBLY.md", status="已确定3处孔；型号未选定", model_instances=[],
             notes="两侧机壳出线孔各1、托盘过线孔1。需确认实际线束/预装插头能穿过，必要时选可开合护线套；不把设计孔当选定商品。"),
    ])
    for row in rows:
        if row.get("model_instances"):
            missing = set(row["model_instances"]) - physical
            if missing:
                raise ValueError(f"BOM refers to absent/nonphysical objects: {row['id']}: {sorted(missing)}")
            row["module"] = "、".join(sorted({module_of[name] for name in row["model_instances"]}))

    coverage = collections.defaultdict(list)
    for row in rows:
        for name in row.get("model_instances", []):
            coverage[name].append(row["id"])
    missing = sorted(physical - coverage.keys())
    duplicate = {name: ids for name, ids in coverage.items() if len(ids) != 1}
    if missing or duplicate:
        raise ValueError(f"CAD/BOM mismatch: missing={missing}, duplicate={duplicate}")
    assert len({row["id"] for row in rows}) == len(rows)
    totals = {kind: dict(types=sum(row["supply_type"] == kind for row in rows),
                        pieces=sum(row["quantity"] or 0 for row in rows if row["supply_type"] == kind),
                        unknown_quantity_rows=sum(row["quantity"] is None for row in rows if row["supply_type"] == kind))
              for kind in sorted({row["supply_type"] for row in rows})}
    data = dict(ready_for_workbook=True, revision="V8.2", date="2026-09-28", modules=modules, totals=totals, rows=rows,
                scope_note="1台样机净用量，备件默认0%。新增电气模块；未选DC母座与保护/线束标待定，设备质量为工程预算。",
                baseline_bom_sha256=sha(BASE / "bom_master.json"), native_sha256=sha(native),
                electrical_build_sha256=sha(OUT / "electrical_build.json"), part_manifest_sha256=sha(OUT / "part_manifest.json"))
    (OUT / "bom_master.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    audit = dict(physical_cad_objects=len(physical), excluded_routing_objects=sorted(excluded), covered_objects=len(coverage),
                 missing=missing, duplicate=duplicate, totals=totals,
                 baseline_bom_sha256=data["baseline_bom_sha256"], native_sha256=data["native_sha256"],
                 note="D435分析包络与官方mesh属于同一采购相机；原厂设备内部件不拆计。线束占位不算实物。")
    (OUT / "bom_cad_audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_manufacturing_list(rows, totals)
    print(json.dumps(dict(rows=len(rows), totals=totals, physical=len(physical), excluded=len(excluded)), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
