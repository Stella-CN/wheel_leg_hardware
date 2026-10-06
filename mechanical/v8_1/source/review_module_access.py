"""Independent V8.1 module mating and straight-tool access review.

No delivered design or placement is edited. Run with system FreeCAD Python.
Tool cylinders are specified envelopes, not a promise that every tool brand
fits; cables, hands and torque application are outside the geometric scope.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools'))
import build_printable_robot as cad
import build_enclosed_robot as wheel
import cad_v81_chassis as chassis
import cad_v81_leg as leg
import cad_v81_coupling as coupling
import cad_v81_battery as battery

OUT = ROOT / 'mechanical/v8_1'
cad.configure(OUT)
Part, V = cad.Part, cad.V
TOL = .001
FILES = [ROOT / 'tools' / name for name in (
    'cad_v81_chassis.py', 'cad_v81_leg.py', 'cad_v81_coupling.py',
    'cad_v6_leg.py', 'cad_v6_chassis.py', 'cad_v5_chassis.py',
    'cad_v5_coupling.py', 'build_printable_robot.py', 'cad_v81_battery.py')]
HASHES = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in FILES}


def hits(tool, targets):
    result = []
    for name, target in targets.items():
        if not tool.BoundBox.intersect(target.BoundBox):
            continue
        volume = cad.interference_volume(tool, target)
        if volume > TOL:
            result.append(dict(part=name, overlap_mm3=volume))
    return result


def moved(shape, dy):
    result = shape.copy()
    result.translate(V(0, dy, 0))
    return result


def bbox(shape, dy=0.):
    b = shape.BoundBox
    return Part.makeBox(b.XLength, b.YLength + abs(dy), b.ZLength,
                        V(b.XMin, b.YMin + min(dy, 0), b.ZMin))


def main():
    parts = chassis.build_chassis()
    frame = {name: shape for name, shape in parts.items()
             if name.startswith('chassis_') and not name.endswith(('shell', 'cover'))}
    # Only the five metal frame members belong in this stage.
    assert len(frame) == 5, list(frame)
    frame_hardware = {name: shape for name, shape, _ in chassis.chassis_hardware()
                      if name.startswith(('belly_frame_', 'crossframe_'))}
    empty_tray = {'empty_battery_tray': parts['battery_tray']}
    empty_tray.update({name: shape for name, shape, _ in chassis.chassis_hardware()
                       if name.startswith('battery_tray_M3x8_')})
    designs = {'hip_stator_mount': (chassis.hip_stator_mount(), 'fixed', 'CNC')}
    designs.update(coupling.designs())
    designs.update(leg.designs())
    designs['wheel_rim'] = (wheel.wheel_rim(), 'wheel', 'CNC')
    rows = [(name, shape, role) for name, (shape, role, _) in designs.items()]
    rows += coupling.hardware() + leg.hardware() + chassis.hip_hardware()
    refs = ROOT.parent / 'references'
    jpath = refs / 'DM-J4310-2EC/3D模型/DM-J4310-2EC-V1.1_3d_20260228_1.stp'
    hpath = refs / 'DM-H6215/3D模型/6215_轮毂电机3D模型20240821.stp'
    rows += [('J4310_hip', cad.motor_shape(jpath, 72.5), 'fixed'),
             ('J4310_knee', cad.motor_shape(jpath, cad.P['knee_motor_translation_y']), 'hip'),
             ('H6215', cad.motor_shape(hpath, cad.P['hub_stator_face_y'] + 42), 'wheel')]
    tyre = cad.cut(cad.cyl(50, cad.P['hub_stator_face_y'] + 10, 32),
                   cad.cyl(43, cad.P['hub_stator_face_y'] + 9, 34))
    rows.append(('elastic_tyre', tyre, 'wheel'))
    screw_points = [(x, z) for x in (-30., 30.) for z in (-30., 30.)]
    # AF2.5 hex key has a 2.887 mm circumscribed diameter. D3.2 includes
    # 0.156 mm radial tool clearance. Socket starts just above head face.
    tools = {f'M4_{i}': Part.makeCylinder(1.6, 152.15, V(x, 77.85, z), V(0, 1, 0))
             for i, (x, z) in enumerate(screw_points)}
    report = dict(
        revision='v8_1', units='mm', source_sha256=HASHES,
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        assembly_state='Five-piece metal frame and complete left/right legs. Battery, Jetson, IMU, shells and front face absent. Tool and leg-mating checks additionally include the new empty tray as an optional stricter obstacle; recommended final assembly order may install the entire battery tray module after legs when the independent battery-module path review passes.',
        outer_tools=dict(hex_key_across_flats=2.5, conservative_diameter=3.2,
                         shaft_y=[77.85, 230.], socket_head_top_y=77.8,
                         purpose='Straight un-angled long driver for hip M4 countersunk screws; no ball-end bypass.'),
        sampled_driver_access=[], internal_socket_access=[], insertion_samples=[],
        limitations=['Discrete pose samples are not a continuous articulated tool-motion proof.',
                     'Tool envelopes do not include hands, handle swing, cable bundles or torque qualification.',
                     'Real tools must fit the listed maximum envelope; no generic AF7 socket diameter is assumed.',
                     'No geometry, kinematics or nominal robot pose is modified by this review.'])
    selected = None
    cache = OUT / 'module_access_review.json'
    old = None
    if '--reuse-scan' in sys.argv and cache.exists():
        old = json.loads(cache.read_text())
        if old.get('source_sha256') == HASHES and len(old.get('sampled_driver_access', [])) == 24:
            report['sampled_driver_access'] = old['sampled_driver_access']
            report['driver_scan_reused_same_source_hashes'] = True
    scan_lengths = [] if report['sampled_driver_access'] else range(100, 216, 5)
    for length in scan_lengths:
        state = cad.pose(length)
        obstacles = {name: cad.transform(shape, role, state) for name, shape, role in rows}
        obstacles.update(frame)
        obstacles.update(frame_hardware)
        access = []
        for index, (name, tool) in enumerate(tools.items()):
            excluded = f'hip_case_M4x12_CS_{index}'
            contacts = hits(tool, {n: s for n, s in obstacles.items() if n != excluded})
            access.append(dict(screw=index, centre_xz=screw_points[index], collisions=contacts))
        passed = not any(row['collisions'] for row in access)
        report['sampled_driver_access'].append(dict(leg_length=length, beta=0.,
                                                  all_four_clear=passed, screws=access))
        if passed and selected is None:
            selected = length
        print('DRIVER_ACCESS', length, passed, [(r['screw'], r['collisions']) for r in access if r['collisions']], flush=True)
    report['all_four_clear_leg_lengths'] = [r['leg_length'] for r in report['sampled_driver_access'] if r['all_four_clear']]
    candidates = report['all_four_clear_leg_lengths']
    # No single posture need expose every screw simultaneously: a supported,
    # unpowered complete leg may be articulated between two tested postures.
    # Each straight tool is removed before articulation. All four screws
    # have already been preloaded into the hip seat before leg preassembly.
    plan = []
    for i in range(4):
        valid = [r['leg_length'] for r in report['sampled_driver_access']
                 if not r['screws'][i]['collisions']]
        preferred = 110 if i == 1 else 165
        chosen = preferred if preferred in valid else (valid[len(valid)//2] if valid else None)
        plan.append(dict(screw=i, centre_xz=screw_points[i],
                         installation_leg_length=chosen, clear_sampled_lengths=valid))
    report['per_screw_installation_plan'] = plan
    selected = 180
    report['recommended_leg_length_for_module_installation'] = selected
    state = cad.pose(selected)
    complete_leg = {name: cad.transform(shape, role, state) for name, shape, role in rows}
    report['assembly_pose_angles_deg'] = {key: state[key] for key in ('hip', 'oa', 'output')}
    # AF7 holding socket OD <= 10.5 mm, kept inside existing D11 relief.
    # Its internal bore clears nut corners (D8.083) and projecting screw end.
    for i, (x, z) in enumerate(screw_points):
        sleeve = Part.makeCylinder(5.25, 41.15, V(x, 30., z), V(0, 1, 0))
        sleeve = sleeve.cut(Part.makeCylinder(4.15, 41.35, V(x, 29.9, z), V(0, 1, 0)))
        extension = Part.makeCylinder(3., 50., V(x, -20., z), V(0, 1, 0))
        tool = Part.makeCompound([sleeve, extension])
        ignored = {f'hip_case_M4_nut_{i}', f'hip_case_M4_washer_{i}', f'hip_case_M4x12_CS_{i}'}
        targets = {n: s for n, s in complete_leg.items() if n not in ignored}
        targets.update(frame)
        targets.update(frame_hardware)
        targets.update(empty_tray)
        result = hits(tool, targets)
        report['internal_socket_access'].append(dict(screw=i, centre_xz=[x, z],
            socket_od_max=10.5, socket_bore_model=8.3, socket_y=[30., 71.15],
            extension_diameter=6., extension_y=[-20., 30.], collisions=result))
        print('INNER_SOCKET', i, result, flush=True)
    # Pre-position the four M4 bolts while the hip seat is still bare. Their
    # D8 heads need not be threaded through a completed linkage. The bolts
    # travel with the leg and enter the D4.4 frame holes; nuts/washers are
    # added from the open electronics bay only after axial mating.
    moving = {name: shape for name, shape in complete_leg.items()
              if not name.startswith(('hip_case_M4_washer_', 'hip_case_M4_nut_'))}
    report['preloaded_module_fasteners'] = [name for name in moving if name.startswith('hip_case_M4')]
    report['fastener_mating_order'] = 'Preload four M4x12 countersunk screws in bare hip seat before completing leg; temporarily retain. Their shanks enter frame holes with the whole leg. Add washers and nuts afterward from empty body cavity.'
    fixed = dict(frame, **frame_hardware)
    fixed.update({name + '_opposite': cad.mirror(shape) for name, shape in moving.items()})
    fixed.update(empty_tray)
    # Incremental reuse is permitted only for identical geometry sources,
    # same pose and the same four preloaded bolts. Always evaluate the new
    # empty-tray targets; a clean run evaluates all targets.
    cached_insertion = bool(old and old.get('source_sha256') == HASHES
        and old.get('recommended_leg_length_for_module_installation') == selected
        and old.get('preloaded_module_fasteners') == report['preloaded_module_fasteners']
        and old.get('pass', {}).get('sampled_complete_leg_axial_mating_clear')
        and len(old.get('insertion_samples', [])) == 10)
    report['insertion_frame_results_reused_identical_sources'] = cached_insertion
    cached_rows = {r['outward_y_offset']: r for r in old['insertion_samples']} if cached_insertion else {}
    for dy in (0., .25, 1., 2., 4., 8., 16., 32., 64., 120.):
        contacts = list(cached_rows[dy]['collisions']) if cached_insertion else []
        for name, shape in moving.items():
            for contact in hits(moved(shape, dy), empty_tray if cached_insertion else fixed):
                contacts.append(dict(moving=name, **contact))
        report['insertion_samples'].append(dict(outward_y_offset=dy, collisions=contacts))
        print('LEG_INSERTION', dy, contacts, flush=True)
    # Use the actual newly selected drawing envelope, never the inherited
    # 110x50x35 placeholder. The body module owns the complete tray+battery
    # insertion review; this independent sweep also checks battery alone.
    hip_motors = {'J4310_hip_right': complete_leg['J4310_hip'],
                  'J4310_hip_left': cad.mirror(complete_leg['J4310_hip'])}
    battery_name, battery_shape, battery_mass, battery_note = battery.payload()
    bb = battery_shape.BoundBox
    battery_sweep = Part.makeBox(bb.XLength, bb.YLength, bb.ZLength + 100.,
                                V(bb.XMin, bb.YMin, bb.ZMin))
    battery_targets = dict(fixed, **complete_leg)
    battery_targets.update(hip_motors)
    report['battery_only_top_in_conservative_sweep'] = dict(
        payload=battery_name, drawing_envelope_size=[bb.XLength, bb.YLength, bb.ZLength],
        swept_bounds=[bb.XMin, bb.YMin, bb.ZMin, bb.XMax, bb.YMax, bb.ZMax + 100.],
        nominal_lateral_motor_gap=hip_motors['J4310_hip_right'].BoundBox.YMin - bb.YMax,
        collisions=hits(battery_sweep, battery_targets),
        exclusions='Actual DC plug, straps/cable bends; exact selected SKU and plug envelope are unresolved.')
    battery_review_path = OUT / 'battery_local_review.json'
    battery_review = json.loads(battery_review_path.read_text())
    battery_path_verified = (
        battery_review.get('all_pass') is True
        and battery_review.get('source_sha256') == HASHES['cad_v81_battery.py']
        and all(any(row.get('name') == name and row.get('passed') is True
                    for row in battery_review.get('checks', []))
                for name in ('complete_battery_module_vertical_insertion',
                             'four_M3x8_top_driver_access_after_module_insertion')))
    report['battery_module_insertion_review'] = dict(
        file='battery_local_review.json', owner='cad_v81_battery local body review',
        note='Complete tray+battery+single-layer strap vertical route and four tray screw tool lines pass there against frame and both complete legs; upper electronics and body covers absent. No selected plug, buckle or cable geometry is included.',
        referenced_report_sha256=hashlib.sha256(battery_review_path.read_bytes()).hexdigest(),
        referenced_report_all_pass_same_battery_source=battery_path_verified,
        battery_source_sha256=HASHES['cad_v81_battery.py'])
    # Exact geometry samples above are supplemented by bounds: all parts
    # wholly outside the side-frame Y75 face can only move farther away.
    report['outward_of_frame_y75'] = [n for n, s in moving.items() if s.BoundBox.YMin >= 75. - 1e-6]
    report['crossing_frame_during_insertion'] = {
        n: dict(ymin=s.BoundBox.YMin, ymax=s.BoundBox.YMax)
        for n, s in moving.items() if s.BoundBox.YMin < 75. - 1e-6}
    report['symmetry_scope'] = 'Left leg/frame are exact Y mirrors. Mirroring the tested tools and Y translation gives the same clearances; opposite complete leg was present for insertion checks.'
    report['body_detail_review'] = 'body_detail_review.json contains independent checks of four top tool columns for preassembled Jetson tray and its integral retainer reliefs.'
    report['source_unchanged_during_review'] = all(hashlib.sha256(p.read_bytes()).hexdigest() == HASHES[p.name] for p in FILES)
    report['pass'] = dict(each_outer_tool_has_verified_pose=all(r['installation_leg_length'] is not None for r in plan),
                          internal_holding_socket_clear=not any(r['collisions'] for r in report['internal_socket_access']),
                          sampled_complete_leg_axial_mating_clear=not any(r['collisions'] for r in report['insertion_samples']),
                          battery_only_top_in_clear=not report['battery_only_top_in_conservative_sweep']['collisions'],
                          complete_battery_module_review_matches_source=battery_path_verified,
                          source_unchanged=report['source_unchanged_during_review'])
    report['failures'] = [name for name, passed in report['pass'].items() if not passed]
    (OUT / 'module_access_review.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({key: report[key] for key in ('recommended_leg_length_for_module_installation', 'pass', 'failures')}, indent=2), flush=True)
    if report['failures']:
        raise RuntimeError(report['failures'])


if __name__ == '__main__':
    main()
