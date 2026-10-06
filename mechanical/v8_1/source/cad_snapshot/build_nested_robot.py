"""V3: full twin OB plates, three nested double-shear joints, curved outlines.

Units: mm. A/C use 35 mm ground pins; B uses 56 mm. All pins are retained
by two steel external circlips, avoiding projecting shoulder-screw threads.
"""
import json
from pathlib import Path

import build_printable_robot as cad
import cad_v3_profiles as profiles
from build_reference_robot import profile_fillet, ring

App, Part, V = cad.App, cad.Part, cad.V
cyl, bar, cut, union, box = cad.cyl, cad.bar, cad.cut, cad.union, cad.box
POSTS = ((31, 12), (31, -12), (0, -66), (0, -93))
C_FASTENERS = ((-9, -20), (9, -20))
L, R = 130.0, 35.0


def translated(shape, y):
    result = shape.copy()
    result.translate(V(0, y, 0))
    return result


def ob_plate(outer=False):
    y = 184 if outer else 139
    shape = profiles.make_ob_profile(y, 8)
    shape = cut(shape, cyl(23.5 if outer else 20.2, y-1, 10))
    shape = cut(shape, cyl(cad.P["bushing_bore"]/2, y-1, 10, z=-L))
    for x, z in POSTS:
        shape = cut(shape, cyl(2.2, y-1, 10, x, z))
        if not outer:
            shape = cut(shape, cad.hex_pocket(x, z, 138.9, 3.3, 7.3))
    if not outer:
        shape = cad.bolt_pattern(shape, 25, 6, 30, 138, 10)
        for x, z in cad.points(25, 6, 30):
            shape = cut(shape, cyl(3.1, 144, 4, x, z))
    else:
        # A shallow curved relief follows the upper head, leaving 6.8 mm skin.
        annulus = cut(cyl(34, 190.8, 2), cyl(31, 190, 4))
        sector = annulus.common(box(-36, 190, 18, 50, 4, 22))
        shape = cut(shape, sector)
    return shape


def crank_profile(y, thickness):
    return profile_fillet(union(cyl(22, y, thickness), bar(0, -R, 9, y, thickness),
                                 cyl(13, y, thickness, z=-R)), 3.0)


def oa_inner():
    shape = union(crank_profile(150, 8), cyl(18, 157.9, 16.1),
                  cyl(19.5, 139.2, 11))
    shape = cut(shape, cyl(cad.P["print_register_diameter"]/2, 138, 2),
                cyl(cad.P["bushing_bore"]/2, 149, 10, z=-R))
    return cad.bolt_pattern(shape, 13.5, 6, 0, 139, 36)


def oa_outer():
    shape = cut(crank_profile(174, 8), cyl(cad.P["bushing_bore"]/2, 173, 10, z=-R))
    shape = cad.bolt_pattern(shape, 13.5, 6, 0, 173, 10)
    for x, z in cad.points(13.5, 6, 0):
        shape = cut(shape, cyl(3.1, 177, 6, x, z))
    return shape


def ac_link():
    # Tangent circular eyes and a gently waisted central strip.
    h = (16**2-8**2)**0.5
    c = profiles._Contour((8, -h))
    c.arc((0, 16), (-8, -h))
    c.bezier((-6.5, -h-.866), (-7, -23), (-7, -32))
    c.bezier((-7, -48), (-6.2, -57), (-6.2, -65))
    c.bezier((-6.2, -73), (-7, -82), (-7, -98))
    c.bezier((-7, -107), (-6.5, -L+h+.866), (-8, -L+h))
    c.arc((0, -L-16), (8, -L+h))
    c.bezier((6.5, -L+h+.866), (7, -107), (7, -98))
    c.bezier((7, -82), (6.2, -73), (6.2, -65))
    c.bezier((6.2, -57), (7, -48), (7, -32))
    c.bezier((7, -23), (6.5, -h-.866), (8, -h))
    shape = c.prism(159, 14)
    for z in (0, -L):
        shape = cad.bearing_pair(shape, z, 159)
    return shape


