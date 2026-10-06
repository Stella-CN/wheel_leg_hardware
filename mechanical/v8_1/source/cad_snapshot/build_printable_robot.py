"""Build the manufacturing-review robot with the installed FreeCAD Python API.

Run with /Applications/FreeCAD.app/Contents/Resources/bin/python.
All geometry is in millimetres. Motor interface data comes from the supplied
STEP and dimension drawings, not the simplified MuJoCo visual parameters.
"""
from __future__ import annotations

import csv
import json
import math
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "mechanical/v1"
RESOURCES = Path("/Applications/FreeCAD.app/Contents/Resources")
for folder in (RESOURCES / "lib", RESOURCES / "Mod", Path(__file__).parent):
    sys.path.insert(0, str(folder))

import FreeCAD as App
import Part
import Mesh
import MeshPart

from cad_chassis import build_chassis

V = App.Vector
P = {}
L, R = 130.0, 35.0
YAXIS = V(0, 1, 0)
COLORS = {
    "PETG": (0.20, 0.48, 0.65),
    "CNC": (0.76, 0.79, 0.83),
    "motor": (0.20, 0.22, 0.25),
    "steel": (0.67, 0.70, 0.74),
    "rubber": (0.13, 0.14, 0.16),
}


def configure(output_directory):
    """Load the selected revision without an implicit dependency on another one."""
    global OUT, P, L, R
    OUT = Path(output_directory)
    P = json.loads((OUT / "design_parameters.json").read_text())
    L, R = P["rod_length"], P["crank_length"]


def cyl(radius, y, height, x=0, z=0):
    return Part.makeCylinder(radius, height, V(x, y, z), YAXIS)


def box(x, y, z, dx, dy, dz):
    return Part.makeBox(dx, dy, dz, V(x, y, z))


def union(*shapes):
    return shapes[0].multiFuse(list(shapes[1:])).removeSplitter() if len(shapes) > 1 else shapes[0]


def cut(shape, *tools):
    return shape.cut(Part.makeCompound(list(tools))).removeSplitter()


def points(radius, count, phase):
    return [(radius * math.cos(math.radians(phase + i * 360 / count)),
             radius * math.sin(math.radians(phase + i * 360 / count)))
            for i in range(count)]


def bolt_pattern(shape, radius, count, phase, y, height, diameter=3.4):
    return cut(shape, *(cyl(diameter / 2, y, height, x, z)
                        for x, z in points(radius, count, phase)))


def bar(z0, z1, radius, y, height):
    lo, hi = sorted((z0, z1))
    return union(cyl(radius, y, height, 0, lo), cyl(radius, y, height, 0, hi),
                 box(-radius, y, lo, 2 * radius, height, hi - lo))


def hex_pocket(x, z, y, height, across_flats):
    corners = [V(x + a, y, z + b) for a, b in points(across_flats / math.sqrt(3), 6, 30)]
    return Part.Face(Part.makePolygon(corners + [corners[0]])).extrude(V(0, height, 0))


def fixed_pin(shape, z, y0, y1, shoulder_start):
    """Flush inward M5 nut, through-thread clearance and a supported 6 mm shoulder."""
    return cut(shape, cyl(2.7, y0 - 1, y1 - y0 + 2, z=z),
               cyl(3.1, shoulder_start, y1 - shoulder_start + 1, z=z),
               hex_pocket(0, z, y0 - 0.1, 5.3 if y0 == 150 else 4.3, 8.3))


def bearing_pair(shape, z, y):
    """Two 626 bearings: 6 mm each, with a 2 mm web and steel inner spacer."""
    radius = P["bearing_bore"] / 2
    return cut(shape, cyl(P.get("bearing_web_bore", 10.4) / 2, y - 1, 16, z=z),
               cyl(radius, y - 0.1, 6.15, z=z),
               cyl(radius, y + 7.95, 6.15, z=z))


