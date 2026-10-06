"""Package V8 only after current geometry, interface and mass gates pass."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import zipfile
from package_sleeved_robot import SCRIPTS as INHERITED_SCRIPTS

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'mechanical/v8'
NEW_SCRIPTS=('build_rounded_robot.py','cad_v8_chassis.py','cad_v8_payload.py',
    'cad_v8_display.py','cad_v7_imu.py','cad_v7_payload.py','cad_v7_display.py','cad_v7_chassis.py',
    'render_rounded_robot.py','orient_v8_prints.py','analyze_v8_motor_load.py',
    'analyze_v7_motor_load.py','draw_v8_interfaces.py','review_v8_unchanged_legs.py',
    'package_rounded_robot.py','export_v8_hardware.py')


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def read(name):return json.loads((OUT/name).read_text())


def verify_hashes(rows):
    for name,value in rows.items():assert digest(ROOT/'tools'/name)==value,name


def main():
    documents=read('documentation_review.json')
    assert not documents['failures']
    for name,value in documents['files_sha256'].items():assert digest(OUT/name)==value,name
    validation=read('validation.json');interfaces=read('payload_independent_review.json')
    chassis=read('chassis_review.json');maintenance=read('maintenance_access_review.json')
    legs=read('unchanged_legs_review.json');mass=read('mass_budget.json')
    native=read('motor_native_validation.json');manifest=read('part_manifest.json')
    assert validation['sampled_lengths']==list(range(100,216,5)) and not validation['collisions'] and validation['solids_valid']
    assert not read('joint_hardware_validation.json')['collisions']
    assert not read('native_hardware_placement_validation.json')['errors']
    assert interfaces['pass'] and interfaces['source_unchanged'] and not interfaces['failures']
    verify_hashes(interfaces['sources_after'])
    assert not chassis['collisions'] and not chassis['hardware_collisions']
    assert chassis['source_sha256']==digest(ROOT/'tools/cad_v8_chassis.py')
    beta=read('body_beta_motion_review.json')
    assert not beta['collisions'] and beta['source_unchanged'] and beta['leg_geometry_frozen_to_v6']
    verify_hashes(beta['source_sha256'])
    assert maintenance['source_unchanged_during_review'] and not maintenance['failures']
    assert all(maintenance['pass'].values());verify_hashes(maintenance['source_sha256'])
    assert legs['pass_all']
    for name,row in legs['source_hashes'].items():assert digest(ROOT/'tools'/name)==row['current']==row['released'],name
    display=read('display_interface.json')
    assert display['selected_variant_inches']==5 and display['outer_width_height_depth']==[122.,78.,14.5]
    assert display['manufacturer_device_mounting_holes'] is None
    verify_hashes(mass['source_CAD']['geometry_source_sha256'])
    assert native['maximum_COM_error_mm']<.001 and native['maximum_gravity_effort_error_Nm']<2e-5
    assert read('print_mesh_validation.json')['all_passed']
    for process,folder,suffix in (('CNC','cnc','.step'),('PETG','print','.stl')):
        assert {row['part']+suffix for row in manifest if row['process']==process}=={p.name for p in (OUT/folder).glob('*'+suffix)}
    for name in ('wheel_leg_v8.FCStd','wheel_leg_assembly.step','wheel_leg_assembly.stl',
                 'README.md','CHASSIS.md','DISPLAY.md','IMU.md','MASS.md','MOTOR_LOAD.md',
                 'body_beta_motion_review.json','previews/display_dimensions.svg'):
        assert (OUT/name).is_file(),name
    for name in ('assembly.png','body_oblique.png','electronics_layout.png','imu_mount.png'):
        assert (OUT/'previews'/name).stat().st_size>40000,name+' missing or blank'
    scripts=tuple(dict.fromkeys((*NEW_SCRIPTS,*INHERITED_SCRIPTS)))
    report=dict(revision='V8',geometry='Small-R5 rectangular body, removable complete front panel, GK-HD5 envelope, D435 above, official centredHI13R2',
        unchanged_legs=True,geometric_poses=len(validation['sampled_lengths']),
        body_beta_motion_report='body_beta_motion_review.json',payload_checks=len(interfaces['checks']),
        PETG_types=sum(row['process']=='PETG' for row in manifest),
        CNC_types=sum(row['process']=='CNC' for row in manifest),mass_kg=mass['total_kg'],
        assembly_stl=read('assembly_stl_report.json'),
        source_hashes={name:digest(ROOT/'tools'/name) for name in scripts},
        limits='Review prototype: confirm screen metal-rim contact, actual mass and plugs before manufacturing. No jump, thermal, fatigue or dynamic balance qualification.')
    (OUT/'release_review.json').write_text(json.dumps(report,indent=2)+'\n')
    files={p for p in OUT.rglob('*') if p.is_file() and not any(s.startswith('.') or s=='__pycache__' for s in p.relative_to(OUT).parts)
           and p.suffix not in ('.FCBak','.pyc') and p.name!='SHA256SUMS.json'}
    files.update(ROOT/'tools'/name for name in scripts)
    for folder in ('jetson','d435'):
        files.update(p for p in (ROOT/'mechanical/v6/source'/folder).rglob('*') if p.is_file() and p.suffix!='.pyc')
    files.update(ROOT/'mechanical/v6'/name for name in ('mass_budget.json','motor_load_analysis.json','design_parameters.json','release_review.json'))
    files.update(ROOT/'mechanical/v7'/name for name in ('mass_budget.json','motor_load_analysis.json','design_parameters.json'))
    files.update(p for p in (ROOT/'mechanical/v7/source/hi13r2').rglob('*') if p.is_file() and p.suffix!='.pyc')
    hashes={str(p.relative_to(ROOT)):digest(p) for p in sorted(files)}
    sums=OUT/'SHA256SUMS.json';sums.write_text(json.dumps(hashes,indent=2)+'\n');files.add(sums)
    destination=ROOT/'mechanical/wheel_leg_v8_bundle.zip'
    with zipfile.ZipFile(destination,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for path in sorted(files):archive.write(path,path.relative_to(ROOT))
    with zipfile.ZipFile(destination) as archive:
        assert archive.testzip() is None
        for path,value in hashes.items():assert hashlib.sha256(archive.read(path)).hexdigest()==value,path
    checksum=digest(destination)
    destination.with_suffix('.sha256').write_text(f'{checksum}  {destination.name}\n')
    print(json.dumps(dict(bundle=str(destination),files=len(files),bytes=destination.stat().st_size,
                         sha256=checksum,all_checks_passed=True),indent=2))


if __name__=='__main__':main()
