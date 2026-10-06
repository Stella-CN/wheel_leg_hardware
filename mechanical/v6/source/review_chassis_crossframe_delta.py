"""Requalify the final rail reinforcement against the immutable6c5ca468 review.

Only newly added metal is collision-tested. Removed material cannot create
interference; affected supporting faces and thread-core depths are retested.
Unchanged geometry and the previous full assembly checks remain traceable.
"""
from pathlib import Path
import ast
import copy
import hashlib
import importlib.util
import json
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools'))
import build_printable_robot as cad
import cad_v6_chassis as current
import cad_v6_payload as payload
import cad_v6_jetson_mount as mounts

OUT=ROOT/'mechanical/v6'
SOURCE=OUT/'source'
BASELINE=SOURCE/'review_baselines'
BASE_SHA='6c5ca468937e011e070385949ad7fd5618ee7a5eab851bf9e1ed0f6d5753845e'
baseline_source=BASELINE/'cad_v6_chassis_6c5ca468.py'
baseline_report=BASELINE/'body_review_6c5ca468.json'
assert hashlib.sha256(baseline_source.read_bytes()).hexdigest()==BASE_SHA
spec=importlib.util.spec_from_file_location('review_baseline_chassis',baseline_source)
old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
files=[ROOT/'tools'/n for n in ('cad_v6_chassis.py','cad_v6_payload.py','cad_v6_jetson_mount.py')]
hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
baseline=json.loads(baseline_report.read_text())
assert all(baseline['pass'].values()) and not baseline['failures']
assert all(hashes[n]==baseline['source_sha256'][n] for n in ('cad_v6_payload.py','cad_v6_jetson_mount.py'))

def syntax(source):
    tree=ast.parse(source)
    functions={n.name:ast.dump(n,include_attributes=False) for n in tree.body if isinstance(n,ast.FunctionDef)}
    remaining=ast.Module(body=[n for n in tree.body if not isinstance(n,ast.FunctionDef)],type_ignores=[])
    return functions,ast.dump(remaining,include_attributes=False)

before,before_globals=syntax(baseline_source.read_text())
after,after_globals=syntax(files[0].read_text())
changed=[n for n in set(before)|set(after) if before.get(n)!=after.get(n)]
assert set(changed)=={'_crossframe','_side'},changed
assert before_globals==after_globals,'A global, import or constant changed outside the reinforcement scope'

# Reuse the exact audited probe functions, without executing that full review.
# These are local maintained test definitions, not CAD sources or external code.
helper_source=SOURCE/'review_chassis_payload_interfaces.py'
helper_tree=ast.parse(helper_source.read_text())
helpers=[n for n in helper_tree.body if isinstance(n,ast.FunctionDef) and n.name in
         ('overlap','annulus','fraction','moved','chain')]
Part,V,EPS,TOL=cad.Part,cad.V,.002,.001
exec(compile(ast.Module(body=helpers,type_ignores=[]),str(helper_source),'exec'),globals())
cad.configure(OUT)

old_parts={};new_parts={}
for name,function,right in (
    ('chassis_hip_frame_right','_side',True),('chassis_hip_frame_left','_side',False),
    ('chassis_front_crossframe','_crossframe',True),('chassis_rear_crossframe','_crossframe',False)):
    old_parts[name]=getattr(old,function)(right)
    new_parts[name]=getattr(current,function)(right)

delta=dict(method='exact added/removed BRep volumes; unchanged source syntax and immutable full-review inheritance',
    baseline_source_sha256=BASE_SHA,baseline_report_sha256=hashlib.sha256(baseline_report.read_bytes()).hexdigest(),
    source_sha256=hashes,changed_functions=sorted(changed),unchanged_global_syntax=True,
    helper_source_sha256=hashlib.sha256(helper_source.read_bytes()).hexdigest(),
    geometry_differences={},new_material_collisions=[],path_collisions=[],updated_fastener_chains=[],failures=[])