def motor_mount():
    # Flat plate against the outside of the shell. A ring extends into its D64
    # opening to meet the actual stator plane at y=72. The center clears the
    # rotating CNC neck, including its radial running gap.
    shape = union(box(-39, 75, -39, 78, 5, 78), cyl(31, 72, 8))
    shape = cut(shape, cyl(20.2, 71, 11))
    shape = bolt_pattern(shape, 25, 6, 30, 71, 11)
    for x, z in points(25, 6, 30):
        shape = cut(shape, cyl(3.1, 77, 4, x, z))
    for x in (-30, 30):
        for z in (-30, 30):
            shape = cut(shape, cyl(2.2, 74, 7, x, z))
            # A protruding socket head at R42.4 would sweep into the R40 CNC
            # flange above y82. Use an M4 90-degree countersunk head flush
            # with y80; washer and nut are only on the inside of the case.
            shape = cut(shape, Part.makeCone(2.2, 4.5, 2.3,
                                            V(x, 77.8, z), YAXIS))
    return shape


def hip_adapter():
    # Rotor face is y73, stator face y72: 0.2 mm axial clearance at the lip.
    shape = union(cyl(19.5, 72.2, 10), cyl(40, 82, 6))
    shape = cut(shape, cyl(P["cnc_register_diameter"] / 2, 71, 2))
    shape = bolt_pattern(shape, 13.5, 6, 0, 72, 17)
    for x, z in points(13.5, 6, 0):
        shape = cut(shape, cyl(2.9, 84.5, 4, x, z))
    # M4x0.7 THROUGH threads, modelled by D3.3 tapping drills. Bolts enter
    # from the knee side; there is no space for nuts behind this flange.
    shape = bolt_pattern(shape, 34, 4, 45, 81, 8, 3.3)
    for x in (-34, 34):
        shape = cut(shape, cyl(1.5, 81, 8, x, 0))
    return shape


def knee_adapter():
    shape = cyl(40, 88, 6)
    shape = bolt_pattern(shape, 19, 4, 45, 87, 8)
    for x, z in points(19, 4, 45):
        shape = cut(shape, cyl(2.9, 87.9, 3.6, x, z))
    shape = bolt_pattern(shape, 34, 4, 45, 87, 8, 4.4)
    for x in (-34, 34):
        shape = cut(shape, cyl(1.51, 87, 8, x, 0))
    return shape


def carrier_ob():
    shape = union(cyl(37, 139, 8), bar(0, -L, 15, 139, 8))
    shape = cut(shape, cyl(20.2, 138, 10))
    shape = bolt_pattern(shape, 25, 6, 30, 138, 10)
    for x, z in points(25, 6, 30):
        shape = cut(shape, cyl(3.1, 144, 4, x, z))
    shape = fixed_pin(shape, -L, 139, 147, 144.5)
    # Axial lightening pocket leaves a full 4 mm web and wide solid edges.
    shape = cut(shape, bar(-54, -102, 6, 139 - 0.1, 4.1))
    return shape


def crank_oa():
    shape = union(cyl(19.5, 139.2, 11), cyl(22, 150, 14), bar(0, -R, 15, 150, 14))
    shape = cut(shape, cyl(P["print_register_diameter"] / 2, 138, 2))
    shape = bolt_pattern(shape, 13.5, 6, 0, 139, 26)
    for x, z in points(13.5, 6, 0):
        shape = cut(shape, cyl(3.1, 157, 8, x, z))
    return fixed_pin(shape, -R, 150, 164, 159.5)


def coupler_ac():
    shape = bar(0, -L, 16, 167, 14)
    shape = bearing_pair(shape, 0, 167)
    shape = bearing_pair(shape, -L, 167)
    # A broad web preserves the tension/compression load path.
    shape = cut(shape, bar(-29, -101, 6, 167 - 0.1, 4.1))
    return shape


