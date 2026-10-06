"""Verify V7 inherited the released V6 leg sources, parameters and placement."""
import hashlib
import json
import build_printable_robot as cad

ROOT=cad.ROOT;OUT=ROOT/'mechanical/v7'
SOURCES=('cad_v6_leg.py','cad_v5_coupling.py','build_enclosed_robot.py',
         'cad_v6_chassis.py','build_printable_robot.py','cad_v3_profiles.py')
FIELDS=('rod_length','lower_length','crank_length','leg_length','beta_deg',
        'hip_stator_face_y','hip_output_face_y','hub_stator_face_y',
        'knee_motor_translation_y','wheel_center_y','wheel_track')


def main():
    baseline=json.loads((ROOT/'mechanical/v6/release_review.json').read_text())
    sources={name:dict(current=hashlib.sha256((ROOT/'tools'/name).read_bytes()).hexdigest(),
                       released=baseline['source_hashes'][name]) for name in SOURCES}
    params=[json.loads((ROOT/f'mechanical/{rev}/design_parameters.json').read_text()) for rev in ('v6','v7')]
    values={name:[p.get(name) for p in params] for name in FIELDS}
    a=cad.App.openDocument(str(ROOT/'mechanical/v6/wheel_leg_v6.FCStd'))
    b=cad.App.openDocument(str(OUT/'wheel_leg_v7.FCStd'))
    rows=[]
    try:
        for obj in a.Objects:
            if obj.TypeId!='Part::Feature':continue
            role=getattr(obj,'KinematicRole','fixed')
            if role=='fixed' and not obj.Name.startswith(('hip_stator_mount','J4310_hip')):continue
            other=b.getObject(obj.Name)
            if other is None:raise ValueError(f'Missing unchanged leg item: {obj.Name}')
            aa,bb=obj.Shape,other.Shape
            bounds_error=max(abs(getattr(aa.BoundBox,attr)-getattr(bb.BoundBox,attr)) for attr in
                ('XMin','XMax','YMin','YMax','ZMin','ZMax'))
            rows.append(dict(name=obj.Name,volume_error_mm3=abs(aa.Volume-bb.Volume),
                area_error_mm2=abs(aa.Area-bb.Area),bounds_error_mm=bounds_error,
                expression_engine_unchanged=list(obj.ExpressionEngine)==list(other.ExpressionEngine)))
        passed=(all(row['current']==row['released'] for row in sources.values()) and
            all(v[0]==v[1] for v in values.values()) and
            all(row['volume_error_mm3']<1e-6 and row['area_error_mm2']<1e-6 and
                row['bounds_error_mm']<1e-6 and row['expression_engine_unchanged'] for row in rows))
        report=dict(pass_all=passed,source_hashes=sources,parameters=values,objects=rows,
                    scope='Identical inherited source hashes and motion parameters; native object volume, area, bounds and expressions agree. Body paint/visibility excluded.')
        (OUT/'unchanged_legs_review.json').write_text(json.dumps(report,indent=2)+'\n')
        if not passed:raise ValueError('V6 leg preservation mismatch')
        print(f'V6_LEGS_UNCHANGED {len(rows)} objects',flush=True)
    finally:
        cad.App.closeDocument(a.Name);cad.App.closeDocument(b.Name)


if __name__=='__main__':main()
