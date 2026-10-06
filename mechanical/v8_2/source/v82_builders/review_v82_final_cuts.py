"""Prove final clearance edits only remove material, and close the audit chain."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import shutil

import build_printable_robot as cad
from review_v82_integration import is_physical, signature, same_signature
from review_v82_final_delta import check

OUT = cad.ROOT/'mechanical/v8_2'
SOURCE = OUT/'source'


def main():
    prior_report_path = SOURCE/'final_delta_before_clearance.json'
    prior_signatures_path = SOURCE/'physical_geometry_before_final_cuts.json'
    if not prior_report_path.exists():
        shutil.copy2(OUT/'electrical_final_validation.json',prior_report_path)
        shutil.copy2(OUT/'physical_geometry_signatures.json',prior_signatures_path)
    prior = json.loads(prior_report_path.read_text())
    old_metrics = {row['name']:row for row in json.loads(prior_signatures_path.read_text())}
    expected = {'electrical_service_carrier','electronics_tray','USB_hub_rear_clamp'}
    paths = {name:SOURCE/f'validation_before_cut_{name}.brep' for name in expected}
    if not all(path.exists() for path in paths.values()):
        old = cad.App.openDocument('/tmp/v82_validated_pre_routes.FCStd')
        try:
            for name in expected-{'USB_hub_rear_clamp'}:
                old.getObject(name).Shape.exportBrep(str(paths[name]))
            shutil.copy2('/tmp/v82_hub_clamp_before_clearance.brep',paths['USB_hub_rear_clamp'])
        finally:
            cad.App.closeDocument(old.Name)
    doc = cad.App.openDocument(str(OUT/'wheel_leg_v8_2.FCStd'))
    try:
        doc.Parameters.LegLength=180
        doc.Parameters.Beta=0
        doc.recompute()
        physical = [o for o in doc.Objects if is_physical(o)]
        current = [signature(o) for o in physical]
        differences=[]
        for row in current:
            result=same_signature(old_metrics[row['name']],row)
            if not result['passed']: differences.append(result)
        changed={row['name'] for row in differences}
        pure=[]
        for name in expected:
            original=cad.Part.read(str(paths[name]))
            latest=doc.getObject(name).Shape
            pure.append(dict(name=name,added_volume_mm3=latest.cut(original).Volume,
                             removed_volume_mm3=original.cut(latest).Volume,
                             valid=latest.isValid()))
        shapes={o.Name:o.Shape for o in physical if o.TypeId=='Part::Feature'}
        hits=check({name:shapes[name] for name in expected},shapes)
        # The old delta audit failed only for this explicitly resolved pair.
        allowed_old_pair={'chassis_rear_cover','USB_hub_rear_clamp'}
        inherited_ok=(not prior['unexpected_changes'] and not prior['missing_objects']
            and not prior['added_physical_objects']
            and prior['front_shell_pure_subtraction']['passed']
            and all(not row['collisions'] for row in prior['delta_motion_checks'])
            and not prior['insertion']['new_part_continuous_collisions']
            and all(not row['collisions'] for row in prior['insertion']['complete_module_samples'])
            and all({row['a'],row['b']}==allowed_old_pair for row in prior['changed_static_collisions']))
        final_ok=(inherited_ok and not changed-expected and not hits
                  and all(row['valid'] and row['added_volume_mm3']<.001 for row in pure))
        metrics=json.dumps(current,sort_keys=True,separators=(',',':'))
        (OUT/'physical_geometry_signatures.json').write_text(json.dumps(current,ensure_ascii=False,indent=2)+'\n')
        prior.update(
            all_pass=final_ok,
            physical_geometry_metrics_sha256=hashlib.sha256(metrics.encode()).hexdigest(),
            routing_objects_excluded=[o.Name for o in doc.Objects if getattr(o,'Material','')=='routing_allowance'],
            changed_static_collisions=hits,
            final_clearance_update=dict(
                prior_report='source/final_delta_before_clearance.json',
                actual_changed=sorted(changed),unexpected_changes=sorted(changed-expected),
                pure_subtractions=pure,final_static_collisions=hits,
                inheritable_motion_and_insertion_evidence=inherited_ok,
                rationale='Each final altered solid is an exact subset of its previously checked solid. The resolved hub/cover overlap was the only old static failure; all other static, sampled-motion and insertion checks remain valid. No added physical material can create a new intersection.',
                all_pass=final_ok))
        (OUT/'electrical_final_validation.json').write_text(json.dumps(prior,ensure_ascii=False,indent=2)+'\n')
        print('FINAL_CUTS',json.dumps(dict(pass_all=final_ok,changed=sorted(changed),pure=pure,clashes=hits)),flush=True)
    finally:
        cad.App.closeDocument(doc.Name)


if __name__=='__main__':main()
