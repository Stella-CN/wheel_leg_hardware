"""Independent continuous-body contact and sampled installation review.

Run with installed FreeCAD Python. Production CAD sources are read-only.
Nominal support and thread-core probes do not establish load capacity.
"""
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
import build_printable_robot as cad
import cad_v6_chassis as chassis
import cad_v6_payload as payload
import cad_v6_jetson_mount as mounts

OUT = ROOT / "mechanical/v6"
cad.configure(OUT)
Part, V = cad.Part, cad.V
FILES = [ROOT / "tools" / n for n in ("cad_v6_chassis.py", "cad_v6_payload.py", "cad_v6_jetson_mount.py")]
HASHES = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in FILES}
EPS, TOL = .002, .001


def overlap(a, b):
    # The official kit is wholly contained by this box. If the exact shell
    # has zero common volume with the box, the1393-solid boolean is needless.
    # This is conservative rejection only, never a replacement collision.
    if len(b.Solids)>100:
        bb=b.BoundBox
        envelope=Part.makeBox(bb.XLength,bb.YLength,bb.ZLength,V(bb.XMin,bb.YMin,bb.ZMin))
        if a.common(envelope).Volume<1e-9:
            return 0.
    return float(cad.interference_volume(a, b))


def annulus(point, axis, outer=3.5, inner=1.7):
    p, n = V(*point), V(*axis)
    return Part.makeCylinder(outer, EPS, p, n).cut(Part.makeCylinder(inner, EPS+.002, p-n*.001, n))


def fraction(probe, target):
    return overlap(probe, target) / probe.Volume


def moved(shape, delta):
    result = shape.copy(); result.translate(V(*delta)); return result


def chain(name, point, axis, grip, engagement, clamped, threaded, contact, sink=False):
    p, n = V(*point), V(*axis)
    thread = Part.makeCylinder(1.2, engagement-.02, p+n*(grip+.01), n)
    shaft = Part.makeCylinder(1.5, grip-.04, p+n*.02, n)
    row = dict(name=name, head_seat_or_flush_point_mm=point, inward_axis=axis,
               nominal_grip_mm=grip, nominal_engagement_mm=engagement,
               nominal_screw_end_mm=list(p+n*(grip+engagement)),
               interface_support_fraction=fraction(annulus(contact,axis,3 if sink else 2.75),threaded),
               clearance_shaft_overlap_mm3=overlap(shaft,clamped),
               thread_core_overlap_mm3=overlap(thread,threaded),thread_core_diameter_mm=2.4)
    if sink:
        head=Part.makeCylinder(3,.2,p,n).fuse(Part.makeCone(3,1.5,1.5,p+n*.2,n))
        row.update(head_geometry="DIN7991-style D6 x1.7; thread omitted",
                   head_distance_mm=head.distToShape(clamped)[0],head_overlap_mm3=overlap(head,clamped),
                   head_inward_0p01_overlap_mm3=overlap(moved(head,list(n*.01)),clamped))
    else:
        row["head_support_fraction"]=fraction(annulus(point,axis,2.75),clamped)
    row["pass"]=(row["interface_support_fraction"]>.8 and row["clearance_shaft_overlap_mm3"]<TOL and
                   row["thread_core_overlap_mm3"]<TOL and row.get("head_support_fraction",1)>.95 and
                   row.get("head_distance_mm",0)<TOL and row.get("head_overlap_mm3",0)<TOL and
                   row.get("head_inward_0p01_overlap_mm3",1)>TOL)
    return row


