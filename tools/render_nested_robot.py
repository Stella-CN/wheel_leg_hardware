"""Render the nested double-shear V3 with the installed FreeCAD GUI (macOS).

Run with /Applications/FreeCAD.app/Contents/Resources/bin/python.
The exploded illustration uses a temporary document, so the manufacturing
assembly keeps every placement expression and its original assembly pose.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "mechanical/v3"
PREVIEWS = OUT / "previews"
sys.path.insert(0, "/Applications/FreeCAD.app/Contents/Resources/lib")

import FreeCAD as App
import FreeCADGui as Gui
import Part
from PySide import QtCore, QtWidgets


def refresh(document):
    document.recompute()
    Gui.updateGui()
    QtWidgets.QApplication.processEvents()


def save_view(document, name, rotation, width=1800, height=1400):
    App.setActiveDocument(document.Name)
    # Finish restoring a newly opened document before assigning its camera.
    # Otherwise the deferred GUI restore can overwrite the requested view.
    refresh(document)
    view = Gui.activeDocument().activeView()
    view.setCameraType("Orthographic")
    # Set the quaternion directly: standard view commands can animate, leaving
    # an image captured part way through a camera transition.
    view.setCameraOrientation(rotation)
    refresh(document)
    # Let the native view finish its camera transition before the snapshot.
    # Immediate captures can retain part of the preceding oblique orientation.
    loop = QtCore.QEventLoop()
    QtCore.QTimer.singleShot(1000, loop.quit)
    loop.exec_()
    if globals().get('EXACT_CAPTURE_ORIENTATION',False):
        from pivy import coin
        view.getCameraNode().orientation.setValue(coin.SbRotation(*rotation))
    view.fitAll()
    # V5 can reserve extra output margin for its portrait-height assembly.
    # Default stays unchanged for previous revisions.
    margin = globals().get('FRAME_MARGIN', 1.0)
    if margin != 1.0:
        from pivy import coin  # noqa: F401; register the native Coin bindings
        camera = view.getCameraNode()
        camera.height.setValue(camera.height.getValue() * margin)
    refresh(document)
    settled = QtCore.QEventLoop()
    QtCore.QTimer.singleShot(1000, settled.quit)
    settled.exec_()
    refresh(document)
    if globals().get('EXACT_CAPTURE_ORIENTATION',False):
        # Embedded GUI navigation can stop its animation between frames.
        # Set the native Coin camera directly immediately before capture.
        from pivy import coin
        view.getCameraNode().orientation.setValue(coin.SbRotation(*rotation))
    view.saveImage(str(PREVIEWS / name), width, height, "White")


def color_feature(obj):
    material = getattr(obj, "Material", "")
    name = obj.Name
    color = (0.76, 0.78, 0.79)
    if material == "motor":
        color = (0.20, 0.22, 0.25)
    elif "cnc" in name:
        color = (0.81, 0.82, 0.84)
    elif "OB_outer_full" in name:
        color = (0.62, 0.84, 0.49)
    elif "OB_inner_full" in name:
        color = (0.39, 0.78, 0.34)
    elif "OA_inner_hub" in name or "OA_outer_cheek" in name:
        color = (0.46, 0.35, 0.80)
    elif "AC_bearing_link" in name:
        color = (0.91, 0.42, 0.42)
    elif "CW_" in name:
        color = (0.23, 0.74, 0.76)
    elif "rim" in name:
        color = (0.47, 0.51, 0.57)
    elif material == "rubber" or "tyre" in name:
        color = (0.13, 0.14, 0.16)
    elif "bronze_sleeve" in name:
        color = (0.75, 0.53, 0.24)
    elif material == "steel":
        color = (0.73, 0.76, 0.79)
    obj.ViewObject.Visibility = True
    obj.ViewObject.ShapeColor = color
    obj.ViewObject.LineColor = (0.16, 0.18, 0.20)
    obj.ViewObject.LineWidth = 1.0
    obj.ViewObject.DisplayMode = "Flat Lines"


def explosion_offset(obj):
    """Spread the manufactured layers without changing their XZ centres."""
    name = obj.Name
    groups = (("J4310_hip", -95), ("hip_stator_mount", -65),
              ("hip_rotor_cnc", -35), ("knee_stator_cnc", -10),
              ("J4310_knee", 20), ("OB_inner_full", 60),
              ("OA_inner_hub", 100), ("CW_main_inner", 100),
              ("AC_bearing_link", 155), ("OA_outer_cheek", 205),
              ("CW_outer_fork", 205), ("OB_outer_full", 270),
              ("H6215", 330), ("wheel_rim", 380), ("tyre", 380))
    for prefix, offset in groups:
        if prefix in name:
            return offset
    return 0


def render_exploded(source, rotation):
    exploded = App.newDocument("WheelLegV3ExplodedPreview")
    try:
        for obj in source.Objects:
            if obj.TypeId != "Part::Feature" or not obj.Name.endswith("_right"):
                continue
            if getattr(obj, "Material", "") == "steel":
                continue
            clone = exploded.addObject("Part::Feature", obj.Name)
            # obj.Shape contains its evaluated placement. Wrap it in an
            # identity compound before adding the illustration-only offset.
            clone.Shape = Part.makeCompound([obj.Shape.copy()])
            clone.Placement.Base = App.Vector(0, explosion_offset(obj), 0)
            clone.ViewObject.ShapeColor = obj.ViewObject.ShapeColor
            clone.ViewObject.LineColor = obj.ViewObject.LineColor
            clone.ViewObject.LineWidth = 1.0
            clone.ViewObject.DisplayMode = "Flat Lines"
        save_view(exploded, "right_leg_exploded.png", rotation, 2200, 1400)
    finally:
        App.closeDocument(exploded.Name)
        App.setActiveDocument(source.Name)


def linkage_svg(parameters):
    """Draw measured design coordinates, with +Y exterior view (X left)."""
    length = float(parameters["leg_length"])
    rod = float(parameters["rod_length"])
    crank = float(parameters["crank_length"])
    beta = math.radians(float(parameters.get("beta_deg", 0)))
    alpha = math.acos(length / (2 * rod))

    def down(radius, angle):
        return (radius * math.sin(angle), -radius * math.cos(angle))

    a = down(crank, beta + alpha - math.pi)
    b = down(rod, beta - alpha)
    bw = down(rod, beta + alpha)
    coordinates = {"O": (0.0, 0.0), "A": a, "B": b,
                   "C": (a[0] + b[0], a[1] + b[1]),
                   "W": (b[0] + bw[0], b[1] + bw[1])}

    def project(point):
        return 330 - 2.4 * point[0], 155 - 2.4 * point[1]

    points = {name: project(point) for name, point in coordinates.items()}

    def path(names, color, width):
        positions = " ".join(f"{points[n][0]:.2f},{points[n][1]:.2f}" for n in names)
        return (f'<polyline points="{positions}" fill="none" stroke="{color}" '
                f'stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round"/>')

    colors = {"OB": "#64b754", "OA": "#7960cb", "AC": "#e57978", "BCW": "#3ab6bc"}
    wx, wy = points["W"]
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="800" viewBox="0 0 1080 800">',
        '<rect width="1080" height="800" fill="#fff"/>',
        '<style>text{font-family:Arial,"PingFang SC","Noto Sans CJK SC",sans-serif;fill:#263238}'
        '.title{font-size:28px;font-weight:700}.label{font-size:22px;font-weight:700;'
        'paint-order:stroke;stroke:#fff;stroke-width:6px;stroke-linejoin:round}'
        '.note{font-size:18px}.small{font-size:15px}</style>',
        '<text x="46" y="49" class="title">V3 四杆拓扑 / 轮足中心坐标</text>',
        '<text x="46" y="78" class="small">沿 +Y 看向 −Y；Z 向上、X 向左。单位：mm</text>',
        f'<circle cx="{wx:.2f}" cy="{wy:.2f}" r="120" fill="#f3f4f5" stroke="#606a71" stroke-width="6"/>',
        f'<circle cx="{wx:.2f}" cy="{wy:.2f}" r="81.6" fill="#e3e6e8" stroke="#87929a" stroke-width="2"/>',
        f'<circle cx="{points["O"][0]:.2f}" cy="{points["O"][1]:.2f}" r="68.4" fill="#f0f2f3" stroke="#a7b0b5" stroke-width="2"/>',
        path("OB", colors["OB"], 24), path("OA", colors["OA"], 18),
        path("AC", colors["AC"], 12), path("CBW", colors["BCW"], 20),
    ]
    offsets = {"O": (-33, 0), "A": (6, -20), "B": (19, 17), "C": (18, -8), "W": (16, 8)}
    for name, (x, y) in points.items():
        dx, dy = offsets[name]
        parts.extend([f'<circle cx="{x:.2f}" cy="{y:.2f}" r="7" fill="#fff" stroke="#293940" stroke-width="2"/>',
                      f'<text x="{x+dx:.2f}" y="{y+dy:.2f}" class="label">{name}</text>'])
    parts.extend([
        '<text x="387" y="297" class="label">OB = 130</text>',
        '<text x="508" y="185" class="label">AC = 130</text>',
        '<text x="397" y="515" class="label">BW = 130</text>',
        '<text x="413" y="134" class="label">OA = 35</text>',
        '<text x="622" y="362" class="label">BC = 35</text>',
        '<text x="747" y="169" class="note">O：髋 / 膝电机共轴</text>',
        '<text x="747" y="201" class="note">W：H6215 轮轴中心</text>',
        '<text x="747" y="250" class="note">OB = AC = BW</text>',
        '<text x="747" y="282" class="note">OA = BC</text>',
        '<text x="747" y="331" class="note">C / B / W 共线</text>',
        f'<text x="747" y="363" class="note">当前腿长：{length:.2f}</text>',
        '<text x="747" y="395" class="note">轮径：100</text>',
        '<text x="747" y="444" class="small">拓扑来自用户参考图；</text>',
        '<text x="747" y="469" class="small">数值与共线关系沿用工程基准。</text>',
        '<text x="747" y="510" class="small">此图表示运动中心与杆长；</text>',
        '<text x="747" y="535" class="small">曲线外形及轴向内扣见实体图。</text>',
        '<text x="46" y="758" class="small">圆圈表示转轴；两圈轮廓表示轮胎外径与轮毂电机包络。无 Hip Roll 自由度。</text>',
        '</svg>',
    ])
    (PREVIEWS / "linkage_layout.svg").write_text("\n".join(parts) + "\n", encoding="utf-8")
    (PREVIEWS / "linkage_coordinates.json").write_text(
        json.dumps({"units": "mm", "view": "+Y toward -Y, X left, Z up",
                    "coordinates_xz": coordinates, "leg_length": length,
                    "rod_length": rod, "crank_length": crank}, indent=2) + "\n")


def joint_sections_svg():
    """Exact axial stack at A/B/C, with simplified radial outside profiles.

    Coordinates correspond to hardware() in build_nested_robot.py. The rings
    are symmetric section envelopes; the 626 bearing internal balls/races and
    circlip split are intentionally not presented as manufacturing geometry.
    """
    width, height = 1280, 1640
    scale = 10.0
    xorigin = 322.0

    def xpos(y):
        return xorigin + (y - 137) * scale

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        f'<rect width="{width}" height="{height}" fill="white"/>',
        '<defs><marker id="arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0,0 L8,4 L0,8 Z" fill="#34434c"/></marker></defs>',
        '<style>text{font-family:Arial,"PingFang SC","Noto Sans CJK SC",sans-serif;fill:#26343e}'
        '.title{font-size:29px;font-weight:700}.heading{font-size:25px;font-weight:700}'
        '.label{font-size:17px}.note{font-size:16px}.dim{font-size:15px;font-variant-numeric:tabular-nums}'
        '.tiny{font-size:13px}</style>',
        '<text x="40" y="45" class="title">V3 内扣关节：两侧支承夹住中间活动舌</text>',
        '<text x="40" y="75" class="note">右腿轴向中心剖面；横向为机身坐标 +Y。Y 区间取自实体 CAD，单位 mm。</text>',
        '<text x="40" y="100" class="note">叉根位于剖面外；径向轮廓简化，626 为包络。此图不是加工图。</text>',
    ]
    steel, bearing, bronze = "#bcc5cc", "#8194a3", "#d8af64"

    def rect(y0, y1, radial_lo, radial_hi, center, color, stroke="#47545e"):
        parts.append(f'<rect x="{xpos(y0):.2f}" y="{center-radial_hi*scale:.2f}" '
                     f'width="{(y1-y0)*scale:.2f}" height="{(radial_hi-radial_lo)*scale:.2f}" '
                     f'fill="{color}" stroke="{stroke}" stroke-width="0.85"/>')

    def ring_section(y0, y1, inner, outer, center, color):
        rect(y0, y1, inner, outer, center, color)
        rect(y0, y1, -outer, -inner, center, color)

    def line(x1, y1, x2, y2, color="#44545e", dash="", arrow=False):
        style = f' stroke-dasharray="{dash}"' if dash else ""
        style += ' marker-end="url(#arrow)"' if arrow else ""
        parts.append(f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
                     f'stroke="{color}" stroke-width="1.2"{style}/>')

    def txt(x, y, text, cls="label", anchor="start"):
        parts.append(f'<text x="{x:.2f}" y="{y:.2f}" class="{cls}" text-anchor="{anchor}">{text}</text>')

    stacks = [
        dict(name="A", center=385, inner=(150, 158), outer=(174, 182),
             pin=(148.5, 183.5), grooves=(149, 182.2), ear_radius=13,
             ear_color="#8b73d3", outer_color="#a68cdc", tongue_color="#e98582",
             fork="OA 双耳", tongue="AC 活动舌", subtitle="OA 两侧耳板 → 铜套 / 钢销 → AC 双轴承舌"),
        dict(name="B", center=885, inner=(139, 147), outer=(184, 192),
             pin=(137.5, 193.5), grooves=(138, 192.2), ear_radius=17,
             ear_color="#70bd5d", outer_color="#a9ce74", tongue_color="#60c5c7",
             fork="完整 OB 双板", tongue="CW 活动舌", subtitle="完整 OB 内 / 外板 → 铜套 / 钢销 → CW 双轴承舌"),
        dict(name="C", center=1385, inner=(150, 158), outer=(174, 182),
             pin=(148.5, 183.5), grooves=(149, 182.2), ear_radius=13,
             ear_color="#60c5c7", outer_color="#8dd8d6", tongue_color="#e98582",
             fork="CW 双耳", tongue="AC 活动舌", subtitle="CW 两侧耳板 → 铜套 / 钢销 → AC 双轴承舌"),
    ]
    for data in stacks:
        center = data["center"]
        title_y = center - 295
        txt(40, title_y + 30, f'{data["name"]} 点', "heading")
        txt(164, title_y + 29, data["subtitle"], "label")
        line(40, title_y + 46, width - 40, title_y + 46, "#dbe0e3")
        inner, outer = data["inner"], data["outer"]

        # Two PETG side supports, bored for 8 mm OD bronze sleeves.
        for span, color in ((inner, data["ear_color"]), (outer, data["outer_color"])):
            ring_section(*span, 4.025, data["ear_radius"], center, color)
            ring_section(*span, 3.025, 4, center, bronze)

        # Middle printed tongue: two counterbores and the central 1.9 mm web.
        tongue_radius = 17 if data["name"] == "B" else 16
        ring_section(159, 165.05, 9.575, tongue_radius, center, data["tongue_color"])
        ring_section(165.05, 166.95, 8.4, tongue_radius, center, data["tongue_color"])
        ring_section(166.95, 173, 9.575, tongue_radius, center, data["tongue_color"])
        for start in (159, 167):
            ring_section(start, start + 6, 3, 9.5, center, bearing)
        ring_section(165, 167, 3.1, 4.2, center, steel)
        for start in (158, 173):
            ring_section(start, start+1, 3.1, 4.2, center, steel)
        if data["name"] == "B":
            ring_section(147, 158, 3.1, 5, center, steel)
            ring_section(174, 184, 3.1, 5, center, steel)

        # Ground pin with the same circlip groove locations as the CAD model.
        start, end = data["pin"]
        g1, g2 = data["grooves"]
        for y0, y1, radius in ((start, g1, 3), (g1, g1+.8, 2.85),
                               (g1+.8, g2, 3), (g2, g2+.8, 2.85),
                               (g2+.8, end, 3)):
            rect(y0, y1, -radius, radius, center, "#d4dce1")
        for y0 in (inner[0]-.2, outer[1]):
            ring_section(y0, y0+.2, 3.1, 5, center, steel)
        for y0 in (g1+.1, g2):
            ring_section(y0, y0+.7, 2.85, 6, center, "#52626b")
        line(xpos(136.4), center, xpos(195), center, "#697d89", "8 4 2 4", True)
        txt(xpos(195)+7, center+6, "+Y", "dim")

        # Explicit three-part nesting labels, with leaders to the printed bodies.
        label_y = center - 187 if data["name"] != "B" else center - 220
        for span, label in ((inner, "内侧支承"), ((159, 173), "中间活动舌"), (outer, "外侧支承")):
            x = xpos(sum(span)/2)
            txt(x, label_y, label, "label", "middle")
            txt(x, label_y+20, f'Y {span[0]}–{span[1]}', "dim", "middle")
            top = center - (16 if label == "中间活动舌" else data["ear_radius"]) * scale
            if top > label_y+26:
                line(x, label_y+26, x, top-4)

        # A compact right-hand bill of this section; every row uses actual stack.
        txt(966, center-92, data["fork"], "label")
        txt(966, center-67, f'夹住 {data["tongue"]}', "label")
        txt(966, center-26, f'钢销：Ø6 × {end-start:g}', "note")
        txt(966, center, '两端：外卡簧 + 0.2 垫片', "note")
        txt(966, center+26, '两耳铜套：Ø8 / Ø6.05 × 8', "note")
        txt(966, center+52, '中舌：2 × 626（6 × 19 × 6）', "note")
        txt(966, center+78, '中间隔套：Ø8.4 / Ø6.2 × 2', "note")
        txt(966, center+104, '两侧钢垫：Ø8.4 / Ø6.2 × 1', "note")
        if data["name"] == "B":
            txt(966, center+134, '额外钢隔套：内 11 / 外 10', "note")

        # Dimension line under the section identifies the full pin length.
        dimension_y = center + 184 if data["name"] != "B" else center + 208
        for y in (start, end):
            line(xpos(y), center+61, xpos(y), dimension_y+5, "#9aa7ae")
        line(xpos(start), dimension_y, xpos(end), dimension_y)
        for y in (start, end):
            line(xpos(y)-4, dimension_y+4, xpos(y)+4, dimension_y-4)
        txt(xpos((start+end)/2), dimension_y-7,
            f'销长 {end-start:g}；Y {start:g}–{end:g}', "dim", "middle")

    # Common legend fits outside the section and explanatory columns.
    legend_y = 1615
    for x, color, label in ((40, "#83c471", "PETG 支承 / 活动舌"),
                            (337, bronze, "青铜衬套"), (559, bearing, "626 轴承包络"),
                            (817, steel, "钢销 / 隔套 / 垫片")):
        parts.append(f'<rect x="{x}" y="{legend_y-17}" width="22" height="18" fill="{color}" stroke="#58646c"/>')
        txt(x+31, legend_y, label, "note")
    parts.append('</svg>')
    (PREVIEWS / "joint_sections.svg").write_text("\n".join(parts)+"\n", encoding="utf-8")
    (PREVIEWS / "joint_sections_data.json").write_text(json.dumps({
        "units": "mm", "right_leg_axial_direction": "+Y",
        "joint_stacks": [{k: value for k, value in data.items()
                          if k not in ("center", "ear_color", "outer_color", "tongue_color")}
                         for data in stacks],
        "bronze_sleeve": {"outside_diameter": 8, "inside_diameter": 6.05, "length": 8},
        "tongue_span_y": [159, 173], "central_web_relief_diameter": 16.8,
        "race_contact_hardware_outside_diameter": 8.4, "race_contact_hardware_inside_diameter": 6.2, "bearing_spans_y": [[159, 165], [167, 173]],
        "inner_race_spacer_span_y": [165, 167], "race_washer_spans_y": [[158, 159], [173, 174]],
        "B_extra_standoff_spans_y": [[147, 158], [174, 184]],
    }, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")


def main():
    document_path = OUT / "wheel_leg_v3.FCStd"
    if not document_path.is_file():
        raise FileNotFoundError(f"Build the V3 assembly first: {document_path}")
    PREVIEWS.mkdir(parents=True, exist_ok=True)
    Gui.showMainWindow()
    # Import after the GUI exists; this initializes the Part view provider.
    import PartGui  # noqa: F401

    doc = App.openDocument(str(document_path))
    parameters = json.loads((OUT / "design_parameters.json").read_text())
    original_parameters = (doc.Parameters.LegLength.Value, doc.Parameters.Beta.Value)
    original_expressions = {obj.Name: list(obj.ExpressionEngine) for obj in doc.Objects}
    features = [obj for obj in doc.Objects if obj.TypeId == "Part::Feature"]
    for group in (doc.Robot, doc.PurchasedParts):
        group.ViewObject.Visibility = True
    for obj in features:
        color_feature(obj)

    assembly_rotation = App.Rotation(0.364705, 0.279848, 0.115917, 0.880476).Q
    exterior_rotation = App.Rotation(App.Vector(-1, 1, 0), App.Vector(-0.7, -0.7, 2),
                                     App.Vector(1, 1, 0.7), "ZXY").Q
    side_rotation = App.Rotation(0, math.sqrt(0.5), math.sqrt(0.5), 0).Q

    save_view(doc, "assembly.png", assembly_rotation)
    for name in ("chassis_lid", "electronics_tray"):
        doc.getObject(name).ViewObject.Visibility = False
    save_view(doc, "open_chassis.png", assembly_rotation)

    for obj in features:
        obj.ViewObject.Visibility = obj.Name.endswith("_right")
    save_view(doc, "right_leg.png", exterior_rotation)
    save_view(doc, "right_leg_side.png", side_rotation)
    # Reveal the nested moving tongues. Only the complete outer OB plate is
    # hidden; transparent outer A/C cheeks retain both sides of each fork.
    doc.OB_outer_full_right.ViewObject.Visibility = False
    for name in ("OA_outer_cheek_right", "CW_outer_fork_right"):
        doc.getObject(name).ViewObject.Transparency = 70
    save_view(doc, "nested_joints_cutaway.png", exterior_rotation)
    for name in ("OA_outer_cheek_right", "CW_outer_fork_right"):
        doc.getObject(name).ViewObject.Transparency = 0
    doc.OB_outer_full_right.ViewObject.Visibility = True
    render_exploded(doc, exterior_rotation)

    # Store the editable FCStd in its complete, assembled, coloured view only.
    for obj in features:
        obj.ViewObject.Visibility = True
    save_view(doc, "assembly.png", assembly_rotation)
    assert original_parameters == (doc.Parameters.LegLength.Value, doc.Parameters.Beta.Value)
    assert original_expressions == {obj.Name: list(obj.ExpressionEngine) for obj in doc.Objects}
    doc.save()
    linkage_svg(parameters)
    joint_sections_svg()
    print("FREECAD_V3_PREVIEWS_COMPLETE", flush=True)


if __name__ == "__main__":
    main()
