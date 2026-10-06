"""Audit every modelled left/right leg hardware instance into procurement rows."""
from __future__ import annotations

import json
from pathlib import Path

import build_printable_robot as cad
import cad_v81_coupling as coupling
import cad_v81_leg as leg
import cad_v8_chassis as chassis

OUT = cad.ROOT/"mechanical/v8_1"
SOURCES = {
    "iso4762": "https://www.norelem.es/medias/07160-ST-Datasheet-32102-Socket-head-screws-DIN-EN-ISO-4762-enhanced-steel-en.pdf?context=bWFzdGVyfHJvb3R8Mjc4MTEzfGFwcGxpY2F0aW9uL3BkZnxhREEyTDJobE5TODVORGt5TmpreE9ERXlNemd5THpBM01UWXdYMU5VWDBSaGRHRnphR1ZsZEY4ek1qRXdNbDlUYjJOclpYUmZhR1ZoWkY5elkzSmxkM05mUkVsT1gwVk9YMGxUVDE4ME56WXlYMlZ1YUdGdVkyVmtYM04wWldWc0xTMWxiaTV3WkdZfGM1Y2MxMzYwMDFiYzUzMDY3ZDQ4NTAxMWJhZmE0NTlmZWI2NjQ4OTY3NGI0MGRjZWY2NjU5MTZjMzJmODI1OTI",
    "din7991": "https://www.bossard.com/us-en/eshop/screws-and-bolts-with-internal-drive/hex-socket-flat-countersunk-head-screws-fully-threaded/p/20/",
    "slh": "https://www.nbk1560.com/images/en-US/product/lowsmallheadscrew/SLH-SD/SLH-SD_1.pdf",
    "sets": "https://www.nbk1560.com/en-US/products/specialscrew/nedzicom/spacesaving/SETS/",
    "pin": "https://www.norelem.mx/doc/mx/es/did.97191/03320_Datasheet_2785_Pasadores_cil_ndricos_DIN_6325--es.pdf",
    "pin_length_tolerance": "https://www.ganternorm.com/en/products/New-products/New-products/DIN-6325-Dowel-Pins-Steel",
    "bearing": "https://www.nsk.com/jp-ja/engineering/products/bearings/ball-bearings/deep-groove-ball-bearings/extra-small-ball-bearings-and-miniature-ball-bearings-metric-series/626zz1-esm-md.html",
    "washer": "https://www.obo.de/de-de/produkte/unterlegscheibe-9-4-3-0-8-m4-3402045.html",
    "nut": "https://www.norelem.com/doc/hu/hu/did.294335/Normenuebersicht-der-Verbindungselemente-NLM_HU.pdf",
    "j4310": str(cad.ROOT / "references/DM-J4310-2EC/2D图纸/DM_J4310_V1.1 减速电机 标注.PDF"),
    "h6215": str(cad.ROOT / "references/DM-H6215/2D图纸/6215_轮毂电机20251203.PDF"),
}


def row(identifier, name, spec, material, supply_type, source, notes, key=None):
    return dict(id=identifier, module="左右腿", name=name, spec=spec,
                quantity=0, unit="件", material=material,
                process="采购" if supply_type in ("standard", "catalog") else "金属加工",
                supply_type=supply_type, source=source, status="原型装配规格；未验证跳跃强度",
                notes=notes, standard_key=key, usage=[], model_instances=[])


