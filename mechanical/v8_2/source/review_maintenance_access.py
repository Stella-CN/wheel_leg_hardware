"""Review V8.1 Jetson service translations without modifying any CAD files.

The crossframe removal is sampled; the tray translations use conservative
continuous swept boxes. Neither result includes cables, hands or tool paths.
"""
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools'))
import build_printable_robot as cad
import cad_v81_chassis as chassis
import cad_v81_payload as payload
import cad_v6_jetson_mount as mounts

OUT = ROOT / 'mechanical/v8_1'
Part, V = cad.Part, cad.V
SOURCE_NAMES = (
    'cad_v81_chassis.py', 'cad_v81_payload.py', 'cad_v81_display.py', 'cad_v81_battery.py',
    'cad_v8_chassis.py', 'cad_v8_display.py', 'cad_v7_chassis.py',
    'cad_v6_chassis.py', 'cad_v6_payload.py', 'cad_v7_payload.py',
    'cad_v7_imu.py', 'cad_v6_jetson_mount.py', 'build_printable_robot.py',
)
FILES = [ROOT / 'tools' / name for name in SOURCE_NAMES]
HASHES = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in FILES}
TOL = .001


def bounds(shape):
    b = shape.BoundBox
    return [b.XMin, b.YMin, b.ZMin, b.XMax, b.YMax, b.ZMax]


def moved(shape, x=0., z=0.):
    result = shape.copy()
    result.translate(V(x, 0, z))
    return result


def envelope(shape, delta=(0., 0., 0.)):
    b = shape.BoundBox
    origin = V(b.XMin + min(0., delta[0]), b.YMin + min(0., delta[1]),
               b.ZMin + min(0., delta[2]))
    return Part.makeBox(b.XLength + abs(delta[0]), b.YLength + abs(delta[1]),
                        b.ZLength + abs(delta[2]), origin)


def collisions(moving, targets):
    hits = []
    for name, shape in moving.items():
        for target_name, target in targets.items():
            volume = cad.interference_volume(shape, target)
            if volume > TOL:
                hits.append(dict(moving=name, target=target_name, mm3=volume))
    return hits


cad.configure(OUT)
parts = chassis.build_chassis()
kit = payload.devices.jetson()
motion_keys = ('rod_length', 'lower_length', 'crank_length', 'knee_stator_face_y',
               'knee_motor_translation_y', 'hub_stator_face_y', 'wheel_center_y')
v8_parameters = json.loads((ROOT / 'mechanical/v8/design_parameters.json').read_text())
assert all(cad.P[key] == v8_parameters[key] for key in motion_keys)

retainer_names = ('Jetson_base_retainer_right', 'Jetson_base_retainer_left')
retainer_hardware = {name: shape for name, shape, _ in mounts.hardware()}
module = {'electronics_tray': parts['electronics_tray'],
          'official_Jetson_bounds': envelope(kit)}
# Use actual V8.1 parts, including both new screw clearances and tool holes.
module.update({name: parts[name] for name in retainer_names})
module.update(retainer_hardware)
module_compound = Part.makeCompound(list(module.values()))
rear_frame = parts['chassis_rear_crossframe']

removed_parts = {'chassis_rear_cover', 'chassis_rear_crossframe',
                 'shoulder_fairing_right', 'shoulder_fairing_left'}
removed_hardware = {
    **{f'electronics_tray_M3x8_{i}': 'tray-to-frame screw' for i in range(4)},
    **{f'rear_cover_M3x12_{i}': 'rear-cover screw' for i in range(4)},
    **{f'shoulder_{side}_M3x20_{i}': 'shoulder-cover screw'
       for side in (-1, 1) for i in range(2)},
    **{f'crossframe_DIN7991_M3x8_{side}_{i}': 'rear-crossframe screw'
       for side in (-1, 1) for i in (0, 1)},
}
body_hardware = {name: shape for name, shape, _ in chassis.chassis_hardware()}
assert len(removed_hardware) == 16
assert set(removed_hardware) <= set(body_hardware)
assert set(retainer_hardware) <= set(body_hardware)
assert not set(removed_hardware) & set(retainer_hardware)

fixed = {name: shape for name, shape in parts.items()
         if name not in removed_parts | set(retainer_names) | {'electronics_tray'}}
fixed.update(payload.designs())
fixed.update({name: shape for name, shape, _ in payload.hardware()})
fixed.update({name: shape for name, shape in body_hardware.items()
              if name not in set(removed_hardware) | set(retainer_hardware)})
fixed.update({name: shape for name, shape, _, _ in payload.payloads()
              if name != 'Jetson_Orin_Nano_official'})
motor_path = ROOT.parent / 'references/DM-J4310-2EC/3D模型/DM-J4310-2EC-V1.1_3d_20260228_1.stp'
hip = cad.motor_shape(motor_path, 72.5)
seat = chassis.hip_stator_mount()
fixed.update(hip_motor_right=hip, hip_motor_left=cad.mirror(hip),
             hip_mount_right=seat, hip_mount_left=cad.mirror(seat))
