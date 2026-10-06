"""Independent V6 O-interface and axial cover insertion check in FreeCAD.

Read-only with respect to design code. Writes this review's JSON only. Threads
are probed at their minor core, not modelled as helical engagement geometry.
"""
from pathlib import Path
import hashlib
import json
import math
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
import build_printable_robot as cad
import cad_v6_leg as leg

OUT = ROOT / "mechanical/v6"
SOURCE = ROOT / "tools/cad_v6_leg.py"
BEFORE = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
cad.configure(OUT)
cad.P.update(leg.configure())
S = leg.S()
V = cad.V
parts = leg.designs()
hw = leg.hardware()
inner = parts["OB_inner_carrier"][0]
outer = parts["OB_outer_shell"][0]
oa = parts["OA_one_piece"][0]
motor_path = ROOT.parent / "references/DM-J4310-2EC/3D模型/DM-J4310-2EC-V1.1_3d_20260228_1.stp"
motor = cad.motor_shape(motor_path, cad.P["knee_motor_translation_y"])


def overlap(a, b):
    aa, bb = a.BoundBox, b.BoundBox
    if any(getattr(aa, k + "Max") <= getattr(bb, k + "Min") + 1e-8 or
           getattr(bb, k + "Max") <= getattr(aa, k + "Min") + 1e-8
           for k in "XYZ"):
        return 0.0
    return float(a.common(b).Volume)


def shifted(shape, distance):
    out = shape.copy()
    out.translate(V(0, distance, 0))
    return out


def scalar_length(value):
    return float(value.Value if hasattr(value, "Value") else value)


report = {
    "status": "independent geometric review; no load or manufacturing release",
    "source_sha256": BEFORE,
    "motor_source": str(motor_path),
    "motor_source_sha256": hashlib.sha256(motor_path.read_bytes()).hexdigest(),
    "motor_solids": len(motor.Solids),
    "reference_stator_plane_mm": S,
    "assembly_pose_mm": 180.0,
    "collision_threshold_mm3": 0.001,
    "O_interface_dimensions_mm": {
        "motor_stator_diameter": 57.0,
        "motor_rotor_diameter": 35.0,
        "rotor_projection_from_stator": 1.0,
        "inner_thickness": 4.0,
        "inner_entry_diameter": 40.4,
        "stator_holes_pcd": 50.0,
        "stator_clearance": 3.4,
        "stator_counterbore": 4.8,
        "stator_counterbore_floor_offset": 2.0,
        "stator_counterbore_outer_edge_web": 28.5 - 25 - 2.4,
        "stator_counterbore_inner_edge_web": 25 - 2.4 - 20.2,
        "SLH_M3x6_nominal_grip": 2.0,
        "SLH_M3x6_nominal_engagement": 4.0,
        "stator_thread_depth": 5.0,
        "stator_nominal_bottom_margin": 1.0,
        "SLH_M3_head_bearing_area_mm2": math.pi / 4 * (4.5**2 - 3.4**2),
        "OA_bridge_diameter": 37.0,
        "OA_nose_diameter": 35.0,
        "outer_nose_bore_diameter": 35.4,
        "nose_nominal_radial_clearance": 0.2,
        "nose_nominal_axial_clearance": 0.4,
    },
    "local_unrotated_intersections_mm3": {},
    "stator_AF2_tools_before_OA": [],
    "rotor_AF2_5_tools_before_outer_shell": [],
    "motor_thread_core_probes": [],
    "shell_insertion_samples": [],
    "shell_insertion_collisions": [],
    "angular_limit_checks": [],
    "shape_checks": {},
    "notes": [
        "O motor hole phase and pilot are checked in their aligned local datum; motor rotor visual is not a native independently rotating STEP subassembly. qk=0 is outside this leg's allowed assembled range.",
        "Stator AF2 access precedes OA installation. Rotor AF2.5 access follows inner-carrier installation and precedes outer-shell installation.",
        "Tools stop at the nominal screw top plane; screw socket recesses are not included in the smooth hardware geometry.",
        "D2.4 core probes verify nominal 4 mm engagement against the original STEP hole void, not thread flank strength or effective tap depth.",
        "Cover insertion is prescribed at the 180 mm nominal assembly pose. Other poses are rejection/probing cases, not additional authorized assembly states.",
        "Cover insertion excludes four final shell-fastening screws, the B outer end washer/screw, and removable angular-stop hardware installed afterward. The B outer bronze sleeve travels with the outer shell.",
        "M3 head bearing pressure, motor thread strength, fit/finish, continuous motion, and jumping impacts remain separate checks.",
    ],
}
for name, (shape, _, _) in parts.items():
    report["shape_checks"][name] = dict(valid=shape.isValid(), solids=len(shape.Solids),
                                       volume_mm3=shape.Volume)
