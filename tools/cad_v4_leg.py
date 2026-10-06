"""V4 co-planar nested PETG leg with thin CNC OA and paired 686AZZ1 bearings; FreeCAD solids are in millimetres.

OB outer plate, OA outer cheek and CW C cap occupy the same Y layer.
The open OB head clears the crank sweep; the C cap fastens from the opposite
side of AC's sweep. No hidden dimensions are inferred from the reference image.
Call configure(), designs(), hardware(), export_hardware() from the builder.
"""
from __future__ import annotations
import json
import math

import build_printable_robot as cad
import cad_v3_profiles as profiles
import build_nested_robot as prior
from build_reference_robot import profile_fillet, ring

App, Part, V = cad.App, cad.Part, cad.V
cyl, bar, cut, union, box = cad.cyl, cad.bar, cad.cut, cad.union, cad.box
L, R = 130.0, 35.0
POSTS = ((31, 12), (31, -12), (0, -66), (0, -93))
C_FASTENERS = ((-23, 24), (-23, 46))


def configure():
    """Return parameter updates without writing or replacing the caller's P."""
    return dict(carrier_y=[139, 145], outer_OB_y=[166, 172],
                fork_inner_y=[146, 152], fork_outer_y=[166, 172],
                A_fork_inner_y=[149, 152], A_fork_outer_y=[166, 169],
                OA_center_outer_y=[165, 170], OA_center_bridge_end=165,
                OA_material="6061-T6 CNC", oa_register_diameter=35.05,
                driven_links_y=[153, 165], coupler_link_y=[153, 165],
                hub_stator_face_y=165, wheel_center_y=191, wheel_track=382,
                bearing_bore=13.15, bearing_web_bore=11.8, bushing_bore=8.05,
                cnc_bushing_bore=8.0, inner_race_spacer_outer_diameter=7.2,
                bearing="NSK 686AZZ1 6x13x5; two per joint; not open 686A",
                leg_structure_width=33, joint_bushing_length=6, A_bushing_length=3,
                shaft="ground D6: A L23, C L29, B L36; steel external circlips",
                joint_support="OB outer / OA outer / CW C cap co-planar; A/B/C double shear",
                C_fork_fasteners=list(C_FASTENERS),
                ob_open_head_clearance_sector_degrees=[116, 248])

def _shift(shape, y):
    result = shape.copy()
    result.translate(V(0, y, 0))
    return result


def capsule(p, q, radius, y, thickness):
    """Exact straight rail with circular ends, for the curved C-fork branch."""
    dx, dz = q[0]-p[0], q[1]-p[1]
    length = math.hypot(dx, dz)
    nx, nz = -dz/length*radius, dx/length*radius
    pts = [V(x, y, z) for x, z in
           ((p[0]+nx, p[1]+nz), (q[0]+nx, q[1]+nz),
            (q[0]-nx, q[1]-nz), (p[0]-nx, p[1]-nz))]
    web = Part.Face(Part.makePolygon(pts+pts[:1])).extrude(V(0, thickness, 0))
    return union(web, cyl(radius, y, thickness, *p), cyl(radius, y, thickness, *q))


def _sector(y, thickness, radius=51, start=116, end=248):
    def point(deg):
        a = math.radians(deg)
        return V(radius*math.cos(a), y, radius*math.sin(a))
    p, m, q = point(start), point((start+end)/2), point(end)
    o = V(0, y, 0)
    wire = Part.Wire([Part.makeLine(o, p), Part.Arc(p, m, q).toShape(), Part.makeLine(q, o)])
    return Part.Face(wire).extrude(V(0, thickness, 0))


def ob_plate(outer=False):
    y = 166 if outer else 139
    shape = profiles.make_ob_profile(y, 6)
    shape = cut(shape, cyl(23.5 if outer else 20.2, y-1, 8))
    if outer:
        # A center swings at R35 through relative angles -119.83..-54.97 deg.
        # A's R13 eye plus clearance requires an open left head, not a bore alone.
        shape = cut(shape, _sector(y-1, 8))
    shape = cut(shape, cyl(cad.P["bushing_bore"]/2, y-1, 8, z=-L))
    for x, z in POSTS:
        shape = cut(shape, cyl(2.2, y-1, 8, x, z))
        if not outer:
            shape = cut(shape, cad.hex_pocket(x, z, 138.9, 3.3, 7.3))
    if not outer:
        shape = cad.bolt_pattern(shape, 25, 6, 30, 138, 8)
        for x, z in cad.points(25, 6, 30):
            shape = cut(shape, cyl(3.1, 142, 4, x, z))
    return shape


