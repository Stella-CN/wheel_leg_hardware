"""Read-only exact collision and V8.1 preservation audit for V8.2.

Run using the system FreeCAD Python.  The default is a quick nominal-pose
diagnostic.  --full adds all changed-to-moving pairs at 100..215 mm in 5 mm
increments, with beta=0.  Native documents are never saved by this script.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import time

import build_printable_robot as cad

ROOT = cad.ROOT
OUT = ROOT / 'mechanical/v8_2'
BASE = ROOT / 'mechanical/v8_1/wheel_leg_v8_1.FCStd'
NATIVE = OUT / 'wheel_leg_v8_2.FCStd'
THRESHOLD = 0.001
TOLERANCE = 1e-6


def bounds(bb):
    return [getattr(bb, key) for key in
            ('XMin', 'YMin', 'ZMin', 'XMax', 'YMax', 'ZMax')]


def signature(obj):
    result = dict(name=obj.Name, type=obj.TypeId,
                  expressions=list(obj.ExpressionEngine),
                  placement=list(obj.Placement.toMatrix().A))
    if obj.TypeId == 'Part::Feature':
        shape = obj.Shape
        result.update(volume=shape.Volume, area=shape.Area,
                      bounds=bounds(shape.BoundBox), solids=len(shape.Solids))
    elif obj.TypeId == 'Mesh::Feature':
        points, facets = obj.Mesh.Topology
        raw = repr(([(p.x, p.y, p.z) for p in points], facets)).encode()
        result.update(mesh_points=obj.Mesh.CountPoints,
                      mesh_facets=obj.Mesh.CountFacets,
                      topology_sha256=hashlib.sha256(raw).hexdigest(),
                      bounds=bounds(obj.Mesh.BoundBox))
    return result


def same_signature(old, new):
    exact = ('name', 'type', 'expressions', 'solids', 'mesh_points',
             'mesh_facets', 'topology_sha256')
    numeric = ('volume', 'area')
    vector = ('placement', 'bounds')
    bad = []
    for key in exact:
        if old.get(key) != new.get(key):
            bad.append(key)
    for key in numeric:
        if key in old and abs(old[key] - new[key]) > TOLERANCE:
            bad.append(key)
    for key in vector:
        if key in old and max(abs(a-b) for a, b in zip(old[key], new[key])) > TOLERANCE:
            bad.append(key)
    return dict(name=old['name'], passed=not bad, differing_fields=bad)


def preserve(before, after, changed):
    rows, missing = [], []
    baseline_objects = [o for o in before.Objects
                        if o.TypeId in ('Part::Feature', 'Mesh::Feature')]
    for old in baseline_objects:
        new = after.getObject(old.Name)
        if new is None:
            missing.append(old.Name)
        elif old.Name not in changed:
            rows.append(same_signature(signature(old), signature(new)))
    return dict(baseline_physical_objects=len(baseline_objects),
                changed_existing=sorted(changed), unchanged_objects=rows,
                missing_objects=missing,
                all_pass=not missing and all(r['passed'] for r in rows))


def overlapping(a, b):
    return all(min(getattr(a, k+'Max'), getattr(b, k+'Max')) >
               max(getattr(a, k+'Min'), getattr(b, k+'Min'))
               for k in ('X', 'Y', 'Z'))


def pair_check(a, b, length, counts, errors):
    counts['pairs'] += 1
    if not overlapping(a.Shape.BoundBox, b.Shape.BoundBox):
        return None
    counts['broadphase_overlaps'] += 1
    try:
        volume = cad.interference_volume(a.Shape, b.Shape)
    except Exception as exc:
        errors.append(dict(a=a.Name, b=b.Name, length_mm=length,
                           error=repr(exc)))
        return None
    if volume > THRESHOLD:
        return dict(a=a.Name, b=b.Name, length_mm=length,
                    volume_mm3=volume,
                    a_role=getattr(a, 'KinematicRole', 'fixed'),
                    b_role=getattr(b, 'KinematicRole', 'fixed'))
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--full', action='store_true')
    args = parser.parse_args()
    started = time.monotonic()
    build_path = OUT / 'electrical_build.json'
    build = json.loads(build_path.read_text())
    changed = set(build['changed_existing'])
    declared_new = set(build['new_objects'])
    base_hash = hashlib.sha256(BASE.read_bytes()).hexdigest()
    native_hash = hashlib.sha256(NATIVE.read_bytes()).hexdigest()
    before = cad.App.openDocument(str(BASE))
    after = cad.App.openDocument(str(NATIVE))
    print('DOCUMENTS_OPEN', flush=True)
    try:
        for doc in (before, after):
            doc.Parameters.LegLength = 180
            doc.Parameters.Beta = 0
            doc.recompute()
        conservation = preserve(before, after, changed)
        print('PRESERVATION_DONE', len(conservation['unchanged_objects']),
              conservation['all_pass'], flush=True)
        physical = [o for o in after.Objects if o.TypeId == 'Part::Feature']
        base_names = {o.Name for o in before.Objects
                      if o.TypeId in ('Part::Feature', 'Mesh::Feature')}
        actual_new = {o.Name for o in physical if o.Name not in base_names}
        delta_names = changed | declared_new | actual_new
        delta = [o for o in physical if o.Name in delta_names]
        missing_delta = sorted(delta_names - {o.Name for o in physical})
        invalid = [o.Name for o in delta
                   if o.Shape.isNull() or not o.Shape.isValid()]
        print('DELTA_VALIDITY_DONE', len(delta), invalid, flush=True)
        moving = [o for o in physical
                  if getattr(o, 'KinematicRole', 'fixed') != 'fixed']
        counts = dict(pairs=0, broadphase_overlaps=0)
        collisions, errors = [], []
        checked_pairs = set()
        for a in delta:
            for b in physical:
                key = tuple(sorted((a.Name, b.Name)))
                if a.Name == b.Name or key in checked_pairs:
                    continue
                checked_pairs.add(key)
                hit = pair_check(a, b, 180, counts, errors)
                if hit:
                    collisions.append(hit)
                    print('CLASH', json.dumps(hit), flush=True)
            print('STATIC_DONE', a.Name, 'clashes', len(collisions), flush=True)
        static_pairs = counts['pairs']
        sampled = [180]
        if args.full:
            for length in range(100, 216, 5):
                if length == 180:
                    continue
                after.Parameters.LegLength = length
                after.recompute()
                seen = set()
                for a in delta:
                    targets = (physical if getattr(a, 'KinematicRole', 'fixed') != 'fixed'
                               else moving)
                    for b in targets:
                        key = tuple(sorted((a.Name, b.Name)))
                        if a.Name == b.Name or key in seen:
                            continue
                        seen.add(key)
                        hit = pair_check(a, b, length, counts, errors)
                        if hit:
                            collisions.append(hit)
                sampled.append(length)
                print('POSE_DONE', length, 'clashes', len(collisions), flush=True)
        after.Parameters.LegLength = 180
        after.recompute()
        report = dict(
            mode='full' if args.full else 'nominal_diagnostic',
            baseline_native_sha256=base_hash,
            baseline_hash_matches_build=base_hash == build['baseline_sha256'],
            native_sha256=native_hash,
            build_json_sha256=hashlib.sha256(build_path.read_bytes()).hexdigest(),
            review_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            threshold_mm3=THRESHOLD, signature_tolerance=TOLERANCE,
            preservation=conservation,
            native_solid_objects=len(physical), delta_objects=len(delta),
            delta_object_names=sorted(delta_names),
            declared_new_count=len(declared_new), actual_new_count=len(actual_new),
            undeclared_new_objects=sorted(actual_new-declared_new),
            missing_delta_objects=missing_delta, invalid_shapes=invalid,
            validity_scope='Changed and new shapes; unchanged shapes preserve baseline validity evidence.',
            moving_objects=len(moving), sampled_lengths_mm=sorted(sampled),
            beta_deg=0, static_pair_checks=static_pairs,
            collision_pair_checks=counts['pairs'],
            broadphase_overlap_checks=counts['broadphase_overlaps'],
            collisions=collisions, boolean_errors=errors,
            largest_collisions=sorted(collisions, key=lambda r:r['volume_mm3'], reverse=True)[:20],
            exclusions=['App::Part aggregate shapes, origin planes and document groups are containers, not physical parts.',
                        'D435 visualization mesh is preserved by topology signature; its existing Part::Feature clearance proxy participates in collision checks.',
                        'Unchanged-to-unchanged pairs retain baseline evidence; this review checks every pair involving a changed or newly added solid.',
                        'No physical pair is excluded merely for being in the same module.'],
            scope='Rigid nominal CAD only. No cable flexibility, thermal test, certified load validation or continuous motion claim.',
            elapsed_seconds=round(time.monotonic()-started, 3))
        report['all_pass'] = (not collisions and not errors and not invalid
                              and not missing_delta and conservation['all_pass']
                              and report['baseline_hash_matches_build'])
        destination = OUT / 'electrical_validation.json'
        destination.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
        print('RESULT', json.dumps(dict(mode=report['mode'], all_pass=report['all_pass'],
                                        pairs=counts['pairs'], collisions=len(collisions),
                                        largest=report['largest_collisions'])), flush=True)
    finally:
        cad.App.closeDocument(after.Name)
        cad.App.closeDocument(before.Name)


if __name__ == '__main__':
    main()
