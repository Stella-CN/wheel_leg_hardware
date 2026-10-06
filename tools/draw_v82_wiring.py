#!/usr/bin/env python3
"""Draw the reviewed V8.2 functional topology; this is not a pin-level netlist."""

from html import escape
from pathlib import Path


OUT = Path(__file__).resolve().parents[1] / "mechanical" / "v8_2"
W, H = 1560, 1240
COLORS = {"bat": "#c33c38", "dc": "#c78520", "usb": "#2776be", "can": "#1c8967", "video": "#7657a8"}
items = []


def text(x, y, value, size=17, color="#233444", weight=400, anchor="start"):
    items.append(f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" font-weight="{weight}" text-anchor="{anchor}">{escape(value)}</text>')


def rect(x, y, w, h, fill="#fff", stroke="#cad4dd", radius=8):
    items.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" stroke="{stroke}"/>')


def box(x, y, w, h, title, subtitle="", color="#233444"):
    rect(x, y, w, h)
    text(x + w / 2, y + 29, title, 18, color, 600, "middle")
    if subtitle:
        text(x + w / 2, y + 53, subtitle, 14, "#68788a", anchor="middle")


def path(points, kind, arrow=True, dash=False):
    d = "M " + " L ".join(f"{x},{y}" for x, y in points)
    tail = f' marker-end="url(#{kind})"' if arrow else ""
    if dash:
        tail += ' stroke-dasharray="8 5"'
    items.append(f'<path d="{d}" fill="none" stroke="{COLORS[kind]}" stroke-width="3" stroke-linejoin="round"{tail}/>')


def panel(y, h, number, title, note):
    rect(28, y, W - 56, h, "#f7f9fc", "#e0e7ed", 14)
    text(52, y + 33, number, 20, "#8495a5", 600)
    text(96, y + 33, title, 22, weight=600)
    text(96, y + 60, note, 15, "#607183")


text(38, 42, "V8.2  电源与通信功能拓扑", 30, weight=700)
text(38, 73, "后部四口 USB 外露 · 顶部自锁开关 · 后部右下充电口 · 不改变腿部机构", 17, "#607183")

panel(95, 315, "01", "电源分配", "粗线代表供电正负线对；箭头表示连接路径，不代表充电能量方向。板端引脚与额定值待核实。")
box(54, 220, 186, 76, "E626S 电池", "22.2 V / 满充 25.2 V", COLORS["bat"])
box(293, 220, 178, 76, "DC 一分二", "5.5 × 2.1 充放共口")
box(526, 169, 174, 76, "顶部 M16 开关", "自锁 · DC 额定待核实")
box(526, 306, 174, 76, "后部右下充电口", "位于开关之前")
box(773, 169, 191, 76, "用户分配 PCB", "铜箔网络 / 线序待核实")
box(1042, 169, 215, 76, "左右腿 · 六台电机", "电源电气并联", COLORS["bat"])
box(773, 306, 191, 76, "24→19 V 转换器", "图示 58 × 25 × 20")
box(1042, 306, 215, 76, "Jetson DC 输入", "插头 5.5 × 2.5", COLORS["dc"])
path([(240,258),(293,258)], "bat")
path([(471,258),(496,258),(496,207),(526,207)], "bat")
path([(496,258),(496,344),(526,344)], "bat")
path([(700,207),(773,207)], "bat")
path([(734,207),(734,344),(773,344)], "bat")
path([(964,207),(1042,207)], "bat")
path([(964,344),(1042,344)], "dc")
text(1300, 193, "电机顺接 ≠ 串联分压", 16, COLORS["bat"], 600)
text(1300, 221, "动力与 CAN 分别识别", 15)
text(1300, 333, "25.2 V 不可直连 Jetson", 16, COLORS["bat"], 600)
text(1300, 361, "降压模块电气参数待确认", 15)

panel(430, 262, "02", "双路 CAN", "USB2CAN 的供电来自 USB；GH1.25 2P 仅 CANH/CANL，不输入电池电压。")
box(54, 535, 234, 98, "USB2CANFD Dual", "两条独立总线 · 近端各 120 Ω", COLORS["can"])
box(445, 521, 238, 65, "左髋 J4310 → 左膝 J4310", "中间不加终端")
box(778, 521, 217, 65, "左轮 H6215", "末端 120 Ω：核实是否已内置")
box(445, 608, 238, 65, "右髋 J4310 → 右膝 J4310", "中间不加终端")
box(778, 608, 217, 65, "右轮 H6215", "末端 120 Ω：核实是否已内置")
path([(288,554),(445,554)], "can")
path([(288,612),(348,612),(348,641),(445,641)], "can")
path([(683,554),(778,554)], "can")
path([(683,641),(778,641)], "can")
text(315, 544, "CAN 1", 15, COLORS["can"], 600)
text(362, 630, "CAN 2", 15, COLORS["can"], 600)
text(1076, 548, "两端各 120 Ω；每路断电约 60 Ω", 18, weight=600)
text(1076, 581, "CAN 双绞线沿各腿连续布置", 16)
text(1076, 610, "左右 H/L 不互连；节点 ID 各自唯一", 16)
text(1076, 639, "运动接口保留弯折环与两侧应力释放", 16)

panel(712, 355, "03", "Jetson 主机接口与前后面板", "外露扩展坞四口全部留给外接设备；内部 IMU 使用 Jetson Type-C Host。")
box(54, 820, 216, 155, "Jetson Orin Nano", "4 × Type-A + Type-C Host", COLORS["usb"])
text(162, 919, "每个双层 Type-A 座", 15, anchor="middle")
text(162, 945, "合计 VBUS 限制 3 A", 15, anchor="middle")
destinations = [
    (811, "Type-A · 正Y座下", "D435", "USB 3.x A→C · 前面板上方"),
    (880, "Type-A · 负Y座上", "USB2CANFD Dual", "USB A→C · 供电 + 双路通信"),
    (949, "Type-C Host", "HI13R2-USB", "C→C 数据线 · 原点保持居中"),
]
for cy, label, title, subtitle in destinations:
    box(444, cy - 18, 280, 61, title, subtitle)
    path([(270, cy + 11),(444, cy + 11)], "usb")
    text(295, cy, label, 14, COLORS["usb"])
box(986, 793, 276, 61, "后部四口 USB 扩展坞", "原线150 mm + 延长线250 mm")
box(986, 880, 276, 61, "5 寸前屏 USB", "5 V 供电 / 触摸版本待核实")
box(986, 986, 276, 61, "5 寸前屏 HDMI", "视频 · DP→HDMI 线或转接器")
path([(270,966),(314,966),(314,1040),(756,1040),(756,824),(986,824)], "usb")
path([(270,970),(303,970),(303,1048),(780,1048),(780,910),(986,910)], "usb")
path([(270,975),(287,975),(287,1057),(954,1057),(954,1017),(986,1017)], "video")
text(797, 813, "Type-A · 正Y座上", 14, COLORS["usb"])
text(797, 899, "Type-A · 负Y座下", 14, COLORS["usb"])
text(793, 1005, "DisplayPort", 14, COLORS["video"])
text(1293, 817, "104 × 30 × 10 mm", 16, weight=600)
text(1293, 845, "速率 / 总供电能力待核实", 15)
text(1293, 905, "两条线：USB + 视频", 16)
text(1293, 933, "USB-C 不输出显示信号", 15)
text(1293, 1012, "刷机时先拔 Type-C IMU", 15)

rect(28, 1085, W - 56, 121, "#fff7e8", "#eed9ae", 12)
text(52, 1118, "机械包络已定义，电气放行仍有明确边界", 21, "#835b20", 600)
text(52, 1150, "需核实：主开关 DC 分断 / LED 电压，转换器输入与功率，DC 母座极性与载流，分配板原理图，USB 总负载。", 17)
text(52, 1179, "E626S 持续 6 A；J4310 V1.1 手册最低工作电压按更严格 20 V 审查。不能据此宣称已具备跳跃供电能力。", 17)
text(38, 1230, "功能示意，非引脚接线图。依据与未确认项见 ELECTRICAL_INTEGRATION.md。", 14, "#607183")

defs = []
for key, color in COLORS.items():
    defs.append(f'<marker id="{key}" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto" markerUnits="userSpaceOnUse"><path d="M0,0 L8,4 L0,8 z" fill="{color}"/></marker>')
svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<title>V8.2 power and communications functional topology</title>
<desc>Separate battery power, CAN buses, USB ports and DisplayPort video. Proposed wiring is pending PCB pinout and electrical ratings verification.</desc>
<defs>{''.join(defs)}</defs>
<rect width="100%" height="100%" fill="white"/>
<g font-family="PingFang SC, Noto Sans CJK SC, Microsoft YaHei, sans-serif">{''.join(items)}</g>
</svg>'''
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "WIRING_TOPOLOGY.svg").write_text(svg, encoding="utf-8")
print(OUT / "WIRING_TOPOLOGY.svg")
