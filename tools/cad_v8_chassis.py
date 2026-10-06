"""V8 small-radius rectangular enclosure with a removable complete front face.

Dimensions are millimetres. The V6 metal load frame, motor interfaces and leg
datums are unchanged. V7's four IMU bridge tapping holes are retained. The
printed shell has six broad planar faces and real R5 edge fillets, with no
faceted shoulders, taper or added upper compartment. Screen and camera mounts
are both carried by the single detachable front panel.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import cad_v6_chassis as prior

core, App, Part, V = prior.core, prior.App, prior.Part, prior.V
box, cyl, fuse, cut = prior.box, prior.cyl, prior.fuse, prior.cut
hip_stator_mount, hip_hardware = prior.hip_stator_mount, prior.hip_hardware
BOTTOM_FASTENERS, TRAY_FASTENERS = prior.BOTTOM_FASTENERS, prior.TRAY_FASTENERS
SHELL_FASTENERS, SHOULDER_FASTENERS = prior.SHELL_FASTENERS, prior.SHOULDER_FASTENERS
SPLIT_X = -20.0
BODY_BOUNDS = (-94., -82., -55., 117., 82., 100.)
SCREEN_PADS = tuple((y, z) for y in (-67., 67.) for z in (-34., 26.))
CAMERA_PADS = tuple((y, z) for y in (-50., 50.) for z in (53.5, 69.5))
FACE_FASTENERS = tuple((y, z) for y in (-68., 68.) for z in (-44., 88.))
IMU_BRIDGE_HOLES = tuple((x, y) for x in (-10., 10.) for y in (-68., 68.))


def _rounded_box(x0, y0, z0, x1, y1, z1, radius):
    blank = box(x0, y0, z0, x1-x0, y1-y0, z1-z0)
    return blank.makeFillet(radius, blank.Edges)


def _outer():
    return _rounded_box(*BODY_BOUNDS, 5.)


def _inner(offset=3., top=97.):
    # Open bottom is closed by a lip against the existing metal belly plate.
    return _rounded_box(-94+offset, -82+offset, -57.,
                        117-offset, 82-offset, top, max(5-offset, .5))


def _side(right=True, lightweight=True):
    shape = prior._side(right, lightweight)
    side = 1 if right else -1
    return cut(shape, [core.tap_drill((x, 68*side, 47), (0, 0, -1), 6)
                       for x in (-10., 10.)])


def _face_blank(x=114., depth=3., clearance=0.):
    return core.rounded_pocket_yz(-74-clearance, 74+clearance,
                                 -49-clearance, 95+clearance,
                                 x, depth, 4.+clearance)


def _hex_x(x, y, z, across_flats, depth):
    radius = across_flats / math.sqrt(3.)
    vertices = [V(x, y+radius*math.cos(math.radians(30+60*i)),
                  z+radius*math.sin(math.radians(30+60*i))) for i in range(6)]
    return Part.Face(Part.makePolygon(vertices+[vertices[0]])).extrude(V(depth, 0, 0))


def _face():
    cutters = [
        core.rounded_pocket_yz(-61.5, 61.5, -43.5, 35.5, 113.8, 3.4, .4),
        core.rounded_pocket_yz(-45.3, 45.3, 48.2, 73.8, 113.8, 3.4, .3),
    ]
    cutters.extend(cyl(1.7, 3.4, (113.8, y, z), (1, 0, 0))
                   for y, z in SCREEN_PADS + CAMERA_PADS + FACE_FASTENERS)
    shape = cut(_face_blank(), cutters)
    # The datasheet provides no active area or mounting lip. These four very
    # small provisional front stops overlap the case only 0.5 mm at the
    # corners. Assembly must verify a metal case rim here; never load glass.
    stops = [box(114., y, z, 3., 1., 4.)
             for y in (-61.5, 60.5) for z in (-43.5, 31.5)]
    return fuse([shape]+stops)


def _body_cutters():
    tools = []
    for side in (-1, 1):
        tools.append(cyl(36.2, 35., (0, 60*side, 0), (0, side, 0)))
        relief = core.rounded_pocket_xz(-39.5, 39.5, -39.5, 39.5, 74.9, 3.6, 1.)
        tools.append(relief if side > 0 else core.mirror(relief, (0, 1, 0)))
        for x, z in SHOULDER_FASTENERS:
            tools.append(cyl(1.7, 15., (x, 74.9*side, z), (0, side, 0)))
    # The faceplate lifts away as a complete module. Its clearance pocket is
    # wider than the panel; a separate integral rear ring provides its seat.
    tools.append(_face_blank(114., 3.3, .2))
    tools.append(core.rounded_pocket_yz(-71., 71., -46., 92., 110.8, 3.4, 3.))
    # The screen cradle's R5 mounting ears sit behind the removable panel.
    # Give them 0.3 mm radial clearance through the integral seating ring.
    tools.extend(cyl(5.3, 3.4, (110.8, y, z), (1, 0, 0))
                 for y, z in SCREEN_PADS)
    # Simple isolated parallel slots, with a solid spine above the IMU.
    for x in (-66., -54., -42., 42., 54., 66.):
        for side in (-1, 1):
            y = -48. if side < 0 else 22.
            tools.append(box(x-2., y, 96.8, 4., 26., 3.4))
    for side in (-1, 1):
        for z in (57., 66., 75.):
            for x0, x1 in ((-78., -32.), (-6., 62.)):
                tools.append(core.rounded_pocket_xz(x0, x1, z-1.7, z+1.7,
                                                   78.8 if side > 0 else -82.2,
                                                   3.4, 1.5))
    for z in (55., 64., 73., 82.):
        tools.append(core.rounded_pocket_yz(-49., 49., z-2., z+2., -94.2, 3.4, 1.8))
    return tools


def _shell_pair():
    outer = _outer()
    shape = cut(outer, [_inner()])
    lip = outer.common(box(-100., -90., -55., 225., 180., 5.))
    aperture = core.prior._rounded_prism(170., 140., 7., -56., 6.)
    additions = [cut(lip, [aperture])]
    # The front-face ring is joined to all four shell walls, rather than
    # floating against the cosmetic panel pocket. Its broad rear seat is X114.
    ring = core.rounded_pocket_yz(-80., 80., -53., 98., 111., 3., 4.)
    additions.append(ring.common(outer))
    for side in (-1, 1):
        additions.extend(cyl(8., 11., (x, 75*side, z), (0, side, 0))
                         for x, z in SHOULDER_FASTENERS)
    for y, z in SHELL_FASTENERS:
        # Tighten these four front screws through the open whole front face.
        # The X97 head ends remain behind the display's X99.5 rear surface.
        additions.extend((cyl(5., 8., (86., y, z), (1, 0, 0)),
                          box(86., 57. if y > 0 else -80., z-5., 8., 23., 10.),
                          cyl(5., 8., (-94., y, z), (1, 0, 0))))
    shape = fuse([shape]+additions)
    shape = cut(shape, _body_cutters())
    # Corner bosses are added after the large module opening. Captive M3 nuts
    # are loaded from inside while the panel is off; steel, not PETG threads.
    bosses = [cyl(4.5, 7., (107., y, z), (1, 0, 0)) for y, z in FACE_FASTENERS]
    shape = fuse([shape]+bosses)
    cutters = []
    for y, z in FACE_FASTENERS:
        cutters.extend((cyl(1.7, 7.4, (106.8, y, z), (1, 0, 0)),
                        _hex_x(106.8, y, z, 5.8, 2.8)))
    for y, z in SHELL_FASTENERS:
        cutters.extend((cyl(1.7, 8.4, (85.8, y, z), (1, 0, 0)),
                        cyl(1.7, 8.4, (-94.2, y, z), (1, 0, 0))))
    cutters.extend(cyl(4., 6., (x, y, -55.5)) for x, y in BOTTOM_FASTENERS)
    shape = cut(shape, cutters)
    front = shape.common(box(SPLIT_X, -90., -60., 145., 180., 170.)).removeSplitter()
    rear = shape.common(box(-100., -90., -60., 80., 180., 170.)).removeSplitter()
    guide = cut(_inner(2.8, 97.2), [_inner(5., 95.)])
    guide = guide.common(box(-24., -90., -54.8, 4.5, 180., 160.))
    guide = cut(guide, _body_cutters())
    front = fuse([front, guide])
    receiver = _inner(2.5, 97.5).common(box(-24.3, -90., -55.2, 4.4, 180., 160.))
    rear = cut(rear, [receiver])
    return front, rear


def _shoulder(right=True):
    return prior._shoulder(right)


def materials():
    result = prior.materials()
    result['display_front_bezel'] = 'PETG'
    return result


def build_chassis(lightweight=True):
    front, rear = _shell_pair()
    parts = {
        'chassis_belly_plate': prior._bottom(lightweight),
        'chassis_hip_frame_right': _side(True, lightweight),
        'chassis_hip_frame_left': _side(False, lightweight),
        'chassis_front_crossframe': prior._crossframe(True, lightweight),
        'chassis_rear_crossframe': prior._crossframe(False, lightweight),
        'chassis_front_shell': front, 'chassis_rear_cover': rear,
        'display_front_bezel': _face(),
        'shoulder_fairing_right': _shoulder(True),
        'shoulder_fairing_left': _shoulder(False),
        'battery_tray': core.prior._battery_tray(),
        'electronics_tray': prior._tray(),
    }
    parts.update(prior.jetson_mount.designs())
    for name, shape in parts.items():
        core._check(name, shape)
    return parts


def chassis_hardware():
    items = list(prior.jetson_mount.hardware())
    for side in (-1, 1):
        for i, (x, z) in enumerate(SHOULDER_FASTENERS):
            screw = fuse([cyl(1.5, 14., (x, 75*side, z), (0, side, 0)),
                          cyl(2.75, 3., (x, 89*side, z), (0, side, 0))])
            items.append((f'shoulder_{side}_M3x20_{i}', screw, 'fixed'))
    for i, (y, z) in enumerate(SHELL_FASTENERS):
        front = fuse([cyl(1.5, 8., (86., y, z), (1, 0, 0)),
                      cyl(2.75, 3., (94., y, z), (1, 0, 0))])
        rear = fuse([cyl(1.5, 8., (-94., y, z), (1, 0, 0)),
                     cyl(2.75, 3., (-97., y, z), (1, 0, 0))])
        items.extend(((f'front_shell_M3x14_{i}', front, 'fixed'),
                      (f'rear_cover_M3x14_{i}', rear, 'fixed')))
    for i, (y, z) in enumerate(FACE_FASTENERS):
        screw = fuse([cyl(1.5, 12., (105., y, z), (1, 0, 0)),
                      cyl(2.75, 3., (117., y, z), (1, 0, 0))])
        nut = cut(_hex_x(107.2, y, z, 5.5, 2.4),
                  [cyl(1.5, 2.8, (107., y, z), (1, 0, 0))])
        items.extend(((f'front_face_M3x12_{i}', screw, 'fixed'),
                      (f'front_face_M3_nut_{i}', nut, 'fixed')))
    return items


def fastener_specification():
    specs = prior.fastener_specification()
    for spec in specs:
        if spec['location'] == 'continuous front shell to front crossframe':
            spec.update(spec='M3x14 socket', grip=8, engagement=6,
                        access='through whole front face before screen/camera panel installation; modeled grip and head',
                        head_seat_x=94, head_end_x=97, screen_rear_x=99.5)
        elif spec['location'] == 'large rear cover to rear crossframe':
            spec.update(spec='M3x14 socket', grip=8, engagement=6,
                        access='rear outside; modeled grip and head', head_seat_x=-94)
    specs.extend((
        dict(location='complete front face to shell', quantity=4,
             spec='M3x12 socket + captive AF5.5 M3 nut thickness2.4',
             centres_yz=FACE_FASTENERS, panel_x=[114, 117], boss_x=[107, 114],
             nut_x=[107.2, 109.6], hole_diameter=3.4,
             access='front outside; load captive nuts before panel; modeled'),
        dict(location='IMU bridge feet to upper sideframe beams', quantity=4,
             spec='M3x8 socket; grip3, engagement5', centres_xy=IMU_BRIDGE_HOLES,
             tapping_face_z=47, tapping_pilot_diameter=2.5, tapping_depth=6,
             note='V7 holes retained; bridge module owns fasteners'),
    ))
    return specs


def export_review(folder):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    parts, hardware = build_chassis(), chassis_hardware()
    report = dict(
        units='mm', source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        architecture='Six planar main faces; small R5 edge fillets; one full-height enclosure; vertical X-20 service split; detachable complete front face',
        body=dict(bounds=BODY_BOUNDS, size=[211, 164, 155], edge_radius=5,
                  wall=3, roof_inner_z=97, face_panel_bounds=[114, -74, -49, 117, 74, 95]),
        parts={}, collisions=[], hardware_collisions=[], fasteners=fastener_specification(),
        display=dict(front_panel_x=117, front_glass_x=114, rear_x=99.5, centre_z=-4,
                     body_size_yz=[122, 78], thickness=14.5,
                     device_aperture_yz=[123, 79], full_front_panel_yz=[148, 144],
                     pads=SCREEN_PADS, pad_contact_x=114, hole_diameter=3.4,
                     front_corner_stop_case_overlap=.5,
                     unknowns='No active-area, mounting-hole, rim or connector coordinates supplied. Four provisional stops require a metal rim and must not press glass; verify on actual unit before manufacture.'),
        camera=dict(front_x=117, centre_z=61, window_y=[-45.3, 45.3],
                    window_z=[48.2, 73.8], pad_contact_x=114, pads=CAMERA_PADS),
        electronics=dict(tray_x=[-86, 66], tray_y=[-54, 54], tray_z=[30, 33],
                         tray_support_centres=TRAY_FASTENERS),
        imu=dict(bridge_holes_xy=IMU_BRIDGE_HOLES, metal_face_z=47,
                 nominal_origin_xyz=[0, 0, 85], roof_inner_z=97),
        shoulder=dict(y_range=[78.2, 130], inner_radius=33, outer_radius=36,
                      body_mount_y=86, geometry='V6 smooth arc unchanged'),
        qualification='Local rigid chassis geometry only; full payload and leg checks belong to integrated build. Not a strength, impact, print-fit or thermal qualification.')
    for name, shape in parts.items():
        bb = shape.BoundBox
        report['parts'][name] = dict(valid=shape.isValid(), solids=len(shape.Solids),
                                    volume_mm3=shape.Volume,
                                    bbox=[bb.XMin, bb.YMin, bb.ZMin, bb.XMax, bb.YMax, bb.ZMax])
    named = list(parts.items())
    for i, (an, a) in enumerate(named):
        for bn, b in named[i+1:]:
            if a.BoundBox.intersect(b.BoundBox):
                volume = a.common(b).Volume
                if volume > .001:
                    report['collisions'].append(dict(a=an, b=bn, volume=volume))
    for hn, h, _ in hardware:
        for pn, p in named:
            if h.BoundBox.intersect(p.BoundBox):
                volume = h.common(p).Volume
                if volume > .001:
                    report['hardware_collisions'].append(dict(hardware=hn, part=pn, volume=volume))
    report['bare_screen_insertion'] = dict(
        method='Exact 122 x78 case sweep along X with front face removed; carrier/camera integrated path checked separately',
        overlap_mm3=box(99.5, -61, -43, 60, 122, 78).common(parts['chassis_front_shell']).Volume)
    report['bare_screen_insertion']['pass_geometry'] = report['bare_screen_insertion']['overlap_mm3'] < .001
    report['metal_geometry_retained'] = dict(
        base='V6 metal parts plus the identical V7 four M3 IMU bridge pilot holes',
        legs='No leg, flange, wheel or motor transform edited by this module')
    (folder/'chassis_review.json').write_text(json.dumps(report, indent=2)+'\n')
    return report


if __name__ == '__main__':
    out = Path(__file__).resolve().parents[1]/'mechanical/v8'
    result = export_review(out)
    print(json.dumps({k: result[k] for k in ('parts', 'collisions', 'hardware_collisions', 'bare_screen_insertion')}, indent=2))
