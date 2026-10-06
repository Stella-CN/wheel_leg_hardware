"""Package V6 artifacts after geometry, load and printable-mesh checks."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'mechanical/v6'
SCRIPTS=(
    'build_sleeved_robot.py','cad_v6_leg.py','cad_v6_chassis.py','cad_v6_payload.py','cad_v6_jetson_mount.py',
    'analyze_v6_proportions.py','analyze_v6_motor_load.py','render_sleeved_robot.py',
    'inspect_v6_jetson.py','inspect_v6_d435_mesh.py','package_sleeved_robot.py',
    'orient_v6_prints.py',
    'build_enclosed_robot.py','cad_v5_leg.py','cad_v5_chassis.py','cad_v5_coupling.py',
    'cad_v5_payload.py','build_printable_robot.py','cad_chassis.py','cad_v3_profiles.py',
    'build_reference_robot.py','build_nested_robot.py','render_nested_robot.py',
    'render_compact_robot.py','export_robot_assembly_stl.py','validate_print_meshes.py',
)


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda:source.read(1024*1024),b''):
            h.update(chunk)
    return h.hexdigest()


def read(name):
    return json.loads((OUT/name).read_text())


def main():
    validation=read('validation.json')
    placement=read('native_hardware_placement_validation.json')
    interface=read('O_interface_independent_review.json')
    chassis=read('chassis_review.json')
    body_interfaces=read('chassis_payload_independent_review.json')
    maintenance=read('maintenance_access_review.json')
    native=read('motor_native_validation.json')
    manifest=read('part_manifest.json')
    assert validation['sampled_lengths']==list(range(100,216,5))
    assert not validation['collisions'] and validation['solids_valid']
    assert not placement['errors']
    assert not chassis['collisions'] and not chassis['hardware_collisions']
    assert body_interfaces['source_unchanged_during_review']
    assert not body_interfaces['failures'] and all(body_interfaces['pass'].values())
    for name,expected in body_interfaces['source_sha256'].items():
        assert digest(ROOT/'tools'/name)==expected
    assert maintenance['source_unchanged_during_review']
    assert not maintenance['failures'] and all(maintenance['pass'].values())
    assert interface['nominal_180_assembly_pass']
    assert interface['angular_stops_precede_body_collisions_pass']
    assert interface['angular_endpoint_AC_clearance_pass']
    assert interface['source_unchanged_during_review']
    assert interface['source_sha256']==digest(ROOT/'tools/cad_v6_leg.py')
    assert native['maximum_COM_error_mm']<=.001
    assert native['maximum_angle_error_deg']<=1e-6
    assert native['maximum_gravity_effort_error_Nm']<=2e-5
    mass=read('mass_budget.json')
    for name,expected in mass['source_CAD']['geometry_source_sha256'].items():
        assert digest(ROOT/'tools'/name)==expected
    assert read('print_mesh_validation.json')['all_passed']
    for process,folder,extension in (('CNC','cnc','.step'),('PETG','print','.stl')):
        expected={row['part']+extension for row in manifest if row['process']==process}
        assert expected=={p.name for p in (OUT/folder).glob('*'+extension)}
    for name in ('wheel_leg_v6.FCStd','wheel_leg_assembly.stl','part_breakdown.FCStd',
                 'README.md','CHASSIS.md','INTERFACES.md','MOTOR_LOAD.md',
                 'previews/assembly.png','previews/electronics_layout.png',
                 'previews/OB_shell_inside.png','previews/assembly_stage_3.png'):
        assert (OUT/name).is_file(),name
    report=dict(revision='V6',
        main_geometry='D57 pocketed OB shell; OB/AC130, BW105, OA/BC45;23mm main width',
        geometric_poses=len(validation['sampled_lengths']),collisions=validation['collisions'],
        hardware_objects=placement['hardware_objects'],native_motor_validation=native,
        body_interface_checks=body_interfaces['pass'],
        maintenance_checks=maintenance['pass'],
        mass_kg=mass['total_kg'],
        assembly_stl=read('assembly_stl_report.json'),
        source_hashes={name:digest(ROOT/'tools'/name) for name in SCRIPTS},
        limits='Reviewable prototype. No jump, fatigue, thermal or manufacturing qualification; camera mesh is a dated official visualization with documented1mm depth discrepancy.')
    (OUT/'release_review.json').write_text(json.dumps(report,indent=2)+'\n')
    files=[p for p in OUT.rglob('*') if p.is_file()
           and not any(s.startswith('.') or s=='__pycache__' for s in p.relative_to(OUT).parts)
           and p.suffix not in ('.FCBak','.pyc') and p.name!='SHA256SUMS.json']
    files += [ROOT/'tools'/name for name in SCRIPTS]
    files += [ROOT/'mechanical/v5'/name for name in ('mass_budget.json','motor_load_analysis.json')]
    hashes={str(p.relative_to(ROOT)):digest(p) for p in sorted(files)}
    sums=OUT/'SHA256SUMS.json'
    sums.write_text(json.dumps(hashes,indent=2)+'\n');files.append(sums)
    target=ROOT/'mechanical/wheel_leg_v6_bundle.zip'
    with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for path in sorted(files):archive.write(path,path.relative_to(ROOT))
    with zipfile.ZipFile(target) as archive:
        assert archive.testzip() is None
        for name,expected in hashes.items():
            assert hashlib.sha256(archive.read(name)).hexdigest()==expected,name
    checksum=digest(target)
    target.with_suffix('.sha256').write_text(f'{checksum}  {target.name}\n')
    print(json.dumps(dict(bundle=str(target),files=len(files),bytes=target.stat().st_size,
                          sha256=checksum,crc_and_hashes_verified=True),indent=2))


if __name__=='__main__':main()