parts=chassis.build_chassis()
bracket=payload.camera_bracket(); parts["D435_embedded_bracket"]=bracket
hardware=chassis.chassis_hardware()+payload.camera_hardware()
hw={n:s for n,s,_ in hardware}
payload_rows=payload.payloads()
kit=next(s for n,s,_,_ in payload_rows if n=="Jetson_Orin_Nano_official")
camera=next(s for n,s,_,_ in payload_rows if n=="D435_clearance_envelope")
report=dict(status="Independent continuous-body contact and sampled assembly review; no structural qualification",
    superseded=False,source_sha256=HASHES,collision_tolerance_mm3=TOL,contact_probe_thickness_mm=EPS,
    parts={n:dict(valid=s.isValid(),solids=len(s.Solids)) for n,s in parts.items()},
    modeled_fixed_hardware_objects=len(hardware),unmodeled_frame_tray_fasteners=24,
    fastener_chains=[],camera_configurations=[],jetson_contacts=[],installation_paths=[],front_module_internal_collisions=[],failures=[],notes=[
        "Front/rear-shell and shoulder M3x20/M3x30 objects omit 6mm metal-thread engagement. Zero solid collision alone does not verify the full screw.",
        "The24 belly/frame/battery/tray screws are holes+BOM, not assembly solids. Independent head and D2.4 thread-core probes check nominal seats and endpoints without simulating threads.",
        "Partial nominal interface support is quantified, not treated as a strength or preload rating. No thread-runout, fatigue or jump-impact qualification is implied.",
        "Install front shell with preinstalled camera before outer coupling/knee/legs; test includes actual hip motors and hip mounts. Remove both bridging shoulder covers before withdrawing rear cover.",
        "Cables/connectors and physical print fit are outside sampled translation tests. Original1393 Jetson solids and original base are retained.",
        "Camera visual mesh and analytic collision volume are distinct; two explicitly different camera depths are checked."])

front_module=[("front_shell",parts["chassis_front_shell"]),("camera_bracket",bracket),("camera",camera)]
front_module.extend((n,s) for n,s,_ in payload.camera_hardware())
for i,(name,shape) in enumerate(front_module):
    for other_name,other_shape in front_module[i+1:]:
        mm3=overlap(shape,other_shape)
        if mm3>TOL:
            report["front_module_internal_collisions"].append(dict(a=name,b=other_name,mm3=mm3))
print("FRONT_MODULE_INTERNAL",json.dumps(report["front_module_internal_collisions"]),flush=True)

# Check both camera variants first, so a packaging failure is reported early.
for depth,shim,length in ((25.05,1.,6),(26.05,0.,5)):
    rear=100-depth; z=payload.CAMERA_CENTER_Z
    volume=cad.box(rear,-45.075,z-12.575,depth,90.15,25.15)
    volume=cad.cut(volume,*(payload.prior.xcyl(1.6,rear-.1,3.1,y,z) for y in (-22.5,22.5)))
    config=dict(depth_mm=depth,rear_plane_x_mm=rear,shim_mm=shim,screw=f"M3x{length}",
                nominal_insertion_mm=length-3-shim,collisions=[],contacts=[])
    for name,shape in parts.items():
        mm3=overlap(volume,shape)
        if mm3>TOL:config["collisions"].append(dict(part=name,mm3=mm3))
    for y in (-22.5,22.5):
        screw=cad.union(payload.prior.xcyl(1.5,70.95,length,y,z),payload.prior.xcyl(2.75,67.95,3,y,z))
        config["contacts"].append(dict(y=y,bracket_fraction=fraction(annulus((73.95,y,z),(-1,0,0),4),bracket),
            camera_fraction=fraction(annulus((rear,y,z),(1,0,0),4),volume),
            screw_camera_mm3=overlap(screw,volume),screw_bracket_mm3=overlap(screw,bracket)))
    config["pass"]=not config["collisions"] and all(c["bracket_fraction"]>.99 and c["camera_fraction"]>.99 and c["screw_camera_mm3"]<TOL and c["screw_bracket_mm3"]<TOL for c in config["contacts"])
    report["camera_configurations"].append(config)
    print("CAMERA",json.dumps(config),flush=True)

for x,y in chassis.BOTTOM_FASTENERS:
    side=parts["chassis_hip_frame_right" if y>0 else "chassis_hip_frame_left"]
    report["fastener_chains"].append(chain(f"belly_{x}_{y}",(x,y,-50),(0,0,1),3,5,parts["chassis_belly_plate"],side,(x,y,-47),True))
for x in (-82.,82.):
    cross=parts["chassis_front_crossframe" if x>0 else "chassis_rear_crossframe"]
    for sign in (-1,1):
        side=parts["chassis_hip_frame_right" if sign>0 else "chassis_hip_frame_left"]
        for z in (-25.,25.):
            report["fastener_chains"].append(chain(f"cross_{x}_{sign}_{z}",(x,75*sign,z),(0,-sign,0),3,5,side,cross,(x,72*sign,z),True))