def oa_inner():
    # Thin 3 mm CNC A ear. The O neck stays at the verified motor pilot,
    # while the hollow bridge ends 1 mm inside the central outer cap.
    shape = union(prior.crank_profile(149, 3), cyl(22, 146, 3.1),
                  cyl(18, 151.9, 13.1), cyl(19.5, 139.2, 7))
    shape = cut(shape, cyl(cad.P["oa_register_diameter"]/2, 138, 2),
                cyl(cad.P["cnc_bushing_bore"]/2, 148, 5, z=-R),
                cyl(6, 138, 29))
    return cad.bolt_pattern(shape, 13.5, 6, 0, 139, 27)

def oa_outer():
    # Central disc nests inward by 1 mm, giving 2 mm under the M3 head.
    # A ear remains 3 mm, and the screw tops are flush at Y170.
    shape = union(prior.crank_profile(166, 3), cyl(22, 165, 5))
    shape = cut(shape, cyl(cad.P["cnc_bushing_bore"]/2, 165, 5, z=-R),
                cyl(6, 164, 7))
    shape = cad.bolt_pattern(shape, 13.5, 6, 0, 164, 7)
    for x, z in cad.points(13.5, 6, 0):
        shape = cut(shape, cyl(3.1, 167, 4, x, z))
    return shape

def bearing_pair(shape, z, y):
    """Two NSK 686AZZ1 6x13x5, 2 mm inner spacer, outer-race shoulder only."""
    radius = cad.P["bearing_bore"]/2
    return cut(shape, cyl(cad.P["bearing_web_bore"]/2, y-1, 14, z=z),
               cyl(radius, y-.1, 5.15, z=z),
               cyl(radius, y+6.95, 5.15, z=z))


def ac_link():
    # Smaller bearing eyes follow the selected D13 bearing, retaining a
    # continuous curved web rather than carrying unused D19 eye material.
    h = (12**2-8**2)**.5
    tangent_drop = 1.5*8/h
    c = profiles._Contour((8, -h))
    c.arc((0, 12), (-8, -h))
    c.bezier((-6.5, -h-tangent_drop), (-7, -23), (-7, -32))
    c.bezier((-7, -48), (-6.2, -57), (-6.2, -65))
    c.bezier((-6.2, -73), (-7, -82), (-7, -98))
    c.bezier((-7, -107), (-6.5, -L+h+tangent_drop), (-8, -L+h))
    c.arc((0, -L-12), (8, -L+h))
    c.bezier((6.5, -L+h+tangent_drop), (7, -107), (7, -98))
    c.bezier((7, -82), (6.2, -73), (6.2, -65))
    c.bezier((6.2, -57), (7, -48), (7, -32))
    c.bezier((7, -23), (6.5, -h-tangent_drop), (8, -h))
    shape = c.prism(153, 12)
    for z in (0, -L):
        shape = bearing_pair(shape, z, 153)
    return shape

def _c_cap_outline(y, thickness):
    # Retain generous C bushing wall; put both screws behind AC's swept region.
    # The cap has no B annulus: that would clash with OB's co-planar B support.
    return union(cyl(12, y, thickness, z=R),
                 capsule((0, R), C_FASTENERS[0], 6, y, thickness),
                 capsule((0, R), C_FASTENERS[1], 6, y, thickness))


def _c_side_bridge(y, thickness):
    # Keep the rail behind AC's reduced R12 eye and its full motion sweep.
    return union(capsule((-10, 5), C_FASTENERS[0], 6, y, thickness),
                 capsule(C_FASTENERS[0], C_FASTENERS[1], 6, y, thickness))


def cw_main():
    lower = profiles.make_cw_profile(153, 12).common(box(-50, 152, -170, 100, 14, 170))
    lower = union(lower, cyl(17, 153, 12))
    inner = union(prior.c_fork_outline(146, 6), _c_cap_outline(146, 6))
    bridge = union(ring(17, 10.2, 151.9, 13.1, 0), _c_side_bridge(151.9, 13.1),
                   *(cyl(6, 164.9, 1.1, x, z) for x, z in C_FASTENERS))
    shape = union(lower, inner, bridge)
    shape = cut(shape, cyl(cad.P["bushing_bore"]/2, 145, 8, z=R))
    for x, z in C_FASTENERS:
        shape = cut(shape, cyl(1.7, 145, 28, x, z),
                    cad.hex_pocket(x, z, 145.9, 9.6, 5.8))
    shape = bearing_pair(shape, 0, 153)
    for x, zz in cad.points(8.75, 3, 90):
        shape = cut(shape, cyl(1.7, 152, 14, x, zz-L),
                    cyl(2.9, 152.9, 7.1, x, zz-L))
    shape = cut(shape, cyl(6.6, 152, 14, z=-L))
    for x in (-10, 10):
        shape = cut(shape, cyl(1.8, 152, 14, x, -L+24))
    return shape.removeSplitter()

