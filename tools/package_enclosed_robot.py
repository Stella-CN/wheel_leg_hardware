"""Package the reviewed V5 outputs and their local rebuild dependencies."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'mechanical/v5'
SCRIPTS = (
    'build_enclosed_robot.py', 'cad_v5_leg.py', 'cad_v5_coupling.py',
    'cad_v5_chassis.py', 'cad_v5_payload.py', 'analyze_v5_motor_load.py',
    'render_enclosed_robot.py', 'build_printable_robot.py', 'cad_chassis.py',
    'cad_v3_profiles.py', 'build_reference_robot.py', 'build_nested_robot.py',
    'render_nested_robot.py', 'render_compact_robot.py',
    'export_robot_assembly_stl.py', 'validate_print_meshes.py',
    'package_enclosed_robot.py',
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    validation=json.loads((OUT/'validation.json').read_text())
    placement=json.loads((OUT/'native_hardware_placement_validation.json').read_text())
    native=json.loads((OUT/'distributed_gravity_native_review.json').read_text())
    assert validation['sampled_lengths']==list(range(120,226,5))
    assert not validation['collisions'] and validation['solids_valid']
    assert not placement['errors']
    assert native['passed']
    assert json.loads((OUT/'print_mesh_validation.json').read_text())['all_passed']
    assert len(list((OUT/'cnc').glob('*.step')))==22
    assert len(list((OUT/'print').glob('*.stl')))==5
    # Require all user-facing deliverables before creating the bundle.
    for name in ('wheel_leg_v5.FCStd','wheel_leg_assembly.stl',
                 'part_breakdown.FCStd','MOTOR_LOAD.md','STRUCTURAL_SCREENING.md',
                 'previews/assembly.png','previews/OA_inside_OB.png'):
        assert (OUT/name).is_file(), name
    report=dict(revision='V5',
        main_geometry='22 mm nested leg;14.9 mm two-piece coupling;W solid bearing face with original motor side outlet',
        geometric_poses=len(validation['sampled_lengths']),
        geometric_collisions=len(validation['collisions']),
        hardware_objects=placement['hardware_objects'],
        native_gravity_review=native,
        mass_kg=json.loads((OUT/'mass_budget.json').read_text())['total_kg'],
        assembly_stl=json.loads((OUT/'assembly_stl_report.json').read_text()),
        source_hashes={name:digest(ROOT/'tools'/name) for name in SCRIPTS},
        scope='Reviewable mechanical prototype; discrete geometry and first-pass load calculations. No jump, fatigue, thermal, cable-routing or manufacturing-process qualification.')
    (OUT/'release_review.json').write_text(json.dumps(report,indent=2)+'\n')
    files=[p for p in OUT.rglob('*') if p.is_file() and
           not any(s.startswith('.') or s=='__pycache__' for s in p.relative_to(OUT).parts)
           and p.suffix not in ('.FCBak','.pyc') and p.name!='SHA256SUMS.json']
    files += [ROOT/'tools'/name for name in SCRIPTS]
    hashes={str(p.relative_to(ROOT)):digest(p) for p in sorted(files)}
    sums=OUT/'SHA256SUMS.json'
    sums.write_text(json.dumps(hashes,indent=2)+'\n')
    files.append(sums)
    target=ROOT/'mechanical/wheel_leg_v5_bundle.zip'
    with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for path in sorted(files):
            archive.write(path,path.relative_to(ROOT))
    with zipfile.ZipFile(target) as archive:
        assert archive.testzip() is None
        for name,expected in hashes.items():
            assert hashlib.sha256(archive.read(name)).hexdigest()==expected,name
    checksum=digest(target)
    target.with_suffix('.sha256').write_text(f'{checksum}  {target.name}\n')
    print(json.dumps(dict(bundle=str(target),files=len(files),bytes=target.stat().st_size,
                          sha256=checksum,crc_and_hashes_verified=True),indent=2))


if __name__=='__main__':
    main()
