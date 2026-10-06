"""Read-only post-hub revision audit, preserving the completed 24-pose proof."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import time

import build_printable_robot as cad
from review_v82_integration import signature, same_signature, is_physical, bounds

OUT = cad.ROOT / 'mechanical/v8_2'
PREVIOUS = cad.ROOT / 'references/audit_baselines/v82_validated_pre_routes.FCStd'
TOL = .001


def intersects(a, b):
    return all(min(getattr(a, axis+'Max'), getattr(b, axis+'Max')) >
               max(getattr(a, axis+'Min'), getattr(b, axis+'Min'))
               for axis in ('X', 'Y', 'Z'))


def check(shapes, targets):
    result = []
    seen = set()
    for aname, a in shapes.items():
        for bname, b in targets.items():
            pair = tuple(sorted((aname, bname)))
            if aname == bname or pair in seen:
                continue
            seen.add(pair)
            if not intersects(a.BoundBox, b.BoundBox):
                continue
            volume = cad.interference_volume(a, b)
            if volume > TOL:
                result.append(dict(a=aname, b=bname, volume_mm3=volume))
    return result


def swept_box(shape, length=100.):
    b = shape.BoundBox
    return cad.Part.makeBox(b.XLength+length, b.YLength, b.ZLength,
                            cad.V(b.XMin-length, b.YMin, b.ZMin))


def main():
    started = time.monotonic()
    previous_report = json.loads((OUT/'source/electrical_validation_pre_hub_update.json').read_text())
    assert previous_report['mode'] == 'full' and previous_report['all_pass']
    assert hashlib.sha256(PREVIOUS.read_bytes()).hexdigest() == previous_report['native_sha256']
    old = cad.App.openDocument(str(PREVIOUS))
    new = cad.App.openDocument(str(OUT/'wheel_leg_v8_2.FCStd'))
    try:
        for doc in (old, new):
            doc.Parameters.LegLength = 180
            doc.Parameters.Beta = 0
            doc.recompute()
        physical = [o for o in new.Objects if is_physical(o)]
        solids = [o for o in physical if o.TypeId == 'Part::Feature']
        old_names = {o.Name for o in old.Objects if is_physical(o)}
        expected = {'chassis_front_shell', 'chassis_rear_cover', 'USB_hub_rear_clamp',
                    'V82_hub_clamp_screw_0', 'V82_hub_clamp_nut_0',
                    'V82_hub_clamp_screw_1', 'V82_hub_clamp_nut_1'}
        comparisons = []
        signatures = []
        for obj in physical:
            signatures.append(signature(obj))
            original = old.getObject(obj.Name)
            if original:
                comparisons.append(same_signature(signature(original), signatures[-1]))
        changes = {row['name'] for row in comparisons if not row['passed']}
        unexpected_changes = sorted(changes-expected)
        missing = sorted(old_names-{o.Name for o in physical})
        added = sorted({o.Name for o in physical}-old_names)
        print('CHANGED', sorted(changes), flush=True)
        front_added = new.chassis_front_shell.Shape.cut(old.chassis_front_shell.Shape).Volume
        front_removed = old.chassis_front_shell.Shape.cut(new.chassis_front_shell.Shape).Volume
        all_shapes = {o.Name:o.Shape for o in solids}
        changed_shapes = {name:all_shapes[name] for name in changes}
        static = check(changed_shapes, all_shapes)
        print('STATIC', static, flush=True)
        # Only the seven final changed objects need another moving-neighbour
        # audit. All other new/old pairs retain the completed 210795 checks.
        motion_rows = []
        moving_names = [o.Name for o in solids if getattr(o, 'KinematicRole', 'fixed') != 'fixed']
        dynamic_delta = {name for name in changes if name != 'chassis_front_shell'}
        fixed_changed = {name:new.getObject(name).Shape for name in dynamic_delta}
        for length in range(100,216,5):
            new.Parameters.LegLength = length
            new.recompute()
            targets = {name:new.getObject(name).Shape for name in moving_names}
            hits = check(fixed_changed, targets)
            motion_rows.append(dict(length_mm=length, collisions=hits))
        new.Parameters.LegLength = 180
        new.recompute()
        print('DELTA_MOTION_DONE', flush=True)
        module_names = {'chassis_rear_cover', 'USB_hub_rear_clamp',
                        'DC_charge_replaceable_plate', 'USB_hub_104x30x10'}
        module_names.update(o.Name for o in solids
                            if o.Name.startswith(('V82_hub_', 'V82_DC_plate_')))
        removed = {o.Name for o in solids if o.Name.startswith('rear_cover_M3x12_')}
        removed.update(('shoulder_fairing_right', 'shoulder_fairing_left'))
        removed.update(o.Name for o in solids if o.Name.startswith('shoulder_') and '_M3x20_' in o.Name)
        targets = {o.Name:o.Shape for o in solids if o.Name not in module_names|removed}
        # The added inward fixtures are bounded separately from the original
        # hollow enclosure. Splitting at X-86.1 keeps DC bosses behind the
        # rear frame and proves the hub hardware through its opening.
        original_cover = cad.Part.read(str(cad.ROOT/'mechanical/v8_1/step/chassis_rear_cover.step'))
        added_cover = new.chassis_rear_cover.Shape.cut(original_cover)
        addition_parts = {
            'rear_cover_added_behind_frame': added_cover.common(cad.Part.makeBox(113.9,400,400,cad.V(-200,-200,-200))),
            'rear_cover_added_through_frame': added_cover.common(cad.Part.makeBox(200,400,400,cad.V(-86.1,-200,-200))),
        }
        swept = {name:swept_box(shape) for name,shape in addition_parts.items()
                 if not shape.isNull() and shape.Volume > TOL}
        swept.update({name:swept_box(new.getObject(name).Shape) for name in module_names
                      if name != 'chassis_rear_cover'})
        continuous = check(swept, targets)
        print('INSERTION_CONTINUOUS_NEW_PARTS', continuous, flush=True)
        samples = []
        for offset in (0., -.25, -1., -2., -4., -8., -16., -32., -64., -100.):
            shapes = {}
            for name in module_names:
                shape = new.getObject(name).Shape.copy()
                shape.translate(cad.V(offset,0,0))
                shapes[name] = shape
            hits = check(shapes, targets)
            samples.append(dict(offset_x_mm=offset, collisions=hits))
            print('INSERTION_SAMPLE', offset, len(hits), flush=True)
        metrics = json.dumps(signatures, sort_keys=True, separators=(',',':'))
        (OUT/'physical_geometry_signatures.json').write_text(json.dumps(signatures,ensure_ascii=False,indent=2)+'\n')
        report = dict(
            scope='Final seven-object hub update and two side holes, inheriting unchanged-pair full-motion evidence. Routing allowances explicitly separate.',
            prior_full_evidence='source/electrical_validation_pre_hub_update.json',
            prior_native_sha256=previous_report['native_sha256'],
            physical_geometry_metrics_sha256=hashlib.sha256(metrics.encode()).hexdigest(),
            signature_scope='Volume, area, bounds, placement, expression engine, solid count; mesh topology hashed. Independent of visibility and colour. Metrics are identity checks, not a mathematical uniqueness hash for arbitrary solids.',
            signature_file='physical_geometry_signatures.json',
            physical_objects=len(physical), routing_objects_excluded=[o.Name for o in new.Objects if getattr(o,'Material','')=='routing_allowance'],
            expected_changed=sorted(expected), actual_changed=sorted(changes),
            unexpected_changes=unexpected_changes, missing_objects=missing, added_physical_objects=added,
            unchanged_count=sum(row['passed'] for row in comparisons), comparisons=comparisons,
            front_shell_pure_subtraction=dict(added_volume_mm3=front_added,removed_volume_mm3=front_removed,passed=front_added<TOL),
            changed_static_collisions=static, delta_motion_checks=motion_rows,
            insertion=dict(direction='Rearward withdrawal/forward mating along X',travel_mm=100,
                moving_module_names=sorted(module_names),removed_before_insertion=sorted(removed),
                continuous_scope='Conservative continuous swept boxes for every newly added rear-module component and both partitions of added rear-cover material. Original hollow shell checked at the explicit discrete offsets.',
                new_part_swept_bounds_mm={name:bounds(shape.BoundBox) for name,shape in swept.items()},
                new_part_continuous_collisions=continuous,complete_module_samples=samples,
                limitations='No attached cable/plug slack, hand/tool motion or flexible deformation. Discrete whole-shell samples are not a continuous whole-shell proof.'),
            threshold_mm3=TOL,elapsed_seconds=round(time.monotonic()-started,3))
        report['all_pass'] = (not unexpected_changes and not missing and not added and front_added<TOL
            and not static and all(not row['collisions'] for row in motion_rows)
            and not continuous and all(not row['collisions'] for row in samples))
        (OUT/'electrical_final_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        print('FINAL_DELTA_RESULT', report['all_pass'], flush=True)
    finally:
        cad.App.closeDocument(new.Name)
        cad.App.closeDocument(old.Name)


if __name__ == '__main__':
    main()
