"""Check the delivered main linkage and motor datums against V8."""
import hashlib
import json
import build_printable_robot as cad

OUT=cad.ROOT/'mechanical/v8_1'
FIELDS=('rod_length','lower_length','crank_length','leg_length','beta_deg',
        'hip_stator_face_y','hip_output_face_y','hub_stator_face_y',
        'knee_motor_translation_y','wheel_center_y','wheel_track')


def main():
    params=[json.loads((cad.ROOT/f'mechanical/{v}/design_parameters.json').read_text()) for v in ('v8','v8_1')]
    assert all(params[0][k]==params[1][k] for k in FIELDS)
    a=cad.App.openDocument(str(cad.ROOT/'mechanical/v8/wheel_leg_v8.FCStd'))
    b=cad.App.openDocument(str(OUT/'wheel_leg_v8_1.FCStd'))
    rows=[]
    for obj in a.Objects:
        if obj.TypeId!='Part::Feature':continue
        if not obj.Name.startswith(('OB_inner_carrier_','OB_outer_shell_','OA_one_piece_',
                'AC_bearing_link_','CW_one_piece_','wheel_rim_','hip_stator_mount_',
                'knee_stator_cnc_','J4310_','H6215_','elastic_tyre_')):continue
        other=b.getObject(obj.Name)
        assert other is not None,obj.Name
        sa,sb=obj.Shape,other.Shape
        error=max(abs(getattr(sa.BoundBox,k)-getattr(sb.BoundBox,k)) for k in
                  ('XMin','YMin','ZMin','XMax','YMax','ZMax'))
        row=dict(name=obj.Name,volume_error_mm3=abs(sa.Volume-sb.Volume),
                 area_error_mm2=abs(sa.Area-sb.Area),bounds_error_mm=error,
                 expressions_same=list(obj.ExpressionEngine)==list(other.ExpressionEngine))
        row['pass']=row['volume_error_mm3']<1e-6 and row['area_error_mm2']<1e-6 and error<1e-6 and row['expressions_same']
        rows.append(row)
    report=dict(all_pass=all(r['pass'] for r in rows),objects=rows,
        parameters_unchanged={k:params[1][k] for k in FIELDS},
        allowed_changes='Rotor-flange dowel blind depth, custom shaft internal threads, combined bushes, hardware and local body mounting details; not claimed unchanged.',
        scope='Main five links per leg, hip seats, knee cups, rims, motors and tyres: volume, area, bounds, expressions. Exact source geometry retained for these objects.')
    (OUT/'preserved_geometry_review.json').write_text(json.dumps(report,indent=2)+'\n')
    assert report['all_pass'] and len(rows)>=26
    cad.App.closeDocument(a.Name);cad.App.closeDocument(b.Name)
    print('V81_PRESERVED_GEOMETRY',len(rows),flush=True)


if __name__=='__main__':main()
