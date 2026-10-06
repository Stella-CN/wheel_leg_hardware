"""V8.1 manufacturing details, standard hardware and modular assembly.

Run using the installed FreeCAD Python. V8 remains a read-only baseline.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil

import build_printable_robot as cad
import build_enclosed_robot as wheel
import build_sleeved_robot as native
import cad_v81_leg as leg
import cad_v81_coupling as coupling
import cad_v81_chassis as chassis
import cad_v81_payload as payload


def configure():
    out = cad.ROOT / 'mechanical/v8_1'
    out.mkdir(parents=True, exist_ok=True)
    parameters = json.loads((cad.ROOT / 'mechanical/v8/design_parameters.json').read_text())
    parameters.update(coupling.configure())
    parameters.update(revision='v8_1_modular_prototype', prototype_quantity=1,
        manufacturing_scope='Standard preferred hardware; preserve V8 kinematics, nesting and body exterior',
        validation_scope='Geometry and assembly-detail review, not jump/thermal/fatigue qualification',
        battery_source='source/battery/WHEELTEC_battery_user_drawing.png',battery_dimensions_xyz_mm=[85.6,44.5,61.6],
        battery_mass_g=400.,battery_mass_confirmed=False,battery_interface='battery_interface.json',
        battery_model='E626S',battery_model_confirmed_by_user=True)
    (out / 'design_parameters.json').write_text(json.dumps(parameters, indent=2) + '\n')
    cad.configure(out)
    cad.P.update(leg.configure())
    (out / 'design_parameters.json').write_text(json.dumps(cad.P, indent=2) + '\n')
    return out


def components():
    fixed = chassis.build_chassis()
    fixed.update(payload.designs())
    materials = chassis.materials()
    materials.update(payload.materials())
    designs = {'hip_stator_mount': (chassis.hip_stator_mount(), 'fixed', 'CNC')}
    designs.update(coupling.designs())
    designs.update(leg.designs())
    designs['wheel_rim'] = (wheel.wheel_rim(), 'wheel', 'CNC')
    hardware = coupling.hardware() + leg.hardware() + chassis.hip_hardware()
    global_hardware = chassis.chassis_hardware() + payload.hardware()
    return fixed, materials, designs, hardware, global_hardware


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--integration-check', action='store_true')
    args = parser.parse_args()
    out = configure()
    baseline = cad.ROOT / 'mechanical/v8'
    baseline_files = ('wheel_leg_v8.FCStd', 'design_parameters.json', 'part_manifest.json')
    before = {name: hashlib.sha256((baseline/name).read_bytes()).hexdigest() for name in baseline_files}
    for name in ('display', 'hi13r2'):
        shutil.copytree(baseline/'source'/name, out/'source'/name, dirs_exist_ok=True)
    leg.export_hardware()
    payload.export_notes(out)
    fixed, materials, designs, hardware, global_hardware = components()
    lengths = [100, 180, 215] if args.integration_check else list(range(100, 216, 5))
    doc = cad.build(designs, hardware=hardware,
        mirrored_print_parts=tuple(name for name in designs if name != 'wheel_rim'),
        hub_offset=cad.P['hub_stator_face_y']-164,
        knee_translation_y=cad.P['knee_motor_translation_y'],
        chassis_parts=fixed, chassis_materials=materials, chassis_process='CNC',
        global_hardware=global_hardware, payloads=payload.payloads(), coupons={},
        reference_stls=True, check_hardware_pairs=True, validation_lengths=lengths)
    native.native_hardware_check(doc, hardware, global_hardware)
    payload.install_camera_mesh(doc)
    after = {name: hashlib.sha256((baseline/name).read_bytes()).hexdigest() for name in baseline_files}
    assert before == after, 'V8 baseline was modified'
    (out/'baseline_preservation.json').write_text(json.dumps(dict(
        baseline='V8', before=before, after=after, unchanged=True), indent=2)+'\n')
    print('V81_BUILD_COMPLETE', flush=True)


if __name__ == '__main__':
    main()