added={}
for name,new in new_parts.items():
    old_shape=old_parts[name]
    positive=new.cut(old_shape);negative=old_shape.cut(new)
    delta['geometry_differences'][name]=dict(valid=new.isValid(),solids=len(new.Solids),
        old_volume_mm3=old_shape.Volume,new_volume_mm3=new.Volume,added_mm3=positive.Volume,removed_mm3=negative.Volume)
    delta['geometry_differences'][name]['added_solid_bounds_mm']=[
        [s.BoundBox.XMin,s.BoundBox.YMin,s.BoundBox.ZMin,s.BoundBox.XMax,s.BoundBox.YMax,s.BoundBox.ZMax]
        for s in positive.Solids]
    if positive.Volume>TOL:added[name]=positive
    if name.startswith('chassis_hip_frame'):
        assert positive.Volume<TOL,'Side frames should only lose end material'
    else:
        assert negative.Volume<TOL,'Crossframes should only gain rails; extended drills must stay in the new stock'
delta['net_aluminium_mass_change_g']=sum(r['new_volume_mm3']-r['old_volume_mm3'] for r in delta['geometry_differences'].values())*.0027

front,rear=current._shell_pair()
targets=dict(new_parts,chassis_belly_plate=current._bottom(),electronics_tray=current._tray(),
             battery_tray=current.core.prior._battery_tray(),chassis_front_shell=front,chassis_rear_cover=rear,
             D435_embedded_bracket=payload.camera_bracket())
targets.update(mounts.designs())
targets['D435_alternate_26p05_depth']=cad.box(73.95,-45.075,payload.CAMERA_CENTER_Z-12.575,26.05,90.15,25.15)
targets.update({n:s for n,s,_ in mounts.hardware()})
for name,shape,_ in current.hip_hardware():
    targets[name+'_right']=shape;targets[name+'_left']=cad.mirror(shape)
seat=current.hip_stator_mount();targets.update(hip_seat_right=seat,hip_seat_left=cad.mirror(seat))
motor_path=ROOT.parent/'references/DM-J4310-2EC/3D模型/DM-J4310-2EC-V1.1_3d_20260228_1.stp'
motor=cad.motor_shape(motor_path,72.5);targets.update(hip_motor_right=motor,hip_motor_left=cad.mirror(motor))
for name,shape,_,_ in payload.payloads():
    if name=='Jetson_Orin_Nano_official':
        bb=shape.BoundBox
        envelope=Part.makeBox(bb.XLength,bb.YLength,bb.ZLength,V(bb.XMin,bb.YMin,bb.ZMin))
        targets['official_Jetson_conservative_source_bounds']=envelope
        delta['Jetson_rejection_bounds_mm']=[bb.XMin,bb.YMin,bb.ZMin,bb.XMax,bb.YMax,bb.ZMax]
    else:targets[name]=shape

for name,material in added.items():
    for target_name,target in targets.items():
        if target_name==name:continue
        mm3=overlap(material,target)
        if mm3>TOL:delta['new_material_collisions'].append(dict(added_to=name,target=target_name,mm3=mm3))
print('DELTA_COLLISIONS',json.dumps(delta['new_material_collisions']),flush=True)

# Affected seats:8 side-to-crossframe,8 belly-to-side,4 tray-to-side and8
# shell-to-crossframe screws. Other seats are unchanged in identical geometry.
for x in (-82.,82.):
    cross=new_parts['chassis_front_crossframe' if x>0 else 'chassis_rear_crossframe']
    for sign in (-1,1):
        side=new_parts['chassis_hip_frame_right' if sign>0 else 'chassis_hip_frame_left']
        for z in (-25.,25.):
            delta['updated_fastener_chains'].append(chain(f'cross_{x}_{sign}_{z}',(x,75*sign,z),(0,-sign,0),3,5,side,cross,(x,72*sign,z),True))
for x,y in current.BOTTOM_FASTENERS:
    side=new_parts['chassis_hip_frame_right' if y>0 else 'chassis_hip_frame_left']
    delta['updated_fastener_chains'].append(chain(f'belly_{x}_{y}',(x,y,-50),(0,0,1),3,5,targets['chassis_belly_plate'],side,(x,y,-47),True))
for x,y in current.TRAY_FASTENERS:
    side=new_parts['chassis_hip_frame_right' if y>0 else 'chassis_hip_frame_left']
    delta['updated_fastener_chains'].append(chain(f'tray_{x}_{y}',(x,y,33),(0,0,-1),3,5,targets['electronics_tray'],side,(x,y,30)))
