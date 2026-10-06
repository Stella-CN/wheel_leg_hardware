"""Render the reference-image V2 with the installed FreeCAD GUI (macOS).

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
OUT = ROOT / "mechanical/v2"
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
    view.fitAll()
    refresh(document)
    view.saveImage(str(PREVIEWS / name), width, height, "White")


def color_feature(obj):
    material = getattr(obj, "Material", "")
    name = obj.Name
    color = (0.76, 0.78, 0.79)
    if material == "motor":
        color = (0.20, 0.22, 0.25)
    elif "cnc" in name:
        color = (0.81, 0.82, 0.84)
    elif "B_outer_cheek" in name:
        color = (0.62, 0.84, 0.49)
    elif "fixed_arm_OB" in name:
        color = (0.39, 0.78, 0.34)
    elif "active_arm_OA" in name:
        color = (0.46, 0.35, 0.80)
    elif "coupler_AC" in name:
        color = (0.91, 0.42, 0.42)
    elif "output_BCW" in name:
        color = (0.23, 0.74, 0.76)
    elif "rim" in name:
        color = (0.47, 0.51, 0.57)
    elif material == "rubber" or "tyre" in name:
        color = (0.13, 0.14, 0.16)
    elif material == "steel":
        color = (0.73, 0.76, 0.79)
    obj.ViewObject.Visibility = True
    obj.ViewObject.ShapeColor = color
    obj.ViewObject.LineColor = (0.16, 0.18, 0.20)
    obj.ViewObject.LineWidth = 1.0
    obj.ViewObject.DisplayMode = "Flat Lines"


def explosion_offset(obj):
    """Separate the axial layers without changing their XZ linkage pose."""
    name = obj.Name
    if "J4310_hip" in name:
        return -80
    if "hip_stator_mount" in name:
        return -45
    if "hip_rotor_cnc" in name:
        return -20
    if "knee_stator_cnc" in name:
        return 10
    if "J4310_knee" in name:
        return 35
    if "fixed_arm_OB" in name:
        return 65
    if "active_arm_OA" in name or "output_BCW" in name:
        return 115
    if "B_outer_cheek" in name:
        return 205
    if "coupler_AC" in name:
        return 255
    if "H6215" in name:
        return 300
    if "wheel_rim" in name or "tyre" in name:
        return 345
    # Joint envelopes travel with their associated assembly layer. The view
    # deliberately omits these small parts to keep the structure legible.
    return 0


def render_exploded(source, rotation):
    exploded = App.newDocument("WheelLegV2ExplodedPreview")
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
        '<text x="46" y="49" class="title">V2 四杆拓扑 / 轮足中心坐标</text>',
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
        '<text x="747" y="510" class="small">此图只表示运动中心与杆长，</text>',
        '<text x="747" y="535" class="small">不表示实体板厚或轴向间隙。</text>',
        '<text x="46" y="758" class="small">圆圈表示转轴；两圈轮廓表示轮胎外径与轮毂电机包络。无 Hip Roll 自由度。</text>',
        '</svg>',
    ])
    (PREVIEWS / "linkage_layout.svg").write_text("\n".join(parts) + "\n", encoding="utf-8")
    (PREVIEWS / "linkage_coordinates.json").write_text(
        json.dumps({"units": "mm", "view": "+Y toward -Y, X left, Z up",
                    "coordinates_xz": coordinates, "leg_length": length,
                    "rod_length": rod, "crank_length": crank}, indent=2) + "\n")


def main():
    document_path = OUT / "wheel_leg_v2.FCStd"
    if not document_path.is_file():
        raise FileNotFoundError(f"Build the V2 assembly first: {document_path}")
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
    render_exploded(doc, exterior_rotation)

    # Store the editable FCStd in its complete, assembled, coloured view only.
    for obj in features:
        obj.ViewObject.Visibility = True
    save_view(doc, "assembly.png", assembly_rotation)
    assert original_parameters == (doc.Parameters.LegLength.Value, doc.Parameters.Beta.Value)
    assert original_expressions == {obj.Name: list(obj.ExpressionEngine) for obj in doc.Objects}
    doc.save()
    linkage_svg(parameters)
    print("FREECAD_V2_PREVIEWS_COMPLETE", flush=True)


if __name__ == "__main__":
    main()
