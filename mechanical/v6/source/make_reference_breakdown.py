"""Draw a schematic of V6 part ownership; not manufacturing geometry."""
from pathlib import Path
import math

OUT = Path(__file__).resolve().parents[1] / "previews" / "reference_breakdown.svg"
items = []


def add(s):
    items.append(s)


def text(x, y, s, size=22, color="#25374b", weight=400):
    add(f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" font-weight="{weight}">{s}</text>')


def rect(x, y, w, h, fill, stroke="#344657", r=0, sw=2):
    add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')


def circle(x, y, r, fill, stroke="#344657", sw=2):
    add(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')


def line(x1, y1, x2, y2, color="#475569", width=2, dash="", arrow=False):
    add(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{width}" stroke-dasharray="{dash}"' + (' marker-end="url(#arrow)"' if arrow else '') + '/>')


add('<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="1130" viewBox="0 0 1600 1130">')
add('<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10z" fill="#475569"/></marker></defs>')
add('<g font-family="PingFang SC, Noto Sans CJK SC, Arial, sans-serif">')
rect(0, 0, 1600, 1130, "#f3f6f9", "none")
text(40, 54, "V6 参考图拆件：内座 → OA → 整体外壳套合", 34, weight=650)
text(40, 92, "130 / 105 / 45 mm · 主宽 23 mm；隐藏结构为本机设计决定，示意非加工图。", 21, "#657488")
rect(30, 120, 1540, 420, "white", "#d4dce4", 16)
text(52, 157, "五个主要制造件", 24, weight=600)

# Inner carrier: D57 head and continuous B load path.
rect(119, 266, 102, 170, "#acd685", r=25)
circle(170, 247, 76, "#acd685")
circle(170, 247, 53.9, "white")
circle(170, 435, 28, "#acd685")
circle(170, 435, 11, "white")
for a in range(30, 390, 60):
    circle(170 + 66.7 * math.cos(math.radians(a)), 247 + 66.7 * math.sin(math.radians(a)), 4, "white", sw=1)
add('<path d="M140 334 L140 393 L190 393 Z" fill="white" stroke="#344657" stroke-width="2"/>')
text(75, 488, "① OB 内座 / 内臂", 21, weight=600)
text(65, 520, "Ø57 环面先连定子", 20)

# OA: the A arm is visibly outside the O circular envelope.
add('<path d="M452 262 Q423 225 385 205 Q365 183 379 164 Q394 149 416 163 L480 214 Z" fill="#8e83dc" stroke="#344657" stroke-width="2"/>')
circle(459, 247, 50, "#8e83dc")
circle(459, 247, 16, "white")
circle(397, 182, 18, "#8e83dc")
circle(397, 182, 7, "white")
for a in range(0, 360, 60):
    circle(459 + 37 * math.cos(math.radians(a)), 247 + 37 * math.sin(math.radians(a)), 4, "white", sw=1)
text(419, 340, "O", 24, "#7264ca", 600)
text(365, 160, "A", 24, "#7264ca", 600)
text(366, 391, "轮毂穿过内座圆口", 20)
text(366, 423, "A 臂由侧窗伸出", 20)
text(365, 488, "② OA 一体曲柄", 21, weight=600)
text(375, 520, "转子驱动件", 20)

# Outer shell: show front and back rim to make the side wall unmistakable.
add('<path d="M773 172 A76 76 0 0 1 849 248 L827 427 Q823 454 781 454 L719 448 L739 176 Z" fill="#c5dfb4" stroke="#344657" stroke-width="2"/>')
add('<path d="M809.74 300.74 C800 314 811 385 810 420 Q808 445 773 445 Q737 445 734 420 C729 365 719 315 702.26 300.74 A76 76 0 1 1 809.74 300.74 Z" fill="#78bd7d" stroke="#344657" stroke-width="2"/>')
circle(756, 247, 50, "white")
add('<path d="M713.4 202.9 A61.3 61.3 0 0 0 712.6 290.4" fill="none" stroke="#344657" stroke-width="13" stroke-linecap="round"/>')
add('<path d="M713.4 202.9 A61.3 61.3 0 0 0 712.6 290.4" fill="none" stroke="white" stroke-width="10" stroke-linecap="round"/>')
circle(696, 236, 5, "#8e83dc", sw=1)
circle(773, 430, 12, "white")
add('<path d="M747 335 L751 384 L792 377 Z" fill="white" stroke="#344657" stroke-width="2"/>')
add('<path d="M776 315 L755 326 L782 355 Z" fill="white" stroke="#344657" stroke-width="2"/>')
line(825, 358, 885, 347, arrow=True)
text(848, 387, "侧壁", 19)
text(669, 488, "③ OB 包覆式外壳", 21, weight=600)
text(670, 520, "一体前壁、侧壁与台阶", 19)

# AC double bearing tongue.
rect(1017, 223, 42, 205, "#e98e95", r=17)
circle(1038, 222, 29, "#e98e95")
circle(1038, 428, 29, "#e98e95")
circle(1038, 222, 15, "white")
circle(1038, 428, 15, "white")
text(990, 191, "A", 22)
text(990, 443, "C", 22)
text(956, 488, "④ AC 轴承连杆", 21, weight=600)
text(960, 520, "两端插入相应叉口", 19)

# CW C fork, B tongue, W mount.
add('<path d="M1284 203 Q1291 184 1308 198 L1351 270 L1418 431 Q1431 454 1411 468 Q1391 478 1380 456 L1304 292 L1281 224 Q1277 212 1284 203 Z" fill="#80d5ce" stroke="#344657" stroke-width="2"/>')
circle(1298, 211, 21, "#80d5ce")
circle(1298, 211, 7, "white")
circle(1328, 281, 29, "#80d5ce")
circle(1328, 281, 15, "white")
circle(1398, 444, 26, "#80d5ce")
circle(1398, 444, 8, "white")
add('<path d="M1348 353 L1374 405 L1386 399 Z" fill="white" stroke="#344657" stroke-width="2"/>')
text(1257, 191, "C", 22)
text(1287, 295, "B", 22)
text(1438, 452, "W", 22)
text(1261, 488, "⑤ CW 一体下连杆", 21, weight=600)
text(1261, 520, "C 叉、B 舌、W 轮端", 19)

# Schematic axial section of the stationary and moving nested interfaces.
rect(30, 563, 790, 374, "white", "#d4dce4", 16)
text(52, 602, "轴向套合原理：外壳朝电机侧开腔", 24, weight=600)
rect(66, 690, 180, 146, "#ced3d9", "#758391", 5)
rect(219, 726, 41, 74, "#8b96a5", "#758391")
rect(259, 672, 22, 49, "#acd685")
rect(259, 805, 22, 78, "#acd685")
rect(263, 725, 160, 32, "#8e83dc")
rect(263, 769, 160, 32, "#8e83dc")
rect(389, 710, 31, 107, "#8e83dc")
rect(280, 643, 193, 18, "#78bd7d")
rect(280, 865, 193, 18, "#78bd7d")
rect(453, 643, 20, 92, "#78bd7d")
rect(453, 792, 20, 91, "#78bd7d")
line(64, 763, 505, 763, "#a1adba", 1, "7 7")
text(79, 867, "膝电机", 20)
line(269, 666, 332, 626)
text(346, 631, "内座 0～4", 19)
line(351, 722, 516, 693)
text(526, 699, "OA 主桥至 +20.6", 21, "#7264ca")
line(463, 802, 516, 813)
text(526, 819, "圆口 Ø35.4 / 颈 Ø35", 21, "#438657")
line(358, 874, 516, 868)
text(526, 874, "外壳前壁 +20～23", 21, "#438657")
text(528, 748, "先锁 OA，再套外壳", 21, weight=600)
line(653, 765, 500, 765, width=3, arrow=True)
text(52, 917, "示意剖面未画活动侧窗；并非四周封死的闭合圆杯。", 18, "#657488")

# O circular envelope must not be confused with the sweep of A.
rect(840, 563, 730, 374, "white", "#d4dce4", 16)
text(864, 602, "Ø57 圆面只能包轮毂，不能包 A 全扫掠", 24, weight=600)
circle(1050, 757, 74.1, "#e7f4e7", "#438657", 3)
circle(1050, 757, 117, "none", "#b8accf", 1.5)
add('<circle cx="1050" cy="757" r="117" fill="none" stroke="#b8accf" stroke-width="2" stroke-dasharray="7 6"/>')
line(1050, 757, 967.27, 674.27, "#8e83dc", 28)
circle(1050, 757, 45.5, "#8e83dc")
circle(1050, 757, 14, "white")
circle(967.27, 674.27, 24, "#8e83dc")
circle(967.27, 674.27, 7, "white")
text(940, 638, "A", 22, "#7264ca", 600)
text(1099, 802, "O", 22, "#7264ca", 600)
text(1202, 687, "OA = 45 mm", 23, weight=600)
text(1202, 728, "电机半径 = 28.5 mm", 22)
text(1202, 769, "A 必须从侧窗伸出", 22, "#438657", 600)
text(1202, 810, "不能再用放大圆盖遮住", 21)
text(864, 917, "圆口单边间隙0.2；另设 R23 × 宽4.6 弧槽与可拆 Ø4 肩销。", 18, "#657488")

rect(30, 960, 1540, 137, "#e6edf4", "none", 14)
text(53, 999, "装配顺序", 23, weight=600)
for x, label in [(220, "内座锁定子"), (520, "OA 穿圆口锁转子"), (882, "B 舌对入内支撑"), (1230, "外壳轴向套合")]:
    text(x, 1000, label, 23)
for x1, x2 in [(380, 490), (736, 850), (1090, 1205)]:
    line(x1, 991, x2, 991, width=3, arrow=True)
text(53, 1062, "核验项：真实电机孔系 · 定子螺钉小径头余肉 · 轴向装入 · 工具通路 · 全角域侧窗间隙 · B 双剪支承", 22)
add('</g></svg>')
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text("\n".join(items), encoding="utf-8")
print(OUT)