def cw_outer():
    shape = cut(_c_cap_outline(166, 6),
                cyl(cad.P["bushing_bore"]/2, 165, 8, z=R))
    for x, z in C_FASTENERS:
        shape = cut(shape, cyl(1.7, 165, 8, x, z),
                    Part.makeCone(1.7, 3.2, 1.5, V(x, 170.5, z), cad.YAXIS))
    return shape

def designs():
    return {
        "OB_inner_full": (ob_plate(), "hip", "PETG"),
        "OB_outer_full": (ob_plate(True), "hip", "PETG"),
        "OA_inner_hub": (oa_inner(), "oa", "CNC"),
        "OA_outer_cheek": (oa_outer(), "oa", "CNC"),
        "AC_bearing_link": (ac_link(), "ac", "PETG"),
        "CW_main_inner": (cw_main(), "output", "PETG"),
        "CW_outer_fork": (cw_outer(), "output", "PETG"),
    }


def hardware():
    items = []
    for name, role, z in (("A", "ac", 0), ("C", "ac", -L), ("B", "output", 0)):
        for offset in (0, 7):
            items.append((f"686AZZ1_{name}_{offset}", ring(6.5, 3, 153+offset, 5, z), role))
        items.append((f"inner_race_spacer_{name}", ring(3.6, 3.1, 158, 2, z), role))
    for name, role, z, inner, outer, ear, start, length in (
        ("A", "oa", -R, 149, 166, 3, 147.5, 23),
        ("C", "output", R, 146, 166, 6, 144.5, 29),
        ("B", "hip", -L, 139, 166, 6, 137.5, 36),
    ):
        grooves = (start+.5, start+length-1.3)
        items.append((f"ground_pin_{name}_{length}", prior.pin_shape(start, length, *grooves, z), role))
        for suffix, y in (("inner", inner), ("outer", outer)):
            items.append((f"bronze_sleeve_{name}_{suffix}", ring(4, 3.025, y, ear, z), role))
        for suffix, y in (("inner", inner-.2), ("outer", outer+ear)):
            items.append((f"end_shim_{name}_{suffix}", ring(5, 3.1, y, .2, z), role))
        items.append((f"circlip_{name}_inner", prior.circlip(grooves[0]+.1, z), role))
        items.append((f"circlip_{name}_outer", prior.circlip(grooves[1], z), role))
        for suffix, y in (("inner", 152), ("outer", 165)):
            items.append((f"race_washer_{name}_{suffix}", ring(3.6, 3.1, y, 1, z), role))
        if name == "B":
            items.append(("B_inner_standoff_7", ring(5, 3.1, 145, 7, z), role))
    for i, (x, z) in enumerate(POSTS):
        spacer = cut(cyl(5, 145, 21, x, z), cyl(2.15, 144, 23, x, z))
        # M4x35 fully engages 139..142.2 captive nut, with 1.2 mm inward tip.
        screw = union(cyl(2, 137.8, 35, x, z), cyl(3.5, 172.8, 4, x, z))
        washer = cut(cyl(4.5, 172, .8, x, z), cyl(2.15, 171, 3, x, z))
        nut = cut(cad.hex_pocket(x, z, 139, 3.2, 7), cyl(2, 138, 6, x, z))
        for label, shape in (("spacer21", spacer), ("M4x35", screw), ("washer", washer), ("nut", nut)):
            items.append((f"OB_tie_{i}_{label}", shape, "hip"))
    for i, (x, z) in enumerate(C_FASTENERS):
        # Head envelope: 1.5 mm cone + 0.2 mm rim = manufacturer k1.7.
        screw = union(cyl(1.5, 147, 23.3, x, z),
                      Part.makeCone(1.5, 3, 1.5, V(x, 170.3, z), cad.YAXIS),
                      cyl(3, 171.8, .2, x, z))
        nut = cut(cad.hex_pocket(x, z, 153, 2.4, 5.5), cyl(1.5, 152, 5, x, z))
        items.extend(((f"C_fork_M3x25_{i}", screw, "output"),
                      (f"C_fork_nut_{i}", nut, "output")))
    for i, (x, z) in enumerate(cad.points(13.5, 6, 0)):
        # 27 mm exposed grip and 3 mm motor thread engagement for M3x30.
        screw = union(cyl(1.5, 140, 27, x, z), cyl(2.75, 167, 3, x, z))
        items.append((f"OA_rotor_M3x30_{i}", screw, "oa"))
    return items