def c_fork_outline(y, thickness):
    # Full C-to-B cheek, rounded at its lower fastening lobe.
    raw = profiles.cw_outer_prism(y, thickness)
    limit = union(box(-40, y-1, -16, 80, thickness+2, 80),
                  bar(-16, -20, 17, y-1, thickness+2))
    result = raw.common(limit).removeSplitter()
    return cut(result, cyl(10.2, y-1, thickness+2),
               cyl(cad.P["bushing_bore"]/2, y-1, thickness+2, z=R))


def cw_main():
    # The B bearing tongue and curved lower arm sit inside the OB plate pair.
    # Terminate the middle web at B and use a round bearing boss. A flat web
    # extending to z17 leaves a corner that clips AC at the shortest pose.
    lower = profiles.make_cw_profile(159, 14).common(box(-50, 158, -170, 100, 16, 170))
    lower = union(lower, cyl(17, 159, 14))
    bridge = ring(17, 10.2, 157.9, 16.1, 0)
    shape = union(lower, bridge, c_fork_outline(150, 8))
    for x, z in C_FASTENERS:
        # One millimetre mating land supports the removable outer C cheek.
        shape = union(shape, cyl(5.5, 172.9, 1.1, x, z))
        # The inner C cheek overlaps this XY footprint: open the nut access
        # channel all the way to its y150 face, including the projecting thread.
        shape = cut(shape, cyl(2.2, 149, 26, x, z),
                    cad.hex_pocket(x, z, 149.9, 12.4, 7.3))
    shape = cad.bearing_pair(shape, 0, 159)
    for x, zz in cad.points(8.75, 3, 90):
        shape = cut(shape, cyl(1.7, 158, 16, x, zz-L),
                    cyl(2.9, 158.9, 9.1, x, zz-L))
    shape = cut(shape, cyl(6.6, 158, 16, z=-L))
    for x in (-10, 10):
        shape = cut(shape, cyl(1.8, 158, 16, x, -L+24))
    return shape.removeSplitter()


def cw_outer():
    shape = c_fork_outline(174, 8)
    for x, z in C_FASTENERS:
        shape = cut(shape, cyl(2.2, 173, 10, x, z),
                    Part.makeCone(2.2, 4.5, 2.3, V(x, 179.8, z), cad.YAXIS))
    return shape


def pin_shape(start, length, groove1, groove2, z=0):
    shape = cyl(3, start, length, z=z)
    for y in (groove1, groove2):
        shape = cut(shape, ring(3.5, 2.85, y, .8, z))
    return shape


def circlip(y, z):
    # Conservative D12 envelope; split ring is a reference, not a cutting drawing.
    return cut(ring(6, 2.85, y, .7, z), box(2.4, y-1, z-.6, 5, 3, 1.2))