for y,z in current.SHELL_FASTENERS:
    for sign in (-1,1):
        cross=new_parts['chassis_front_crossframe' if sign>0 else 'chassis_rear_crossframe']
        delta['updated_fastener_chains'].append(chain(f'shell_{sign}_{y}_{z}',(100 if sign>0 else -110,y,z),(-sign,0,0),14 if sign>0 else 24,6,front if sign>0 else rear,cross,(86*sign,y,z)))
delta['crossframe_edge_dimensions_mm']=dict(hole_centre_abs_x=82,rail_inner_abs_x=78,skin_outer_abs_x=86,
    hole_centre_to_both_edges=4,drill_diameter=2.5,drill_to_edge_web=2.75,nominal_M3_major_to_edge_web=2.5)
print('DELTA_CHAINS_FAILED',json.dumps([r for r in delta['updated_fastener_chains'] if not r['pass']]),flush=True)

# Previous full-path tests cover unchanged obstacles and removed side material.
# Only the newly added rail stock needs a fresh sweep against moving modules.
moving_front={'front_shell':front,'camera_bracket':targets['D435_embedded_bracket']}
moving_front.update({n:s for n,s,_ in payload.camera_hardware()})
moving_front['camera']=next(s for n,s,_,_ in payload.payloads() if n=='D435_clearance_envelope')
moving_front['camera_alternate_depth_probe']=targets['D435_alternate_26p05_depth']
for label,direction,moving in (('front',1,moving_front),('rear',-1,{'rear_cover':rear})):
    for step in (0.,.1,.5,1.,2.,4.,8.,16.,32.,64.,120.):
        for name,shape in moving.items():
            shifted=moved(shape,(step*direction,0,0))
            for added_name,material in added.items():
                mm3=overlap(shifted,material)
                if mm3>TOL:delta['path_collisions'].append(dict(path=label,offset_mm=step*direction,moving=name,added_to=added_name,mm3=mm3))
        print('DELTA_PATH',label,step*direction,flush=True)

delta['pass']=dict(valid_parts=all(r['valid'] and r['solids']==1 for r in delta['geometry_differences'].values()),
    no_new_material_interference=not delta['new_material_collisions'],
    affected_fastener_chains_supported=all(r['pass'] for r in delta['updated_fastener_chains']),
    added_material_clear_on_all_previous_path_samples=not delta['path_collisions'])
delta['source_unchanged_during_review']=all(hashlib.sha256(p.read_bytes()).hexdigest()==hashes[p.name] for p in files)
delta['failures']=[n for n,v in delta['pass'].items() if not v]
if not delta['source_unchanged_during_review']:delta['failures'].append('source_changed_during_review')
(OUT/'crossframe_reinforcement_independent_review.json').write_text(json.dumps(delta,indent=2)+'\n')

report=copy.deepcopy(baseline)
report['status']='Final body revision: immutable full6c5ca468 review plus exact reinforcement delta requalification'
report['source_sha256']=hashes
report['source_unchanged_during_review']=delta['source_unchanged_during_review']
report['revision_evidence']=dict(baseline_report='source/review_baselines/body_review_6c5ca468.json',
    baseline_source='source/review_baselines/cad_v6_chassis_6c5ca468.py',baseline_source_sha256=BASE_SHA,
    baseline_report_sha256=delta['baseline_report_sha256'],delta_report='crossframe_reinforcement_independent_review.json',
    changed_functions=sorted(changed),inheritance='Every original pass remains applicable: unchanged geometry retained; removed side material cannot add interference; added crossframe stock and affected28 screw chains were retested.')
updates={r['name']:r for r in delta['updated_fastener_chains']}
report['fastener_chains']=[updates.get(r['name'],r) for r in report['fastener_chains']]
for name,data in delta['geometry_differences'].items():report['parts'][name]=dict(valid=data['valid'],solids=data['solids'])
report['pass']['crossframe_reinforcement_delta']=all(delta['pass'].values())
report['failures']=delta['failures']
(OUT/'chassis_payload_independent_review.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(passed=delta['pass'],failures=delta['failures'],mass_change_g=delta['net_aluminium_mass_change_g']),indent=2))