for name, shape in (("inner_vs_motor", inner), ("OA_vs_motor", oa), ("outer_vs_motor", outer)):
    report["local_unrotated_intersections_mm3"][name] = overlap(shape, motor)
report["outside_range_qk_zero_diagnostic"] = {
    "inner_vs_OA_mm3": overlap(inner, oa),
    "admissible_assembly_pose": False,
    "note": "The full arm at zero relative angle is outside the side-window angular range; assemble at 180 mm using the mapped motor angle.",
}

for i, (x, z) in enumerate(cad.points(25, 6, 30)):
    tool = cad.hex_pocket(x, z, S + 4.0, 45, 2.0)
    values = {"index": i, "x_mm": x, "z_mm": z,
              "inner_mm3": overlap(tool, inner), "motor_mm3": overlap(tool, motor)}
    report["stator_AF2_tools_before_OA"].append(values)
    core = cad.cyl(1.2, S - 4, 4, x, z)
    report["motor_thread_core_probes"].append({"interface": "stator", "index": i,
                                                 "overlap_mm3": overlap(core, motor)})

for i, (x, z) in enumerate(cad.points(13.5, 6, 0)):
    tool = cad.hex_pocket(x, z, S + 16.0, 45, 2.5)
    state = cad.pose(180.)
    nominal_tool = cad.transform(tool, "oa", state)
    values = {"index": i, "x_mm": x, "z_mm": z,
              "OA_mm3": overlap(nominal_tool, cad.transform(oa, "oa", state)),
              "inner_mm3": overlap(nominal_tool, cad.transform(inner, "hip", state)),
              "motor_mm3": overlap(tool, motor)}
    report["rotor_AF2_5_tools_before_outer_shell"].append(values)
    core = cad.cyl(1.2, S - 3, 4, x, z)
    report["motor_thread_core_probes"].append({"interface": "rotor", "index": i,
                                                 "overlap_mm3": overlap(core, motor)})

for length in (100., 180., 215.):
    st = cad.pose(length)
    static = [(name, cad.transform(shape, role, st))
              for name, (shape, role, _) in parts.items() if name != "OB_outer_shell"]
    static.append(("J4310_knee", cad.transform(motor, "hip", st)))
    cover_members = [("OB_outer_shell", cad.transform(outer, "hip", st))]
    for name, shape, role in hw:
        if name.startswith("OB_shell_") or name in ("axis_washer_B_outer", "axis_B_SETS_M2x4_outer"):
            continue
        if "stop" in name.lower() or "limit" in name.lower():
            continue
        if name == "bronze_sleeve_B_outer":
            cover_members.append((name, cad.transform(shape, role, st)))
        else:
            static.append((name, cad.transform(shape, role, st)))
    for distance in (0., .1, .5, 1., 2., 4., 8., 16., 24.):
        collisions = []
        for cover_name, cover_shape in cover_members:
            moved = shifted(cover_shape, distance)
            for fixed_name, fixed_shape in static:
                volume = overlap(moved, fixed_shape)
                if volume > .001:
                    collisions.append(dict(moving=cover_name, fixed=fixed_name, mm3=volume))
        report["shell_insertion_samples"].append(dict(leg_length_mm=length,
            axial_offset_mm=distance, collisions=len(collisions)))
        report["shell_insertion_collisions"].extend(dict(leg_length_mm=length,
            axial_offset_mm=distance, **entry) for entry in collisions)
    print(f"O_REVIEW_INSERTION {length} mm complete", flush=True)

