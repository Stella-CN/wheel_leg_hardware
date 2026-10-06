"""Curved XZ plate profiles for the reference-leg V3, in millimetres.

The nominal pivots remain O=(0,0), B=(0,-130) for OB, and
C=(0,35), B=(0,0), W=(0,-130) for CW.  Only outer contours and
lightening windows live here: motor holes, forks and fastening features
belong to the assembly builder.  CAD curves are exact arcs and Beziers.

Run with FreeCAD's Python to write an SVG and geometry-check JSON:
  /Applications/FreeCAD.app/Contents/Resources/bin/python \
      tools/cad_v3_profiles.py --output /tmp/v3-profiles

API reference:
https://github.com/FreeCAD/FreeCAD-documentation/blob/main/wiki/Topological_data_scripting.md
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys

_FC_LIB = Path("/Applications/FreeCAD.app/Contents/Resources/lib")
if str(_FC_LIB) not in sys.path:
    sys.path.insert(0, str(_FC_LIB))

import FreeCAD as App
import Part

V = App.Vector
WINDOW_RADIUS = 2.0
MIN_RIB = 6.0

# Every triangle is an unrounded construction polygon.  R2 fillets remove
# the acute tips, increasing the true wall width beyond the polygon limit.
OB_WINDOWS = (
    ((-10.0, -42.0), (10.0, -42.0), (-10.0, -55.0)),
    ((10.0, -70.0), (10.0, -84.0), (-10.0, -84.0)),
    ((-10.0, -101.5), (10.0, -101.5), (-10.0, -113.5)),
)
CW_WINDOWS = (
    ((-8.0, -29.0), (8.0, -29.0), (-8.0, -42.0)),
    ((8.0, -38.0), (8.0, -57.0), (-8.0, -57.0)),
    ((-8.0, -64.0), (10.0, -64.0), (-8.0, -81.0)),
    ((10.0, -75.0), (10.0, -95.0), (-8.0, -95.0)),
)


def _point(xz, y=0.0):
    return V(xz[0], y, xz[1])


def _fmt(xz):
    return f"{xz[0]:.8g},{xz[1]:.8g}"


def _arc_svg(start, middle, end):
    """Compute SVG's circular-arc flags from the same three CAD points."""
    ax, az = start
    bx, bz = middle
    cx, cz = end
    determinant = 2 * (ax * (bz-cz) + bx * (cz-az) + cx * (az-bz))
    if abs(determinant) < 1e-10:
        raise ValueError("Collinear circular-arc points")
    aa, bb, cc = ax*ax+az*az, bx*bx+bz*bz, cx*cx+cz*cz
    ux = (aa*(bz-cz) + bb*(cz-az) + cc*(az-bz)) / determinant
    uz = (aa*(cx-bx) + bb*(ax-cx) + cc*(bx-ax)) / determinant
    radius = math.hypot(ax-ux, az-uz)
    a, b, c = (math.atan2(z-uz, x-ux) for x, z in (start, middle, end))
    turn = 2*math.pi
    ccw_end, ccw_mid = (c-a) % turn, (b-a) % turn
    sweep = int(ccw_mid < ccw_end)
    angle = ccw_end if sweep else turn-ccw_end
    return f"A {radius:.8g},{radius:.8g} 0 {int(angle > math.pi)} {sweep} {_fmt(end)}"


class _Contour:
    """One ordered closed wire, with an exact SVG projection for review."""

    def __init__(self, start):
        self.start = tuple(start)
        self.current = self.start
        self.edges = []
        self.svg = ["M " + _fmt(start)]

    def line(self, end):
        self.edges.append(Part.makeLine(_point(self.current), _point(end)))
        self.svg.append("L " + _fmt(end))
        self.current = tuple(end)
        return self

    def bezier(self, control1, control2, end):
        curve = Part.BezierCurve()
        curve.setPoles([_point(p) for p in (self.current, control1, control2, end)])
        # Exact polynomial conversion, not tessellation or approximation.
        # OCC's BOP checker in the installed FreeCAD aborts on extruded native
        # Bezier surfaces; the equivalent B-spline representation is supported.
        self.edges.append(curve.toBSpline().toShape())
        self.svg.append("C " + " ".join(_fmt(p) for p in (control1, control2, end)))
        self.current = tuple(end)
        return self

    def arc(self, middle, end):
        self.edges.append(Part.Arc(_point(self.current), _point(middle), _point(end)).toShape())
        self.svg.append(_arc_svg(self.current, middle, end))
        self.current = tuple(end)
        return self

    def wire(self):
        if math.dist(self.current, self.start) > 1e-7:
            raise ValueError("Contour is not closed")
        result = Part.Wire(self.edges)
        if not result.isClosed() or not result.isValid():
            raise ValueError("Invalid contour")
        return result

    def prism(self, y, thickness):
        if thickness <= 0:
            raise ValueError("Plate thickness must be positive")
        result = Part.Face(self.wire()).extrude(V(0, thickness, 0))
        result.translate(V(0, y, 0))
        if not result.isValid() or len(result.Solids) != 1:
            raise ValueError("Invalid curved plate extrusion")
        return result

    def svg_path(self):
        return " ".join(self.svg) + " Z"