for x,y in chassis.core.BATTERY_FASTENERS:
    report["fastener_chains"].append(chain(f"battery_{x}_{y}",(x,y,-36),(0,0,-1),3,5,parts["battery_tray"],parts["chassis_belly_plate"],(x,y,-39)))
for x,y in chassis.TRAY_FASTENERS:
    side=parts["chassis_hip_frame_right" if y>0 else "chassis_hip_frame_left"]
    report["fastener_chains"].append(chain(f"tray_{x}_{y}",(x,y,33),(0,0,-1),3,5,parts["electronics_tray"],side,(x,y,30)))
for y,z in chassis.SHELL_FASTENERS:
    for sign in (-1,1):
        shell=parts["chassis_front_shell" if sign>0 else "chassis_rear_cover"]
        cross=parts["chassis_front_crossframe" if sign>0 else "chassis_rear_crossframe"]
        report["fastener_chains"].append(chain(f"shell_{sign}_{y}_{z}",(100 if sign>0 else -110,y,z),(-sign,0,0),14 if sign>0 else 24,6,shell,cross,(86*sign,y,z)))
for x,z in chassis.SHOULDER_FASTENERS:
    for sign in (-1,1):
        shoulder=parts["shoulder_fairing_right" if sign>0 else "shoulder_fairing_left"]
        side=parts["chassis_hip_frame_right" if sign>0 else "chassis_hip_frame_left"]
        body=parts["chassis_front_shell" if x>chassis.SPLIT_X else "chassis_rear_cover"]
        row=chain(f"shoulder_{sign}_{x}",(x,89*sign,z),(0,-sign,0),14,6,Part.makeCompound([shoulder,body]),side,(x,75*sign,z))
        row["shoulder_body_fraction"]=fraction(annulus((x,86*sign,z),(0,-sign,0)),body)
        row["pass"] &= row["shoulder_body_fraction"]>.95
        report["fastener_chains"].append(row)
for index,(y,z) in enumerate(( (y,z) for y in (-50,50) for z in payload.CAMERA_FRAME_Z )):
    nut=hw[f"D435_frame_M3_nut_{index}"]
    probe=payload.prior.xhex(93,EPS,y,z,5.5).cut(payload.prior.xcyl(1.7,92.999,EPS+.002,y,z))
    row=dict(name=f"camera_frame_{index}",head_fraction=fraction(annulus((100,y,z),(-1,0,0),2.75),parts["chassis_front_shell"]),
             bracket_shell_fraction=fraction(annulus((97,y,z),(1,0,0)),parts["chassis_front_shell"]),
             nut_roof_fraction=fraction(probe,bracket),nut_distance_mm=nut.distToShape(bracket)[0],
             grip_mm=7.,nut_engagement_mm=2.4,tip_projection_mm=.6)
    row["pass"]=all(row[k]>.95 for k in ("head_fraction","bracket_shell_fraction","nut_roof_fraction")) and row["nut_distance_mm"]<TOL
    report["fastener_chains"].append(row)
print("CHAINS_FAILED",json.dumps([r for r in report["fastener_chains"] if not r["pass"]]),flush=True)

base=kit.Solids[1266]; tray=parts["electronics_tray"]
report["jetson_actual_minimum_base_vertex_z_mm"]=min(v.Point.z for v in base.Vertexes)
report["jetson_base_to_final_tray_distance_mm"]=base.distToShape(tray)[0]
report["jetson_kit_to_final_tray_overlap_mm3"]=overlap(tray,kit)
for x,y in mounts.TRAY_HOLES:
    retainer=parts["Jetson_base_retainer_right" if y>0 else "Jetson_base_retainer_left"]
    row=dict(centre_xy_mm=[x,y],head_fraction=fraction(annulus((x,y,36),(0,0,-1),2.75),retainer),
             retainer_tray_fraction=fraction(annulus((x,y,33),(0,0,-1)),tray),
             washer_tray_fraction=fraction(annulus((x,y,30),(0,0,1),3.5,1.6),tray),
             total_grip_mm=6.5,nut_engagement_mm=2.4,tip_projection_mm=1.1)
    row["pass"]=all(row[k]>.95 for k in ("head_fraction","retainer_tray_fraction","washer_tray_fraction"))
    report["jetson_contacts"].append(row)
print("JETSON_CONTACTS",json.dumps(report["jetson_contacts"]),flush=True)

