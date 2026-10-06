"""Diagnose routing allowance / fixed-part intersections without editing CAD."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import time

import build_printable_robot as cad
from review_v82_integration import bounds, is_physical

OUT = cad.ROOT/'mechanical/v8_2'


def main():
    started = time.monotonic()
    path = OUT/'wheel_leg_v8_2.FCStd'
    doc = cad.App.openDocument(str(path))
    try:
        routes = [o for o in doc.Objects if getattr(o,'Material','') == 'routing_allowance']
        targets = [o for o in doc.Objects if o.TypeId == 'Part::Feature' and is_physical(o)]
        hits = []
        for route in routes:
            for target in targets:
                volume = cad.interference_volume(route.Shape,target.Shape)
                if volume <= .001:
                    continue
                common = route.Shape.common(target.Shape)
                row = dict(route=route.Name,part=target.Name,volume_mm3=volume,
                           common_bounds_xyz_mm=bounds(common.BoundBox),
                           separate_overlap_solids=[dict(volume_mm3=s.Volume,bounds=bounds(s.BoundBox))
                                                    for s in common.Solids])
                hits.append(row)
                print('ROUTING_CLASH',json.dumps(row),flush=True)
        route_data = json.loads((OUT/'routing_allowances.json').read_text())
        route_metrics = [dict(name=o.Name,volume=o.Shape.Volume,
                              area=o.Shape.Area,bounds=bounds(o.Shape.BoundBox))
                         for o in routes]
        report = dict(
            native_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            native_hash_scope='Historical file identity only; colour/visibility changes do not invalidate the independent route geometry metrics.',
            route_geometry_metrics=route_metrics,
            route_geometry_metrics_sha256=hashlib.sha256(json.dumps(route_metrics,sort_keys=True).encode()).hexdigest(),
            route_geometry_source='Native Material=routing_allowance objects',
            routes=route_data['routes'], route_objects=len(routes),
            physical_targets=len(targets), threshold_mm3=.001,
            contacts=hits, all_clear=not hits,
            limitations=['No automatic port-endpoint contact exclusions.',
                         'Swept illustrative tubes use user/engineering radii and sharp polyline corners; no verified flexible-cable bend radius.',
                         'Nominal assembled-pose diagnosis only; moving joint harnesses and powered thermal/electrical tests are outside scope.',
                         'Common volumes of compound corridor primitives serve clash localization, not cable material/mass calculation.'],
            elapsed_seconds=round(time.monotonic()-started,3))
        (OUT/'routing_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        print('ROUTING_RESULT',len(hits),report['all_clear'],flush=True)
    finally:
        cad.App.closeDocument(doc.Name)


if __name__ == '__main__':
    main()