def output_bcw():
    shape = union(bar(R, -L, 16, 150, 14), cyl(24, 150, 14, z=-L))
    shape = bearing_pair(shape, 0, 150)
    shape = fixed_pin(shape, R, 150, 164, 159.5)
    # H6215 is reversed about X: fixed-side 3-hole phase becomes 90 deg.
    for x, zz in points(8.75, 3, 90):
        shape = cut(shape, cyl(1.7, 149, 16, x, zz - L),
                    cyl(2.9, 149.9, 9.1, x, zz - L))
    shape = cut(shape, cyl(6.6, 149, 16, z=-L))
    # Cable route: central cavity remains open from both sides. Tie points
    # are on the link away from the small motor screw circle.
    for x in (-10, 10):
        shape = cut(shape, cyl(1.8, 149, 16, x, -L + 29))
    shape = cut(shape, bar(-32, -87, 6, 150 - 0.1, 4.1))
    return shape


def wheel_rim():
    # H motor body y174..206; inner clearance D68.8. A rear lip and front
    # wheel disc retain the 32 mm-wide elastic tyre between y174..206.
    ring = cut(cyl(43, 172, 37), cyl(34.4, 171, 39))
    lip = cut(cyl(45, 172, 2), cyl(34.4, 171, 4))
    front = cyl(43, 207.7, 4.8)
    shape = union(ring, lip, front)
    shape = cut(shape, cyl(16.65, 207, 1.5))  # rotor face at208.5
    shape = bolt_pattern(shape, 14, 6, 30, 207, 7)
    for x, z in points(28, 6, 0):
        shape = cut(shape, cyl(7, 207, 7, x, z))
    return shape


def tolerance_coupon():
    shape = box(0, 0, 0, 100, 30, 6)
    for i, dia in enumerate((19.0, 19.1, 19.15, 19.2)):
        shape = shape.cut(Part.makeCylinder(dia / 2, 8, V(13 + i * 24, 15, -1)))
    return shape.removeSplitter()


def mirror(shape):
    return shape.mirror(V(0, 0, 0), V(0, 1, 0))


def moved(shape, x=0, z=0, angle=0):
    copy = shape.copy()
    copy.rotate(V(0, 0, 0), YAXIS, -angle)
    copy.translate(V(x, 0, z))
    return copy


def pose(length, beta=0):
    lower = P.get('lower_length', L)
    cosine = (length*length-L*L-lower*lower)/(2*L*lower)
    if not -1 <= cosine <= 1:
        raise ValueError(f'Unreachable hip-to-wheel length: {length} mm')
    bend = math.acos(cosine)
    hip = beta-math.degrees(math.atan2(lower*math.sin(bend), L+lower*math.cos(bend)))
    output = hip+math.degrees(bend)
    oa = output-180
    def down(n, angle):
        return n * math.sin(math.radians(angle)), -n * math.cos(math.radians(angle))
    a, b = down(R, oa), down(L, hip)
    woff = down(lower, output)
    return dict(hip=hip, oa=oa, output=output, a=a, b=b,
                w=(b[0] + woff[0], b[1] + woff[1]))


def transform(shape, role, state):
    if role == "hip":
        return moved(shape, angle=state["hip"])
    if role == "oa":
        return moved(shape, angle=state["oa"])
    if role == "ac":
        return moved(shape, *state["a"], angle=state["hip"])
    if role == "output":
        return moved(shape, *state["b"], angle=state["output"])
    if role == "wheel":
        return moved(shape, *state["w"], angle=state["output"])
    return shape.copy()


def print_orientation(shape, native_z=False, flip=False, reverse_face=False):
    shape = shape.copy()
    if flip:
        shape.rotate(V(0, 0, 0), V(1, 0, 0), 180)
    elif not native_z:
        # Lay the large XZ face on the bed, keeping bearing/motor bores vertical.
        shape.rotate(V(0, 0, 0), V(1, 0, 0), 90 if reverse_face else -90)
    bb = shape.BoundBox
    shape.translate(V(-bb.XMin, -bb.YMin, -bb.ZMin))
    return shape


