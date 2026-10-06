"""V4 two-piece nested J4310 motor coupling, in millimetres.

Use the installed FreeCAD Python. Importing this module does not configure the
shared builder or write files. Threads are represented by their tapping drills;
hardware() contains only exposed screw shanks, not the engaged thread segments.
"""
from __future__ import annotations

import itertools
import json
import math
from pathlib import Path

import build_printable_robot as cad

App, Part, V = cad.App, cad.Part, cad.V
cyl, cut, union = cad.cyl, cad.cut, cad.union
RADIAL_ANGLES = (15, 105, 195, 285)
RADIAL_Y = 84.0
RADIAL_SEAT = 25.3
RADIAL_HEAD_HEIGHT = 3.0
TAP_INNER_RADIUS = 16.5
PIN_ANGLES = (90, 210, 330)


def radial_cylinder(radius, r0, length, angle, y=RADIAL_Y):
    theta = math.radians(angle)
    direction = V(math.cos(theta), 0, math.sin(theta))
    return Part.makeCylinder(radius, length,
                             V(r0 * direction.x, y, r0 * direction.z), direction)


def xy_at(radius, angle):
    theta = math.radians(angle)
    return radius * math.cos(theta), radius * math.sin(theta)


def tapping_drill(angle):
    """5 mm cylindrical pilot plus 118-degree drill tip for a bottoming tap."""
    tip_length = 1.25 / math.tan(math.radians(59))
    theta = math.radians(angle)
    direction = V(math.cos(theta), 0, math.sin(theta))
    tip = Part.makeCone(0, 1.25, tip_length,
                        V(direction.x*(TAP_INNER_RADIUS-tip_length), RADIAL_Y,
                          direction.z*(TAP_INNER_RADIUS-tip_length)), direction)
    return union(radial_cylinder(1.25, TAP_INNER_RADIUS,
                                 22-TAP_INNER_RADIUS, angle), tip)


def rotor_flange():
    """D39 locating neck / D43 male spigot, rotor dowels and radial threads."""
    shape = cut(union(cyl(19.5, 72.2, 8.4), cyl(21.5, 80.5, 7)),
                cyl(17.525, 71.9, 1.1))
    for x, z in cad.points(13.5, 6, 0):
        shape = cut(shape, cyl(1.7, 72, 16, x, z),
                    cyl(2.9, 82, 6, x, z))
    for angle in PIN_ANGLES:
        x, z = xy_at(12.15, angle)
        # Nominal D4 reamed blind hole; the drawing specifies matched dowel fit.
        shape = cut(shape, cyl(2, 72.9, 6.1, x, z))
    for angle in RADIAL_ANGLES:
        shape = cut(shape, tapping_drill(angle))
    return shape


def stator_cup():
    """D57 cup: D43.05 sleeve 7 mm deep and axial knee-mounting disc."""
    shape = cut(cyl(28.5, 80.5, 13.5), cyl(21.525, 80.4, 7.1))
    for x, z in cad.points(19, 4, 45):
        # These channels intentionally intersect the cup's central bore and
        # permit a straight driver and screw to enter before nesting the male.
        shape = cut(shape, cyl(1.7, 87.4, 6.8, x, z),
                    cyl(2.9, 80.4, 11.1, x, z))
    for angle in RADIAL_ANGLES:
        shape = cut(shape, radial_cylinder(1.7, 21.4, 10, angle),
                    radial_cylinder(2.9, RADIAL_SEAT, 5, angle))
    return shape


def designs():
    return {
        "hip_rotor_cnc": (rotor_flange(), "hip", "CNC"),
        "knee_stator_cnc": (stator_cup(), "hip", "CNC"),
    }


def hardware(full_pins=False):
    """List (name, shape, role); all coupling hardware follows the hip rotor."""
    items = []
    for i, (x, z) in enumerate(cad.points(13.5, 6, 0)):
        screw = union(cyl(1.5, 73, 9, x, z), cyl(2.75, 82, 3, x, z))
        items.append((f"coupling_rotor_M3x12_{i}", screw, "hip"))
    for i, angle in enumerate(PIN_ANGLES):
        x, z = xy_at(12.15, angle)
        start = 70 if full_pins else 73
        items.append((f"coupling_rotor_dowel_D4_L9_{i}",
                      cyl(2, start, 79-start, x, z), "hip"))
    for i, (x, z) in enumerate(cad.points(19, 4, 45)):
        screw = union(cyl(1.5, 91.5, 2.5, x, z), cyl(2.75, 88.5, 3, x, z))
        items.append((f"coupling_knee_M3x6_{i}", screw, "hip"))
    for i, angle in enumerate(RADIAL_ANGLES):
        screw = union(radial_cylinder(1.5, 21.5, RADIAL_SEAT-21.5, angle),
                      radial_cylinder(2.75, RADIAL_SEAT, RADIAL_HEAD_HEIGHT, angle))
        items.append((f"coupling_radial_M3x8_{i}", screw, "hip"))
    return items


def _interference(a, b):
    return a.common(b).Volume


def _minimum_webs():
    axial_tools = [cyl(2.9, 80.4, 11.1, x, z)
                   for x, z in cad.points(19, 4, 45)]
    radial_tools = [radial_cylinder(1.7, 21.4, 10, angle)
                    for angle in RADIAL_ANGLES]
    axial_rotor = [cyl(2.9, 82, 6, x, z)
                   for x, z in cad.points(13.5, 6, 0)]
    tap_tools = [tapping_drill(angle) for angle in RADIAL_ANGLES]
    return {
        "cup_axial_tool_channel_to_radial_clearance_mm": min(
            a.distToShape(b)[0] for a, b in itertools.product(axial_tools, radial_tools)),
        "rotor_counterbore_to_radial_tap_mm": min(
            a.distToShape(b)[0] for a, b in itertools.product(axial_rotor, tap_tools)),
    }


