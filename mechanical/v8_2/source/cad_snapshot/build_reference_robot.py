"""Reference-image V2: ribbed planar links and a removable double-sided B fork.

Rebuild using the installed FreeCAD Python interpreter. Geometry is in mm.
The user image defines the topology/style; supplied motor STEP defines interfaces.
"""
import json
import build_printable_robot as cad

App, Part, V = cad.App, cad.Part, cad.V
cyl, bar, cut, union = cad.cyl, cad.bar, cad.cut, cad.union
L, R = cad.L, cad.R


def prism(vertices, y, thickness):
    points = [V(x, y, z) for x, z in vertices]
    return Part.Face(Part.makePolygon(points + points[:1])).extrude(V(0, thickness, 0))


def profile_fillet(shape, radius):
    """Round extrusion corners, excluding cylinder seam edges and planar rims."""
    edges = []
    for edge in shape.Edges:
        if len(edge.Vertexes) != 2:
            continue
        p, q = (v.Point for v in edge.Vertexes)
        if abs(p.x-q.x) > 1e-6 or abs(p.z-q.z) > 1e-6 or abs(p.y-q.y) < 1:
            continue
        parents = [f for f in shape.Faces if any(e.isSame(edge) for e in f.Edges)]
        if len(parents) == 2:
            edges.append(edge)
    result = shape.makeFillet(radius, edges).removeSplitter() if edges else shape
    if not result.isValid() or len(result.Solids) != 1:
        raise ValueError("Invalid rounded extrusion")
    return result


def triangle(vertices, y, thickness):
    return profile_fillet(prism(vertices, y, thickness), 1.2)


def upper_ob():
    outline = prism([(-25, -20), (-21, -45), (-18, -115),
                     (18, -115), (21, -45), (25, -20)], 139, 8)
    shape = profile_fillet(union(cyl(37, 139, 8), outline,
                                 bar(-112, -L, 18, 139, 8)), 1.5)
    # Two integrated bosses bridge the knee fork gap; the outer cheek is removable.
    for z in (-65, -87):
        shape = union(shape, cyl(7, 146.8, 20.2, z=z))
    shape = cut(shape, cyl(20.2, 138, 10))
    shape = cad.bolt_pattern(shape, 25, 6, 30, 138, 10)
    for x, z in cad.points(25, 6, 30):
        shape = cut(shape, cyl(3.1, 144, 4, x, z))
    for z in (-65, -87):
        shape = cut(shape, cyl(2.2, 138, 31, z=z),
                    cad.hex_pocket(0, z, 138.9, 3.3, 7.3))
    shape = cut(shape, cyl(3.1, 138, 10, z=-L),
                cyl(5.1, 138.9, 1.6, z=-L))
    for vertices in ([(-12, -40), (12, -40), (-12, -53)],
                     [(-10, -98), (10, -98), (10, -111)]):
        shape = cut(shape, triangle(vertices, 138, 10))
    return shape


def outer_cheek():
    shape = profile_fillet(union(bar(-65, -L, 9, 167, 8),
                                 cyl(14, 167, 8, z=-L)), 1.5)
    for z in (-65, -87):
        shape = cut(shape, cyl(2.2, 166, 10, z=z))
    return cut(shape, cyl(3.1, 166, 10, z=-L))


def crank_oa():
    plate = profile_fillet(union(cyl(22, 150, 14), bar(0, -R, 9, 150, 14),
                                 cyl(12, 150, 14, z=-R)), 1.5)
    shape = union(cyl(19.5, 139.2, 11), plate)
    shape = cut(shape, cyl(cad.P["print_register_diameter"] / 2, 138, 2))
    shape = cad.bolt_pattern(shape, 13.5, 6, 0, 139, 26)
    for x, z in cad.points(13.5, 6, 0):
        shape = cut(shape, cyl(3.1, 157, 8, x, z))
    return cad.fixed_pin(shape, -R, 150, 164, 159.5)


def coupler_ac():
    shape = profile_fillet(union(bar(0, -L, 8, 167, 14),
                                 cyl(16, 167, 14), cyl(16, 167, 14, z=-L)), 1.5)
    for z in (0, -L):
        shape = cad.bearing_pair(shape, z, 167)
    return shape


