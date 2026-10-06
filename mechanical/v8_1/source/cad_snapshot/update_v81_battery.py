"""Replace only V8.1 battery interfaces and check their entire CAD neighborhood."""
from __future__ import annotations

import hashlib
import json
import shutil
import build_printable_robot as cad
import cad_v81_battery as battery
import cad_v81_payload as payload

OUT = cad.ROOT / 'mechanical/v8_1'


def signature(obj):
    s = obj.Shape
    bb = s.BoundBox
    return dict(volume=s.Volume, area=s.Area, expressions=list(obj.ExpressionEngine),
                bounds=[getattr(bb,a) for a in ('XMin','YMin','ZMin','XMax','YMax','ZMax')])


def main():
    cad.configure(OUT)
    doc = cad.App.openDocument(str(OUT/'wheel_leg_v8_1.FCStd'))
    doc.Parameters.LegLength=180
    doc.Parameters.Beta=0
    doc.recompute()
    new_name,new_shape,mass,note=battery.payload()
    before={o.Name:signature(o) for o in doc.Objects if o.TypeId=='Part::Feature'
            and o.Name not in ('battery_tray','Battery_400g_envelope',new_name)}
    old_names=[o.Name for o in doc.Objects if o.Name.startswith('Battery_')]
    assert len(old_names)==1, old_names
    tray=battery.tray()
    assert tray.isValid() and len(tray.Solids)==1
    doc.battery_tray.Shape=cad.Part.makeCompound([tray])
    doc.battery_tray.ManufacturingNote='WHEELTEC drawing85.6x61.6x42; overall44.5 including magnetic base. Mechanical strap retention; see BATTERY.md.'
    doc.removeObject(old_names[0])
    obj=cad.put(doc,doc.M04,new_name,new_shape,'fixed','payload',None,note)
    obj.addProperty('App::PropertyFloat','BudgetMassGrams','Manufacturing')
    obj.BudgetMassGrams=mass
    obj.addProperty('App::PropertyString','AssemblyModule','Manufacturing')
    obj.AssemblyModule='M04 电器仓子模块'
    doc.recompute()
    collisions=[]
    checked=0
    for length in range(100,216,5):
        doc.Parameters.LegLength=length
        doc.recompute()
        changed=[doc.battery_tray,doc.getObject(new_name)]
        for a in changed:
            for b in doc.Objects:
                if b.TypeId!='Part::Feature' or b.Name==a.Name:
                    continue
                if a.Name==new_name and b.Name=='battery_tray':
                    continue
                if length!=100 and getattr(b,'KinematicRole','fixed')=='fixed':
                    continue
                checked+=1
                volume=cad.interference_volume(a.Shape,b.Shape)
                if volume>.001:
                    collisions.append(dict(length_mm=length,a=a.Name,b=b.Name,volume_mm3=volume))
        print('BATTERY_SWEEP',length,'collisions',len(collisions),flush=True)
    doc.Parameters.LegLength=180
    doc.recompute()
    unchanged=[]
    for name,s in before.items():
        t=signature(doc.getObject(name))
        passed=(abs(s['volume']-t['volume'])<1e-6 and abs(s['area']-t['area'])<1e-6
                and s['expressions']==t['expressions']
                and max(abs(a-b) for a,b in zip(s['bounds'],t['bounds']))<1e-6)
        unchanged.append(dict(name=name,passed=passed))
    report=dict(source_sha256=hashlib.sha256((cad.ROOT/'tools/cad_v81_battery.py').read_bytes()).hexdigest(),
        sampled_lengths_mm=list(range(100,216,5)),beta_deg=0,threshold_mm3=.001,
        collision_pair_checks=checked,collisions=collisions,unchanged_objects=unchanged,
        all_pass=not collisions and all(r['passed'] for r in unchanged),
        scope='Changed battery tray and drawing envelope checked against all native solid objects; previously checked unmodified pairs retain their earlier results. Static relative pairs checked once. No cables or real connector qualification.')
    (OUT/'battery_integration_review.json').write_text(json.dumps(report,indent=2)+'\n')
    assert report['all_pass'], 'Battery integration failed; document not saved'
    manifest=json.loads((OUT/'part_manifest.json').read_text())
    updated=cad.export_part('battery_tray',tray,'PETG',1,True)
    manifest=[updated if r['part']=='battery_tray' else r for r in manifest]
    (OUT/'part_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    payload.export_notes(OUT)
    parameters=json.loads((OUT/'design_parameters.json').read_text())
    parameters.update(battery_source='source/battery/WHEELTEC_battery_user_drawing.png',
        battery_dimensions_xyz_mm=[85.6,44.5,61.6],battery_mass_g=mass,
        battery_mass_confirmed=False,battery_interface='battery_interface.json')
    (OUT/'design_parameters.json').write_text(json.dumps(parameters,indent=2)+'\n')
    doc.save()
    manufactured=[o for o in doc.Objects if o.TypeId=='Part::Feature' and getattr(o,'Material','') in ('PETG','CNC')]
    cad.Part.export(manufactured,str(OUT/'wheel_leg_structure.step'))
    cad.Part.export([o for o in doc.Objects if o.TypeId=='Part::Feature'],str(OUT/'wheel_leg_assembly.step'))
    validation=json.loads((OUT/'validation.json').read_text())
    if 'battery_update_evidence' not in validation:
        shutil.copy2(OUT/'validation.json',OUT/'pre_battery_pair_validation.json')
    validation.update(battery_update_evidence='battery_integration_review.json',
        scope='Original 24-pose pair sweep plus changed battery/tray against every native solid. See battery_integration_review.json and unchanged-object evidence. Beta=0, discrete nominal rigid-body geometry only.')
    (OUT/'validation.json').write_text(json.dumps(validation,indent=2)+'\n')
    cad.App.closeDocument(doc.Name)
    print('V81_BATTERY_NATIVE_UPDATED',flush=True)


if __name__=='__main__':
    main()