def hardware():
    items = []
    for name, role, z in (("A", "ac", 0), ("C", "ac", -L), ("B", "output", 0)):
        for offset in (0, 8):
            items.append((f"626_{name}_{offset}", ring(9.5, 3, 159+offset, 6, z), role))
        items.append((f"inner_race_spacer_{name}", ring(4.2, 3.1, 165, 2, z), role))

    for name, role, z, inner, outer in (("A", "oa", -R, 150, 174),
                                      ("C", "output", R, 150, 174),
                                      ("B", "hip", -L, 139, 184)):
        start, length, grooves = ((148.5, 35, (149, 182.2)) if name != "B"
                                  else (137.5, 56, (138, 192.2)))
        items.append((f"ground_pin_{name}_{length}", pin_shape(start, length, *grooves, z), role))
        for suffix, y in (("inner", inner), ("outer", outer)):
            items.append((f"bronze_sleeve_{name}_{suffix}", ring(4, 3.025, y, 8, z), role))
        for suffix, y in (("inner", inner-.2), ("outer", outer+8)):
            items.append((f"end_shim_{name}_{suffix}", ring(5, 3.1, y, .2, z), role))
        items.append((f"circlip_{name}_inner", circlip(grooves[0]+.1, z), role))
        items.append((f"circlip_{name}_outer", circlip(grooves[1], z), role))
        for suffix, y in (("inner", 158), ("outer", 173)):
            items.append((f"race_washer_{name}_{suffix}", ring(4.2, 3.1, y, 1, z), role))
        if name == "B":
            items.append(("B_inner_standoff_11", ring(5, 3.1, 147, 11, z), role))
            items.append(("B_outer_standoff_10", ring(5, 3.1, 174, 10, z), role))

    for i, (x, z) in enumerate(POSTS):
        spacer = cut(cyl(5, 147, 37, x, z), cyl(2.15, 146, 39, x, z))
        screw = union(cyl(2, 137.8, 55, x, z), cyl(3.5, 192.8, 4, x, z))
        washer = cut(cyl(4.5, 192, .8, x, z), cyl(2.15, 191, 3, x, z))
        nut = cut(cad.hex_pocket(x, z, 139, 3.2, 7), cyl(2, 138, 6, x, z))
        for label, shape in (("spacer37", spacer), ("M4x55", screw), ("washer", washer), ("nut", nut)):
            items.append((f"OB_tie_{i}_{label}", shape, "hip"))
    for i, (x, z) in enumerate(C_FASTENERS):
        screw = union(cyl(2, 157, 22.8, x, z),
                      Part.makeCone(2, 4.2, 2.2, V(x, 179.8, z), cad.YAXIS))
        nut = cut(cad.hex_pocket(x, z, 159, 3.2, 7), cyl(2, 158, 6, x, z))
        items.extend(((f"C_fork_M4x25_{i}", screw, "output"),
                      (f"C_fork_nut_{i}", nut, "output")))
    # Rotor fasteners also clamp the two printed OA halves, through the O bridge.
    for i, (x, z) in enumerate(cad.points(13.5, 6, 0)):
        # Only the exposed 37 mm is included. The remaining 3 mm engages the
        # moving rotor thread, which the supplied rigid motor STEP cannot animate.
        screw = union(cyl(1.5, 140, 37, x, z), cyl(2.75, 177, 3, x, z))
        items.append((f"OA_rotor_M3x40_{i}", screw, "oa"))
    return items


def export_pin_drawings():
    folder = cad.OUT / "metal_hardware"
    folder.mkdir(parents=True, exist_ok=True)
    rows = []
    for length, quantity in ((35, 4), (56, 2)):
        # Local length axis Y; end lands 0.5, grooves width0.8, diameter5.7.
        shape = pin_shape(0, length, .5, length-1.3)
        assert shape.isValid() and len(shape.Solids) == 1
        shape.exportStep(str(folder / f"ground_pin_D6_L{length}.step"))
        rows.append(dict(part=f"ground_pin_D6_L{length}", quantity=quantity,
                         diameter_nominal=6, fit="g6 recommended; confirm bearing fit",
                         length=length, groove_start_from_end=.5, end_land_min=.5, groove_width=.8,
                         groove_diameter=5.7, groove_diameter_tolerance="0/-0.04",
                         groove_width_tolerance="+0.10/0", ring="steel STWN6 / DIN471-6 t0.7",
                         material="ground steel shaft; machine grooves before final inspection"))
    (folder / "pin_specification.json").write_text(json.dumps(rows, indent=2)+"\n")
    rings = (
        ("inner_spacer_ID6_2_OD8_4_L2", 6.2, 8.4, 2, 6, "steel"),
        ("race_washer_ID6_2_OD8_4_t1", 6.2, 8.4, 1, 12, "steel"),
        ("B_standoff_ID6_2_OD10_L11", 6.2, 10, 11, 2, "steel"),
        ("B_standoff_ID6_2_OD10_L10", 6.2, 10, 10, 2, "steel"),
        ("OB_tube_ID4_3_OD10_L37", 4.3, 10, 37, 8, "steel or aluminum, dimensionally matched"),
        ("end_shim_ID6_2_OD10_t0_2", 6.2, 10, .2, 12, "steel shim"),
        ("bushing_ID6_05_OD8_L8", 6.05, 8, 8, 12, "bearing bronze"),
    )
    ring_rows = []
    for name, inner, outer, length, quantity, material in rings:
        shape = ring(outer/2, inner/2, 0, length, 0)
        shape.check(True)
        shape.exportStep(str(folder / f"{name}.step"))
        ring_rows.append(dict(part=name, inner_diameter=inner, outer_diameter=outer,
                              length=length, quantity=quantity, material=material))
    (folder / "spacer_specification.json").write_text(json.dumps(ring_rows, indent=2)+"\n")


