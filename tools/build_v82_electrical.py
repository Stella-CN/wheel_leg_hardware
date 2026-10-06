"""Integrate supplied electronics into the unchanged V8.1 robot kinematics.

FreeCAD system Python; dimensions in mm. Vendor geometry, dimensional
envelopes and routing allowances remain explicitly distinguishable.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
from pathlib import Path

import build_printable_robot as cad
import cad_v81_chassis as body

App, Part, V = cad.App, cad.Part, cad.V
ROOT = cad.ROOT
BASE = ROOT / 'mechanical/v8_1'
OUT = ROOT / 'mechanical/v8_2'
box = cad.box
union, cut = cad.union, cad.cut
NEW = []
HARDWARE = []


def cyl(r, h, p, n=(0, 0, 1)):
    return Part.makeCylinder(r, h, V(*p), V(*n))


def hexagon(p, n, af, depth):
    vertices = [V(af / math.sqrt(3) * math.cos(math.pi / 6 + i * math.pi / 3),
                  af / math.sqrt(3) * math.sin(math.pi / 6 + i * math.pi / 3), 0)
                for i in range(6)]
    s = Part.Face(Part.makePolygon(vertices + [vertices[0]])).extrude(V(0, 0, depth))
    s.Placement = App.Placement(V(*p), App.Rotation(V(0, 0, 1), V(*n)))
    return s


def fastener(name, p, n, size, length, module, washer=False):
    """Full bolt, plain nut and optional washer; ISO basic envelope."""
    d, head, height, af, nut_h = {
        'M3': (3., 5.5, 3., 5.5, 2.4),
        'M2.5': (2.5, 4.5, 2.5, 5., 2.),
        'M1.6': (1.6, 3., 1.6, 3.2, 1.3),
    }[size]
    # p is the under-head seat, n points into the grip.
    direction = V(*n)
    s = union(cyl(d / 2, length, p, n),
              Part.makeCylinder(head / 2, height, V(*p), -direction))
    HARDWARE.append((name, s, 'ISO4762', size + 'x' + str(length), module))
    return s


def nut(name, p, n, size, module):
    d, af, height = {'M3': (3., 5.5, 2.4), 'M2.5': (2.5, 5., 2.),
                     'M1.6': (1.6, 3.2, 1.3)}[size]
    s = cut(hexagon(p, n, af, height), cyl(d / 2, height, p, n))
    HARDWARE.append((name, s, 'ISO4032', size, module))
    return s


def washer(name, p, n, size, module):
    inside, outside, thick = {'M3': (3.2, 7., .5), 'M2.5': (2.7, 6., .5)}[size]
    s = cut(cyl(outside / 2, thick, p, n), cyl(inside / 2, thick, p, n))
    HARDWARE.append((name, s, 'ISO7089', size, module))
    return s


def add(doc, name, shape, module='M07', material='PETG', note='', mass=None):
    assert not shape.isNull() and shape.isValid(), name
    o = cad.put(doc, doc.getObject(module), name, shape, 'fixed', material, None, note)
    o.addProperty('App::PropertyString', 'AssemblyModule', 'Manufacturing')
    o.AssemblyModule = module
    if mass is not None:
        o.addProperty('App::PropertyFloat', 'BudgetMassGrams', 'Manufacturing')
        o.BudgetMassGrams = mass
    NEW.append(o.Name)
    return o


def switch_shapes():
    x, y = 60., 0.
    # 47.5 total from outer cap Z101.5; thread is not a meshed helix.
    thread = cyl(8., 13.5, (x, y, 100), (0, 0, -1))
    flange = cyl(8.9, 1.5, (x, y, 100))
    lower = box(x - 8, y - 8, 66.5, 16, 16, 20.)
    harness_socket = box(x - 9, y - 9, 54., 18., 18., 12.5)
    cap = cyl(6.6, .3, (x, y, 101.5))
    locknut = cut(hexagon((x, y, 94), (0, 0, 1), 19., 3.),
                  cyl(8.05, 3., (x, y, 94)))
    return Part.makeCompound([thread, flange, lower, harness_socket, cap, locknut])


def hub_shapes():
    shape = box(-91., -52., 0., 30., 104., 10.)
    holes = [box(-91.1, -52 + 19.14 + i * 19.68, 2.6, 3., 12.68, 4.8)
             for i in range(4)]
    return cut(shape, *holes)


def rear_interfaces(doc):
    """Hub rear face against inside panel, port window exposes all four ports."""
    rear = doc.chassis_rear_cover.Shape.copy()
    # One window avoids treating the approximate USB aperture heights as
    # supplier machining dimensions; case retained on its unused front rim.
    rear = cut(rear, body.core.rounded_pocket_yz(-49., 49., .7, 9.3, -94.2, 3.4, .6))
    # Hub shelf + front stop are integrated into the rear shell. A removable
    # open bridge presses on the back of the housing, never on a connector.
    shelf = box(-91.1, -54.5, -3., 39.6, 109., 3.)
    sides = [box(-91.1, y, -3., 21.1, 2., 13.3) for y in (-54.5, 52.5)]
    rear = union(rear, shelf, *sides)
    hubscrews = [(-56., -47.), (-56., 47.)]
    bosses = [cyl(5., 8., (x, y, -3.)) for x, y in hubscrews]
    webs = []
    rear = union(rear, *bosses, *webs)
    # Nut pockets entered from below while cover is off.
    rear = cut(rear, *[cyl(1.7, 9., (x, y, -3.2)) for x, y in hubscrews],
               *[hexagon((x, y, -3.1), (0, 0, 1), 5.8, 3.3) for x, y in hubscrews])
    clamp = union(box(-63.5, -52.25, 10.5, 5., 104.5, 2.5),
                  box(-61., -52.25, 0., 2.5, 104.5, 13.))
    for x, y in hubscrews:
        clamp = union(clamp, cyl(5., 8., (x, y, 5.)), box(-63.5, y-4., 10.5, 12., 8., 2.5))
        clamp = cut(clamp, cyl(1.7, 8.4, (x, y, 4.8)))
    # Rear-view lower right = negative Y. Removable plate has a deliberately
    # undersize pilot, not a fictitious final DC jack diameter.
    rear = cut(rear, body.core.rounded_pocket_yz(-55, -37, -32, -18, -94.2, 3.4, 2.))
    plate = body.core.rounded_pocket_yz(-63, -29, -36, -14, -96.5, 2.5, 2.)
    plate = cut(plate, cyl(1.5, 3., (-96.7, -46, -25), (1, 0, 0)))
    for i, y in enumerate((-59., -33.)):
        rear = union(rear, cyl(4.5, 6., (-94, y, -25), (1, 0, 0)))
        rear = cut(rear, cyl(1.7, 6.4, (-94.2, y, -25), (1, 0, 0)),
                   hexagon((-90.8, y, -25), (1, 0, 0), 5.8, 2.9))
        plate = cut(plate, cyl(1.7, 3., (-96.7, y, -25), (1, 0, 0)))
        fastener('V82_DC_plate_screw_%d' % i, (-96.5, y, -25), (1, 0, 0), 'M3', 10, 'M06')
        nut('V82_DC_plate_nut_%d' % i, (-90.6, y, -25), (1, 0, 0), 'M3', 'M06')
    for i, (x, y) in enumerate(hubscrews):
        clamp = cut(clamp, cyl(5.2, 5.2, (x,y,-.2)))
        fastener('V82_hub_clamp_screw_%d' % i, (x, y, 13), (0, 0, -1), 'M3', 16, 'M06')
        nut('V82_hub_clamp_nut_%d' % i, (x, y, -2.4), (0, 0, 1), 'M3', 'M06')
    doc.chassis_rear_cover.Shape = Part.makeCompound([rear.removeSplitter()])
    add(doc, 'USB_hub_rear_clamp', clamp, 'M06', note='PETG one-piece; open housing backstop. Use 0.5mm anti-rattle pads at upper edge.')
    add(doc, 'DC_charge_replaceable_plate', plate, 'M06', note='PETG; rear-view lower right; D3 pilot atY-46/Z-25. Enlarge/replace only after jack drawing is known.')
    add(doc, 'USB_hub_104x30x10', hub_shapes(), 'M08', 'payload',
        'User dimensional envelope; USB face -X, 150mm upstream cable exits +Y. Four apertures illustrate only; height not dimensioned.', 60.)


def board_and_converter(doc):
    bare_path = OUT / 'source/board_model_inspection_usb2can_bare.step'
    if not bare_path.exists():
        raise FileNotFoundError('Run inspect_v82_board_models first: ' + str(bare_path))
    can = Part.read(str(bare_path))
    can.rotate(V(), V(0,0,1), 90.)
    can.translate(V(60, -27, 40))  # PCB bottom2 +40 =42; TypeC to-Y.
    pcb_path = OUT / 'source/electrical/3D_PCB1_2026-09-28.step'
    if not pcb_path.exists():
        pcb_path = ROOT / 'references/user_supplied/3D_PCB1_2026-09-28.step'
    pcb = Part.read(str(pcb_path))
    b = pcb.BoundBox
    source_min_x, source_min_y = b.XMin, b.YMin
    pcb.rotate(V(), V(1,1,1), 120.)  # X->Y, Y->Z, Z->X.
    pcb.rotate(V(), V(1,0,0), 180.)  # DC input faces up, away from battery ear.
    b = pcb.BoundBox
    pcb_shift = V(66., 5 - b.YMin, -13 - b.ZMin)
    pcb.translate(pcb_shift)
    can_holes = [(60 - y, -27 + x) for x in (-13.05, 13.95) for y in (-9., 9.)]
    pcb_holes = [(pcb_shift.y - x, pcb_shift.z - y)
                 for x in (2.413005, 29.464059) for y in (-2.540005, -36.576073)]
    # One service module carries two boards and converter, leaving the
    # central lane Y-6..5 for switch/low-current leads.
    plate = box(47., -46, 36, 29, 96, 2.)
    plate = union(plate, box(60, 2, -16, 3, 39, 54))
    doc.electronics_tray.Shape = cut(doc.electronics_tray.Shape,box(59.7,1.7,29.8,3.6,39.6,3.4),
                                     cyl(5.,3.4,(51.,-1.,29.8)))
    feet = [(49., -30.), (62., -30.), (49., 47.), (62., 47.)]
    for x, y in feet:
        plate = union(plate, cyl(4.5, 5., (x, y, 33)))
        plate = cut(plate, cyl(1.7, 5.4, (x, y, 32.8)))
        # New through holes in existing PETG tray; nuts accessible underside
        # before the electronics module enters the body.
        doc.electronics_tray.Shape = cut(doc.electronics_tray.Shape,
                                         cyl(1.7, 3.4, (x, y, 29.8)))
        i = len([r for r in HARDWARE if r[0].startswith('V82_carrier_screw')])
        fastener('V82_carrier_screw_%d' % i, (x, y, 38), (0, 0, -1), 'M3', 12, 'M07')
        nut('V82_carrier_nut_%d' % i, (x, y, 27.6), (0, 0, 1), 'M3', 'M07')
    for tag, centres, height, radius, size, length in (
            ('CAN', can_holes, 4., 1.0, 'M1.6', 10),):
        for i, (x, y) in enumerate(centres):
            plate = union(plate, cyl(3.5, height, (x, y, 38)))
            plate = cut(plate, cyl(radius, height + 2.4, (x, y, 35.8)))
            seat = 38 + height + 1.6001
            if tag == 'PCB':
                washer('V82_PCB_washer_%d' % i, (x, y, seat), (0, 0, 1), size, 'M07')
                seat += .5
            fastener('V82_%s_screw_%d' % (tag, i), (x, y, seat), (0, 0, -1), size, length, 'M07')
            nut_height = 1.3 if tag == 'CAN' else 2.
            nut('V82_%s_nut_%d' % (tag, i), (x, y, 36 - nut_height), (0, 0, 1), size, 'M07')
    for i, (y, z) in enumerate(pcb_holes):
        plate = union(plate, cyl(3.5, 3., (63,y,z),(1,0,0)))
        plate = cut(plate, cyl(1.35, 6.4, (59.8,y,z),(1,0,0)))
        fastener('V82_PCB_screw_%d' % i,(67.6001,y,z),(-1,0,0),'M2.5',12,'M07')
        nut('V82_PCB_nut_%d' % i,(58.,y,z),(1,0,0),'M2.5','M07')
    # Converter body45x25x20, two mounting ears58 overall, D4 at51 pitch.
    converter = box(28.5, -68, 54, 45., 25., 20.)
    for x in (25.5, 76.5):
        converter = union(converter, cyl(3.5, 2., (x, -55.5, 54)))
        converter = cut(converter, cyl(2., 2.4, (x, -55.5, 53.8)))
        # Integrated arms are outside the side-frame top Z47 and connect
        # to the plate at Y-36; no new metal side-frame drilling.
        plate = union(plate, box(x - 4., -59.5, 51., 8., 26., 3.))
        if x > 50:
            plate = union(plate,box(x - 4., -46., 36., 8., 5., 18.))
        plate = cut(plate, cyl(1.7, 3.4, (x, -55.5, 50.8)))
        i = int(x > 50)
        fastener('V82_DCDC_screw_%d' % i, (x, -55.5, 56), (0, 0, -1), 'M3', 8, 'M07')
        nut('V82_DCDC_nut_%d' % i, (x, -55.5, 48.6), (0, 0, 1), 'M3', 'M07')
    # Cable tie slots in the accessible edge; no unsupported adhesive clips.
    for y in (-3., 18., 35.):
        plate = cut(plate, box(70., y - 2., 35.8, 4., 1.5, 2.4))
    plate = cut(plate, box(48., -5., 35.8, 29., 7., 2.4))
    # Connector corridor immediately ahead of Jetson: retain a perimeter
    # frame, not a solid floor against low USB/DP/C sockets.
    plate = cut(plate, box(30., -29., 35.8, 16., 67., 2.4))
    plate = union(plate,box(21.5,-59.5,51,59.,8.,3.))
    # Drill after every web/post addition so no later union refills a bore.
    for x,y in feet:
        plate = cut(plate,cyl(1.7,6,(x,y,32.5)),cyl(3.,4,(x,y,38)))
    for x,y in can_holes:
        plate = cut(plate,cyl(1.,7,(x,y,35.5)))
    for y,z in pcb_holes:
        plate = cut(plate,cyl(1.35,7,(59.5,y,z),(1,0,0)))
    for x in (25.5,76.5):
        plate = cut(plate,cyl(1.7,4,(x,-55.5,50.5)))
    add(doc, 'electrical_service_carrier', plate.removeSplitter(), 'M07', note='PETG integrated board standoffs and converter ears; preassemble outside. Maintain 3mm underside nut/tool gap.')
    add(doc, 'USB2CANFD_Dual_bare_official', can, 'M07', 'payload', 'Provided vendor STEP, electronics solids only; case, case screws and light guides removed. D2 board holes use M1.6.', 18.)
    add(doc, 'Distribution_PCB1_user_STEP', pcb, 'M07', 'payload', 'User STEP; 4xD3 holes retained, M2.5 clearance fixing. Copper nets and electrical pin mapping not encoded in STEP.', 18.)
    add(doc, 'DCDC_24_to_19_drawing_envelope', converter, 'M07', 'payload', 'Body45x25x20,58 total,51 pitch/D4 from user. Tab thickness2 provisional; actual power/input range unconfirmed.', 65.)
    return dict(can_holes_xy=can_holes, pcb_holes_yz=pcb_holes, carrier_holes=feet,
                can_rotation_z_deg=90., can_translation=[60,-27,40],
                pcb_rotation_axis=[1,1,1],pcb_rotation_deg=120.,pcb_additional_rotation_x_deg=180.,pcb_translation=list(pcb_shift),
                dcdc_holes=[[25.5,-55.5],[76.5,-55.5]])


def signature(obj):
    b = obj.Shape.BoundBox
    return dict(volume=obj.Shape.Volume, area=obj.Shape.Area,
                bounds=[getattr(b, k) for k in ('XMin','YMin','ZMin','XMax','YMax','ZMax')],
                expressions=list(obj.ExpressionEngine))


def prepare():
    OUT.mkdir(exist_ok=True)
    for directory in ('cnc','step','print','manufacturing','metal_hardware','stl','alternates','source'):
        source = BASE / directory
        if source.exists():
            shutil.copytree(source, OUT / directory, dirs_exist_ok=True)
    for name in ('design_parameters.json','part_manifest.json','manufacturing_aliases.json','leg_mirror_equivalence.json'):
        shutil.copy2(BASE / name, OUT / name)
    ref = OUT / 'baseline_v81'
    ref.mkdir(exist_ok=True)
    for p in BASE.glob('*.md'):
        shutil.copy2(p, ref / p.name)
    for p in BASE.glob('*review.json'):
        shutil.copy2(p, ref / p.name)
    (OUT / 'previews').mkdir(exist_ok=True)


def build():
    prepare()
    cad.configure(OUT)
    doc = App.openDocument(str(BASE / 'wheel_leg_v8_1.FCStd'))
    doc.Parameters.LegLength = 180
    doc.Parameters.Beta = 0
    doc.recompute()
    changed = {'chassis_front_shell','chassis_rear_cover','electronics_tray'}
    before = {o.Name: signature(o) for o in doc.Objects if o.TypeId == 'Part::Feature' and o.Name not in changed}
    for key, label in (('M07','前部配电通信服务模块'),('M08','后部USB扩展模块')):
        g = doc.addObject('App::DocumentObjectGroup',key)
        g.Label = key + ' ' + label
        doc.Robot.addObject(g)
    doc.chassis_front_shell.Shape = cut(doc.chassis_front_shell.Shape, cyl(8.15, 3.6, (60,0,96.7)))
    add(doc, 'Power_switch_M16_latching', switch_shapes(), 'M06', 'payload',
        'User drawing; M16x1, D16.3 panel hole, 3mm panel, D17.8 cap, AF19 nut. Plugged depth47.5; 24V DC rating/LED voltage not confirmed.', 35.)
    rear_interfaces(doc)
    interface = board_and_converter(doc)
    for name, shape, family, size, module in HARDWARE:
        add(doc,name,shape,module,'steel',family+' '+size+'; ISO basic envelope, thread simplified.')
    doc.recompute()
    checks = []
    for name, old in before.items():
        new = signature(doc.getObject(name))
        ok = abs(old['volume']-new['volume']) < 1e-6 and abs(old['area']-new['area']) < 1e-6 and old['expressions']==new['expressions'] and max(abs(x-y) for x,y in zip(old['bounds'],new['bounds'])) < 1e-6
        checks.append(dict(name=name,passed=ok))
    assert all(x['passed'] for x in checks)
    for name in changed:
        assert doc.getObject(name).Shape.isValid(), name
    doc.Label = 'Wheel Leg V8.2 Electrical Integration'
    doc.saveAs(str(OUT / 'wheel_leg_v8_2.FCStd'))
    params = json.loads((OUT/'design_parameters.json').read_text())
    params.update(revision='V8.2',electrical_integration='ELECTRICAL_INTEGRATION.md',
                  battery_model='E626S user confirmed',switch_hole_mm=16.3,
                  rear_charge_pilot_xyz_mm=[-94,-46,-25],usb2can_case=False)
    (OUT/'design_parameters.json').write_text(json.dumps(params,indent=2)+'\n')
    data = dict(changed_existing=sorted(changed),new_objects=NEW,
                preserved=checks,interfaces=interface,
                hardware=[dict(name=n,family=f,size=s,module=m) for n,_,f,s,m in HARDWARE],
                coordinates='X front, Z up; rear view right=-Y',
                baseline_sha256=hashlib.sha256((BASE/'wheel_leg_v8_1.FCStd').read_bytes()).hexdigest())
    (OUT/'electrical_build.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    App.closeDocument(doc.Name)
    print('V82_BUILT',flush=True)


if __name__ == '__main__':
    build()