def export_hardware():
    folder = cad.OUT / "metal_hardware"
    folder.mkdir(parents=True, exist_ok=True)
    rows = []
    for length, quantity in ((23, 2), (29, 2), (36, 2)):
        shape = prior.pin_shape(0, length, .5, length-1.3)
        shape.check(True)
        shape.exportStep(str(folder / f"ground_pin_D6_L{length}.step"))
        rows.append(dict(part=f"ground_pin_D6_L{length}", quantity=quantity,
                         diameter_nominal=6, fit="g6 recommended; confirm actual fit", length=length,
                         groove_start_from_end=.5, end_land_min=.5, groove_width=.8,
                         groove_diameter=5.7, groove_diameter_tolerance="0/-0.04",
                         groove_width_tolerance="+0.10/0", ring="steel STWN6 / DIN471-6 t0.7"))
    (folder / "pin_specification.json").write_text(json.dumps(rows, indent=2)+"\n")
    rows = []
    for name, inner, outer, length, quantity, material in (
        ("inner_spacer_ID6_2_OD7_2_L2", 6.2, 7.2, 2, 6, "steel"),
        ("race_washer_ID6_2_OD7_2_t1", 6.2, 7.2, 1, 12, "steel"),
        ("B_standoff_ID6_2_OD10_L7", 6.2, 10, 7, 2, "steel"),
        ("OB_tube_ID4_3_OD10_L21", 4.3, 10, 21, 8, "metal"),
        ("end_shim_ID6_2_OD10_t0_2", 6.2, 10, .2, 12, "steel"),
        ("bushing_ID6_05_OD8_L6", 6.05, 8, 6, 8, "bearing bronze"),
        ("bushing_ID6_05_OD8_L3", 6.05, 8, 3, 4, "bearing bronze"),
    ):
        shape = ring(outer/2, inner/2, 0, length, 0)
        shape.check(True)
        shape.exportStep(str(folder / f"{name}.step"))
        rows.append(dict(part=name, inner_diameter=inner, outer_diameter=outer,
                         length=length, quantity=quantity, material=material))
    (folder / "spacer_specification.json").write_text(json.dumps(rows, indent=2)+"\n")


def local_review():
    """Bounded leg-only geometry review; full assembly verification is external."""
    parts = designs()
    report = dict(structural_width_mm=33, shared_outer_layer=[166, 172],
                  parameters=configure(), parts={}, collisions=[], minimum_clearances={},
                  sampled_lengths_mm=[120, 125, 150, 183.8477631085, 210, 225],
                  scope="7 leg bodies; sampled leg-versus-leg only; full assembly and strength external")
    for name, (shape, _, _) in parts.items():
        shape.check(True)
        report["parts"][name] = dict(valid=shape.isValid(), solids=len(shape.Solids),
                                     volume_mm3=shape.Volume,
                                     y_range=[shape.BoundBox.YMin, shape.BoundBox.YMax])
    for length in report["sampled_lengths_mm"]:
        state = cad.pose(length)
        placed = [(n, cad.transform(s, role, state)) for n, (s, role, _) in parts.items()]
        for i, (a, sa) in enumerate(placed):
            for b, sb in placed[i+1:]:
                d = sa.distToShape(sb)[0]
                key = a+"/"+b
                report["minimum_clearances"][key] = min(d, report["minimum_clearances"].get(key, 1e9))
                if d < 1e-6:
                    vol = sa.common(sb).Volume
                    if vol > .05:
                        report["collisions"].append(dict(length=length, a=a, b=b, volume_mm3=vol))
    (cad.OUT / "leg_layout_review.json").write_text(json.dumps(report, indent=2)+"\n")
    return report


if __name__ == "__main__":
    cad.configure(cad.ROOT / "mechanical/v4")
    cad.P.update(configure())
    result = local_review()
    print(json.dumps(result, indent=2))
