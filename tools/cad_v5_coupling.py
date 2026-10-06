"""Compact CNC J4310 coupling using verified low-profile small-head screws.

System FreeCAD Python; all lengths are millimetres. Import is read-only.
configure(), designs(), hardware() follow the V4 module contract. build(P, out)
optionally exports a standalone local review, without changing the main builder.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import math
from pathlib import Path

import build_printable_robot as cad

App, Part, V = cad.App, cad.Part, cad.V
cyl, cut, union = cad.cyl, cad.cut, cad.union
PIN_ANGLES = (90, 210, 330)
RADIAL_ANGLES = (15, 105, 195, 285)
RADIAL_Y, RADIAL_SEAT, TAP_INNER_RADIUS = 79.5, 26.3, 17.0
CUP_FRONT, MALE_END, KNEE_BACK = 75.5, 82.5, 87.1
KNEE_TRANSLATION = 132.6
SOURCE = cad.ROOT / "references/DM-J4310-2EC/3D模型/DM-J4310-2EC-V1.1_3d_20260228_1.stp"
SMALL_HEAD_SOURCE = "https://www.nbk1560.com/images/en-US/product/lowsmallheadscrew/SLH-SD/SLH-SD_1.pdf"


def configure():
    return dict(hip_motor_translation_y=72.5, hip_stator_front_y=72.0,
                hip_rotor_face_y=73.0, knee_motor_translation_y=KNEE_TRANSLATION,
                knee_stator_back_y=KNEE_BACK, knee_stator_front_y=132.1,
                knee_rotor_face_y=133.1, coupling_front_y=72.2,
                knee_rear_face_y=KNEE_BACK, knee_stator_face_y=132.1,
                knee_output_face_y=133.1, coupler_nesting_y=[CUP_FRONT, MALE_END],
                coupling_cup_front_y=CUP_FRONT, coupling_male_end_y=MALE_END,
                coupling_axial_span=14.9, coupling_sleeve_depth=7.0,
                coupling_cup_outer_diameter=57.0, coupling_male_diameter=43.0,
                coupling_sleeve_diameter=43.05,
                coupling_radial_screw="NBK SLH-M3-8-SD",
                coupling_knee_screw="NBK SLH-M3-6-SD",
                coupling_rotor_screw="ISO4762 M3x8",
                coupling_radial_plane_y=RADIAL_Y,
                coupling_material="6061-T6 CNC")


def _check_parameters(parameters):
    if parameters is None:
        return
    # This revision is dimensioned against the supplied motor, not a generic
    # infinitely resizable adapter. Never silently accept displaced motor faces.
    for key in ("hip_motor_translation_y", "knee_motor_translation_y",
                "knee_stator_front_y", "knee_rotor_face_y"):
        if key in parameters and abs(parameters[key]-configure()[key]) > 1e-6:
            raise ValueError(f"V5 coupling requires {key}={configure()[key]}")


def radial_cylinder(radius, r0, length, angle, y=RADIAL_Y):
    a = math.radians(angle)
    d = V(math.cos(a), 0, math.sin(a))
    return Part.makeCylinder(radius, length, V(r0*d.x, y, r0*d.z), d)


def radial_hex(r0, length, angle, across_flats, y=RADIAL_Y):
    a = math.radians(angle)
    d, u = V(math.cos(a), 0, math.sin(a)), V(0, 1, 0)
    v = d.cross(u)
    center = V(r0*d.x, y, r0*d.z)
    rad = across_flats/math.sqrt(3)
    pts = [center + u*(rad*math.cos(math.radians(30+60*i))) +
           v*(rad*math.sin(math.radians(30+60*i))) for i in range(6)]
    return Part.Face(Part.makePolygon(pts+pts[:1])).extrude(d*length)


def tapping_drill(angle):
    h = 1.25/math.tan(math.radians(59))
    a = math.radians(angle)
    d = V(math.cos(a), 0, math.sin(a))
    tip = Part.makeCone(0, 1.25, h,
                        V((TAP_INNER_RADIUS-h)*d.x, RADIAL_Y,
                          (TAP_INNER_RADIUS-h)*d.z), d)
    return union(radial_cylinder(1.25, TAP_INNER_RADIUS, 22-TAP_INNER_RADIUS, angle), tip)


def rotor_flange():
    shape = union(cyl(19.5, 72.2, 3.4), cyl(21.5, CUP_FRONT, 7))
    shape = cut(shape, cyl(17.525, 72.1, .9))
    for x, z in cad.points(13.5, 6, 0):
        shape = cut(shape, cyl(1.7, 72, 11, x, z), cyl(2.9, 78, 5, x, z))
    for x, z in cad.points(12.15, 3, 90):
        shape = cut(shape, cyl(2, 72.9, 6.1, x, z))
    for angle in RADIAL_ANGLES:
        shape = cut(shape, tapping_drill(angle))
    return shape


def stator_cup():
    # Every axial D4.8 head/tool pocket is entirely inside the D43.05 sleeve.
    # The old four axial channels through the sleeve wall are eliminated.
    shape = cut(cyl(28.5, CUP_FRONT, KNEE_BACK-CUP_FRONT),
                cyl(21.525, CUP_FRONT-.1, 7.1))
    for x, z in cad.points(19, 4, 45):
        shape = cut(shape, cyl(1.7, MALE_END-.1, 5, x, z),
                    cyl(2.4, CUP_FRONT-.1, 9.2, x, z))
    for angle in RADIAL_ANGLES:
        shape = cut(shape, radial_cylinder(1.7, 21.4, 8, angle),
                    radial_cylinder(2.4, RADIAL_SEAT, 3.5, angle))
    return shape


def designs(parameters=None):
    _check_parameters(parameters)
    return {"hip_rotor_cnc": (rotor_flange(), "hip", "CNC"),
            "knee_stator_cnc": (stator_cup(), "hip", "CNC")}


def hardware(parameters=None, full_pins=False):
    _check_parameters(parameters)
    items = []
    for i, (x, z) in enumerate(cad.points(13.5, 6, 0)):
        screw = union(cyl(1.5, 73, 5, x, z), cyl(2.75, 78, 3, x, z))
        screw = cut(screw, cad.hex_pocket(x, z, 79.7, 1.5, 2.55))
        items.append((f"coupling_rotor_ISO4762_M3x8_{i}", screw, "hip"))
    for i, (x, z) in enumerate(cad.points(12.15, 3, 90)):
        start = 70 if full_pins else 73
        items.append((f"coupling_rotor_dowel_D4_L9_{i}",
                      cyl(2, start, 79-start, x, z), "hip"))
    for i, (x, z) in enumerate(cad.points(19, 4, 45)):
        screw = union(cyl(1.5, 84.6, 2.5, x, z), cyl(2.25, 82.6, 2, x, z))
        screw = cut(screw, cad.hex_pocket(x, z, 82.5, 1.6, 2.04))
        items.append((f"coupling_knee_SLH_M3x6_SD_{i}", screw, "hip"))
    for i, angle in enumerate(RADIAL_ANGLES):
        screw = union(radial_cylinder(1.5, 21.5, 4.8, angle),
                      radial_cylinder(2.25, RADIAL_SEAT, 2, angle))
        screw = cut(screw, radial_hex(26.8, 1.7, angle, 2.04))
        items.append((f"coupling_radial_SLH_M3x8_SD_{i}", screw, "hip"))
    return items


def _minimum_webs():
    axrot = [cyl(2.9, 78, 5, x, z) for x, z in cad.points(13.5, 6, 0)]
    pins = [cyl(2, 72.9, 6.1, x, z) for x, z in cad.points(12.15, 3, 90)]
    taps = [tapping_drill(a) for a in RADIAL_ANGLES]
    axcup = [cyl(2.4, CUP_FRONT-.1, 9.2, x, z) for x, z in cad.points(19, 4, 45)]
    radcup = [radial_cylinder(1.7, 21.4, 8, a) for a in RADIAL_ANGLES]
    def distance(a, b):
        return min(x.distToShape(y)[0] for x, y in itertools.product(a, b))
    return dict(rotor_counterbore_to_radial_tap=distance(axrot, taps),
                rotor_counterbore_to_dowel=distance(axrot, pins),
                dowel_to_radial_tap=distance(pins, taps),
                knee_counterbore_to_radial_through=distance(axcup, radcup),
                radial_counterbore_to_cup_mouth=RADIAL_Y-2.4-CUP_FRONT,
                radial_tap_to_male_end=MALE_END-RADIAL_Y-1.25,
                dowel_blind_end_web=MALE_END-79,
                axial_knee_tool_to_sleeve_radial_clearance=21.525-19-2.4,
                knee_head_bearing_thickness=KNEE_BACK-84.6,
                knee_head_axial_recess=82.6-MALE_END)


def verify(include_motors=True):
    ds, hw = designs(), hardware(full_pins=include_motors)
    manufactured = [(name, value[0]) for name, value in ds.items()]
    named = manufactured + [(name, shape) for name, shape, _ in hw]
    report = dict(revision="v5", status="CNC manufacturing review prototype",
                  units="mm", parameters=configure(), solids={}, collisions=[],
                  minimum_webs_mm=_minimum_webs(), motor_source=str(SOURCE),
                  source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  source_motor_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest())
    for n, sh in named:
        sh.check(True)
        report["solids"][n] = dict(valid=sh.isValid(), solids=len(sh.Solids), volume_mm3=sh.Volume)
        assert sh.isValid() and len(sh.Solids) == 1, n
    for (an, a), (bn, b) in itertools.combinations(named, 2):
        vol = a.common(b).Volume
        if vol > .001:
            report["collisions"].append(dict(a=an, b=bn, volume_mm3=vol))
    motors = []
    if include_motors:
        for n, y in (("hip_motor", 72.5), ("knee_motor", KNEE_TRANSLATION)):
            sh = cad.motor_shape(SOURCE, y)
            motors.append((n, sh))
            for pn, p in named:
                vol = sh.common(p).Volume
                if vol > .001:
                    report["collisions"].append(dict(a=pn, b=n, volume_mm3=vol))
        report["motor_to_motor_axial_gap"] = motors[1][1].BoundBox.YMin-motors[0][1].BoundBox.YMax
    env = cyl(28.5, 69, 25)
    report["hardware_outside_D57"] = []
    for n, sh, _ in hw:
        vol = sh.cut(env).Volume
        if vol > .001:
            report["hardware_outside_D57"].append(dict(name=n, volume_mm3=vol))
    # The NBK drawing gives head D1 +/-0.1. Check the largest specified D4.6,
    # in addition to the nominal detailed hardware used in the assembly.
    report["low_head_D4_6_limit_envelope"] = []
    for i, a in enumerate(RADIAL_ANGLES):
        head = radial_cylinder(2.3, RADIAL_SEAT, 2, a)
        report["low_head_D4_6_limit_envelope"].append(dict(index=i,
            outside_D57_mm3=head.cut(env).Volume,
            cup_intersection_mm3=head.common(ds["knee_stator_cnc"][0]).Volume))
    # Tools are checked at the appropriate stage. Rear screws are installed in
    # the cup before nesting; hip screws before the cup is installed. Radial
    # tools reach from outside after nesting. Actual hex sockets are included.
    report["tool_intersections_mm3"] = {}
    small, cup = ds["hip_rotor_cnc"][0], ds["knee_stator_cnc"][0]
    for i, (x, z) in enumerate(cad.points(13.5, 6, 0)):
        tool = cad.hex_pocket(x, z, 79.8, 20, 2.5)
        report["tool_intersections_mm3"][f"rotor_hex_{i}"] = sum(
            tool.common(p).Volume for n, p in named if n != "knee_stator_cnc" and
            not n.startswith(("coupling_knee_", "coupling_radial_")))
    for i, (x, z) in enumerate(cad.points(19, 4, 45)):
        tool = cad.hex_pocket(x, z, 60, 24, 2)
        report["tool_intersections_mm3"][f"knee_hex_{i}"] = cup.common(tool).Volume + sum(
            tool.common(p).Volume for n, p in named if n.startswith("coupling_knee_"))
    for i, angle in enumerate(RADIAL_ANGLES):
        tool = radial_hex(26.9, 25, angle, 2)
        report["tool_intersections_mm3"][f"radial_hex_{i}"] = sum(tool.common(p).Volume for _, p in named)
    # A conservative round envelope verifies clearance to the agreed Y75..78
    # motor-support outer ears, even where the six-sided driver rotates.
    report["radial_tool_min_y"] = RADIAL_Y-2/math.sqrt(3)
    report["radial_tool_clearance_to_mount_outer_y78"] = RADIAL_Y-2/math.sqrt(3)-78
    moving = [("cup", cup)] + [(n, sh) for n, sh in named if n.startswith("coupling_knee_")]
    if motors:
        moving.append(motors[1])
    fixed = [(n, sh) for n, sh in named if n == "hip_rotor_cnc" or n.startswith(("coupling_rotor_",))]
    if motors:
        fixed.append(motors[0])
    report["axial_nesting_sweep"] = []
    for delta in (0, 1.75, 3.5, 5.25, 7, 8):
        overlaps = []
        for n, sh in moving:
            shifted = sh.copy(); shifted.translate(V(0, delta, 0))
            for fn, fs in fixed:
                # Motor-to-motor bounding boxes are separated throughout;
                # avoid a costly check between two very detailed STEP motors.
                if n == "knee_motor" and fn == "hip_motor":
                    continue
                vol = shifted.common(fs).Volume
                if vol > .001:
                    overlaps.append(dict(moving=n, fixed=fn, volume_mm3=vol))
        report["axial_nesting_sweep"].append(dict(translation_y=delta, collisions=overlaps))
    report["fasteners"] = dict(rotor=dict(part="ISO4762 M3x8", head_diameter=5.5,
                                          head_height=3, engagement=3, grip=5),
        knee=dict(part="NBK SLH-M3-6-SD", head_diameter=4.5, head_height=2,
                  engagement=3.5, grip=2.5, screw_head_y=[82.6,84.6]),
        radial=dict(part="NBK SLH-M3-8-SD", head_diameter=4.5, head_height=2,
                    engagement=3.2, grip=4.8, tap_drill_diameter=2.5,
                    tap_drill_cylindrical_depth=4.5, drill_point_angle=118,
                    full_thread_depth_min=3.5, head_bearing_area_mm2=math.pi*(2.25**2-1.7**2)),
        low_head_primary_source=SMALL_HEAD_SOURCE, low_head_property_class="8.8",
        low_head_diameter_tolerance="+/-0.1", low_head_diameter_max=4.6,
        low_head_hex_AF=2, low_head_socket_depth=1.5,
        manufacturer_screw_max_torque_Nm=1.4,
        joint_torque_status="NOT a joint torque specification; verify aluminum head bearing pressure and proof load",
        dowels=dict(count=3, diameter=4, pcd=24.3, phase_degrees=list(PIN_ANGLES),
                    length=9, motor_engagement=3, flange_engagement=6))
    report["thread_representation"] = "Tapped pilots only; engaged screw lengths omitted; full motor-insertion dowels checked locally."
    report["strength_validated"] = False
    return report, named+motors


def build(parameters=None, output_directory=None, include_motors=True):
    _check_parameters(parameters)
    folder = Path(output_directory) if output_directory else cad.ROOT/"mechanical/v5"
    folder.mkdir(parents=True, exist_ok=True)
    report, named = verify(include_motors)
    (folder/"coupling_review.json").write_text(json.dumps(report, indent=2)+"\n")
    (folder/"coupling_fasteners.json").write_text(json.dumps(report["fasteners"], indent=2)+"\n")
    cnc = folder/"cnc";cnc.mkdir(exist_ok=True)
    doc = App.newDocument("V5_Coupling_Local_Review")
    doc.Label = "V5 compact coupling — manufacturing review"
    for n, sh in named:
        obj = doc.addObject("PartDesign::Feature", n);obj.Label=n;obj.Shape=sh
        if n in ("hip_rotor_cnc", "knee_stator_cnc"):
            sh.exportStep(str(cnc/f"{n}.step"))
            cad.mirror(sh).exportStep(str(cnc/f"{n}_left.step"))
    doc.recompute();doc.saveAs(str(folder/"coupling_local_review.FCStd"));App.closeDocument(doc.Name)
    return report


if __name__ == "__main__":
    report = build()
    print(json.dumps({k:report[k] for k in ("parameters", "minimum_webs_mm", "collisions",
          "hardware_outside_D57", "tool_intersections_mm3", "axial_nesting_sweep")}, indent=2))
