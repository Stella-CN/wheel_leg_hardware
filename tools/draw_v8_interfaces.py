"""One-page V8 interface drawing; vendor case dimensions vs our cradle.

Uses the exported V8 interfaces, without importing or modifying FreeCAD.
The source drawing provides no active-area, device-hole or mass dimensions.
"""
from html import escape
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "mechanical/v8"
INK = "#233747"
LINE = "#536b78"
LIGHT = "#9baab1"
TEAL = "#177d87"
AMBER = "#a76726"


def draw_display():
    display = json.loads((OUT / "display_interface.json").read_text())
    camera = json.loads((OUT / "payload_interfaces.json").read_text())["d435"]
    body = json.loads((OUT / "chassis_review.json").read_text())["body"]
    width, height, depth = display["outer_width_height_depth"]
    holes = display["cradle_holes_yz"]
    if (width, height, depth) != (122.0, 78.0, 14.5):
        raise ValueError("Drawing layout is for the selected 5-inch 122 x 78 x 14.5 mm case")
    expected_holes = {(-67.0, -34.0), (-67.0, 26.0), (67.0, -34.0), (67.0, 26.0)}
    if {tuple(point) for point in holes} != expected_holes:
        raise ValueError("Cradle interface changed; update drawing annotations")
    if display["active_display_area"] is not None or display["manufacturer_device_mounting_holes"] is not None:
        raise ValueError("New vendor information requires a reviewed drawing revision")
    if (display["face_x"], display["center_z"], camera["front_face_x"], camera["center_z"]) != (114.0, -4.0, 117.0, 61.0):
        raise ValueError("Front device datums changed; review the front layout")
    if body["size"] != [211, 164, 155] or body["edge_radius"] != 5:
        raise ValueError("Enclosure envelope changed; update the one-page layout")
    svg = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="810" viewBox="0 0 1100 810">',
        '<title>V8 5-inch GK-HD outside case and designed cradle interface</title>',
        '<desc>Manufacturer confirms only 122 by 78 by 14.5 mm. The four M3 cradle holes are our design, not device mounting holes. Active area and mass are not provided.</desc>',
        '<rect width="1100" height="810" fill="#f5f7f8"/>',
        f'<g font-family="Arial, sans-serif" fill="{INK}">',
    ]

    def text(x, y, label, size=17, color=INK, anchor="start", weight="normal", rotate=None):
        transform = f' transform="rotate({rotate} {x} {y})"' if rotate is not None else ""
        svg.append(f'<text x="{x:.2f}" y="{y:.2f}" font-size="{size}" fill="{color}" text-anchor="{anchor}" font-weight="{weight}"{transform}>{escape(label)}</text>')

    def line(x1, y1, x2, y2, color=LINE, dash=None, stroke=1.2):
        dashed = f' stroke-dasharray="{dash}"' if dash else ""
        svg.append(f'<path d="M{x1:.2f},{y1:.2f} L{x2:.2f},{y2:.2f}" stroke="{color}" stroke-width="{stroke}" fill="none"{dashed}/>')

    def arrow(tip_x, tip_y, direction_x, direction_y, color=LINE):
        norm = math.hypot(direction_x, direction_y)
        ux, uy = direction_x / norm, direction_y / norm
        bx, by = tip_x - 7 * ux, tip_y - 7 * uy
        points = ((tip_x, tip_y), (bx - 3 * uy, by + 3 * ux), (bx + 3 * uy, by - 3 * ux))
        coordinates = " ".join(f"{x:.2f},{y:.2f}" for x, y in points)
        svg.append(f'<polygon points="{coordinates}" fill="{color}"/>')

    def horizontal_dimension(x1, x2, y, label, ref_y1, ref_y2=None, color=LINE):
        ref_y2 = ref_y1 if ref_y2 is None else ref_y2
        line(x1, ref_y1, x1, y + 7, LIGHT)
        line(x2, ref_y2, x2, y + 7, LIGHT)
        line(x1, y, x2, y, color)
        arrow(x1, y, -1, 0, color)
        arrow(x2, y, 1, 0, color)
        text((x1 + x2) / 2, y - 10, label, color=color, anchor="middle")

    def vertical_dimension(y1, y2, x, label, ref_x, color=LINE):
        line(ref_x, y1, x + 7, y1, LIGHT)
        line(ref_x, y2, x + 7, y2, LIGHT)
        line(x, y1, x, y2, color)
        arrow(x, y1, 0, -1, color)
        arrow(x, y2, 0, 1, color)
        text(x - 12, (y1 + y2) / 2, label, color=color, anchor="middle", rotate=-90)

    text(48, 48, "V8 / 5-inch GK-HD — case & cradle interface", 27, weight="bold")
    text(48, 80, "Units: mm  ·  Datum O: hip-axis centre  ·  Manufacturer GK-HD / V3 / 20240428 / PDF p.2", 16)
    line(48, 103, 70, 103, TEAL, stroke=3)
    text(80, 109, "Supplier-confirmed case", 15, TEAL)
    line(330, 103, 352, 103, AMBER, stroke=3)
    text(362, 109, "Our cradle / enclosure design", 15, AMBER)
    text(48, 143, "SCREEN CASE / front projection (Y–Z)", 18, weight="bold")
    text(675, 143, "DEPTH / side projection", 18, weight="bold")

    scale, cx, cy = 3.4, 320.0, 335.0
    left, top = cx - width * scale / 2, cy - height * scale / 2
    right, bottom = cx + width * scale / 2, cy + height * scale / 2
    # One filled rectangle only: no speculative bezel or active-area line.
    svg.append(f'<rect x="{left:.2f}" y="{top:.2f}" width="{width*scale:.2f}" height="{height*scale:.2f}" fill="#e0e8eb" stroke="{TEAL}" stroke-width="2.2"/>')
    line(left - 8, cy, right + 8, cy, LIGHT, "8 4 2 4")
    line(cx, top - 7, cx, bottom + 8, LIGHT, "8 4 2 4")
    text(cx, cy - 21, "122 × 78 outer metal case", 21, anchor="middle", weight="bold")
    text(cx, cy + 18, "No active-area boundary specified", 16, anchor="middle")
    text(cx, cy + 46, "No device mounting holes specified", 16, anchor="middle")
    hole_positions = []
    for y, z in holes:
        px, py = cx + y * scale, cy - (z - display["center_z"]) * scale
        hole_positions.append((px, py))
        svg.append(f'<circle cx="{px:.2f}" cy="{py:.2f}" r="{display["cradle_hole_diameter"]*scale/2:.2f}" fill="white" stroke="{AMBER}" stroke-width="1.8"/>')
        line(px - 10, py, px + 10, py, AMBER, stroke=0.8)
        line(px, py - 10, px, py + 10, AMBER, stroke=0.8)
    horizontal_dimension(left, right, 184, "122 overall", top, color=TEAL)
    vertical_dimension(top, bottom, 66, "78 overall", left, TEAL)
    hole_left, hole_right = min(p[0] for p in hole_positions), max(p[0] for p in hole_positions)
    hole_top, hole_bottom = min(p[1] for p in hole_positions), max(p[1] for p in hole_positions)
    horizontal_dimension(hole_left, hole_right, 512, "134 cradle pitch", hole_bottom + 8, color=AMBER)
    vertical_dimension(hole_top, hole_bottom, 607, "60 cradle pitch", hole_right + 8, AMBER)
    text(80, 550, "4 × Ø3.4 clearance for M3 — our cradle only", 17, AMBER, weight="bold")
    text(80, 578, "Y = ±67;  Z = −34 / +26;  array centre = screen centre Z −4", 15)

    depth_scale, sx, sy = 2.4, 800.0, 203.0
    sw, sh = depth * depth_scale, height * depth_scale
    svg.append(f'<rect x="{sx:.2f}" y="{sy:.2f}" width="{sw:.2f}" height="{sh:.2f}" fill="#e0e8eb" stroke="{TEAL}" stroke-width="2"/>')
    horizontal_dimension(sx, sx + sw, 184, "14.5", sy, color=TEAL)
    line(748, 245, sx, 245, LIGHT)
    text(738, 238, "Rear", 15, anchor="end")
    text(738, 260, "X 99.5", 15, anchor="end")
    line(sx + sw, 292, 889, 292, LIGHT)
    text(899, 286, "Screen face", 15)
    text(899, 308, "X 114", 15)

    # Compact whole-front arrangement below the depth datum labels.
    text(675, 424, "FRONT LAYOUT / camera above screen", 16, weight="bold")
    front_scale, fc, ft = 0.94, 798.0, 441.0
    bounds = body["bounds"]
    body_width, body_height = body["size"][1], body["size"][2]
    body_left = fc - body_width * front_scale / 2
    svg.append(f'<rect x="{body_left:.2f}" y="{ft:.2f}" width="{body_width*front_scale:.2f}" height="{body_height*front_scale:.2f}" rx="{body["edge_radius"]*front_scale:.2f}" fill="#edf0f2" stroke="{AMBER}" stroke-width="1.5"/>')
    front_z = lambda z: ft + (bounds[5] - z) * front_scale
    screen_top = front_z(display["center_z"] + height / 2)
    svg.append(f'<rect x="{fc-width*front_scale/2:.2f}" y="{screen_top:.2f}" width="{width*front_scale:.2f}" height="{height*front_scale:.2f}" fill="#d8e5e8" stroke="{TEAL}" stroke-width="1.4"/>')
    cw, ch = camera["envelope_dimensions"][:2]
    camera_top = front_z(camera["center_z"] + ch / 2)
    svg.append(f'<rect x="{fc-cw*front_scale/2:.2f}" y="{camera_top:.2f}" width="{cw*front_scale:.2f}" height="{ch*front_scale:.2f}" rx="5" fill="#a3b9c2" stroke="{LINE}" stroke-width="1.2"/>')
    text(fc, front_z(camera["center_z"]) + 5, "D435", 13, anchor="middle")
    text(fc, front_z(display["center_z"]) + 5, "5-inch case", 13, anchor="middle")
    camera_y, screen_y = front_z(camera["center_z"]), front_z(display["center_z"])
    line(fc + cw * front_scale / 2, camera_y, 887, camera_y, LIGHT)
    text(897, camera_y - 5, "X 117 / Z 61", 14)
    line(fc + width * front_scale / 2, screen_y, 887, screen_y, LIGHT)
    text(897, screen_y - 5, "X 114 / Z −4", 14)

    line(48, 613, 1052, 613, "#c8d1d6")
    text(48, 648, "KNOWN", 16, TEAL, weight="bold")
    text(183, 648, "122 × 78 × 14.5 mm outside case; no inferred screen-active-area dimensions.", 16)
    text(48, 680, "NOT PROVIDED", 16, AMBER, weight="bold")
    text(183, 680, "Active area (AA), device mounting-hole datums, mass and mass centre.", 16)
    text(48, 712, "OUR DESIGN", 16, AMBER, weight="bold")
    text(183, 712, "4 × M3 cradle at 134 × 60 mm. These are not holes in the purchased device.", 16)
    text(48, 744, "ENCLOSURE", 16, AMBER, weight="bold")
    text(183, 744, "211 × 164 × 155 mm (X × Y × Z), edge R5. Front arrangement is schematic.", 16)
    text(48, 784, "Review reference only · verify physical contact regions, tolerances and cable clearance before manufacturing.", 15, LINE)
    svg.append("</g></svg>")
    destination = OUT / "previews"
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "display_dimensions.svg").write_text("\n".join(svg) + "\n")


if __name__ == "__main__":
    draw_display()