def create_doc():
    name = "WheelLegManufacturing" + OUT.name.upper()
    if name in App.listDocuments():
        App.closeDocument(name)
    doc = App.newDocument(name)
    assembly = doc.addObject("App::Part", "Robot")
    assembly.Label = "Wheel leg robot — " + P.get("material", "PETG / CNC") + " " + OUT.name
    params = doc.addObject("App::FeaturePython", "Parameters")
    for name, value in (("LegLength", P["leg_length"]), ("RodLength", L),
                        ("LowerLength", P.get('lower_length', L)), ("CrankLength", R)):
        params.addProperty("App::PropertyLength", name, "Kinematics")
        setattr(params, name, value)
    for name, value in (("Beta", 0), ("Alpha", 45), ("Hip", -45), ("OA", -135), ("Output", 45)):
        params.addProperty("App::PropertyAngle", name, "Kinematics")
        setattr(params, name, value)
    params.setExpression("Alpha", "acos((LegLength^2 - RodLength^2 - LowerLength^2) / (2 * RodLength * LowerLength)) / 2")
    params.setExpression("Hip", "Beta - atan2(LowerLength * sin(2 * Alpha), RodLength + LowerLength * cos(2 * Alpha))")
    params.setExpression("OA", "Hip + 2 * Alpha - 180 deg")
    params.setExpression("Output", "Hip + 2 * Alpha")
    params.addProperty("App::PropertyString", "OperatingRange", "Kinematics")
    limits = P.get('operating_leg_length', [120,225])
    params.OperatingRange = f"LegLength {limits[0]}..{limits[1]} mm; beta=0 discrete geometric check range"
    return doc, assembly, params


def put(doc, group, name, shape, role, material, state, description=""):
    obj = doc.addObject("Part::Feature", name)
    obj.Label = name.replace("_", " ")
    # Keep imported STEP top-level locations inside an identity compound;
    # object Placement is reserved exclusively for the live linkage pose.
    obj.Shape = Part.makeCompound([shape])
    group.addObject(obj)
    obj.addProperty("App::PropertyString", "Material", "Manufacturing")
    obj.Material = material
    obj.addProperty("App::PropertyString", "ManufacturingNote", "Manufacturing")
    obj.ManufacturingNote = description
    obj.addProperty("App::PropertyString", "KinematicRole", "Kinematics")
    obj.KinematicRole = role
    if role != "fixed":
        angle = {"hip": "Hip", "oa": "OA", "ac": "Hip", "output": "Output", "wheel": "Output"}[role]
        obj.Placement.Rotation = App.Rotation(YAXIS, 1)
        obj.setExpression("Placement.Rotation.Angle", f"-Parameters.{angle}")
        if role in ("ac", "output", "wheel"):
            distance = "CrankLength" if role == "ac" else "RodLength"
            origin_angle = "OA" if role == "ac" else "Hip"
            xexpr = f"Parameters.{distance} * sin(Parameters.{origin_angle})"
            zexpr = f"-Parameters.{distance} * cos(Parameters.{origin_angle})"
            if role == "wheel":
                xexpr += " + Parameters.LowerLength * sin(Parameters.Output)"
                zexpr += " - Parameters.LowerLength * cos(Parameters.Output)"
            obj.setExpression("Placement.Base.x", xexpr)
            obj.setExpression("Placement.Base.z", zexpr)
    if App.GuiUp:
        obj.ViewObject.ShapeColor = COLORS.get(material, COLORS["PETG"])
        obj.ViewObject.LineColor = (0.08, 0.12, 0.15)
    return obj


