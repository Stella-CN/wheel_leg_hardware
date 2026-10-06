"""Printable enclosure for the biped wheel-leg robot, in millimetres.

Coordinate convention: X forward, Y lateral, Z up; hip axes pass through
X=Z=0. Shapes are returned in their assembled positions. Print the shell
bottom-down, the lid exterior-down, and the trays bottom-down. The shell's
upper screw ledges and circular side openings need local supports. Print the
battery tray's raised mounting ears with local supports as well.

The enclosure is 200 x 150 x 100 mm. It provides an open central battery
envelope of 110 x 50 x 35 mm at Z=-42..-7. Battery and controller dimensions
are provisional. The 188 x 46 mm electronics shelf suits a narrow board;
larger boards require a revised layout, not an assumed fit.

Fasteners: eight M3 lid screws, four M3 screws per tray, and four M4 through
bolts per hip mount. M3 heat-set insert bores are diameter 4.2 x 5 mm deep;
select an insert to match these bores and calibrate with a PETG coupon.
Hip bosses accept accessible metal nuts and washers inside the enclosure.
Neither printed threads nor a printed motor-output flange is assumed.
"""
from __future__ import annotations

import FreeCAD as App
import Part


WALL_MM = 3.2
FLOOR_MM = 4.0
LID_MM = 4.0
HIP_WINDOW_DIAMETER_MM = 64.0
M3_CLEARANCE_MM = 3.4
M3_INSERT_BORE_MM = 4.2
M3_INSERT_DEPTH_MM = 5.0
M4_CLEARANCE_MM = 4.4
LID_FASTENERS = tuple((x, y) for x in (-89.0, 89.0)
                      for y in (-65.0, 65.0)) + tuple(
                          (x, y) for x in (-50.0, 50.0)
                          for y in (-68.0, 68.0))
BATTERY_FASTENERS = tuple((x, y) for x in (-70.0, 70.0)
                          for y in (-20.0, 20.0))
ELECTRONICS_FASTENERS = tuple((x, y) for x in (-88.0, 88.0)
                              for y in (-15.0, 15.0))


def _box(x, y, z, dx, dy, dz):
    return Part.makeBox(dx, dy, dz, App.Vector(x, y, z))


def _cylinder(radius, length, x, y, z, axis=(0, 0, 1)):
    return Part.makeCylinder(radius, length, App.Vector(x, y, z),
                             App.Vector(*axis))


def _fuse(shapes):
    return shapes[0].multiFuse(shapes[1:]).removeSplitter()


def _rounded_prism(width, depth, height, z, radius):
    """A centred rounded rectangle with cylindrical vertical corners."""
    shapes = [
        _box(-width / 2 + radius, -depth / 2, z,
             width - 2 * radius, depth, height),
        _box(-width / 2, -depth / 2 + radius, z,
             width, depth - 2 * radius, height),
    ]
    shapes.extend(_cylinder(radius, height, x, y, z)
                  for x in (-width / 2 + radius, width / 2 - radius)
                  for y in (-depth / 2 + radius, depth / 2 - radius))
    return _fuse(shapes)


def _slot_z(x, y, z, length, width, height):
    """Capsule slot along X, extruded along Z."""
    travel = length - width
    return _fuse([
        _box(x - travel / 2, y - width / 2, z,
             travel, width, height),
        _cylinder(width / 2, height, x - travel / 2, y, z),
        _cylinder(width / 2, height, x + travel / 2, y, z),
    ])


def _vent_x(y):
    """3.2 mm wide, 20 mm tall vertical vent through both end walls."""
    return _fuse([
        _box(-101, y - 1.6, 1.6, 202, 3.2, 16.8),
        _cylinder(1.6, 202, -101, y, 1.6, (1, 0, 0)),
        _cylinder(1.6, 202, -101, y, 18.4, (1, 0, 0)),
    ])


