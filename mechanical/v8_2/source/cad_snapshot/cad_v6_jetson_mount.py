"""Removable PETG peripheral retainers for the official Orin Nano full kit.

The original NVIDIA base, carrier holes and installed fasteners are retained.
Only the robot electronics tray receives the four returned clearance holes.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
import sys

sys.path.insert(0, "/Applications/FreeCAD.app/Contents/Resources/lib")
import FreeCAD as App
import Part
import cad_chassis as primitive

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "mechanical/v6"
V = App.Vector
TRAY_HOLES = tuple((x, y) for x in (-78., 38.) for y in (-38., 38.))


def cylinder(radius, height, origin):
    return Part.makeCylinder(radius, height, V(*origin))


def rounded_xy(x0, x1, y0, y1, z, thickness, radius):
    shape = primitive._rounded_prism(x1 - x0, y1 - y0, thickness, z, radius)
    shape.translate(V((x0 + x1) / 2, (y0 + y1) / 2, 0))
    return shape


def fuse(items):
    return items[0].multiFuse(items[1:]).removeSplitter()


def positive_retainer():
    # Arms land outside the kit's X envelope, so neither the arms nor their
    # screw heads pass underneath the factory base or above the carrier PCB.
    items = [rounded_xy(-82, 42, 52.2, 56.2, 33, 7.0, 1.2)]
    for x in (-78., 38.):
        items.append(rounded_xy(x - 4, x + 4, 34, 56.2, 33, 3, 2))
    # Overhang catches the outer plastic rim while clearing the PCB edge at
    # Y=50. Its lower face has0.5mm clearance over the source rim maximum.
    items.append(rounded_xy(-62, 12, 50.7, 56.2, 40.0, 2.4, 1.0))
    # Longitudinal retention is supplied by end stops at the two side edges;
    # central front connector/cable access remains open.
    for x0 in (-75., 21.):
        items.append(rounded_xy(x0, x0 + 4, 49, 56.2, 33, 6.8, 1))
    shape = fuse(items)
    holes = [cylinder(1.7, 3.4, (x, 38, 32.8)) for x in (-78., 38.)]
    return shape.cut(Part.makeCompound(holes)).removeSplitter()


def designs():
    positive = positive_retainer()
    return {"Jetson_base_retainer_right": positive,
            "Jetson_base_retainer_left": positive.mirror(V(), V(0, 1, 0))}


def tray_hole_tools():
    """Additional holes, not cuts in the original NVIDIA assembly."""
    return [cylinder(1.7, 3.4, (x, y, 29.8)) for x, y in TRAY_HOLES]


def hex_prism(x, y, z, across_flats, height):
    radius = across_flats / math.sqrt(3)
    points = [V(x + radius * math.cos(math.radians(30 + 60 * i)),
                y + radius * math.sin(math.radians(30 + 60 * i)), z) for i in range(6)]
    return Part.Face(Part.makePolygon(points + [points[0]])).extrude(V(0, 0, height))


def hardware():
    result = []
    for index, (x, y) in enumerate(TRAY_HOLES):
        shank = cylinder(1.5, 10., (x, y, 26.))
        head = cylinder(2.75, 3., (x, y, 36.))
        screw = shank.fuse(head).cut(hex_prism(x, y, 37.5, 2.5, 1.7)).removeSplitter()
        washer = cylinder(3.5, .5, (x, y, 29.5)).cut(cylinder(1.6, .7, (x, y, 29.4)))
        nut = hex_prism(x, y, 27.1, 5.5, 2.4).cut(cylinder(1.5, 2.6, (x, y, 27.0)))
        result.extend([(f"Jetson_retainer_M3x10_{index+1}", screw, "fixed"),
                       (f"Jetson_retainer_washer_{index+1}", washer, "fixed"),
                       (f"Jetson_retainer_M3_nut_{index+1}", nut, "fixed")])
    return result


def specification():
    return dict(process="PETG, noncritical electronics restraint", custom_parts=2,
                retained_original_kit="Complete official NVIDIA base and carrier assembly, unmodified",
                tray_holes=dict(diameter_mm=3.4, centres_xy_mm=TRAY_HOLES, z_range_mm=[30, 33]),
                fasteners=dict(screws="4×ISO4762 M3×10, headD5.5×3, AF2.5",
                               washers="4×M3 washer OD7/ID3.2×0.5",
                               nuts="4×M3 hex nut AF5.5×2.4",
                               structural_grip_mm=6, washer_thickness_mm=.5,
                               nominal_grip_mm=6.5, nut_engagement_mm=2.4, tip_projection_mm=1.1),
                retention=dict(side_wall_inner_y_abs_mm=52.2, lip_inner_y_abs_mm=50.7,
                               lip_underside_z_mm=40., front_stop_inner_x_mm=21.,
                               rear_stop_inner_x_mm=-71., nominal_lip_to_max_base_rim_clearance_mm=.5),
                assembly=["Install tray and accessible underside M3 washers/nuts; leave retainer screws loose",
                          "Position the complete NVIDIA kit on trayZ33 at the source-derived transform",
                          "Bring each retainer in from its side, engaging its lip above the plastic rim",
                          "Tighten the four M3 screws through the tray into underside nuts; verify the PCB and connector bodies remain untouched",
                          "Check the actual factory base fit and use thin removable soft pads if needed; never transmit clamp preload through the PCB"],
                print="Bottom faceZ33 down, >=4 perimeters; small1.5mm retaining-lip overhang may need local support; do not use as robot load-bearing structure",
                limitations="Restraint geometry and interface clearance checked; PETG creep, vibration and jump shock retention need physical validation")


def official_kit():
    shape = Part.read(str(OUT / "source/jetson/jetson_devkit_solids.brep"))
    shape.rotate(V(), V(0, 0, 1), 90)
    # Source base's actual supporting plane is Z=-4.9. Its B-rep control
    # BoundBox reaches-5.038511 and must not be mistaken for physical support.
    shape.translate(V(1.66325103075716, -46, 37.9))
    return shape


def validate():
    kit = official_kit()
    bodies = designs()
    hardware_rows = hardware()
    for name, shape in bodies.items():
        if not shape.isValid() or len(shape.Solids) != 1:
            raise ValueError(f"Invalid retainer: {name}")
    collisions = []
    all_items = list(bodies.items()) + [(name, shape) for name, shape, _ in hardware_rows]
    for name, shape in all_items:
        candidates = [s for s in kit.Solids if s.BoundBox.intersect(shape.BoundBox)]
        volume = sum(shape.common(candidate).Volume for candidate in candidates)
        if volume > .001:
            collisions.append(dict(a=name, b="official_NVIDIA_kit", overlap_mm3=volume))
    for index, (name, shape) in enumerate(all_items):
        for other_name, other_shape in all_items[index + 1:]:
            if shape.BoundBox.intersect(other_shape.BoundBox):
                volume = shape.common(other_shape).Volume
                if volume > .001:
                    collisions.append(dict(a=name, b=other_name, overlap_mm3=volume))
    # Tray test is independent of the chassis builder mutation: start with
    # the existing V5 tray and apply only the explicitly returned new holes.
    import cad_v5_chassis
    tray = cad_v5_chassis._electronics_tray().cut(Part.makeCompound(tray_hole_tools())).removeSplitter()
    support_gap = kit.Solids[1266].distToShape(tray)[0]
    kit_tray_overlap = sum(s.common(tray).Volume for s in kit.Solids
                           if s.BoundBox.intersect(tray.BoundBox))
    if kit_tray_overlap > .001:
        collisions.append(dict(a="official_NVIDIA_kit", b="electronics_tray_with_new_holes",
                               overlap_mm3=kit_tray_overlap))
    for name, shape in all_items:
        if shape.BoundBox.intersect(tray.BoundBox):
            volume = shape.common(tray).Volume
            if volume > .001:
                collisions.append(dict(a=name, b="electronics_tray_with_new_holes", overlap_mm3=volume))
    report = dict(parts=[dict(name=name, valid=shape.isValid(), solids=len(shape.Solids),
                              dimensions_mm=[shape.BoundBox.XLength, shape.BoundBox.YLength, shape.BoundBox.ZLength],
                              volume_mm3=shape.Volume) for name, shape in bodies.items()],
                  hardware_objects=len(hardware_rows), collisions=collisions,
                  original_base_to_tray_distance_mm=support_gap,
                  original_kit_to_tray_overlap_mm3=kit_tray_overlap,
                  checks="Actual NVIDIA1393 solids, retainer-to-retainer/hardware, existing tray with four explicit added holes",
                  specification=specification())
    (OUT / "jetson_mount_validation.json").write_text(json.dumps(report, indent=2) + "\n")
    (OUT / "jetson_mount_specification.json").write_text(json.dumps(specification(), indent=2) + "\n")
    if collisions:
        raise ValueError(f"Jetson retainer interference: {collisions}")
    if support_gap > .001:
        raise ValueError(f"Original Jetson base is not supported by the tray: {support_gap}mm")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    validate()