def export_part(name, shape, process, quantity, native_z=False, reverse_face=False,
                reference_stl=False):
    print(f"EXPORT_PART {name}", flush=True)
    if shape.isNull() or not shape.isValid() or len(shape.Solids) != 1:
        raise ValueError(f"Invalid manufacturing solid {name}: {len(shape.Solids)} solids")
    shape.check(True)
    step_path = OUT / ("cnc" if process == "CNC" else "step") / f"{name}.step"
    shape.exportStep(str(step_path))
    print_shape = print_orientation(shape, native_z, name == "chassis_lid", reverse_face)
    mesh = MeshPart.meshFromShape(Shape=print_shape, LinearDeflection=0.06,
                                  AngularDeflection=0.18, Relative=False)
    if not mesh.isSolid():
        raise ValueError(f"Non-solid triangulation: {name}")
    dimensions = [print_shape.BoundBox.XLength, print_shape.BoundBox.YLength, print_shape.BoundBox.ZLength]
    fits = all(a <= b + 1e-6 for a, b in zip(dimensions, P["print_bed"]))
    if process == "PETG":
        if not fits:
            raise ValueError(f"Print bed exceeded: {name} {dimensions}")
        path = OUT / "print" / f"{name}.stl"
        mesh.write(str(path))
        check = Mesh.Mesh(str(path))
        if not check.isSolid():
            raise ValueError(f"Exported STL is not closed: {name}")
    elif reference_stl:
        mesh.write(str(OUT / "stl" / f"{name}.stl"))
    return dict(part=name, process=process, quantity=quantity,
                dimensions_mm=[round(v, 3) for v in dimensions],
                volume_mm3=round(shape.Volume, 3), solids=1, brep_valid=True,
                mesh_closed=True, facets=mesh.CountFacets, fits_bed=fits,
                nominal_solid_mass_g=round(shape.Volume * (0.00127 if process == "PETG" else 0.0027), 1))


def motor_shape(source, translation_y):
    shape = Part.read(str(source))
    shape.rotate(V(0, 0, 0), V(1, 0, 0), 180)
    shape.translate(V(0, translation_y, 0))
    return shape


def interference_volume(a, b):
    """Exact volume after conservative solid bounding-box broad phase.

    Vendor motors and electronics contain multiple solids. Excluding components
    whose bounding boxes cannot overlap avoids a whole-board boolean for
    every fastener, without substituting a simplified collision envelope.
    """
    def overlaps(left, right):
        return all(min(getattr(left, axis+'Max'), getattr(right, axis+'Max')) >
                   max(getattr(left, axis+'Min'), getattr(right, axis+'Min'))
                   for axis in ('X','Y','Z'))
    bounds=(a.BoundBox,b.BoundBox)
    if not overlaps(*bounds):
        return 0.0
    aa, bb = a, b
    for original, other_bounds, which in ((a,bounds[1],0),(b,bounds[0],1)):
        solids=original.Solids
        if len(solids)>1:
            candidates=[s for s in solids if overlaps(s.BoundBox,other_bounds)]
            if not candidates:
                return 0.0
            filtered=Part.makeCompound(candidates)
            if which==0:aa=filtered
            else:bb=filtered
    return aa.common(bb).Volume


