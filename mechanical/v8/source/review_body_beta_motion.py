"""Six V8 body/unchanged-leg samples at100/180/215mm and beta +/-10deg.

Both legs are checked against the real V8 fixed body and installed payloads.
Only the JSON report is written; this does not change or configure CAD files.
"""
from pathlib import Path
import hashlib
import json
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools'))
import build_printable_robot as cad
import build_enclosed_robot as wheels
import cad_v6_leg as leg
import cad_v5_coupling as coupling
import cad_v8_chassis as chassis
import cad_v8_payload as payload


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    out=ROOT/'mechanical/v8';out.mkdir(parents=True,exist_ok=True)
    names=('cad_v8_chassis.py','cad_v8_payload.py','cad_v8_display.py','cad_v6_chassis.py',
           'cad_v6_payload.py','cad_v7_payload.py','cad_v7_imu.py','cad_v6_jetson_mount.py',
           'cad_v6_leg.py','cad_v5_coupling.py','build_printable_robot.py','build_enclosed_robot.py')
    sources={name:ROOT/'tools'/name for name in names}
    before={name:sha(path) for name,path in sources.items()}
    expected_leg='abe2646d426fe4bd03c0f8ec4aa000e7cea71a055b00763f20e39e32ead2f091'
    assert before['cad_v6_leg.py']==expected_leg,'FrozenV6 leg source changed'
    parameter_source=out if (out/'design_parameters.json').exists() else ROOT/'mechanical/v6'
    cad.configure(parameter_source)
    prior=json.loads((ROOT/'mechanical/v6/design_parameters.json').read_text())
    frozen_keys=('rod_length','lower_length','crank_length','knee_stator_face_y',
                 'knee_motor_translation_y','hub_stator_face_y','wheel_center_y')
    assert all(cad.P[k]==prior[k] for k in frozen_keys),'Frozen leg datums changed'
    body=chassis.build_chassis()
    body.update(payload.designs())
    body.update({name:shape for name,shape,_,_ in payload.payloads()})
    moving=dict(coupling.designs());moving.update(leg.designs())
    moving['wheel_rim']=(wheels.wheel_rim(),'wheel','CNC')
    refs=ROOT.parent/'references'
    jpath=refs/'DM-J4310-2EC/3D模型/DM-J4310-2EC-V1.1_3d_20260228_1.stp'
    hpath=refs/'DM-H6215/3D模型/6215_轮毂电机3D模型20240821.stp'
    hub_offset=cad.P['hub_stator_face_y']-164
    moving['J4310_knee_official']=(cad.motor_shape(jpath,cad.P['knee_motor_translation_y']),'hip','official_motor')
    moving['H6215_wheel_official']=(cad.motor_shape(hpath,206+hub_offset),'wheel','official_motor')
    tyre=cad.cut(cad.cyl(50,174,32),cad.cyl(43,173,34));tyre.translate(cad.V(0,hub_offset,0))
    moving['elastic_tyre']=(tyre,'wheel','rubber_reference')
    moving={n:row for n,row in moving.items() if row[1]!='fixed'}
    threshold=.05;results=[];collisions=[]
    for length in (100,180,215):
        for beta in (-10,10):
            state=cad.pose(length,beta);count=0;maximum=0.;worst=None
            for ln,(shape,role,_) in moving.items():
                right=cad.transform(shape,role,state)
                for side,placed in (('right',right),('left',cad.mirror(right))):
                    for bn,bshape in body.items():
                        volume=max(0.,cad.interference_volume(bshape,placed));count+=1
                        if volume>maximum:maximum=volume;worst=[bn,side,ln]
                        if volume>threshold:
                            collisions.append(dict(length_mm=length,beta_deg=beta,side=side,
                                body=bn,moving_part=ln,volume_mm3=volume))
            results.append(dict(length_mm=length,beta_deg=beta,hip_deg=state['hip'],oa_deg=state['oa'],
                                pair_count=count,max_overlap_mm3=maximum,worst_pair=worst))
            print('POSE',length,beta,'max_mm3',maximum,flush=True)
    unchanged=before=={name:sha(path) for name,path in sources.items()}
    report=dict(units='mm',threshold_volume_mm3=threshold,source_sha256=before,
        script_sha256=sha(__file__),source_unchanged=unchanged,source_unchanged_during_review=unchanged,
        leg_geometry_frozen_to_v6=before['cad_v6_leg.py']==expected_leg,
        parameter_source=str(parameter_source.relative_to(ROOT)),preserved_leg_datums={k:cad.P[k] for k in frozen_keys},
        motor_source_sha256={str(jpath.relative_to(ROOT.parent)):sha(jpath),str(hpath.relative_to(ROOT.parent)):sha(hpath)},
        body_parts=list(body),moving_parts={n:dict(role=r[1],source_material=r[2]) for n,r in moving.items()},
        poses=results,collisions=collisions,pass_geometry=not collisions and unchanged,
        scope='V8 R5 rectangular body, full front panel, display/camera supports and installed payloads against both mirrored originalV6 legs, unchanged coupling, wheel rim, tyre and original J4310/H6215 STEP solids.',
        exclusions='No hardware all-pairs, cables/plugs, deformation, dynamics, or continuous sweep. Display is supplier outside-envelope only. Six samples do not establish a continuous safe motion envelope; integrated beta0 scan is separate.')
    report['failures']=(['moving_leg_body_interference'] if collisions else [])+([] if unchanged else ['source_changed_during_review'])
    (out/'body_beta_motion_review.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(pass_geometry=report['pass_geometry'],collisions=collisions,
        body_parts=len(body),moving_parts=len(moving),pairs=sum(p['pair_count'] for p in results))))
    assert report['pass_geometry'],'Body/moving leg interference or source modification'


if __name__=='__main__':main()
