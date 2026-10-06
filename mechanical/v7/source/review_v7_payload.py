"""Independent V7 payload interface review using installed FreeCAD.

This script only writes its own V7 report. It does not rebuild the robot or
export manufacturing parts. Contact checks are made from BRep faces/solids,
not inferred from visual similarity or shared drawing labels.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
import build_printable_robot as cad
import cad_v7_chassis as chassis
import cad_v7_payload as payload
import cad_v7_display as display
import cad_v7_imu as imu

V, Part = cad.V, cad.Part
OUT = ROOT / "mechanical/v7"
cad.configure(OUT)
MODULES = ("cad_v7_payload.py", "cad_v7_display.py", "cad_v7_chassis.py", "cad_v7_imu.py")


def hashes():
    return {name: hashlib.sha256((ROOT / "tools" / name).read_bytes()).hexdigest()
            for name in MODULES}


def v6_stat():
    return {str(p.relative_to(ROOT)): [p.stat().st_size, p.stat().st_mtime_ns]
            for p in (ROOT / "mechanical/v6").rglob("*") if p.is_file()}


def intersection(a, b):
    if not a.BoundBox.intersect(b.BoundBox):
        return 0.0
    return sum(sa.common(sb).Volume for sa in a.Solids for sb in b.Solids
               if sa.BoundBox.intersect(sb.BoundBox))


def distance(a, b):
    """Exact pair distance with bbox pruning for large vendor compounds."""
    best = float("inf")
    for sa in a.Solids:
        aa = sa.BoundBox
        for sb in b.Solids:
            bb = sb.BoundBox
            lower = sum(max(0, getattr(aa, axis + "Min")-getattr(bb, axis + "Max"),
                            getattr(bb, axis + "Min")-getattr(aa, axis + "Max"))**2
                        for axis in ("X", "Y", "Z"))**.5
            if lower <= best:
                best = min(best, sa.distToShape(sb)[0])
    return best


def planar_contact(a, b, axis, datum):
    def faces(s):
        return [f for f in s.Faces
                if getattr(f.BoundBox, axis + "Length") < 1e-6
                and abs(getattr(f.BoundBox, axis + "Min") - datum) < 1e-6]
    return sum(fa.common(fb).Area for fa in faces(a) for fb in faces(b))


def cyl(radius, point, height, direction=(0, 0, 1)):
    return Part.makeCylinder(radius, height, V(*point), V(*direction))


def main():
    before, old_files = hashes(), v6_stat()
    fixed = chassis.build_chassis()
    addons = payload.designs()
    fixed.update(addons)
    devices = {name: shape for name, shape, _, _ in payload.payloads()}
    hardware = {name: shape for name, shape, _ in payload.hardware()}
    bridge, imu_body = addons["HI13R2_rigid_bridge"], devices["HI13R2_official"]
    jetson = devices["Jetson_Orin_Nano_official"]
    front, rear = fixed["chassis_front_shell"], fixed["chassis_rear_cover"]
    bezel = fixed["display_front_bezel"]
    report = {"units": "mm", "sources_before": before, "checks": [], "failures": [],
              "limits": ["No strength, thermal, fatigue, jump or cable-routing qualification.",
                         "Display is a supplied-dimension envelope; mounting-tab datum, thickness, array offset and actual plugs are unknown.",
                         "Camera STEP collision proxy and ROS visualization differ in age; both documented camera depth configurations checked.",
                         "V6 geometry is read as an inherited subsystem and is not rewritten by this review."]}

    def record(name, data, passed):
        row = {"name": name, "pass": bool(passed), **data}
        report["checks"].append(row)
        if not passed:
            report["failures"].append(name)
        print(name, "PASS" if passed else "FAIL", flush=True)

    # Official housing and rigid metal support, including true seat contact.
    imudata = imu.validate()
    origin = imu.sensor_origin()
    contacts = {"IMU_to_bridge_z79_mm2": planar_contact(imu_body, bridge, "Z", 79),
                "IMU_bridge_collision_mm3": intersection(imu_body, bridge),
                "bridge_Jetson_collision_mm3": intersection(bridge, jetson),
                "bridge_Jetson_min_distance_mm": distance(bridge, jetson),
                "IMU_Jetson_min_distance_mm": distance(imu_body, jetson)}
    record("official_IMU_origin_and_support", {"datum_world": list(origin), **contacts},
           imudata["pass"] and abs(origin.x)+abs(origin.y)<1e-7 and contacts["IMU_to_bridge_z79_mm2"]>100
           and contacts["IMU_bridge_collision_mm3"]<1e-6 and contacts["bridge_Jetson_collision_mm3"]<1e-6
           and contacts["bridge_Jetson_min_distance_mm"]>3)

    rows, failures = [], []
    for i, p in enumerate(imu.mount_holes()):
        screw, nut = hardware[f"HI13R2_M2p5x16_{i}"], hardware[f"HI13R2_M2p5_nut_{i}"]
        row = {"index": i, "hole_XY": [p.x,p.y],
               "head_IMU_contact_mm2": planar_contact(screw, imu_body, "Z", 89.4),
               "nut_bridge_contact_mm2": planar_contact(nut, bridge, "Z", 76),
               "shaft_in_IMU_mm3": intersection(screw, imu_body),
               "shaft_in_bridge_mm3": intersection(screw, bridge),
               "nut_in_IMU_or_bridge_mm3": intersection(nut, imu_body)+intersection(nut, bridge),
               "nut_Jetson_gap_mm": distance(nut,jetson)}
        rows.append(row)
        if row["head_IMU_contact_mm2"]<3 or row["nut_bridge_contact_mm2"]<3 or any(row[k]>1e-6 for k in ("shaft_in_IMU_mm3","shaft_in_bridge_mm3","nut_in_IMU_or_bridge_mm3")):
            failures.append(i)
    record("IMU_two_actual_hole_fastener_chains", {"chains":rows}, not failures)

    rows=[]
    for i,(x,y) in enumerate(( (x,y) for x in (-10,10) for y in (-68,68) )):
        side=fixed["chassis_hip_frame_right" if y>0 else "chassis_hip_frame_left"]
        screw=hardware[f"IMU_bridge_M3x8_{i}"]
        pilot=cyl(1.24,(x,y,41.1),5.8)
        clearance=cyl(1.65,(x,y,47.1),2.8)
        annulus=cyl(2.5,(x,y,44),1).cut(cyl(1.6,(x,y,43.9),1.2))
        row={"XY":[x,y],"pilot_probe_collision_mm3":intersection(pilot,side),
             "foot_clearance_probe_collision_mm3":intersection(clearance,bridge),
             "thread_surround_material_mm3":intersection(annulus,side),
             "head_seat_area_mm2":planar_contact(screw,bridge,"Z",50),
             "foot_sideframe_contact_mm2":planar_contact(bridge,side,"Z",47),
             "grip_collisions_mm3":intersection(screw,bridge)+intersection(screw,side)}
        rows.append(row)
    record("bridge_four_sideframe_mounts", {"chains":rows}, all(
        r["pilot_probe_collision_mm3"]<1e-6 and r["foot_clearance_probe_collision_mm3"]<1e-6
        and r["thread_surround_material_mm3"]>5 and r["head_seat_area_mm2"]>10
        and r["foot_sideframe_contact_mm2"]>50 and r["grip_collisions_mm3"]<1e-6 for r in rows))

    imu_items={"IMU":imu_body,"bridge":bridge,"USB_design_allowance":imu.cable_clearance()}
    rows=[]
    for label,s in imu_items.items():
        for sn,shell in (("front",front),("rear",rear)):
            rows.append({"item":label,"shell":sn,"collision_mm3":intersection(s,shell),"distance_mm":distance(s,shell)})
    record("IMU_and_USB_allowance_inside_shell", {"pairs":rows}, all(r["collision_mm3"]<1e-6 and r["distance_mm"]>.2 for r in rows))

    screen=devices["Display_7in_user_envelope"]
    carrier_names=("display_carrier_left","display_carrier_right")
    screen_pairs=[]
    for name in ("chassis_front_shell","display_front_bezel","chassis_front_crossframe",*carrier_names):
        s=fixed[name]
        screen_pairs.append({"part":name,"collision_mm3":intersection(screen,s),"distance_mm":distance(screen,s)})
    record("screen_nominal_envelope_and_carriers", {"pairs":screen_pairs,
        "known_outer_dimensions_mm":[165,110,20],"active_area_mm":[155,87],"panel_window_mm":[157,89],
        "nominal_glass_recess_mm":122-119,"hole_array_is_centred_assumption":True,
        "lug_plane_X99_is_unverified_assumption":True}, all(r["collision_mm3"]<1e-6 for r in screen_pairs))

    rows=[]
    for i,(y,z) in enumerate(display.FRAME_HOLES):
        carrier=addons["display_carrier_right" if y>0 else "display_carrier_left"]
        screw,nut=hardware[f"display_frame_M3x16_{i}"],hardware[f"display_frame_M3_nut_{i}"]
        row={"YZ":[y,z],"carrier_shell_seat_X116_mm2":planar_contact(carrier,front,"X",116),
             "head_bezel_X122_mm2":planar_contact(screw,bezel,"X",122),
             "bezel_shell_seat_X119_mm2":planar_contact(bezel,front,"X",119),
             "nut_carrier_X110_mm2":planar_contact(nut,carrier,"X",110),
             "screw_structural_overlap_mm3":intersection(screw,carrier)+intersection(screw,front)+intersection(screw,bezel),
             "nut_structural_overlap_mm3":intersection(nut,carrier)+intersection(nut,front)}
        rows.append(row)
    record("screen_six_front_panel_fastener_chains", {"chains":rows}, all(
        r["carrier_shell_seat_X116_mm2"]>10 and r["head_bezel_X122_mm2"]>10 and r["bezel_shell_seat_X119_mm2"]>50 and r["nut_carrier_X110_mm2"]>5
        and r["screw_structural_overlap_mm3"]<1e-6 and r["nut_structural_overlap_mm3"]<1e-6 for r in rows))

    rows=[]
    for dx in (0,1,3,10,20,40,80,120):
        test=screen.copy();test.translate(V(dx,0,0))
        row={"screen_translation_X_mm":dx,"front_shell_collision_mm3":intersection(test,front),
             "left_carrier_collision_mm3":intersection(test,addons["display_carrier_left"]),
             "right_carrier_collision_mm3":intersection(test,addons["display_carrier_right"])}
        rows.append(row)
    sweep=cad.box(99,-82.5,-47,140,165,110)
    swept_overlap=intersection(sweep,front)
    record("screen_front_insertion_with_bezel_removed", {"samples":rows,
        "conservative_full_envelope_sweep_shell_overlap_mm3":swept_overlap,
        "sequence":"Remove bezel; pass165x110 display through166x111 main aperture; retain actual tabs then attach bezel.",
        "limit":"Clearance envelope only; actual projecting lugs and connectors remain unverified."},
        swept_overlap<1e-6 and all(all(v<1e-6 for k,v in r.items() if k.endswith("collision_mm3")) for r in rows))

    rows=[]
    for i,(y,z) in enumerate(display.HOLES):
        carrier=addons["display_carrier_right" if y>0 else "display_carrier_left"]
        washer=hardware[f"display_adjustable_washer_{i}"]
        spacer=hardware[f"display_spacer_D8_d3_t2_{i}"]
        for dy in (-2,0,2):
            for dz in (-2,0,2):
                w=washer.copy();w.translate(V(0,dy,dz))
                sp=spacer.copy();sp.translate(V(0,dy,dz))
                shaft=cyl(1.25,(93.1,y+dy,z+dz),3.8,(1,0,0))
                rows.append({"hole_index":i,"adjustment_YZ_mm":[dy,dz],
                    "washer_carrier_seat_mm2":planar_contact(w,carrier,"X",94),
                    "spacer_carrier_seat_mm2":planar_contact(sp,carrier,"X",97),
                    "washer_shell_collision_mm3":intersection(w,front),
                    "spacer_shell_collision_mm3":intersection(sp,front),
                    "shaft_carrier_collision_mm3":intersection(shaft,carrier),
                    "washer_carrier_collision_mm3":intersection(w,carrier),
                    "spacer_carrier_collision_mm3":intersection(sp,carrier)})
    record("screen_four_mount_adjustment_36_samples", {"samples":rows,
        "limit":"Only hardware/carrier adjustment validated. Actual display tab datum remains unknown; do not treat the drilled envelope as manufacturer material."}, all(
        r["washer_carrier_seat_mm2"]>10 and r["spacer_carrier_seat_mm2"]>2 and all(r[k]<1e-6 for k in
        ("washer_shell_collision_mm3","spacer_shell_collision_mm3","shaft_carrier_collision_mm3","washer_carrier_collision_mm3","spacer_carrier_collision_mm3")) for r in rows))

    cam=devices["D435_clearance_envelope"]; bracket=addons["D435_embedded_bracket"]
    rows=[]
    for i,y in enumerate((-22.5,22.5)):
        screw,shim=hardware[f"D435_rear_M3x6_{i}"],hardware[f"D435_depth_shim_1mm_{i}"]
        rows.append({"Y":y,"shim_camera_X96p95_mm2":planar_contact(shim,cam,"X",96.95),
            "shim_bracket_X95p95_mm2":planar_contact(shim,bracket,"X",95.95),
            "head_bracket_X92p95_mm2":planar_contact(screw,bracket,"X",92.95),
            "screw_proxy_bracket_collision_mm3":intersection(screw,cam)+intersection(screw,bracket),
            "nominal_insertion_mm":2.,"manufacturer_max_insertion_mm":3.})
    record("translated_camera_two_rear_mount_chains", {"chains":rows,
        "camera_front_X_mm":cam.BoundBox.XMax,"camera_center_Z_mm":cam.BoundBox.Center.z,
        "proxy_front_shell_overlap_mm3":intersection(cam,front),"bracket_front_shell_overlap_mm3":intersection(bracket,front)},
        abs(cam.BoundBox.XMax-122)<1e-6 and abs(cam.BoundBox.Center.z-88)<1e-6 and intersection(cam,front)<1e-6
        and intersection(bracket,front)<1e-6 and all(r["shim_camera_X96p95_mm2"]>10 and r["shim_bracket_X95p95_mm2"]>10
        and r["head_bracket_X92p95_mm2"]>10 and r["screw_proxy_bracket_collision_mm3"]<1e-6 for r in rows))

    current_camera=cad.box(95.95,-45.075,75.425,26.05,90.15,25.15)
    current_camera=cad.cut(current_camera,*(cyl(1.6,(95.85,y,88),3.2,(1,0,0)) for y in (-22.5,22.5)))
    rows=[]
    for y in (-22.5,22.5):
        screw=cad.union(cyl(1.5,(92.95,y,88),5,(1,0,0)),cyl(2.75,(89.95,y,88),3,(1,0,0)))
        rows.append({"Y":y,"nominal_insertion_mm":97.95-95.95,
            "bracket_camera_contact_X95p95_mm2":planar_contact(bracket,current_camera,"X",95.95),
            "screw_camera_collision_mm3":intersection(screw,current_camera),
            "screw_bracket_collision_mm3":intersection(screw,bracket)})
    record("alternate_26p05_camera_depth_without_shims", {"chains":rows,
        "camera_shell_overlap_mm3":intersection(current_camera,front),
        "configuration":"Current drawing26.05mm rear depth; remove1mm shim and selectM3x5. Actual received camera must be measured."},
        intersection(current_camera,front)<1e-6 and all(r["bracket_camera_contact_X95p95_mm2"]>10
        and r["screw_camera_collision_mm3"]<1e-6 and r["screw_bracket_collision_mm3"]<1e-6 for r in rows))

    rows=[]
    for i,(y,z) in enumerate(chassis.CAMERA_PADS):
        screw,nut=hardware[f"D435_frame_M3x10_{i}"],hardware[f"D435_frame_M3_nut_{i}"]
        rows.append({"YZ":[y,z],"head_shell_X122_mm2":planar_contact(screw,front,"X",122),
            "bracket_shell_X119_mm2":planar_contact(bracket,front,"X",119),
            "nut_bracket_X115_mm2":planar_contact(nut,bracket,"X",115),
            "overlap_mm3":intersection(screw,front)+intersection(screw,bracket)+intersection(nut,front)+intersection(nut,bracket)})
    record("translated_camera_four_panel_chains", {"chains":rows},all(
        r["head_shell_X122_mm2"]>10 and r["bracket_shell_X119_mm2"]>40 and r["nut_bracket_X115_mm2"]>5 and r["overlap_mm3"]<1e-6 for r in rows))

    notes=(OUT/"DISPLAY.md").read_text()
    data=json.loads((OUT/"display_interface.json").read_text())
    record("unknown_display_datums_not_claimed_as_certified", {
        "centred_array_marked_assumed":data.get("centred_array_is_assumption"),
        "screw_length_not_fixed":"not modelled" in data.get("screen_fasteners", ""),
        "lug_plane_and_spacer_limit_documented":any("lug datum" in item for item in data.get("limits",[])),
        "machining_precision_not_inferred":any("not a machining tolerance" in item for item in data.get("limits",[])),
        "unknowns":["array offset relative to bezel","mounting-tab face and thickness","supplier model/tolerance","actual rear plug geometry"]},
        data.get("centred_array_is_assumption") is True and "not modelled" in data.get("screen_fasteners","")
        and any("lug datum" in item for item in data.get("limits",[])))

    report["sources_after"]=hashes()
    report["source_unchanged"]=report["sources_after"]==before
    report["v6_files_unchanged"]=old_files==v6_stat()
    if not report["source_unchanged"]:report["failures"].append("source_changed_during_review")
    if not report["v6_files_unchanged"]:report["failures"].append("v6_mutated_during_review")
    report["pass"]=not report["failures"]
    (OUT/"payload_independent_review.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({"pass":report["pass"],"failures":report["failures"],"sources":before},indent=2),flush=True)


if __name__=="__main__":main()