def build(designs=None, hardware=None, reverse_faces=(), mirrored_print_parts=(),
          hub_offset=0, check_hardware_pairs=False, coupons=None,
          chassis_parts=None, chassis_process="PETG", knee_translation_y=139.5,
          reference_stls=False, validation_lengths=None, global_hardware=(),
          chassis_materials=None, payloads=()):
    directories = ["cnc", "previews", "stl", "print", "step"] if reference_stls else ["print", "cnc", "step", "previews"]
    for dirname in directories:
        (OUT / dirname).mkdir(parents=True, exist_ok=True)
    doc, assembly, params = create_doc()
    state = pose(P["leg_length"])
    records, printable, assembly_items = [], [], []
    chassis = build_chassis() if chassis_parts is None else chassis_parts
    for name, shape in chassis.items():
        process = (chassis_materials or {}).get(name, chassis_process)
        records.append(export_part(name, shape, process, 1, True, reference_stl=reference_stls))
        obj = put(doc, assembly, name, shape, "fixed", process, state)
        printable.append(obj)
        assembly_items.append((name, shape, "fixed", process))

    designs = designs if designs is not None else {
        "hip_stator_mount": (motor_mount(), "fixed", "PETG"),
        "hip_rotor_cnc": (hip_adapter(), "hip", "CNC"),
        "knee_stator_cnc": (knee_adapter(), "hip", "CNC"),
        "fixed_arm_OB": (carrier_ob(), "hip", "PETG"),
        "active_arm_OA": (crank_oa(), "oa", "PETG"),
        "coupler_AC": (coupler_ac(), "ac", "PETG"),
        "output_BCW": (output_bcw(), "output", "PETG"),
        "wheel_rim": (wheel_rim(), "wheel", "PETG"),
    }
    for name, (shape, role, process) in designs.items():
        quantity = 1 if name in mirrored_print_parts else 2
        records.append(export_part(name, shape, process, quantity, reverse_face=name in reverse_faces,
                                   reference_stl=reference_stls))
        if name in mirrored_print_parts:
            records.append(export_part(name + "_left", mirror(shape), process, 1,
                                       reverse_face=name not in reverse_faces, reference_stl=reference_stls))
        for side in ("right", "left"):
            sided = shape if side == "right" else mirror(shape)
            obj = put(doc, assembly, f"{name}_{side}", sided, role, process, state)
            printable.append(obj)
            assembly_items.append((f"{name}_{side}", sided, role, process))
    coupons = {"bearing_fit_coupon": tolerance_coupon()} if coupons is None else coupons
    for name, shape in coupons.items():
        records.append(export_part(name, shape, "PETG", 1, True))

    reference = doc.addObject("App::Part", "PurchasedParts")
    reference.Label = "Purchased motors / bearings / shoulder screws / tyres"
    for name, shape, mass_g, note in payloads:
        obj = put(doc, reference, name, shape, "fixed", "payload", state, note)
        obj.addProperty("App::PropertyFloat", "BudgetMassGrams", "Manufacturing")
        obj.BudgetMassGrams = mass_g
        assembly_items.append((name, shape, "fixed", "payload"))
    refs = ROOT.parent / "references"
    jpath = refs / "DM-J4310-2EC/3D模型/DM-J4310-2EC-V1.1_3d_20260228_1.stp"
    hpath = refs / "DM-H6215/3D模型/6215_轮毂电机3D模型20240821.stp"
    jhip = motor_shape(jpath, 72.5)
    jknee = motor_shape(jpath, knee_translation_y)
    hub = motor_shape(hpath, 206 + hub_offset)
    for name, shape, role in (("J4310_hip", jhip, "fixed"), ("J4310_knee", jknee, "hip"),
                              ("H6215", hub, "wheel")):
        for side in ("right", "left"):
            sided = shape if side == "right" else mirror(shape)
            put(doc, reference, f"{name}_{side}", sided, role, "motor", state,
                "Original supplied STEP, rigid envelope. Internal rotor rotation is not animated.")
            assembly_items.append((f"{name}_{side}", sided, role, "motor"))
    for side in ("right", "left"):
        tyre = cut(cyl(50, 174, 32), cyl(43, 173, 34))
        tyre.translate(V(0, hub_offset, 0))
        if side == "left":
            tyre = mirror(tyre)
        put(doc, reference, f"elastic_tyre_{side}", tyre, "wheel", "rubber", state,
            "Purchased/custom elastic tyre OD100 ID86 width32; not PETG.")

    # Real passive joint hardware: reference steel rings and hardened shoulders.
    hardware = joint_hardware() if hardware is None else hardware
    for name, shape, role in hardware:
        for side in ("right", "left"):
            put(doc, reference, f"{name}_{side}", shape if side == "right" else mirror(shape),
                role, "steel", state, "Metal hardware reference; see this revision's bill of materials and fit specifications.")
    for name, shape, role in global_hardware:
        put(doc, reference, name, shape, role, "steel", state,
            "Global-position chassis hardware; not mirrored again.")
    all_hardware = list(hardware) + list(global_hardware)

    hardware_collisions = []
    # Cylindrical joint hardware is invariant under rotation about the pin.
    # Check it against every manufactured body at the nominal pose, including
    # the central spacer through the web between the two bearing seats.
    nominal_parts=[(name,transform(shape,role,state))
                   for name,shape,role,material in assembly_items
                   if material!='motor' and not name.endswith('_left')]
    for name, shape, role in all_hardware:
        hw = transform(shape, role, state)
        for pn, part in nominal_parts:
            if hw.BoundBox.intersect(part.BoundBox):
                volume = interference_volume(hw, part)
                if volume > 0.05:
                    hardware_collisions.append([name, pn, round(volume, 4)])
    (OUT / "joint_hardware_validation.json").write_text(json.dumps({
        "pose_leg_length_mm": P["leg_length"],
        "tested": "Listed joint hardware against manufactured parts at nominal pose",
        "hardware_objects": [name for name, _, _ in all_hardware],
        "excluded": "unmodelled motor/case/CNC fasteners, unmodelled nuts, wires, bearing rolling elements",
        "collisions": hardware_collisions,
    }, indent=2) + "\n")
    if hardware_collisions:
        raise ValueError(f"Joint hardware collision: {hardware_collisions}")

    doc.recompute()
    # Check live expression placements against the independent kinematics.
    pose_errors = []
    limits = P.get('operating_leg_length', [120,225])
    for length in (limits[0], P["leg_length"], limits[1]):
        params.LegLength = length
        doc.recompute()
        for name, shape, role, material in assembly_items:
            obj = doc.getObject(name)
            expected = transform(shape, role, pose(length))
            if (obj.Shape.BoundBox.Center - expected.BoundBox.Center).Length > 0.001:
                pose_errors.append([length, name])
    if pose_errors:
        raise ValueError(f"Expression placement mismatch: {pose_errors}")
    params.LegLength = P["leg_length"]
    doc.recompute()
    doc.saveAs(str(OUT / f"wheel_leg_{OUT.name}.FCStd"))
    Part.export(printable, str(OUT / "wheel_leg_structure.step"))
    Part.export([o for o in reference.Group if hasattr(o, "Shape")]
                + printable, str(OUT / "wheel_leg_assembly.step"))
    (OUT / "part_manifest.json").write_text(json.dumps(records, indent=2) + "\n")
    with (OUT / "parts.csv").open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(("part", "process", "quantity", "print_X_mm", "print_Y_mm", "print_Z_mm", "solid_mass_g_each"))
        for row in records:
            writer.writerow((row["part"], row["process"], row["quantity"], *row["dimensions_mm"], row["nominal_solid_mass_g"]))
    print("CAD_EXPORT_COMPLETE", flush=True)
    # Geometry checks are deliberately performed on actual solids, including
    # original vendor motor solids, instead of disabled MuJoCo self-collisions.
    verify(designs, chassis, jhip, jknee, hub, all_hardware, check_hardware_pairs,
           validation_lengths, payloads)
    if App.GuiUp:
        import FreeCADGui as Gui
        Gui.activeDocument().activeView().viewAxonometric()
        Gui.activeDocument().activeView().fitAll()
        doc.save()
    return doc