def _lower_shell():
    outer = _rounded_prism(200, 150, 96, -50, 8)
    inner = _rounded_prism(200 - 2 * WALL_MM, 150 - 2 * WALL_MM,
                           96, -50 + FLOOR_MM, 8 - WALL_MM)
    shell = outer.cut(inner)
    additions = [shell]

    # Lid bosses have substantial bridges to the wall, not tangent contacts.
    for x, y in LID_FASTENERS:
        additions.append(_cylinder(6.5, 12, x, y, 34))
        if abs(x) > 80:
            additions.append(_box(86 if x > 0 else -98, y - 6.5, 34,
                                  12, 13, 12))

    # Internal M4 washer seats around the D64 windows: no motor interference.
    for side in (-1, 1):
        for x in (-30, 30):
            for z in (-30, 30):
                additions.append(_cylinder(7, 13.2, x, side * 61.8, z,
                                            (0, side, 0)))

    # Battery posts stop at the underside of the tray's raised screw ears.
    for x, y in BATTERY_FASTENERS:
        additions.append(_cylinder(6, 7, x, y, -46))

    # End-wall ribs support the narrow electronics shelf clear of the battery.
    for x, y in ELECTRONICS_FASTENERS:
        additions.append(_cylinder(5.5, 46, x, y, -46))
        additions.append(_box(86 if x > 0 else -98, y - 5.5, -46,
                              12, 11, 46))
    shell = _fuse(additions)

    cuts = [_cylinder(HIP_WINDOW_DIAMETER_MM / 2, 152,
                      0, -76, 0, (0, 1, 0))]
    cuts.extend(_cylinder(M4_CLEARANCE_MM / 2, 152, x, -76, z,
                           (0, 1, 0))
                for x in (-30, 30) for z in (-30, 30))
    for points, top in ((LID_FASTENERS, 46), (BATTERY_FASTENERS, -39),
                        (ELECTRONICS_FASTENERS, 0)):
        cuts.extend(_cylinder(M3_INSERT_BORE_MM / 2,
                               M3_INSERT_DEPTH_MM + 0.2,
                               x, y, top - M3_INSERT_DEPTH_MM)
                    for x, y in points)

    # Front/back cable passages sit above the controller tray and away from
    # motor and fastener envelopes. Use separate strain relief on the cable.
    cuts.append(_cylinder(6, 202, -101, 0, 20, (1, 0, 0)))
    cuts.extend(_vent_x(y) for y in (-54, -43, 43, 54))
    return shell.cut(Part.makeCompound(cuts)).removeSplitter()


def _lid():
    lid = _rounded_prism(200, 150, LID_MM, 46, 8)
    # 0.4 mm radial clearance to the cavity, with local clearance at bosses.
    lip = _rounded_prism(192.8, 142.8, 3, 43, 4.4).cut(
        _rounded_prism(188, 138, 3.2, 42.9, 2))
    notches = [_cylinder(6.9, 3.4, x, y, 42.8)
               for x, y in LID_FASTENERS]
    # Include the rectangular bridges used by the four corner screw bosses.
    notches.extend(_box(85.6 if x > 0 else -98.4, y - 6.9, 42.8,
                         12.8, 13.8, 3.4)
                   for x, y in LID_FASTENERS if abs(x) > 80)
    lip = lip.cut(Part.makeCompound(notches))
    lid = lid.fuse(lip)
    holes = [_cylinder(M3_CLEARANCE_MM / 2, 4.4, x, y, 45.8)
             for x, y in LID_FASTENERS]
    return lid.cut(Part.makeCompound(holes)).removeSplitter()


def _battery_tray():
    # Tray underside has 1.6 mm clearance to the case floor for thin straps.
    tray = _rounded_prism(118, 58, 10.4, -44.4, 5).cut(
        _rounded_prism(112, 52, 9, -42, 2))
    ears = [tray]
    for x, y in BATTERY_FASTENERS:
        ears.append(_cylinder(7, 3, x, y, -39))
        ears.append(_box(56 if x > 0 else -70, y - 7, -39, 14, 14, 3))
    tray = _fuse(ears)
    cuts = [_cylinder(M3_CLEARANCE_MM / 2, 3.4, x, y, -39.2)
            for x, y in BATTERY_FASTENERS]
    # Two <=10 mm straps pass through four slots in the floor of the tray.
    cuts.extend(_slot_z(x, y, -44.6, 12, 3.4, 3)
                for x in (-32, 32) for y in (-22.5, 22.5))
    return tray.cut(Part.makeCompound(cuts)).removeSplitter()


def _electronics_tray():
    # Narrow central shelf: 4 mm lateral clearance to the motor envelope.
    tray = _rounded_prism(188, 46, 3, 0, 3)
    cuts = [_cylinder(M3_CLEARANCE_MM / 2, 3.4, x, y, -0.2)
            for x, y in ELECTRONICS_FASTENERS]
    cuts.extend(_slot_z(x, y, -0.2, 16, M3_CLEARANCE_MM, 3.4)
                for x in (-60, -20, 20, 60) for y in (-12, 12))
    cuts.extend(_cylinder(4, 3.4, x, 0, -0.2) for x in (-48, 48))
    return tray.cut(Part.makeCompound(cuts)).removeSplitter()


def build_chassis() -> dict[str, Part.Shape]:
    """Build four separate, valid single-solid parts in assembly coordinates."""
    parts = {
        "chassis_lower_shell": _lower_shell(),
        "chassis_lid": _lid(),
        "battery_tray": _battery_tray(),
        "electronics_tray": _electronics_tray(),
    }
    for name, shape in parts.items():
        if not shape.isValid() or len(shape.Solids) != 1:
            raise RuntimeError(f"{name}: expected one valid solid")
    return parts