def _ob_contour():
    q = 40 / math.sqrt(2)
    # The head is a true 270-degree R40 arc.  Its outgoing 45-degree
    # tangents meet the Beziers without a corner or small neck fillet.
    return (_Contour((q, -q))
            .arc((0, 40), (-q, -q))
            .bezier((-20.5, 20.5-2*q), (-18, -42), (-18, -55))
            .bezier((-18, -78), (-17, -104), (-17, -130))
            .arc((0, -147), (17, -130))
            .bezier((17, -104), (18, -78), (18, -55))
            .bezier((18, -42), (20.5, 20.5-2*q), (q, -q)))


def _cw_contour():
    # Curved side rails join the C and W round ends.  Around B the width
    # stays 32 mm, leaving >=6.4 mm outside a nominal D19.2 bearing seat.
    return (_Contour((13, 35))
            .bezier((13, 25), (16, 17), (16, 0))
            .bezier((16, -34), (16, -64), (18, -92))
            .bezier((20, -120), (24, -112), (24, -130))
            .arc((0, -154), (-24, -130))
            .bezier((-24, -110), (-14, -108), (-14, -92))
            .bezier((-14, -60), (-16, -35), (-16, 0))
            .bezier((-16, 17), (-13, 25), (-13, 35))
            .arc((0, 48), (13, 35)))


def _rounded_polygon(vertices, radius=WINDOW_RADIUS):
    """Replace each convex polygon tip by an exact, tangent circular arc."""
    if radius <= 0:
        raise ValueError("Window radius must be positive")
    corners = []
    for i, p in enumerate(vertices):
        prev, nxt = vertices[i-1], vertices[(i+1) % len(vertices)]
        a = (prev[0]-p[0], prev[1]-p[1])
        b = (nxt[0]-p[0], nxt[1]-p[1])
        la, lb = math.hypot(*a), math.hypot(*b)
        a, b = (a[0]/la, a[1]/la), (b[0]/lb, b[1]/lb)
        theta = math.acos(max(-1.0, min(1.0, a[0]*b[0]+a[1]*b[1])))
        tangent = radius/math.tan(theta/2)
        bisector = (a[0]+b[0], a[1]+b[1])
        length = math.hypot(*bisector)
        bisector = (bisector[0]/length, bisector[1]/length)
        offset = radius/math.sin(theta/2)
        center = (p[0]+offset*bisector[0], p[1]+offset*bisector[1])
        inward = (p[0]+tangent*a[0], p[1]+tangent*a[1])
        outward = (p[0]+tangent*b[0], p[1]+tangent*b[1])
        middle = (center[0]-radius*bisector[0], center[1]-radius*bisector[1])
        corners.append((inward, middle, outward, tangent))
    for i in range(len(vertices)):
        length = math.dist(vertices[i], vertices[(i+1) % len(vertices)])
        if corners[i][3]+corners[(i+1) % len(vertices)][3] >= length-1e-6:
            raise ValueError("Window corner radii overlap")
    contour = _Contour(corners[0][0])
    for i, (inward, middle, outward, _) in enumerate(corners):
        if i:
            contour.line(inward)
        contour.arc(middle, outward)
    contour.line(corners[0][0])
    return contour


def ob_outer_prism(y, thickness):
    """OB outline, without lightening windows or joint/motor holes."""
    return _ob_contour().prism(y, thickness)


def cw_outer_prism(y, thickness):
    """C-B-W outline, without lightening windows or joint/motor holes."""
    return _cw_contour().prism(y, thickness)


def ob_window_tools(y, thickness, indices=None):
    """Separate cutting solids; optionally select a subset of the 3 windows."""
    return [_rounded_polygon(OB_WINDOWS[i]).prism(y, thickness)
            for i in (range(len(OB_WINDOWS)) if indices is None else indices)]


def cw_window_tools(y, thickness, indices=None):
    """Separate cutting solids; optionally select a subset of the 4 windows."""
    return [_rounded_polygon(CW_WINDOWS[i]).prism(y, thickness)
            for i in (range(len(CW_WINDOWS)) if indices is None else indices)]