def joint_hardware(joints=("A", "B", "C")):
    hardware = []
    for name, role, z, yy, shoulder, fixed_start in (
            ("A", "ac", 0, 167, 25, 159.5),
            ("C", "ac", -L, 167, 25, 159.5),
            ("B", "output", 0, 150, 20, 144.5)):
        if name not in joints:
            continue
        for offset in (0, 8):
            hardware.append((f"626_{name}_{offset}", cut(cyl(9.5, yy + offset, 6, z=z),
                                                         cyl(3, yy + offset - 1, 8, z=z)), role))
        hardware.append((f"spacer_{name}", cut(cyl(5, yy + 6, 2, z=z),
                                              cyl(3.1, yy + 5, 4, z=z)), role))
        for y, height in ((yy - 3, 2.5), (yy - 0.5, 0.5), (yy + 14, 0.5)):
            hardware.append((f"washer_{name}_{str(y).replace('.', '_')}",
                             cut(cyl(5, y, height, z=z), cyl(3.1, y - 1, height + 2, z=z)), role))
        if name in ("A", "C"):
            hardware.append((f"outer_spacer_{name}",
                             cut(cyl(5, yy + 14.5, 3, z=z), cyl(3.1, yy + 14, 4, z=z)), role))
        pin = union(cyl(3, fixed_start, shoulder, z=z),
                    cyl(5, fixed_start + shoulder, 4.5, z=z),
                    cyl(2.5, fixed_start - 9.5, 9.5, z=z))
        hardware.append((f"shoulder_{name}", pin, role))
    return hardware


