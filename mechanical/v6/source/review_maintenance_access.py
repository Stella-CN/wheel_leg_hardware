"""Limited maintenance check: remove rear crossframe, lift tray, withdraw.

No design geometry is modified. Cable unplugging and tool reach are excluded.
The official device's real BRep bounds conservatively cover all source solids.
"""
from pathlib import Path
import hashlib
import json
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools'))
import build_printable_robot as cad
import cad_v6_chassis as chassis
import cad_v6_payload as payload
import cad_v6_jetson_mount as mounts

OUT=ROOT/'mechanical/v6'
Part,V=cad.Part,cad.V
FILES=[ROOT/'tools'/n for n in ('cad_v6_chassis.py','cad_v6_payload.py','cad_v6_jetson_mount.py')]
HASHES={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in FILES}
TOL=.001

def bounds(shape):
    b=shape.BoundBox
    return [b.XMin,b.YMin,b.ZMin,b.XMax,b.YMax,b.ZMax]

def moved(shape,x=0,z=0):
    result=shape.copy();result.translate(V(x,0,z));return result

def envelope(shape,delta=(0,0,0)):
    b=shape.BoundBox
    origin=V(b.XMin+min(0,delta[0]),b.YMin+min(0,delta[1]),b.ZMin+min(0,delta[2]))
    return Part.makeBox(b.XLength+abs(delta[0]),b.YLength+abs(delta[1]),b.ZLength+abs(delta[2]),origin)

def collisions(moving,targets):
    hits=[]
    for name,shape in moving.items():
        for target_name,target in targets.items():
            volume=cad.interference_volume(shape,target)
            if volume>TOL:hits.append(dict(moving=name,target=target_name,mm3=volume))
    return hits

cad.configure(OUT)
parts=chassis.build_chassis()
kit=payload.jetson()
module={'electronics_tray':parts['electronics_tray'],'official_Jetson_bounds':envelope(kit)}
module.update(mounts.designs());module.update({n:s for n,s,_ in mounts.hardware()})
module_compound=Part.makeCompound(list(module.values()))
rear_frame=parts['chassis_rear_crossframe']
fixed={n:s for n,s in parts.items() if n not in ('electronics_tray','Jetson_base_retainer_right','Jetson_base_retainer_left',
       'chassis_rear_cover','chassis_rear_crossframe','shoulder_fairing_right','shoulder_fairing_left')}
fixed['D435_bracket']=payload.camera_bracket()
fixed.update({n:s for n,s,_ in payload.camera_hardware()})
fixed.update({n:s for n,s,_,_ in payload.payloads() if n!='Jetson_Orin_Nano_official'})
path=ROOT.parent/'references/DM-J4310-2EC/3D模型/DM-J4310-2EC-V1.1_3d_20260228_1.stp'
hip=cad.motor_shape(path,72.5);seat=chassis.hip_stator_mount()
fixed.update(hip_motor_right=hip,hip_motor_left=cad.mirror(hip),hip_mount_right=seat,hip_mount_left=cad.mirror(seat))
for name,shape,_ in chassis.hip_hardware():
    fixed[name+'_right']=shape;fixed[name+'_left']=cad.mirror(shape)

report=dict(scope='Maintenance access only; unchanged final body geometry',source_sha256=HASHES,
    removed_before_tests=['both shoulder covers','rear cover and its4 M3x30','electronics-tray4 M3x8',
                         'rear-crossframe4 side-facing DIN7991 M3x8'],
    module='Original Jetson kit, electronics tray, both retaining rails and their12 hardware objects remain together',
    original_kit_conservative_bounds_mm=bounds(kit),module_bounds_mm=bounds(module_compound),
    rear_frame_opening_top_z_mm=35.,rear_frame_withdrawal_samples=[],straight_withdrawal_diagnostic=[],
    lift_height_mm=4.,lift_conservative_sweep_collisions=[],withdrawal_conservative_sweep_collisions=[],
    notes=['Rear crossframe must be removed: its opening endsZ35, below the kit topZ67.766.',
           'The source kit envelope is conservative, not a changed or simplified delivered device model.',
           'The low retainer screws/nuts stay with the module and initially extend down toZ26.',
           'Lift is covered by each component bounding box swept upward4mm; withdrawal by the whole raised module box swept backward180mm.',
           'Zero intersection of these conservative sweeps proves clearance over those straight translations at fixed orientation.',
           'Rear-crossframe removal is checked at discrete positions, not claimed as a complete continuous sweep.',
           'Cables, plugs, straps, free tool motion, hand access, tilt and physical tolerances are not included. Disconnect and support the module before moving it.'])

frame_targets=dict(fixed,**module)
for dx in (0.,-.5,-4.,-16.,-40.,-100.):
    hits=collisions({'rear_crossframe':moved(rear_frame,dx)},frame_targets)
    report['rear_frame_withdrawal_samples'].append(dict(x_offset_mm=dx,collisions=hits))
    print('REAR_FRAME',dx,hits,flush=True)

# Diagnostic of the rejected straight withdrawal: test real protruding
# hardware against the real hip motors at the critical crossing position.
fasteners={n:moved(s,-38.) for n,s,_ in mounts.hardware()}
report['straight_withdrawal_diagnostic']=collisions(fasteners,{'hip_motor_right':hip,'hip_motor_left':cad.mirror(hip)})
print('STRAIGHT_WITHDRAWAL_DIAGNOSTIC',json.dumps(report['straight_withdrawal_diagnostic']),flush=True)

lift_sweeps={n:envelope(s,(0,0,4.)) for n,s in module.items()}
report['lift_conservative_sweep_collisions']=collisions(lift_sweeps,fixed)
raised=moved(module_compound,z=4.)
swept=envelope(raised,(-180.,0,0))
report['raised_module_bounds_mm']=bounds(raised)
report['withdrawal_swept_bounds_mm']=bounds(swept)
report['withdrawal_conservative_sweep_collisions']=collisions({'raised_module_sweep':swept},fixed)
report['minimum_raised_module_z_mm']=raised.BoundBox.ZMin
report['hip_motor_maximum_z_mm']=hip.BoundBox.ZMax
report['nominal_vertical_gap_to_hip_motor_mm']=raised.BoundBox.ZMin-hip.BoundBox.ZMax
report['pass']=dict(rear_crossframe_sampled_withdrawal_clear=all(not r['collisions'] for r in report['rear_frame_withdrawal_samples']),
    upward4mm_conservative_sweeps_clear=not report['lift_conservative_sweep_collisions'],
    backward180mm_raised_module_conservative_sweep_clear=not report['withdrawal_conservative_sweep_collisions'])
report['source_unchanged_during_review']=all(hashlib.sha256(p.read_bytes()).hexdigest()==HASHES[p.name] for p in FILES)
report['failures']=[n for n,v in report['pass'].items() if not v]
if not report['source_unchanged_during_review']:report['failures'].append('source_changed_during_review')
(OUT/'maintenance_access_review.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ('pass','failures','nominal_vertical_gap_to_hip_motor_mm','source_unchanged_during_review')},indent=2))
