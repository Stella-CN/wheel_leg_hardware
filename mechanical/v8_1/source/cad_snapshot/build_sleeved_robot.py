"""V6: a D57 nested motor carrier and pocketed outer OB arm, 130/105/45 links.

Uses the installed FreeCAD Python API and original motor solids. The motor
mounting datums, coupling and wheels are retained; the entire body is rebuilt.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil

import build_printable_robot as cad
import build_enclosed_robot as previous
import cad_v6_chassis as chassis
import cad_v5_coupling as coupling
import cad_v6_payload as payload


def configure():
    out=cad.ROOT/'mechanical/v6'
    out.mkdir(parents=True,exist_ok=True)
    parameters=dict(revision='v6_sleeved_OB',units='mm',rod_length=130.,
        lower_length=105.,crank_length=45.,leg_length=180.,beta_deg=0.,
        operating_leg_length=[100.,215.],print_bed=[220.,220.,250.],
        material='6061-T6 load-bearing structure / PETG electronics enclosure',
        cnc_material='6061-T6 aluminum',nozzle=.4,layer_height=.2,
        hip_stator_face_y=72.,hip_output_face_y=73.,
        motor_configuration='J4310 24V V1.1, confirmed by user',
        validation_scope='discrete geometric checks and distributed-gravity sizing; not jump/impact/fatigue qualification',
        reference_image='Original user annotated mechanism, interpreted with latest V6 assembly sequence',
        profile='D57 inner stator carrier, one-piece pocketed outer OB shell, OA through nested circular shoulders')
    parameters.update(coupling.configure())
    (out/'design_parameters.json').write_text(json.dumps(parameters,indent=2)+'\n')
    cad.configure(out)
    return out


def apply_leg_parameters(leg):
    cad.P.update(leg.configure())
    cad.P['wheel_center_y']=cad.P['hub_stator_face_y']+26
    cad.P['wheel_track']=2*cad.P['wheel_center_y']
    (cad.OUT/'design_parameters.json').write_text(json.dumps(cad.P,indent=2)+'\n')


def native_hardware_check(doc,hardware,global_hardware):
    rows=[]
    for name,shape,role in hardware:
        rows.extend((f'{name}_{side}',shape if side=='right' else cad.mirror(shape),role)
                    for side in ('right','left'))
    rows.extend(global_hardware)
    errors=[]
    low,high=cad.P['operating_leg_length']
    lengths=(low,cad.P['leg_length'],high)
    for length in lengths:
        doc.Parameters.LegLength=length;doc.recompute()
        for name,shape,role in rows:
            matches=doc.getObjectsByLabel(name.replace('_',' '))
            if len(matches)!=1:
                raise ValueError(f'Expected one hardware instance: {name}')
            expected=cad.transform(shape,role,cad.pose(length))
            error=(matches[0].Shape.BoundBox.Center-expected.BoundBox.Center).Length
            if error>.001:
                errors.append(dict(part=name,length_mm=length,error_mm=error))
    doc.Parameters.LegLength=cad.P['leg_length'];doc.recompute();doc.save()
    (cad.OUT/'native_hardware_placement_validation.json').write_text(json.dumps(dict(
        hardware_objects=len(rows),poses_mm=lengths,placement_tolerance_mm=.001,
        errors=errors),indent=2)+'\n')
    if errors:
        raise ValueError('Native hardware expression mismatch')


def archive_retired_parts(fixed,materials,designs):
    """Preserve retired generated parts outside the current release tree."""
    manifest=cad.OUT/'part_manifest.json'
    if not manifest.is_file():
        return
    expected={name:materials.get(name,'CNC') for name in fixed}
    for name,(_,_,process) in designs.items():
        expected[name]=process
        if name!='wheel_rim':
            expected[name+'_left']=process
    retired=[]
    rows=json.loads(manifest.read_text())
    # A stopped export can write these files before replacing the manifest.
    known={row['part'] for row in rows}
    for name in ('chassis_front_fairing','chassis_rear_fairing',
                 'chassis_upper_shell','chassis_lid'):
        if name not in known:
            rows.append(dict(part=name,process='PETG'))
    for row in rows:
        name=row['part']
        if expected.get(name)==row['process']:
            continue
        for folder,extension in (('cnc','.step'),('step','.step'),
                                 ('stl','.stl'),('print','.stl')):
            path=cad.OUT/folder/(name+extension)
            if path.is_file():
                retired.append(path)
    if retired:
        import tempfile
        archive=Path(tempfile.mkdtemp(prefix='wheel_leg_v6_retired_'))
        for path in retired:
            target=archive/path.relative_to(cad.OUT)
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.move(path,target)
        print(f'RETIRED_EXPORTS_ARCHIVED {archive}',flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--integration-check',action='store_true')
    args=parser.parse_args()
    configure()
    import cad_v6_leg as leg
    apply_leg_parameters(leg)
    fixed=chassis.build_chassis()
    fixed['D435_embedded_bracket']=payload.camera_bracket()
    materials=chassis.materials();materials['D435_embedded_bracket']='PETG'
    designs={'hip_stator_mount':(chassis.hip_stator_mount(),'fixed','CNC')}
    designs.update(coupling.designs());designs.update(leg.designs())
    designs['wheel_rim']=(previous.wheel_rim(),'wheel','CNC')
    archive_retired_parts(fixed,materials,designs)
    leg.export_hardware()
    cad.cyl(2,0,9).exportStep(str(cad.OUT/'metal_hardware/dowel_D4_L9.step'))
    payload.export_notes()
    hardware=coupling.hardware()+leg.hardware()+chassis.hip_hardware()
    global_hardware=chassis.chassis_hardware()+payload.camera_hardware()
    low,high=cad.P['operating_leg_length']
    lengths=([low,cad.P['leg_length'],high] if args.integration_check else
             list(range(int(low),int(high)+1,5)))
    doc=cad.build(designs,hardware=hardware,
        mirrored_print_parts=tuple(name for name in designs if name!='wheel_rim'),
        hub_offset=cad.P['hub_stator_face_y']-164,
        knee_translation_y=cad.P['knee_motor_translation_y'],
        chassis_parts=fixed,chassis_materials=materials,chassis_process='CNC',
        global_hardware=global_hardware,payloads=payload.payloads(),coupons={},
        reference_stls=True,check_hardware_pairs=True,validation_lengths=lengths)
    native_hardware_check(doc,hardware,global_hardware)
    payload.install_camera_mesh(doc)
    chassis.export_review(cad.OUT)
    # Carry the unchanged subsystem evidence with explicit provenance.
    source=cad.ROOT/'mechanical/v5'
    inherited=['chassis_motor_interface_validation.json',
               'coupling_review.md','coupling_review.json','coupling_fasteners.json',
               'coupling_local_review.FCStd']
    for name in inherited:
        if (source/name).is_file():
            shutil.copy2(source/name,cad.OUT/name)
        elif not (cad.OUT/name).is_file():
            raise FileNotFoundError(f'Missing inherited subsystem evidence: {name}')
    (cad.OUT/'inherited_subsystems.json').write_text(json.dumps(dict(
        source_revision='V5',unchanged_parts='Hip motor mounting datums, hip-knee coupling and wheel design; V6 chassis has its own report',
        source_files=inherited,
        note='Inherited reports retain their V5 subsystem titles. V6 whole-robot validation is in validation.json.'),indent=2)+'\n')
    print('V6_BUILD_COMPLETE',flush=True)


if __name__=='__main__':
    main()
