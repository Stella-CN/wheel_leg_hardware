"""V5: enclosed nested CNC leg, lighter removable electronics enclosure.

Run with the installed FreeCAD Python. Original motor references are required
in ../references. Previous manufacturing revisions are not overwritten.
"""
from __future__ import annotations

import argparse
import json

import build_printable_robot as cad
import cad_v5_chassis as chassis
import cad_v5_coupling as coupling
import cad_v5_leg as leg
import cad_v5_payload as payload


def configure():
    out = cad.ROOT / 'mechanical/v5'
    out.mkdir(parents=True, exist_ok=True)
    parameters = dict(revision='v5_enclosed_nested', units='mm', rod_length=130.,
        crank_length=35., leg_length=183.8477631085, beta_deg=0.,
        operating_leg_length=[120.,225.], print_bed=[220.,220.,250.],
        material='6061-T6 load-bearing structure / PETG electronics enclosure',
        cnc_material='6061-T6 aluminum', nozzle=.4, layer_height=.2,
        hip_stator_face_y=72., hip_output_face_y=73.,
        validation_scope='discrete geometric checks and approximate motor sizing; no certified jump/impact/fatigue rating',
        reference_image='Supplied annotated mechanism; no hip roll; wheel at W',
        profile='curved CNC frame, complete outer OB cover, internal OA fork')
    parameters.update(coupling.configure())
    path = out / 'design_parameters.json'
    path.write_text(json.dumps(parameters, indent=2)+'\n')
    cad.configure(out)
    cad.P.update(leg.configure())
    cad.P['wheel_center_y'] = cad.P['hub_stator_face_y'] + 26
    cad.P['wheel_track'] = cad.P['wheel_center_y']*2
    path.write_text(json.dumps(cad.P, indent=2)+'\n')
    return out


def wheel_rim():
    """Turned/milled aluminum rim with two tyre lips and the actual H pilot."""
    face = cad.P['hub_stator_face_y']
    body_inner = face + 10
    rotor_face = face + 44.5
    # A turned 3mm hoop carries the tyre. The motor has radial clearance;
    # there is no need to fill the entire motor-to-tyre annulus with aluminum.
    ring = cad.cut(cad.cyl(43, body_inner-2, 36.5),
                   cad.cyl(40, body_inner-3, 39))
    lips = [cad.cut(cad.cyl(45, y, 2), cad.cyl(40, y-1, 4))
            for y in (body_inner-2, body_inner+32)]
    front = cad.cyl(43, rotor_face-.8, 4.8)
    shape = cad.union(ring, front, *lips)
    shape = cad.cut(shape, cad.cyl(16.525, rotor_face-1, 1))
    shape = cad.bolt_pattern(shape, 14, 6, 30, rotor_face-1, 7)
    for x, z in cad.points(28, 6, 0):
        shape = cad.cut(shape, cad.cyl(7, rotor_face-1, 7, x, z))
    return shape


def native_hardware_check(doc, hardware, global_hardware):
    checks = []
    for name, shape, role in hardware:
        checks.extend((f'{name}_{side}', shape if side=='right' else cad.mirror(shape), role)
                      for side in ('right','left'))
    checks.extend(global_hardware)
    errors = []
    lengths = (120, cad.P['leg_length'], 225)
    for length in lengths:
        doc.Parameters.LegLength = length
        doc.recompute()
        for name, shape, role in checks:
            matches = doc.getObjectsByLabel(name.replace('_',' '))
            if len(matches)!=1:
                raise ValueError(f'Expected one native hardware: {name}')
            expected = cad.transform(shape, role, cad.pose(length))
            error = (matches[0].Shape.BoundBox.Center-expected.BoundBox.Center).Length
            if error>.001:
                errors.append(dict(part=name, length_mm=length, error_mm=error))
    doc.Parameters.LegLength = cad.P['leg_length']
    doc.recompute()
    doc.save()
    (cad.OUT/'native_hardware_placement_validation.json').write_text(json.dumps(dict(
        hardware_objects=len(checks), poses_mm=lengths, placement_tolerance_mm=.001,
        errors=errors), indent=2)+'\n')
    if errors:
        raise ValueError('Native hardware placement mismatch')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--integration-check', action='store_true',
                        help='Three integration poses; use a normal run for all22 poses.')
    args = parser.parse_args()
    configure()
    fixed_parts = chassis.build_chassis()
    fixed_parts['D435_embedded_bracket'] = payload.camera_bracket()
    materials = chassis.materials()
    materials['D435_embedded_bracket'] = 'PETG'
    designs = {'hip_stator_mount': (chassis.hip_stator_mount(),'fixed','CNC')}
    designs.update(coupling.designs())
    designs.update(leg.designs())
    designs['wheel_rim'] = (wheel_rim(),'wheel','CNC')
    leg.export_hardware()
    cad.cyl(2, 0, 9).exportStep(str(cad.OUT/'metal_hardware/dowel_D4_L9.step'))
    payload.export_notes()
    local_hardware = coupling.hardware() + leg.hardware() + chassis.hip_hardware()
    global_hardware = chassis.chassis_hardware() + payload.camera_hardware()
    # All handed CNC shapes receive their own file; orientation can matter to
    # countersinks and pilot faces even if the flat outline looks symmetric.
    handed = tuple(name for name in designs if name!='wheel_rim')
    doc = cad.build(designs, hardware=local_hardware, mirrored_print_parts=handed,
        hub_offset=cad.P['hub_stator_face_y']-164,
        knee_translation_y=cad.P['knee_motor_translation_y'],
        chassis_parts=fixed_parts, chassis_materials=materials, chassis_process='CNC',
        global_hardware=global_hardware, payloads=payload.payloads(),
        coupons={}, reference_stls=True, check_hardware_pairs=True,
        validation_lengths=[120,cad.P['leg_length'],225] if args.integration_check else None)
    native_hardware_check(doc, local_hardware, global_hardware)
    print('V5_BUILD_COMPLETE', flush=True)


if __name__=='__main__':
    main()