def lower_bcw():
    shape = profile_fillet(union(bar(0, -L, 16, 150, 14),
                                 cyl(24, 150, 14, z=-L),
                                 bar(0, R, 9, 150, 14), cyl(12, 150, 14, z=R)), 1.5)
    shape = cad.bearing_pair(shape, 0, 150)
    shape = cad.fixed_pin(shape, R, 150, 164, 159.5)
    for x, zz in cad.points(8.75, 3, 90):
        shape = cut(shape, cyl(1.7, 149, 16, x, zz-L),
                    cyl(2.9, 149.9, 9.1, x, zz-L))
    shape = cut(shape, cyl(6.6, 149, 16, z=-L))
    for x in (-10, 10):
        shape = cut(shape, cyl(1.8, 149, 16, x, -L+29))
    for vertices in ([(-9, -26), (9, -26), (-9, -43)],
                     [(9, -36), (9, -55), (-9, -55)],
                     [(-9, -62), (9, -62), (-9, -79)],
                     [(9, -72), (9, -91), (-9, -91)]):
        shape = cut(shape, triangle(vertices, 149, 16))
    return shape


def wheel_rim():
    # Add a positive outer retaining lip for the elastic tyre at y206..208.
    return union(cad.wheel_rim(), cut(cyl(45, 206, 2), cyl(34.4, 205, 4)))


def ring(outer, inner, y, height, z):
    return cut(cyl(outer, y, height, z=z), cyl(inner, y-1, height+2, z=z))


def hardware():
    items = cad.joint_hardware(("A", "C"))
    for offset in (0, 8):
        items.append((f"626_B_{offset}", ring(9.5, 3, 150+offset, 6, 0), "output"))
    items.append(("spacer_B", ring(5, 3.1, 156, 2, 0), "output"))
    # All clamp parts rotate with the fork; bearing rings with BCW are envelopes.
    for name, y, t, inner in (("inner_standoff", 147, 2.5, 3.1),
                              ("inner_washer", 149.5, .5, 3.1),
                              ("outer_washer", 164, .5, 3.1),
                              ("outer_standoff", 164.5, 2.5, 3.1),
                              ("head_washer", 175, .5, 3.1),
                              ("steel_shoulder_seat", 139.5, 1, 2.65)):
        items.append(("B_"+name, ring(5, inner, y, t, -L), "hip"))
    pin = union(cyl(3, 140.5, 35, z=-L), cyl(5, 175.5, 4.5, z=-L),
                cyl(2.5, 131, 9.5, z=-L))
    items.append(("shoulder_B_35", pin, "hip"))
    items.append(("B_M5_nut", cut(cad.hex_pocket(0, -L, 135.5, 4, 8),
                                  cyl(2.5, 134.5, 6, z=-L)), "hip"))
    for z in (-65, -87):
        suffix = str(abs(z))
        items.append(("fork_M4x40_"+suffix,
                      union(cyl(2, 135.8, 40, z=z), cyl(3.5, 175.8, 4, z=z)), "hip"))
        items.append(("fork_M4_washer_"+suffix, ring(4.5, 2.15, 175, .8, z), "hip"))
        items.append(("fork_M4_nut_"+suffix,
                      cut(cad.hex_pocket(0, z, 139, 3.2, 7), cyl(2, 138, 5.2, z=z)), "hip"))
    return items


def main():
    global L, R
    out = cad.ROOT / "mechanical/v2"
    out.mkdir(parents=True, exist_ok=True)
    if not (out / "design_parameters.json").exists():
        baseline = cad.ROOT / "mechanical/v1/design_parameters.json"
        (out / "design_parameters.json").write_text(baseline.read_text())
    cad.configure(out)
    L, R = cad.L, cad.R
    cad.P.update(revision="v2_reference_truss_prototype",
                 shaft="ISO7379 d6/M5: B shoulder35; A/C shoulder25 plus outer spacer3",
                 B_outer_cheek_y=[167, 175], B_fork_boss_centres_z=[-65, -87],
                 truss_corner_radius=1.2, profile_corner_radius=1.5,
                 reference_image="User supplied annotated leg: no hip roll; W replaced with H6215")
    (cad.OUT / "design_parameters.json").write_text(json.dumps(cad.P, indent=2)+"\n")
    designs = {
        "hip_stator_mount": (cad.motor_mount(), "fixed", "PETG"),
        "hip_rotor_cnc": (cad.hip_adapter(), "hip", "CNC"),
        "knee_stator_cnc": (cad.knee_adapter(), "hip", "CNC"),
        "fixed_arm_OB": (upper_ob(), "hip", "PETG"),
        "B_outer_cheek": (outer_cheek(), "hip", "PETG"),
        "active_arm_OA": (crank_oa(), "oa", "PETG"),
        "coupler_AC": (coupler_ac(), "ac", "PETG"),
        "output_BCW": (lower_bcw(), "output", "PETG"),
        "wheel_rim": (wheel_rim(), "wheel", "PETG"),
    }
    cad.build(designs, hardware(), reverse_faces=("fixed_arm_OB",),
              mirrored_print_parts=("fixed_arm_OB", "output_BCW"))


if __name__ == "__main__":
    main()