for name, shape, _ in chassis.hip_hardware():
    fixed[name + '_right'] = shape
    fixed[name + '_left'] = cad.mirror(shape)

report = dict(
    script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    parameter_source='mechanical/v8_1',
    parameter_sha256=hashlib.sha256((OUT / 'design_parameters.json').read_bytes()).hexdigest(),
    scope='V8.1 fixed-orientation nominal rigid-body Jetson module maintenance path. '
          'Actual V8.1 retainers, current frame fasteners, complete front module, '
          '5-inch display, IMU bridge and battery remain represented.',
    source_sha256=HASHES,
    removed_part_names=sorted(removed_parts),
    removed_hardware=removed_hardware,
    removed_hardware_count=len(removed_hardware),
    module_part_names=sorted(module),
    module_retainer_hardware_count=len(retainer_hardware),
    fixed_obstacle_names=sorted(fixed),
    retainer_volume_mm3={name: parts[name].Volume for name in retainer_names},
    module='Original Jetson kit, electronics tray, two V8.1 retaining rails and '
           'their 12 screws/washers/nuts stay assembled.',
    original_kit_conservative_bounds_mm=bounds(kit),
    module_bounds_mm=bounds(module_compound),
    rear_frame_opening_top_z_mm=35.,
    rear_frame_withdrawal_samples=[],
    straight_withdrawal_diagnostic=[],
    lift_height_mm=4.,
    lift_conservative_sweep_collisions=[],
    withdrawal_conservative_sweep_collisions=[],
    notes=[
        'Preconditions: power off, disconnect all module cables, support module and robot; '
        'remove both shoulders, rear cover, 4 tray screws and the rear crossframe with its 4 screws.',
        'Rear crossframe opening ends at Z35, below kit top Z67.766; frame removal is required.',
        'Kit bounding box conservatively encloses all official source solids. Delivered kit CAD is unchanged.',
        'Retainer hardware remains on the module, extending down to Z26 before lifting.',
        'Each module component bounding box swept upward 4 mm covers continuous vertical translation; '
        'whole raised module bounding box swept backward 180 mm covers continuous rearward translation.',
        'Zero swept-box intersection proves these two fixed-orientation translations clear at nominal geometry.',
        'Rear-crossframe removal uses six discrete offsets only; a continuous crossframe removal path is not proved.',
        'Cable/plug geometry, tool/hand motion, straps, tilted motion and physical tolerances are excluded. '
        'The leg linkage outside the hip seats is excluded from this local inward-body check.',
    ],
)

frame_targets = {**fixed, **module}
for dx in (0., -.5, -4., -16., -40., -100.):
    hits = collisions({'rear_crossframe': moved(rear_frame, x=dx)}, frame_targets)
    report['rear_frame_withdrawal_samples'].append(dict(x_offset_mm=dx, collisions=hits))
    print('REAR_FRAME', dx, hits, flush=True)

fasteners = {name: moved(shape, x=-38.) for name, shape in retainer_hardware.items()}
report['straight_withdrawal_diagnostic'] = collisions(
    fasteners, {'hip_motor_right': hip, 'hip_motor_left': cad.mirror(hip)})
print('STRAIGHT_WITHDRAWAL_DIAGNOSTIC', report['straight_withdrawal_diagnostic'], flush=True)

lift_sweeps = {name: envelope(shape, (0., 0., 4.)) for name, shape in module.items()}
report['lift_conservative_sweep_collisions'] = collisions(lift_sweeps, fixed)
raised = moved(module_compound, z=4.)
swept = envelope(raised, (-180., 0., 0.))
report['raised_module_bounds_mm'] = bounds(raised)
report['withdrawal_swept_bounds_mm'] = bounds(swept)
report['withdrawal_conservative_sweep_collisions'] = collisions({'raised_module_sweep': swept}, fixed)
report['minimum_raised_module_z_mm'] = raised.BoundBox.ZMin
report['hip_motor_maximum_z_mm'] = hip.BoundBox.ZMax
report['nominal_vertical_gap_to_hip_motor_mm'] = raised.BoundBox.ZMin - hip.BoundBox.ZMax
report['pass'] = dict(
    rear_crossframe_sampled_withdrawal_clear=all(not row['collisions'] for row in report['rear_frame_withdrawal_samples']),
    upward4mm_conservative_sweeps_clear=not report['lift_conservative_sweep_collisions'],
    backward180mm_raised_module_conservative_sweep_clear=not report['withdrawal_conservative_sweep_collisions'],
)
report['source_unchanged_during_review'] = all(
    hashlib.sha256(path.read_bytes()).hexdigest() == HASHES[path.name] for path in FILES)
report['preserved_leg_dimensions_mm'] = {key: cad.P[key] for key in ('rod_length', 'lower_length', 'crank_length')}
report['failures'] = [name for name, passed in report['pass'].items() if not passed]
if not report['source_unchanged_during_review']:
    report['failures'].append('source_changed_during_review')
(OUT / 'maintenance_access_review.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({key: report[key] for key in (
    'pass', 'failures', 'nominal_vertical_gap_to_hip_motor_mm',
    'source_unchanged_during_review', 'retainer_volume_mm3')}, indent=2))