pin = next(shape for name, shape, _ in hw if name == "OA_angular_stop_shoulder_M3")
delta = math.degrees(2 * math.asin((2.3 - 2.0) / (2 * 23.0)))
q_min, q_max = cad.P["oa_stop_track_motor_relative_degrees"]
report["angular_limit_nominal"] = {
    "slot_centerline_qk_range_degrees": [q_min, q_max],
    "cap_clearance_angle_degrees": delta,
    "calculated_first_contact_qk_degrees": [q_min - delta, q_max + delta],
    "target_AC_to_shell_clearance_at_stop_mm": 0.4,
    "scope": "Ideal circle centers, zero elastic deflection; no impact rating",
}
for qk in (q_min - 1.5, q_min - delta, q_min, q_max, q_max + delta, q_max + 1., q_max + 1.5):
    pin_rotated = cad.moved(pin, angle=qk)
    phi = math.radians(qk + 180.)
    length = math.sqrt(130.**2 + 105.**2 + 2 * 130. * 105. * math.cos(phi))
    state = cad.pose(length)
    current = [(name, cad.transform(shape, role, state)) for name, (shape, role, _) in parts.items()]
    collisions = []
    for i, (a, sa) in enumerate(current):
        for b, sb in current[i + 1:]:
            volume = overlap(sa, sb)
            if volume > .001:
                collisions.append(dict(a=a, b=b, mm3=volume))
    report["angular_limit_checks"].append({
        "qk_degrees": qk,
        "leg_length_mm": length,
        "pin_vs_shell_mm3": overlap(pin_rotated, outer),
        "pin_to_shell_distance_mm": pin_rotated.distToShape(outer)[0],
        "past_ideal_stop": qk < q_min-delta-1e-8 or qk > q_max+delta+1e-8,
        "other_body_collisions": collisions,
        "outer_to_AC_distance_mm": dict(current)["OB_outer_shell"].distToShape(dict(current)["AC_bearing_link"])[0],
        "outer_to_CW_distance_mm": dict(current)["OB_outer_shell"].distToShape(dict(current)["CW_one_piece"])[0],
    })

report["nominal_180_assembly_pass"] = not any(row["leg_length_mm"] == 180.
    for row in report["shell_insertion_collisions"])
report["angular_stops_precede_body_collisions_pass"] = not any(
    row["other_body_collisions"] for row in report["angular_limit_checks"] if not row["past_ideal_stop"])
contact_rows = [row for row in report["angular_limit_checks"]
    if abs(row["qk_degrees"] - (q_min-delta)) < 1e-6 or abs(row["qk_degrees"] - (q_max+delta)) < 1e-6]
report["angular_endpoint_AC_clearance_pass"] = all(row["outer_to_AC_distance_mm"] >= .4 for row in contact_rows)
report["angular_slot_matches_specification_pass"] = all(
    row["pin_to_shell_distance_mm"] < .001 and row["pin_vs_shell_mm3"] < .001 for row in contact_rows)

report["source_unchanged_during_review"] = hashlib.sha256(SOURCE.read_bytes()).hexdigest() == BEFORE
assert report["source_unchanged_during_review"], "Geometry changed during independent review; rerun."
(OUT / "O_interface_independent_review.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps({key: report[key] for key in ("source_sha256", "local_unrotated_intersections_mm3", "shell_insertion_collisions")}, indent=2))