def _cut_windows(outer, tools):
    result = outer.cut(Part.makeCompound(tools)).removeSplitter()
    if not result.isValid() or len(result.Solids) != 1:
        raise ValueError("Windows disconnected or invalidated the plate")
    return result


def make_ob_profile(y, thickness, indices=None):
    return _cut_windows(ob_outer_prism(y, thickness),
                        ob_window_tools(y-1, thickness+2, indices))


def make_cw_profile(y, thickness, indices=None):
    return _cut_windows(cw_outer_prism(y, thickness),
                        cw_window_tools(y-1, thickness+2, indices))


def validate_profiles():
    """Measure actual curved-edge ribs; holes/assembled clearance are external."""
    report = {}
    for name, outer, windows, make in (
        ("OB", _ob_contour(), OB_WINDOWS, make_ob_profile),
        ("CW", _cw_contour(), CW_WINDOWS, make_cw_profile),
    ):
        shape = make(0, 8)
        outlines = [_rounded_polygon(v).wire() for v in windows]
        borders = [outer.wire().distToShape(w)[0] for w in outlines]
        ribs = [a.distToShape(b)[0] for i, a in enumerate(outlines)
                for b in outlines[i+1:]]
        minimum = min(borders+ribs)
        if minimum < MIN_RIB-1e-6:
            raise ValueError(f"{name}: minimum rib {minimum:.4f} below {MIN_RIB}")
        report[name] = {
            "valid": shape.isValid(), "solids": len(shape.Solids),
            "volume_mm3_at_t8": shape.Volume,
            "minimum_window_to_outer_mm": min(borders),
            "minimum_between_windows_mm": min(ribs),
            "window_radius_mm": WINDOW_RADIUS,
            "curve_types": sorted(set(type(e.Curve).__name__ for e in outer.wire().Edges)),
        }
        if name == "OB":
            # Parent assembly's two M4 tie-rod holes.  This does not add
            # the holes, but prevents a window eroding their load-bearing rim.
            holes = [Part.makeCircle(2.2, V(0, 0, z), V(0, 1, 0))
                     for z in (-66, -93)]
            margins = [hole.distToShape(window)[0]
                       for hole in holes for window in outlines]
            if min(margins) < MIN_RIB-1e-6:
                raise ValueError("OB window violates M4 tie-rod hole edge margin")
            report[name]["minimum_tie_hole_to_window_mm"] = min(margins)
    return report


def write_preview(output):
    """Write a true-curve 2D review SVG; no approximated CAD polylines."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    report = validate_profiles()
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 610">',
             '<rect width="700" height="610" fill="#f4f6f8"/>',
             '<style>text{font-family:Arial,sans-serif;fill:#243043} '
             '.profile{stroke:#243043;stroke-width:.7;stroke-linejoin:round} '
             '.axis{stroke:#6c7786;stroke-width:.3;stroke-dasharray:2 2;fill:none}</style>',
             '<text x="40" y="34" font-size="22">V3 curved plate profiles / mm</text>']
    for xpos, name, color, contour, windows, joints in (
        (200, "OB", "#8adb74", _ob_contour(), OB_WINDOWS, (("O", 0), ("B", -130))),
        (500, "CW", "#62d5d2", _cw_contour(), CW_WINDOWS, (("C", 35), ("B", 0), ("W", -130))),
    ):
        parts.append(f'<text x="{xpos-16}" y="68" font-size="18">{name}</text>')
        parts.append(f'<g transform="translate({xpos},204) scale(2,-2)">')
        paths = [contour.svg_path()] + [_rounded_polygon(v).svg_path() for v in windows]
        parts.append(f'<path class="profile" fill-rule="evenodd" fill="{color}" d="{" ".join(paths)}"/>')
        parts.append('<path class="axis" d="M0 50V-160"/>')
        for label, z in joints:
            parts.append(f'<circle cx="0" cy="{z}" r="2" fill="white" stroke="#243043" stroke-width=".5"/>')
        parts.append('</g>')
        for label, z in joints:
            parts.append(f'<text x="{xpos+8}" y="{204-2*z-7}" font-size="14">{label}</text>')
    parts += ['<text x="40" y="557" font-size="14">Exact circular arcs + tangent cubic Bezier rails; R2 windows.</text>',
              '<text x="40" y="581" font-size="14">Profiles only: motor holes, fork interfaces and fasteners are added by assembly builder.</text>',
              '</svg>']
    (output/"curved_profiles.svg").write_text("\n".join(parts)+"\n")
    (output/"curved_profiles_validation.json").write_text(json.dumps(report, indent=2)+"\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="/tmp/v3-profiles")
    args = parser.parse_args()
    print(json.dumps(write_preview(args.output), indent=2))