def verify(include_motors=True):
    parts = designs()
    hw = hardware(full_pins=include_motors)
    named = [(name, value[0]) for name, value in parts.items()]
    named += [(name, shape) for name, shape, _ in hw]
    solids = {}
    for name, shape in named:
        shape.check(True)
        solids[name] = {"valid": shape.isValid(), "solids": len(shape.Solids),
                        "volume_mm3": round(shape.Volume, 6)}
        if not shape.isValid() or len(shape.Solids) != 1:
            raise ValueError(f"Invalid coupling component: {name}")
    intersections = []
    for (an, ash), (bn, bsh) in itertools.combinations(named, 2):
        volume = _interference(ash, bsh)
        if volume > 0.001:
            intersections.append({"a": an, "b": bn, "volume_mm3": volume})
    source = cad.ROOT / "references/DM-J4310-2EC/3D模型/DM-J4310-2EC-V1.1_3d_20260228_1.stp"
    motors = []
    if include_motors:
        for motor_name, y in (("hip_motor", 72.5), ("knee_motor", 139.5)):
            motor = cad.motor_shape(source, y)
            motors.append((motor_name, motor))
            for name, shape in named:
                volume = _interference(shape, motor)
                if volume > 0.001:
                    intersections.append({"a": name, "b": motor_name,
                                          "volume_mm3": volume})
    envelope = cyl(28.5, 69, 27)
    outside = []
    for name, shape, _ in hw:
        volume = shape.cut(envelope).Volume
        if volume > 0.001:
            outside.append({"name": name, "volume_mm3": volume})
    # Drivers enter from the open cup before the two halves are nested.
    access = {}
    cup = parts["knee_stator_cnc"][0]
    for i, (x, z) in enumerate(cad.points(19, 4, 45)):
        access[f"knee_axial_driver_{i}"] = cup.common(cyl(1.45, 60, 29, x, z)).Volume
    small = parts["hip_rotor_cnc"][0]
    for i, (x, z) in enumerate(cad.points(13.5, 6, 0)):
        access[f"hip_axial_driver_{i}"] = small.common(cyl(1.45, 84, 20, x, z)).Volume
    for i, angle in enumerate(RADIAL_ANGLES):
        access[f"radial_driver_{i}"] = cup.common(
            radial_cylinder(1.45, RADIAL_SEAT+2.5, 20, angle)).Volume
    report = {
        "revision": "v4", "status": "manufacturing_review_prototype",
        "units": "mm", "motor_source": str(source),
        "dimensions": {
            "rotor_flange_diameter": 43, "rotor_neck_diameter": 39,
            "rotor_neck_y": [72.2, 80.5], "rotor_spigot_y": [80.5, 87.5], "rotor_flange_y": [72.2, 87.5],
            "rotor_register_diameter": 35.05, "rotor_register_depth": 0.8,
            "rotor_dowels": {"count": 3, "diameter": 4, "pcd": 24.3,
                              "angles_deg": list(PIN_ANGLES), "y": [70, 79],
                              "motor_engagement": 3, "flange_engagement": 6},
            "stator_cup_diameter": 57, "stator_cup_y": [80.5, 94],
            "nesting_diameter": 43.05, "nesting_depth": 7,
            "radial_screws": {"count": len(RADIAL_ANGLES), "angles_deg": list(RADIAL_ANGLES),
                               "thread": "M3x0.5", "nominal_screw_length": 8,
                               "head_seat_radius": RADIAL_SEAT,
                               "head_height": RADIAL_HEAD_HEIGHT,
                               "tap_drill_diameter": 2.5,
                               "tap_drill_cylindrical_depth": 5,
                               "drill_point_included_angle": 118,
                               "full_thread_depth_min": 4.2,
                               "bottoming_tap_finish_required": True,
                               "engagement_in_male": 21.5-(RADIAL_SEAT-8)},
        },
        "minimum_geometric_webs": _minimum_webs(), "solids": solids,
        "collisions_over_0_001_mm3": intersections,
        "hardware_outside_D57_envelope": outside,
        "driver_intersection_volumes_mm3": access,
        "thread_model": "tapping drill in manufactured parts; only unengaged screw lengths in assembly",
        "full_motor_dowel_geometry_checked_here": include_motors,
        "global_hardware_omits_dowel_inside_rotor": True,
        "strength_validated": False,
    }
    return report, named + motors


def main():
    folder = cad.ROOT / "mechanical/v4"
    folder.mkdir(parents=True, exist_ok=True)
    report, named = verify()
    (folder / "coupling_review.json").write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps({key: report[key] for key in (
        "minimum_geometric_webs", "collisions_over_0_001_mm3",
        "hardware_outside_D57_envelope", "driver_intersection_volumes_mm3")}, indent=2))
    # Independent review files do not replace the complete robot assembly.
    destination = folder / "cnc"
    destination.mkdir(exist_ok=True)
    doc = App.newDocument("V4_Coupling_Local_Review")
    doc.Label = "V4 nested coupling — local manufacturing review"
    design_names = set(designs())
    for name, shape in named:
        obj = doc.addObject("PartDesign::Feature", name)
        obj.Label = name
        obj.Shape = shape
        if name in design_names:
            shape.exportStep(str(destination / f"{name}.step"))
    doc.recompute()
    doc.saveAs(str(folder / "coupling_local_review.FCStd"))
    App.closeDocument(doc.Name)


if __name__ == "__main__":
    main()