def bushing_coupon():
    shape = box(0, 0, 0, 64, 22, 6)
    for index, diameter in enumerate((8.0, 8.05, 8.10, 8.15)):
        shape = shape.cut(Part.makeCylinder(diameter/2, 8, V(8+16*index, 11, -1)))
    return shape.removeSplitter()


def main():
    out = cad.ROOT / "mechanical/v3"
    out.mkdir(parents=True, exist_ok=True)
    config = out / "design_parameters.json"
    if not config.exists():
        data = json.loads((cad.ROOT / "mechanical/v2/design_parameters.json").read_text())
        config.write_text(json.dumps(data, indent=2)+"\n")
    cad.configure(out)
    # Curved contour control points are specifically dimensioned for 130/35.
    if cad.L != L or cad.R != R:
        raise ValueError("V3 curved profiles require rod130/crank35; edit profiles before changing centres")
    for key in ("B_outer_cheek_y", "B_fork_boss_centres_z", "shaft"):
        cad.P.pop(key, None)
    cad.P.setdefault("bushing_bore", 8.05)
    cad.P.update(revision="v3_nested_double_shear", carrier_y=[139,147],
                 bearing="NSK 626ZZ1 6x19x6, or equivalent matching abutment dimensions",
                 bearing_web_bore=16.8, inner_race_spacer_outer_diameter=8.4,
                 outer_OB_y=[184,192], fork_inner_y=[150,158], fork_outer_y=[174,182],
                 driven_links_y=[159,173], coupler_link_y=[159,173],
                 hub_stator_face_y=173, wheel_center_y=199, wheel_track=398,
                 shaft="ground D6 pins: 35mm A/C, 56mm B, paired external steel circlips",
                 joint_support="B: full OB plates straddle CW; A/C: full clevises straddle AC",
                 truss_corner_radius=2.0, profile="tangent circular arcs and cubic Bezier rails")
    config.write_text(json.dumps(cad.P, indent=2)+"\n")
    rim = translated(union(cad.wheel_rim(), ring(45, 34.4, 206, 2, 0)), 9)
    designs = {
        "hip_stator_mount": (cad.motor_mount(), "fixed", "PETG"),
        "hip_rotor_cnc": (cad.hip_adapter(), "hip", "CNC"),
        "knee_stator_cnc": (cad.knee_adapter(), "hip", "CNC"),
        "OB_inner_full": (ob_plate(), "hip", "PETG"),
        "OB_outer_full": (ob_plate(True), "hip", "PETG"),
        "OA_inner_hub": (oa_inner(), "oa", "PETG"),
        "OA_outer_cheek": (oa_outer(), "oa", "PETG"),
        "AC_bearing_link": (ac_link(), "ac", "PETG"),
        "CW_main_inner": (cw_main(), "output", "PETG"),
        "CW_outer_fork": (cw_outer(), "output", "PETG"),
        "wheel_rim": (rim, "wheel", "PETG"),
    }
    export_pin_drawings()
    (out / "curved_profile_validation.json").write_text(json.dumps(profiles.validate_profiles(), indent=2)+"\n")
    cad.build(designs, hardware(), reverse_faces=("OA_inner_hub", "CW_main_inner"),
              mirrored_print_parts=("OB_inner_full", "OB_outer_full", "CW_main_inner", "CW_outer_fork"),
              hub_offset=9, check_hardware_pairs=True,
              coupons={"bearing_fit_coupon": cad.tolerance_coupon(),
                       "bushing_fit_coupon": bushing_coupon()})


if __name__ == "__main__":
    main()
