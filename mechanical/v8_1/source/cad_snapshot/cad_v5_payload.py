"""Payload envelopes and a removable embedded D435 bracket, in millimetres.

The envelopes are explicitly approximate, not vendor CAD. Camera rear holes
come from the manufacturer's October 2025 drawing (Figure 10-9, page 140).
"""
from __future__ import annotations

import json
import math

import build_printable_robot as cad

V, Part = cad.V, cad.Part
CAMERA_REAR = 73.9
CAMERA_CENTER_Z = 63.5


def xcyl(radius, x, length, y, z):
    return Part.makeCylinder(radius, length, V(x, y, z), V(1, 0, 0))


def xhex(x, length, y, z, across_flats):
    radius = across_flats / math.sqrt(3)
    pts = [V(x, y + radius*math.cos(math.radians(30+60*i)),
             z + radius*math.sin(math.radians(30+60*i))) for i in range(6)]
    return Part.Face(Part.makePolygon(pts + pts[:1])).extrude(V(length, 0, 0))


def camera_bracket():
    # The four rails leave the lateral USB connector region open at Z60..68.
    pieces = [cad.box(70.9, -54, 58.5, 3, 108, 10)]
    for y in (-50, 50):
        for z in (56, 72):
            pieces.append(cad.box(70.9, y-4, z-4, 26.1, 8, 8))
    shape = cad.union(*pieces)
    tools = [xcyl(1.7, 70.8, 3.2, y, CAMERA_CENTER_Z) for y in (-22.5, 22.5)]
    for y in (-50, 50):
        for z in (56, 72):
            tools.extend((xcyl(1.7, 70.8, 26.4, y, z),
                          xhex(70.8, 22.2, y, z, 5.8)))
    return cad.cut(shape, *tools)


def camera_hardware():
    result = []
    for index, y in enumerate((-22.5, 22.5)):
        # M3x5: 3mm bracket, 2mm insertion, below the vendor's 3mm maximum.
        screw = cad.union(xcyl(1.5, 70.9, 5, y, CAMERA_CENTER_Z),
                          xcyl(2.75, 67.9, 3, y, CAMERA_CENTER_Z))
        result.append((f'D435_rear_M3x5_{index}', screw, 'fixed'))
    for index, (y, z) in enumerate(( (y,z) for y in (-50,50) for z in (56,72) )):
        screw = cad.union(xcyl(1.5, 90, 10, y, z), xcyl(2.75, 100, 3, y, z))
        nut = cad.cut(xhex(90.6, 2.4, y, z, 5.5), xcyl(1.5, 90.5, 2.6, y, z))
        result.extend(((f'D435_frame_M3x10_{index}', screw, 'fixed'),
                       (f'D435_frame_M3_nut_{index}', nut, 'fixed')))
    return result


def payloads():
    # X dimension follows the port direction: a 35mm forward plug keep-out
    # ends at X55.35, before the camera's rear bracket at X67.9.
    jetson = cad.box(-70.35, -51.6, 33, 90.7, 103.2, 35.86)
    camera = cad.box(CAMERA_REAR, -45.075, 50.925, 26.1, 90.15, 25.15)
    camera = cad.cut(camera, *(xcyl(1.6, CAMERA_REAR-.1, 3.1, y, CAMERA_CENTER_Z)
                              for y in (-22.5, 22.5)))
    return [
        ('Orin_Nano_envelope', jetson, 175,
         'Official developer-kit maximum drawing envelope; not vendor CAD. Ports face +X. Carrier spec v1.3 pp29-30.'),
        ('D435_envelope', camera, 75,
         'Conservative envelope; lenses flush at X100; rear 2xM3 spacing45/max insertion3. October2025 datasheet pp69/140.'),
        ('Battery_400g_envelope', cad.box(-55, -25, -42, 110, 50, 35), 400,
         'User mass 400g. Assumed 110x50x35 rectangular envelope; actual cell, connector and protection dimensions pending.'),
        ('IMU_envelope', cad.box(62, -15, -10, 25, 30, 12), 20,
         'Unselected IMU: assumed 25x30x12 mm and20g; replace with actual module before drilling mounting pattern.'),
    ]


def export_notes():
    target = cad.OUT / 'payload_interfaces.json'
    target.write_text(json.dumps({
        'units': 'mm', 'status': 'packaging envelopes, not vendor solids',
        'jetson': {'maximum_dimensions': [103.2, 90.7, 35.86], 'mass_g': 175,
                   'ports_facing': '+X', 'forward_plug_allowance': 35,
                   'source': 'https://developer.nvidia.com/downloads/assets/embedded/secure/jetson/orin_nano/docs/jetson_orin_nano_devkit_carrier_board_specification_sp.pdf'},
        'd435': {'envelope_dimensions': [90.15, 25.15, 26.1], 'mass_g': 75,
                 'rear_mount_pitch': 45, 'rear_thread': 'M3x0.5',
                 'manufacturer_max_insertion': 3, 'selected_screw': 'M3x5',
                 'bracket_grip': 3, 'nominal_insertion': 2,
                 'manufacturer_recommended_mounting_torque_Nm': .4,
                 'source': 'https://realsenseai.com/wp-content/uploads/2025/09/Intel-RealSense-D400-Series-Datasheet-October-2025.pdf'},
        'battery': {'mass_g': 400, 'dimensions_assumed': [110,50,35]},
        'imu': {'mass_g_assumed': 20, 'dimensions_assumed': [25,30,12]},
        'manufacturing': 'PETG camera bracket uses captive metal M3 nuts. No printed load-bearing leg joints.',
        'limits': 'Device envelopes reserve space; final board standoffs, straps, USB/DC plug shapes, ventilation flow and cable retention require actual devices.'
    }, ensure_ascii=False, indent=2)+'\n')
