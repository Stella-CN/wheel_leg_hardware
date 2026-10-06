"""V8.1 enclosure with preferred-length standard fasteners.

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
import cad_v81_battery as battery

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
        # M3x12: 6 mm PETG grip + 6 mm metal engagement. Front heads endX95.
        additions.extend((cyl(5., 6., (86., y, z), (1, 0, 0)),
                          box(86., 57. if y > 0 else -80., z-5., 6., 23., 10.),
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
                        cyl(1.7, 8.4, (-94.2, y, z), (1, 0, 0)),
                        cyl(3.2, 2.2, (-94.2, y, z), (1, 0, 0))))
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


def _jetson_retainers():
    """Keep the tray screws accessible with the Jetson module preassembled.

    At rearX-74 the screw centre is at the existing arm edge, so a round
    open notch leaves the arm's outer4.8mm web. The frontX38 hole is central;
    an integralD11 pad preserves a2.3mm wall around itsD6.4 opening.
    """
    parts=prior.jetson_mount.designs()
    for name,shape in parts.items():
        side=1 if name.endswith('right') else -1
        shape=fuse([shape,cyl(5.5,3.,(38.,48.*side,33.))])
        parts[name]=cut(shape,[cyl(3.2,3.4,(x,48.*side,32.8))
                               for x in (-74.,38.)]+
                              [cyl(1.7,9.4,(-74.,48.*side,32.8))])
    return parts


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
        'battery_tray': battery.tray(),
        'electronics_tray': prior._tray(),
    }
    parts.update(_jetson_retainers())
    for name, shape in parts.items():
        core._check(name, shape)
    return parts


def chassis_hardware():
    items = list(prior.jetson_mount.hardware())
    # Previously omitted frame/tray screws are now visible and traceable.
    # The threaded engagement inside metal is intentionally omitted, as in
    # the retained V6 hardware, because tap pilots are not modeled threads.
    for i,(x,y) in enumerate(BOTTOM_FASTENERS):
        items.append((f'belly_frame_DIN7991_M3x8_{i}',
                      _countersunk_free_grip((x,y,-50.),(0,0,1)),'fixed'))
    for side in (-1,1):
        for i,(x,z) in enumerate(( (x,z) for x in (-82.,82.) for z in (-25.,25.) )):
            items.append((f'crossframe_DIN7991_M3x8_{side}_{i}',
                          _countersunk_free_grip((x,75.*side,z),(0,-side,0)),'fixed'))
    for tag,points,base in (('battery_tray',core.BATTERY_FASTENERS,-39.),
                            ('electronics_tray',TRAY_FASTENERS,30.)):
        for i,(x,y) in enumerate(points):
            screw=fuse([cyl(1.5,3.,(x,y,base)),cyl(2.75,3.,(x,y,base+3.))])
            items.append((f'{tag}_M3x8_{i}',screw,'fixed'))
    for side in (-1, 1):
        for i, (x, z) in enumerate(SHOULDER_FASTENERS):
            screw = fuse([cyl(1.5, 14., (x, 75*side, z), (0, side, 0)),
                          cyl(2.75, 3., (x, 89*side, z), (0, side, 0))])
            items.append((f'shoulder_{side}_M3x20_{i}', screw, 'fixed'))
    for i, (y, z) in enumerate(SHELL_FASTENERS):
        front = fuse([cyl(1.5, 6., (86., y, z), (1, 0, 0)),
                      cyl(2.75, 3., (92., y, z), (1, 0, 0))])
        rear = fuse([cyl(1.5, 6., (-92., y, z), (1, 0, 0)),
                     cyl(2.75, 3., (-95., y, z), (1, 0, 0))])
        items.extend(((f'front_shell_M3x12_{i}', front, 'fixed'),
                      (f'rear_cover_M3x12_{i}', rear, 'fixed')))
    for i, (y, z) in enumerate(FACE_FASTENERS):
        screw = fuse([cyl(1.5, 12., (105., y, z), (1, 0, 0)),
                      cyl(2.75, 3., (117., y, z), (1, 0, 0))])
        nut = cut(_hex_x(107.2, y, z, 5.5, 2.4),
                  [cyl(1.5, 2.8, (107., y, z), (1, 0, 0))])
        items.extend(((f'front_face_M3x12_{i}', screw, 'fixed'),
                      (f'front_face_M3_nut_{i}', nut, 'fixed')))
    return items


def _countersunk_free_grip(face,inward):
    """DIN7991 selected D6/k1.7 head in a D6.4 90-degree countersink.

    Overall length8 includes the head, metal grip3, nominal insertion5.
    ISO10642 can have a larger head and is not a drop-in procurement option.
    """
    p,n=V(*face),V(*inward)
    return fuse([Part.makeCylinder(3.,.2,p,n),
                 Part.makeCone(3.,1.5,1.5,p+n*.2,n),
                 Part.makeCylinder(1.5,1.3,p+n*1.7,n)])


def fastener_specification():
    specs = prior.fastener_specification()
    for spec in specs:
        if spec['location'] in ('belly plate to CNC side ledges',
                                'side frames to front/rear crossframe rails'):
            spec.update(spec='DIN7991 M3x8; selected headD6 k1.7, not unrestricted ISO10642',
                        access=spec['access'].replace('unmodeled','modeled free grip/head'))
        if spec['location'] in ('battery tray to belly posts',
                                'electronics tray to side-frame shelves'):
            spec.update(spec='ISO4762 M3x8',
                        access=spec['access'].replace('unmodeled','modeled free grip/head'))
        if spec['location'] == 'continuous front shell to front crossframe':
            spec.update(spec='ISO4762 M3x12', grip=6, engagement=6,
                        access='through whole front face before screen/camera panel installation; modeled grip and head',
                        head_seat_x=92, head_end_x=95, screen_rear_x=99.5)
        elif spec['location'] == 'large rear cover to rear crossframe':
            spec.update(spec='ISO4762 M3x12', grip=6, engagement=6,
                        access='rear outside, D6.4x2 recess; modeled grip and head', head_seat_x=-92)
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
        battery_source_sha256=hashlib.sha256(Path(battery.__file__).read_bytes()).hexdigest(),
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


def export_detail_review(folder):
    """Review new local joints and assembly access, independently of exports."""
    import cad_v81_payload as payload
    folder=Path(folder)
    parts=build_chassis()
    parts.update(payload.designs())
    hardware=dict((n,s) for n,s,_ in chassis_hardware()+payload.hardware())
    devices=dict((n,s) for n,s,_,_ in payload.payloads())
    sources=('cad_v81_chassis.py','cad_v81_payload.py','cad_v81_display.py','cad_v81_battery.py',
             'cad_v6_chassis.py','cad_v6_jetson_mount.py','cad_v7_payload.py')
    report=dict(source_hashes={n:hashlib.sha256((Path(__file__).parent/n).read_bytes()).hexdigest()
                              for n in sources}, checks=[],failures=[],units='mm')
    def overlap(a,b):
        if not a.BoundBox.intersect(b.BoundBox):return 0.
        return sum(aa.common(bb).Volume for aa in a.Solids for bb in b.Solids
                   if aa.BoundBox.intersect(bb.BoundBox))
    def record(name,passed,**data):
        report['checks'].append(dict(name=name,passed=bool(passed),**data))
        if not passed:report['failures'].append(name)
    collisions=[]
    all_parts={**parts,**devices}
    for hn,h in hardware.items():
        for pn,p in all_parts.items():
            volume=overlap(h,p)
            if volume>.001:collisions.append(dict(hardware=hn,part=pn,volume_mm3=volume))
    record('all_body_hardware_to_parts_and_devices',not collisions,collisions=collisions,
           representation='Nominal head/grip; metal screw engagement omitted where pilot holes are not true threads.')
    for depth in (25.05,26.05):
        rear=117.-depth
        b=payload.camera_bracket(depth)
        # Accurate rear-plane variant of the same dimensional clearance body.
        camera=box(rear,-45.075,48.425,depth,90.15,25.15)
        camera=cut(camera,[cyl(1.6,3.1,(rear-.1,y,61.),(1,0,0)) for y in (-22.5,22.5)])
        rows=[]
        for n,s,_ in payload.camera_hardware(depth):
            rows.append(dict(name=n,bracket_overlap=overlap(s,b),camera_overlap=overlap(s,camera)))
        record(f'D435_{depth}_standard_M3x8_chain',
               all(r['bracket_overlap']<.001 and r['camera_overlap']<.001 for r in rows),
               camera_front_x=117.,camera_rear_x=rear,bracket_back_x=rear-6.,
               bracket_grip=6.,screw_under_head_length=8.,nominal_insertion=2.,
               maximum_insertion=3.,rows=rows)
    aliases=[]
    for canonical,second in (('chassis_front_crossframe','chassis_rear_crossframe'),
                             ('shoulder_fairing_right','shoulder_fairing_left')):
        rotated=parts[canonical].copy();rotated.rotate(V(),V(0,0,1),180.)
        error=rotated.cut(parts[second]).Volume+parts[second].cut(rotated).Volume
        aliases.append(dict(canonical=canonical,instances=[canonical,second],quantity=2,
                            transform='rotation180degrees_about_worldZ',symmetric_difference_mm3=error,
                            passed=error<1e-6))
    (folder/'manufacturing_aliases.json').write_text(json.dumps(dict(
        aliases=aliases,source_hashes=report['source_hashes'],
        note='One manufacturing SKU, two assembly instances. Other mirrored parts remain separate.'),indent=2)+'\n')
    record('common_manufacturing_parts_by_rigid_transform',all(r['passed'] for r in aliases),rows=aliases)
    access=[]
    for x,y in TRAY_FASTENERS:
        tool=cyl(1.5,70.,(x,y,36.))
        hits=[]
        for n,s in {**parts,**devices}.items():
            if n.startswith(('chassis_front_shell','chassis_rear_cover')):continue
            vol=overlap(tool,s)
            if vol>.001:hits.append(dict(part=n,volume=vol))
        access.append(dict(x=x,y=y,tool_diameter=3.,tool_bottom_z=36.,hits=hits))
    record('preassembled_Jetson_tray_top_driver_access',not any(r['hits'] for r in access),rows=access,
           assembly_state='Body shell and front face absent; IMU bridge may be present; tray module complete.')
    # Support contact and retained side walls: new pads must not enter the
    # original NVIDIA kit, and each retainer must remain a single solid.
    rows=[]
    for n in ('Jetson_base_retainer_right','Jetson_base_retainer_left'):
        s=parts[n]
        rows.append(dict(name=n,valid=s.isValid(),solids=len(s.Solids),
                         kit_overlap_mm3=overlap(s,devices['Jetson_Orin_Nano_official'])))
    record('integral_retainer_access_reliefs',all(r['valid'] and r['solids']==1 and r['kit_overlap_mm3']<.001 for r in rows),rows=rows,
           front_remaining_radial_wall=2.3,rear_min_remaining_arm_width=4.8)
    # Nut seats close the force path; a pocket with excess depth must not
    # leave the nut floating away from its bearing shoulder.
    contacts=[]
    for i,(y,z) in enumerate(SCREEN_PADS):
        nut=hardware[f'display_case_M3_nut_{i}']
        carrier=parts['display_case_cradle_right' if y>0 else 'display_case_cradle_left']
        faces_a=[f for f in nut.Faces if f.BoundBox.XLength<1e-6 and abs(f.BoundBox.XMin-101.)<1e-6]
        faces_b=[f for f in carrier.Faces if f.BoundBox.XLength<1e-6 and abs(f.BoundBox.XMin-101.)<1e-6]
        area=sum(a.common(b).Area for a in faces_a for b in faces_b)
        contacts.append(dict(y=y,z=z,nut_bearing_area_mm2=area,thread_projection_mm=1.6))
    record('M3x20_display_captive_nut_bearing',all(r['nut_bearing_area_mm2']>10 for r in contacts),rows=contacts)
    report['pass_all']=not report['failures']
    report['limitations']=['Discrete local geometry and tool-envelope checks, not strength or vibration qualification.',
                          'Real screen rim, cable plugs and battery specification still require measurement.',
                          'Nominal fastener CAD is not a vendor tolerance-envelope model; purchase sizes are separately controlled.']
    (folder/'body_detail_review.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__ == '__main__':
    out = Path(__file__).resolve().parents[1]/'mechanical/v8_1'
    result = export_review(out)
    print(json.dumps({k: result[k] for k in ('parts', 'collisions', 'hardware_collisions', 'bare_screen_insertion')}, indent=2))