def verify(designs, chassis, jhip, jknee, hub, hardware=(), check_hardware_pairs=False,
           sampled_lengths=None, payloads=()):
    static = [(n, s, "fixed") for n, s in chassis.items()]
    static += [(n, shape, role) for n, (shape, role, _) in designs.items()]
    static += [("hip_motor", jhip, "fixed"), ("knee_motor", jknee, "hip"), ("hub_motor", hub, "wheel")]
    static += [(n, s, "fixed") for n, s, _, _ in payloads]
    collisions = []
    sampled_lengths = list(sampled_lengths) if sampled_lengths is not None else [120 + i * 5 for i in range(22)]
    static += [("hardware_" + n, s, role) for n, s, role in hardware]
    def frame(role):
        return "output" if role == "wheel" else role
    for sample, length in enumerate(sampled_lengths):
        state = pose(length)
        world = [(n, s if role=='fixed' else transform(s, role, state)) for n, s, role in static]
        bounds=[shape.BoundBox for _,shape in world]
        for i, (an, a) in enumerate(world):
            for j in range(i + 1, len(world)):
                bn, b = world[j]
                if (not check_hardware_pairs and an.startswith("hardware_")
                        and bn.startswith("hardware_")):
                    continue
                if sample and frame(static[i][2]) == frame(static[j][2]):
                    continue  # Rigid-relative pairs were checked at the first pose.
                if not bounds[i].intersect(bounds[j]):
                    continue
                volume = interference_volume(a, b)
                if volume > 0.05:
                    collisions.append(dict(leg_length=length, a=an, b=bn, intersection_mm3=round(volume, 4)))
        print(f"SWEEP {length} mm; accumulated collisions={len(collisions)}", flush=True)
    report = dict(freecad_version=App.Version(), units="mm", sampled_lengths=sampled_lengths,
                  beta_deg=0, solids_valid=True, exported_stl_closed=True,
                  live_pose_expressions_checked_at_mm=[P.get('operating_leg_length',[120,225])[0],
                      P["leg_length"], P.get('operating_leg_length',[120,225])[1]],
                  collision_threshold_mm3=0.05, collisions=collisions,
                  scope="Right leg, printed/CNC geometry, original motor STEP solids and listed joint hardware; left is mirror. Unmodelled fasteners, wires and dynamic deflection excluded. Rigid-relative pairs checked once; moving-relative pairs at all samples.",
                  hardware_pair_check=check_hardware_pairs,
                  strength_validated=False)
    (OUT / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"VALIDATION_COMPLETE collisions={len(collisions)}", flush=True)
    if collisions:
        raise ValueError("Interference sweep failed; see validation.json")


if __name__ == "__main__":
    configure(OUT)
    build()
