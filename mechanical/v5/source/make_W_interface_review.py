import sys,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools'));import cad_v5_leg as leg
cad=leg.cad;cad.configure(cad.ROOT/'mechanical/v5');cad.P.update(leg.configure())
path=cad.ROOT.parent/'references/DM-H6215/3D模型/6215_轮毂电机3D模型20240821.stp'
motor=cad.motor_shape(path,cad.P['hub_stator_face_y']+42);motor.translate(cad.V(0,0,-130))
new=leg.cw_fork()
old=leg.cut(new,leg.cyl(6.6,leg.Y(6),10,z=-130))
probe=leg.box(-3.2,leg.Y(15.05),-148,6.4,3.65,18)
assert probe.common(motor).Volume<1e-6
assert probe.common(new).Volume<1e-6
new.check(True)
report=dict(source_step=str(path),source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
 raw_motor_bounds_y_mm=[-2.5,42],cavity=dict(diameter_mm=12.9,y_mm=[35.25,42],kind='recess, not a boss protruding beyond mounting face'),
 native_radial_outlet=dict(x_mm=[-3.25,3.25],y_mm=[38.25,42],radial_direction='+Z',width_mm=6.5,axial_depth_mm=3.75),
 mounted_radial_outlet=dict(face_y_mm=cad.P['hub_stator_face_y'],radial_direction='-Z from W',y_range_mm=[leg.Y(15),leg.Y(18.75)]),
 clearance_probe=dict(width_x_mm=6.4,axial_depth_y_mm=3.65,radial_extent_from_W_mm=[0,18],margin_to_housing_slot_each_side_mm=.05,
                      real_step_intersection_mm3=probe.common(motor).Volume,candidate_CW_intersection_mm3=probe.common(new).Volume),
 candidate_CW=dict(valid=new.isValid(),solids=len(new.Solids),motor_intersection_mm3=new.common(motor).Volume,
                   added_volume_mm3=new.Volume-old.Volume,face_y_mm=cad.P['hub_stator_face_y']),
 bolt_seats=[])
for i,(x,dz) in enumerate(cad.points(8.75,3,90)):
    # Head contact from beneath S+10, measured just inside the aluminum floor.
    annulus=leg.ring(2.75,1.7,leg.Y(10.001),.01,dz-130);annulus.translate(cad.V(x,0,0))
    report['bolt_seats'].append(dict(index=i,annular_probe_volume_mm3=annulus.Volume,
        old_contact_mm3=annulus.common(old).Volume,new_contact_mm3=annulus.common(new).Volume,
        new_support_fraction=annulus.common(new).Volume/annulus.Volume))
report['leg_source_sha256']=hashlib.sha256((cad.ROOT/'tools/cad_v5_leg.py').read_bytes()).hexdigest()
report['limits']=['Cable diameter, connector envelope and minimum bend radius are not dimensioned in the supplied material.','Probe documents unused space in the original stator slot; it is not a modeled cable or proof of bending/service-loop fit.','Keep mounting face, wheel track, all other leg solids and hardware unchanged.']
probe.exportStep(str(cad.OUT/'source/H6215_outlet_clearance_probe.step'))
(cad.OUT/'H6215_W_interface_review.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