# Sample actual final geometry translating past actual fixed hip motors and
# the complete official electronics. Outer coupling/knee/legs are not yet fitted.
path=ROOT.parent/"references/DM-J4310-2EC/3D模型/DM-J4310-2EC-V1.1_3d_20260228_1.stp"
hip=cad.motor_shape(path,72.5); mount=chassis.hip_stator_mount()
fixed={n:s for n,s in parts.items() if n not in ("chassis_front_shell","chassis_rear_cover","D435_embedded_bracket","shoulder_fairing_right","shoulder_fairing_left")}
fixed.update({n:s for n,s,_,_ in payload_rows if n!="D435_clearance_envelope"})
fixed.update(hip_motor_right=hip,hip_motor_left=cad.mirror(hip),hip_mount_right=mount,hip_mount_left=cad.mirror(mount))
fixed.update({n:s for n,s,_ in mounts.hardware()})
for name,shape,_ in chassis.hip_hardware():
    fixed[name+"_right"]=shape
    fixed[name+"_left"]=cad.mirror(shape)
front={"front_shell":parts["chassis_front_shell"],"camera_bracket":bracket,"camera":camera}
front.update({n:s for n,s,_ in payload.camera_hardware()})
rear_targets=dict(fixed,**front)
# A rotationally invariant R30.5 cylinder conservatively contains both
# inherited coupling pieces/hardware and the J4310 knee motor at any hip
# angle. Every downstream leg part is farther out than Y132.1; the rear
# cover remains inside |Y|86. This closes the service-path outer-motor gap.
for sign in (-1,1):
    rear_targets[f"retained_outer_motor_envelope_{sign}"]=Part.makeCylinder(30.5,60.9,V(0,72.2*sign,0),V(0,sign,0))
report["rear_service_outer_motor_check"]="Conservative rotationally invariant R30.5, |Y|72.2..133.1 cylinder; downstream leg parts lie farther out than |Y|132.1"
for label,direction,moving,targets in (
    ("front_shell_camera_install_before_outer_motors",1,front,fixed),
    ("rear_cover_remove_after_shoulders_removed",-1,{"rear_cover":parts["chassis_rear_cover"]},rear_targets)):
    result=dict(name=label,translation_axis="X",sample_offsets_mm=[],collisions=[])
    for step in (0.,.1,.5,1.,2.,4.,8.,16.,32.,64.,120.):
        dx=direction*step; result["sample_offsets_mm"].append(dx)
        for name,shape in moving.items():
            shifted=moved(shape,(dx,0,0))
            for fixed_name,target in targets.items():
                mm3=overlap(shifted,target)
                if mm3>TOL:
                    row=dict(offset_mm=dx,moving=name,fixed=fixed_name,mm3=mm3)
                    result["collisions"].append(row);print("PATH_COLLISION",json.dumps(row),flush=True)
        print(f"PATH {label} X{dx:g}",flush=True)
    result["pass"]=not result["collisions"];report["installation_paths"].append(result)

report["pass"]={
    "valid_single_solid_custom_parts":all(r["valid"] and r["solids"]==1 for r in report["parts"].values()),
    "all_frame_shell_camera_fastener_chains_supported":all(r["pass"] for r in report["fastener_chains"]),
    "both_camera_depth_configurations_fit":all(r["pass"] for r in report["camera_configurations"]),
    "front_camera_module_has_no_internal_interference":not report["front_module_internal_collisions"],
    "jetson_final_tray_contact_and_fastener_support":report["jetson_base_to_final_tray_distance_mm"]<TOL and report["jetson_kit_to_final_tray_overlap_mm3"]<TOL and all(r["pass"] for r in report["jetson_contacts"]),
    "sampled_front_install_and_rear_service_paths_clear":all(r["pass"] for r in report["installation_paths"]),
}
report["failures"]=[name for name,passed in report["pass"].items() if not passed]
report["source_unchanged_during_review"]=all(hashlib.sha256(p.read_bytes()).hexdigest()==HASHES[p.name] for p in FILES)
if not report["source_unchanged_during_review"]:report["failures"].append("source_changed_during_review")
(OUT/"chassis_payload_independent_review.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(dict(passed=report["pass"],failures=report["failures"],source_unchanged_during_review=report["source_unchanged_during_review"]),indent=2))
