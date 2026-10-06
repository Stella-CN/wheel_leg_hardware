"""Independent V8 payload interface review using installed FreeCAD.

This script only writes its own V8 report. It does not rebuild the robot or
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
import cad_v8_chassis as chassis
import cad_v8_payload as payload
import cad_v8_display as display
import cad_v7_imu as imu

V, Part = cad.V, cad.Part
OUT = ROOT / "mechanical/v8"
cad.configure(OUT)
MODULES = ("cad_v8_payload.py", "cad_v8_display.py", "cad_v8_chassis.py", "cad_v7_imu.py", "cad_v7_payload.py", "cad_v6_payload.py")


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
                         "Display is the supplier5-inch outside envelope; active area, mass, front rim contact and actual plugs are unknown.",
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

    screen=devices['Display_GK_HD_5in_supplier_envelope']
    carrier_names=('display_case_cradle_left','display_case_cradle_right')
    pairs=[]
    for name,s in fixed.items():
        pairs.append(dict(part=name,collision_mm3=intersection(screen,s)))
    contact=planar_contact(screen,bezel,'X',114)
    record('five_inch_envelope_and_external_case_support',dict(pairs=pairs,
        supplied_width_height_depth_mm=[122,78,14.5],device_mount_holes='Not specified; none invented',
        screen_front_corner_stop_contact_mm2=contact,
        front_rim_contact_is_provisional=True,
        bottom_support_mm2=sum(planar_contact(screen,addons[n],'Z',-43) for n in carrier_names),
        top_clearance_mm=.5),contact>6 and all(r['collision_mm3']<1e-6 for r in pairs))

    rows=[]
    for i,(y,z) in enumerate(display.FRAME_HOLES):
        carrier=addons['display_case_cradle_right' if y>0 else 'display_case_cradle_left']
        screw,nut=hardware[f'display_case_M3x22_{i}'],hardware[f'display_case_M3_nut_{i}']
        row=dict(YZ=[y,z],head_panel_X117_mm2=planar_contact(screw,bezel,'X',117),
            cradle_panel_X114_mm2=planar_contact(carrier,bezel,'X',114),
            nut_cradle_X99_mm2=planar_contact(nut,carrier,'X',99),
            panel_to_shell_X114_mm2=planar_contact(bezel,front,'X',114),
            screw_overlap_mm3=sum(intersection(screw,s) for s in fixed.values()),
            nut_overlap_mm3=sum(intersection(nut,s) for s in fixed.values()),
            screw_rear_X_mm=screw.BoundBox.XMin)
        rows.append(row)
    record('screen_four_complete_fastener_chains',dict(chains=rows),all(
        r['head_panel_X117_mm2']>10 and r['cradle_panel_X114_mm2']>40 and r['nut_cradle_X99_mm2']>5
        and r['panel_to_shell_X114_mm2']>50 and r['screw_overlap_mm3']<1e-6 and r['nut_overlap_mm3']<1e-6 for r in rows))

    shell_hw={name:s for name,s,_ in chassis.chassis_hardware()}
    rows=[]
    for n,s in list(hardware.items())+list(shell_hw.items()):
        for cn in carrier_names:
            volume=intersection(s,addons[cn])
            if volume>1e-6:rows.append(dict(hardware=n,cradle=cn,overlap_mm3=volume))
    record('all_shell_and_payload_hardware_clear_of_cradles',dict(collisions=rows),not rows)

    rows=[]
    for i,(y,z) in enumerate(chassis.FACE_FASTENERS):
        screw,nut=shell_hw[f'front_face_M3x12_{i}'],shell_hw[f'front_face_M3_nut_{i}']
        rows.append(dict(YZ=[y,z],head_panel_X117_mm2=planar_contact(screw,bezel,'X',117),
            nut_shell_X109p6_mm2=planar_contact(nut,front,'X',109.6),
            panel_shell_X114_mm2=planar_contact(bezel,front,'X',114),
            screw_overlap_mm3=sum(intersection(screw,s) for s in fixed.values()),
            nut_overlap_mm3=sum(intersection(nut,s) for s in fixed.values())))
    record('whole_front_face_four_fastener_chains',dict(chains=rows),all(
        r['head_panel_X117_mm2']>10 and r['nut_shell_X109p6_mm2']>5 and r['panel_shell_X114_mm2']>50
        and r['screw_overlap_mm3']<1e-6 and r['nut_overlap_mm3']<1e-6 for r in rows))

    cam=devices['D435_clearance_envelope'];bracket=addons['D435_embedded_bracket']
    rows=[]
    for i,y in enumerate((-22.5,22.5)):
        screw,shim=hardware[f'D435_rear_M3x6_{i}'],hardware[f'D435_depth_shim_1mm_{i}']
        rows.append(dict(Y=y,shim_camera_X91p95_mm2=planar_contact(shim,cam,'X',91.95),
            shim_bracket_X90p95_mm2=planar_contact(shim,bracket,'X',90.95),
            head_bracket_X87p95_mm2=planar_contact(screw,bracket,'X',87.95),
            overlap_mm3=intersection(screw,cam)+intersection(screw,bracket),
            insertion_mm=2.,manufacturer_max_insertion_mm=3.))
    record('camera_two_rear_mount_chains',dict(chains=rows,
        camera_front_X_mm=cam.BoundBox.XMax,camera_center_Z_mm=cam.BoundBox.Center.z,
        camera_body_overlap_mm3=sum(intersection(cam,s) for s in fixed.values())),
        abs(cam.BoundBox.XMax-117)<1e-6 and abs(cam.BoundBox.Center.z-61)<1e-6
        and all(r['shim_camera_X91p95_mm2']>10 and r['shim_bracket_X90p95_mm2']>10
                and r['head_bracket_X87p95_mm2']>10 and r['overlap_mm3']<1e-6 for r in rows)
        and sum(intersection(cam,s) for s in fixed.values())<1e-6)

    current_camera=cad.box(90.95,-45.075,48.425,26.05,90.15,25.15)
    current_camera=cad.cut(current_camera,*(cyl(1.6,(90.85,y,61),3.2,(1,0,0)) for y in (-22.5,22.5)))
    rows=[]
    for y in (-22.5,22.5):
        screw=cad.union(cyl(1.5,(87.95,y,61),5,(1,0,0)),cyl(2.75,(84.95,y,61),3,(1,0,0)))
        rows.append(dict(Y=y,insertion_mm=2.,contact_mm2=planar_contact(bracket,current_camera,'X',90.95),
            screw_camera_overlap_mm3=intersection(screw,current_camera),screw_bracket_overlap_mm3=intersection(screw,bracket)))
    overlap=sum(intersection(current_camera,s) for s in fixed.values())
    record('alternate_camera_26p05_depth_without_shim',dict(chains=rows,body_overlap_mm3=overlap,
        configuration='26.05 mm camera: remove1mm shims and useM3x5; measure actual camera.'),overlap<1e-6 and all(
        r['contact_mm2']>10 and r['screw_camera_overlap_mm3']<1e-6 and r['screw_bracket_overlap_mm3']<1e-6 for r in rows))

    rows=[]
    for i,(y,z) in enumerate(chassis.CAMERA_PADS):
        screw,nut=hardware[f'D435_frame_M3x10_{i}'],hardware[f'D435_frame_M3_nut_{i}']
        rows.append(dict(YZ=[y,z],head_panel_X117_mm2=planar_contact(screw,bezel,'X',117),
            bracket_panel_X114_mm2=planar_contact(bracket,bezel,'X',114),
            nut_bracket_X110_mm2=planar_contact(nut,bracket,'X',110),
            overlap_mm3=sum(intersection(screw,s)+intersection(nut,s) for s in fixed.values())))
    record('camera_four_front_panel_fastener_chains',dict(chains=rows),all(
        r['head_panel_X117_mm2']>10 and r['bracket_panel_X114_mm2']>40 and r['nut_bracket_X110_mm2']>5
        and r['overlap_mm3']<1e-6 for r in rows))

    # Clearance allocated for candidate low-profile right-angle plugs, not a
    # measurement of any purchased connector or cable.
    keepout=cad.box(86.5,-50,-24,13.,100.,40.)
    plug_pairs=[]
    for name,shape in {**fixed,**hardware,**shell_hw,
                       **{n:s for n,s in devices.items() if n!='Display_GK_HD_5in_supplier_envelope'}}.items():
        volume=intersection(keepout,shape)
        if volume>1e-6:plug_pairs.append(dict(part=name,overlap_mm3=volume))
    record('rear_screen_design_allowance_not_vendor_plug',dict(
        design_allowance_xyz=[86.5,-50,-24,99.5,50,16],depth_mm=13.,collisions=plug_pairs,
        limitation='Only allocated empty volume. Connector coordinates, plug orientation and cable bending must be measured; no plug-fit claim.'),not plug_pairs)

    moving={n:addons[n] for n in carrier_names}
    moving.update({'front_panel':bezel,'screen':screen,'camera':cam,'camera_bracket':bracket})
    moving.update({n:s for n,s in hardware.items() if n.startswith(('display_case_','D435_'))})
    stationary={n:s for n,s in fixed.items() if n not in (*carrier_names,'display_front_bezel','D435_embedded_bracket')}
    stationary.update({n:s for n,s in devices.items() if n not in ('Display_GK_HD_5in_supplier_envelope','D435_clearance_envelope')})
    stationary.update({n:s for n,s in shell_hw.items() if not n.startswith('front_face_M3x12_')})
    samples=[]
    for dx in (0,1,3,10,30,70):
        hits=[]
        for an,a in moving.items():
            a=a.copy();a.translate(V(dx,0,0))
            for bn,b in stationary.items():
                volume=intersection(a,b)
                if volume>1e-5:hits.append(dict(moving=an,stationary=bn,overlap_mm3=volume))
        samples.append(dict(front_module_translation_X_mm=dx,collisions=hits))
    record('complete_front_module_removal_six_poses',dict(samples=samples,
        sequence='Disconnect cables; remove four front face fixing screws; lift complete screen+camera+panel module forward(+X).',
        limits='Six sampled poses only; unknown plugs/cables and tool/finger envelopes excluded.'),all(not r['collisions'] for r in samples))

    data=json.loads((OUT/'display_interface.json').read_text())
    record('manufacturer_data_and_unknowns_separated',dict(
        dimension_page_pdf=data['dimension_page_pdf'],selected_inches=data['selected_variant_inches'],
        mass_is_assumed=data['mass_is_assumed'],device_holes=data['manufacturer_device_mounting_holes'],
        active_area=data['active_display_area'],unresolved=data['unresolved']),
        data['selected_variant_inches']==5 and data['mass_is_assumed'] is True
        and data['manufacturer_device_mounting_holes'] is None and data['active_display_area'] is None)

    report['sources_after']=hashes()
    report['source_unchanged']=report['sources_after']==before
    report['v6_files_unchanged']=old_files==v6_stat()
    if not report['source_unchanged']:report['failures'].append('source_changed_during_review')
    if not report['v6_files_unchanged']:report['failures'].append('v6_mutated_during_review')
    report['pass']=not report['failures']
    (OUT/'payload_independent_review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(pass_=report['pass'],failures=report['failures'],sources=before),indent=2),flush=True)


if __name__=='__main__':main()