def main():
    cad.configure(OUT)
    rows = {
        "m3x8": row("LH01", "内六角圆柱头螺钉", "ISO4762 M3×8", "钢8.8；发黑", "standard", SOURCES["iso4762"], "通用长度；用于髋转子法兰、轮电机定子和轮辋。轮辋12枚为V8.1补齐。", "ISO4762|M3x8|8.8|steel|black"),
        "m3x16": row("LH02", "内六角圆柱头螺钉", "ISO4762 M3×16", "钢8.8；发黑", "standard", SOURCES["iso4762"], "OA到膝转子；夹持12、啮合4 mm，不可用M3×8代替。", "ISO4762|M3x16|8.8|steel|black"),
        "slh6": row("LH03", "低头小头螺钉", "NBK SLH-M3-6-SD；头Ø4.5×2，内六角2", "SWCH45K；8.8；发黑", "catalog", SOURCES["slh"], "膝后定子4/侧及OB前定子6/侧；保留小头以避让紧凑孔壁，非普通ISO4762。", "NBK|SLH-M3-6-SD|8.8|black_oxide"),
        "slh8": row("LH04", "低头小头螺钉", "NBK SLH-M3-8-SD；头Ø4.5×2，内六角2", "SWCH45K；8.8；发黑", "catalog", SOURCES["slh"], "两法兰侧向锁紧。厂家1.4 N·m是螺钉上限，不是该铝接头装配扭矩。", "NBK|SLH-M3-8-SD|8.8|black_oxide"),
        "sets": row("LH05", "超薄头内六角花形螺钉", "NBK SETS-M2-4；头Ø4×0.5，TX4", "SUSXM7；A2；原厂本色", "catalog", SOURCES["sets"], "轴承压盖18枚+轴销两端防脱12枚。原厂最大0.15 N·m不可直接当成铝压盖或薄挡片的最终扭矩。", "NBK|SETS-M2-4|SUSXM7_A2|plain"),
        "cs3x10": row("LH06", "沉头内六角螺钉", "DIN7991 M3×10；头≤Ø6×1.7，90°，内六角2", "钢010.9；发黑", "standard", SOURCES["din7991"], "OB内框到外壳；DIN已撤销但仍有目录件。不得不检查就换ISO10642大头。", "DIN7991|M3x10|010.9|steel|black|headD6_k1.7"),
        "cs3x6": row("LH07", "沉头内六角螺钉", "DIN7991 M3×6；头≤Ø6×1.7，90°，内六角2", "钢010.9；发黑", "standard", SOURCES["din7991"], "髋电机定子到髋座；深5的电机孔中名义啮合3。", "DIN7991|M3x6|010.9|steel|black|headD6_k1.7"),
        "cs4x12": row("LH08", "沉头内六角螺钉", "DIN7991 M4×12；头≤Ø8×2.3，90°，内六角2.5", "钢010.9；发黑", "standard", SOURCES["din7991"], "腿模块到机身侧框；每侧4枚，整机总装时使用，机身BOM不要重复。", "DIN7991|M4x12|010.9|steel|black|headD8_k2.3"),
        "washer4": row("LH09", "普通平垫圈", "ISO7089 M4；Ø4.3/Ø9×0.8", "钢200HV；镀锌", "standard", SOURCES["washer"], "外形来源为厂家DIN125A表；采购选200HV等级，不能拿未标硬度或软塑料垫圈替换。每个M4接口一片。", "ISO7089|M4|200HV|steel|zinc"),
        "nut4": row("LH10", "六角螺母", "ISO4032 M4；AF7×3.2", "钢8级；镀锌", "standard", SOURCES["nut"], "髋座总装用；与M4沉头螺钉配对，现场防松工艺确认后做扭矩标记。", "ISO4032|M4|8|steel|zinc"),
        "pin4": row("LH11", "定位圆柱销", "DIN6325 Ø4m6×10（Norelem03320-04X10）", "工具钢；淬硬磨削60±2HRC；本色", "standard", SOURCES["pin"], "3/髋法兰；取代旧定制9mm。只控制装入法兰7.00±0.05；外露名义3、随实际长度变化（详公差文档），三销按实物检具确认，禁止螺钉强拉。", "DIN6325|4m6x10|hardened_60HRC|ground_plain"),
        "bearing": row("LH12", "深沟球轴承", "NSK626ZZ1；6×19×6；金属防尘盖", "原厂轴承钢", "catalog", SOURCES["bearing"], "A、B、C各1/腿，普通游隙版本；不得仅按626尺寸采购C3/MC3等异游隙版本。额定载荷不等于整机跳跃能力。", "NSK|626ZZ1|standard_clearance|ZZ"),
        "keeper": row("LC01", "轴承外圈压盖", "Ø28/Ø16.8×0.8；3-Ø2.2 PCD24", "不锈钢板", "custom", "metal_hardware/bearing_keeper_D28_D16_8_t0_8.step", "激光/精密板切割后去毛刺整平；薄型结构不够放DIN472槽+保边，保留压盖。"),
        "female": row("LC02", "双端内螺纹关节轴销", "Ø6×14.05；两端M2×0.4完整牙≥4.3；底孔深4.6", "40Cr调质后精磨；具体硬度按试验定", "custom", "metal_hardware/female_pin_D6_L14_05.step", "六个A/B/C轴同一种；非标准肩螺栓。外形冻结，轴径按轴承实测选配；名义中心实心段4.85 mm。"),
        "inner": row("LC03", "内侧一体带肩衬套", "铜套Ø8/Ø6.05×2.5＋肩Ø8.4/Ø6.2×1.25；总长3.75", "轴承青铜CuSn12", "custom", "metal_hardware/flanged_bush_inner_D8_D8p4_L3p75.step", "精密车削；Ø8段朝内叉耳，Ø8.4肩朝轴承。替代独立铜套+1.25隔圈；轻压装，不用窄肩传递轴承预载。"),
        "outer": row("LC04", "外侧一体带肩衬套", "肩Ø8.4/Ø6.2×1.70＋铜套Ø8/Ø6.05×2.5；总长4.20", "轴承青铜CuSn12", "custom", "metal_hardware/flanged_bush_outer_D8_D8p4_L4p20.step", "精密车削；Ø8段朝外叉耳，Ø8.4肩朝轴承。名义游隙0.05留在肩与轴承内圈之间，避免压盖/轴销锁死轴承。"),
        "plate": row("LC05", "轴销薄防脱挡片", "Ø9/Ø2.2×0.20", "钢精密垫片料", "custom", "metal_hardware/axis_washer_D9_d2_2_t0_2.step", "定制功能挡片，不是标准采购垫片。单一规格12件，避免用大/小标准垫片叠层增加散件。"),
        "stop": row("LC06", "OA装配限位肩销", "M3×3；Ø4肩长4.2；Ø7×1头，0.8槽", "钢；强度待验证", "custom", "metal_hardware/OA_angular_stop_M3_D4.step", "只做装配角限位；禁止把它当作带电撞停或落地限位件。"),
    }

    def classify(name):
        if name.startswith("coupling_rotor_ISO4762_"): return "m3x8", "髋转子法兰→髋转子"
        if name.startswith("H6215_stator_"): return "m3x8", "CW→H6215定子"
        if name.startswith("wheel_rim_ISO4762_"): return "m3x8", "轮辋→H6215转子"
        if name.startswith("OA_rotor_"): return "m3x16", "OA→膝转子"
        if name.startswith("coupling_knee_"): return "slh6", "定子杯→膝定子后端"
        if name.startswith("OB_stator_"): return "slh6", "OB内框→膝定子前端"
        if name.startswith("coupling_radial_"): return "slh8", "两法兰径向锁紧"
        if name.startswith("keeper_"): return "sets", "A/B/C轴承外圈压盖"
        if name.startswith("axis_") and "SETS" in name: return "sets", "A/B/C轴销两端防脱"
        if name.startswith("OB_shell_"): return "cs3x10", "OB内框→OB外壳"
        if name.startswith("hip_stator_"): return "cs3x6", "髋定子→髋座"
        if name.startswith("hip_case_") and "M4x12" in name: return "cs4x12", "髋座→机身侧框"
        if name.startswith("hip_case_") and "washer" in name: return "washer4", "髋座→机身侧框"
        if name.startswith("hip_case_") and "nut" in name: return "nut4", "髋座→机身侧框"
        if name.startswith("coupling_rotor_DIN6325_"): return "pin4", "髋转子法兰定位"
        if name.startswith("626_"): return "bearing", "A/B/C关节"
        if name.startswith("bearing_keeper_"): return "keeper", "A/B/C轴承外圈压盖"
        if name.startswith("female_pin_"): return "female", "A/B/C轴销"
        if name.startswith("flanged_bush_"): return ("inner" if name.endswith("_inner") else "outer"), "A/B/C嵌套支撑"
        if name.startswith("axis_washer_"): return "plate", "A/B/C轴销防脱"
        if name.startswith("OA_angular_stop_"): return "stop", "OA装配角限位"
        raise ValueError(f"Unclassified hardware: {name}")

    hardware = coupling.hardware()+leg.hardware()+chassis.hip_hardware()
    for name, _, _ in hardware:
        key, connection = classify(name)
        target = rows[key]
        target["quantity"] += 2
        target["model_instances"].extend([f"{name}_{side}" for side in ("right", "left")])
        for side in ("right", "left"):
            module = ("右腿" if side == "right" else "左腿")
            if key in ("cs4x12", "washer4", "nut4"):
                module = "腿-机身总装"
            match = next((u for u in target["usage"] if u["module"] == module and u["connection"] == connection), None)
            if match:
                match["quantity"] += 1
            else:
                target["usage"].append(dict(module=module, connection=connection, quantity=1))
    result = dict(revision="v8_1", scope="一台双腿整机；仅腿/法兰/轮/髋座硬件，含腿-机身M4接口；不含原厂电机内部件及装配工具/耗材",
                  bom=list(rows.values()), sources=SOURCES,
                  count_audit=dict(modelled_each_leg=len(hardware), modelled_both_legs=2*len(hardware),
                      standard_catalog_quantity=sum(r["quantity"] for r in rows.values() if r["supply_type"] != "custom"),
                      custom_quantity=sum(r["quantity"] for r in rows.values() if r["supply_type"] == "custom"),
                      hardware_purchase_skus=sum(r["supply_type"] != "custom" for r in rows.values()),
                      custom_hardware_skus=sum(r["supply_type"] == "custom" for r in rows.values()),
                      all_model_instances_classified_once=True),
                  manufacturing_aliases=json.loads((OUT/"leg_mirror_equivalence.json").read_text()))
    assert result["count_audit"]["modelled_both_legs"] == 194
    assert result["count_audit"]["custom_quantity"] == 38
    assert sum(r["quantity"] for r in rows.values()) == 2*len(hardware)
    assert all(sum(u["quantity"] for u in r["usage"]) == r["quantity"] for r in rows.values())
    (OUT/"leg_hardware_bom.json").write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n")
    print(json.dumps(result["count_audit"], ensure_ascii=False))


if __name__ == "__main__":
    main()
