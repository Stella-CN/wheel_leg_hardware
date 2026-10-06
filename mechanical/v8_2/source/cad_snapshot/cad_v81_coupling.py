"""V8.1 local adapter detail: catalog D4 x 10 dowels, frozen motor datums.

Only the three blind dowel bores in each hip rotor flange change. Imported
V5/V8 modules are never mutated; the parent builder selects this wrapper.
Nominal CAD pins omit the engaged motor portion unless full_pins is True.
"""
from __future__ import annotations

import itertools
import json
from pathlib import Path

import build_printable_robot as cad
import cad_v5_coupling as prior

App, Part, V = cad.App, cad.Part, cad.V
PIN_LENGTH = 10.0
PIN_MOTOR_INSERTION = 3.0
PIN_FLANGE_INSERTION = PIN_LENGTH - PIN_MOTOR_INSERTION
BORE_END_Y = 80.2


def configure():
    result = prior.configure()
    result.update(coupling_dowel="DIN6325 D4m6x10 hardened ground steel",
                  coupling_dowel_flange_engagement=PIN_FLANGE_INSERTION,
                  coupling_dowel_motor_engagement=PIN_MOTOR_INSERTION,
                  coupling_dowel_flat_bottom_y=BORE_END_Y)
    return result


def rotor_flange():
    shape = prior.rotor_flange()
    for x, z in cad.points(12.15, 3, 90):
        shape = cad.cut(shape, cad.cyl(2, 72.9, BORE_END_Y-72.9, x, z))
    return shape


def designs(parameters=None):
    prior._check_parameters(parameters)
    return {"hip_rotor_cnc": (rotor_flange(), "hip", "CNC"),
            "knee_stator_cnc": (prior.stator_cup(), "hip", "CNC")}


def hardware(parameters=None, full_pins=False):
    items = [(name, shape, role) for name, shape, role in prior.hardware(parameters)
             if not name.startswith("coupling_rotor_dowel_")]
    start = 70.0 if full_pins else 73.0
    for i, (x, z) in enumerate(cad.points(12.15, 3, 90)):
        items.append((f"coupling_rotor_DIN6325_D4x10_{i}",
                      cad.cyl(2, start, 80.0-start, x, z), "hip"))
    return items


def export_review(out):
    out = Path(out)
    shapes = designs()
    named = [(name, shape) for name, (shape, _, _) in shapes.items()]
    named += [(name, shape) for name, shape, _ in hardware(full_pins=True)]
    motors = [(name, cad.motor_shape(prior.SOURCE, y)) for name, y in
              (("hip_motor", 72.5), ("knee_motor", prior.KNEE_TRANSLATION))]
    collisions = []
    for (an, a), (bn, b) in itertools.combinations(named, 2):
        volume = cad.interference_volume(a, b)
        if volume > .001:
            collisions.append(dict(a=an, b=bn, volume_mm3=volume))
    for name, shape in named:
        for mn, motor in motors:
            volume = cad.interference_volume(shape, motor)
            if volume > .001:
                collisions.append(dict(a=name, b=mn, volume_mm3=volume))
    pins = [cad.cyl(2, 72.9, BORE_END_Y-72.9, x, z)
            for x, z in cad.points(12.15, 3, 90)]
    taps = [prior.tapping_drill(a) for a in prior.RADIAL_ANGLES]
    bolts = [cad.cyl(2.9, 78, 5, x, z) for x, z in cad.points(13.5, 6, 0)]
    distance = lambda aa, bb: min(a.distToShape(b)[0] for a in aa for b in bb)
    report = dict(revision="v8_1", parameters=configure(), collisions=collisions,
        changed_features="Only three flange dowel blind bores: bottom Y79 to Y80.2.",
        pin_nominal_y=[70, 80], motor_hole_y_from_STEP=[69, 73],
        motor_hole_bottom_clearance_mm=1.0,
        pin_to_flange_bottom_clearance_mm=.2,
        pin_tolerance_review=dict(incoming_length_acceptance_mm=[9.75,10.25],
            controlled_flange_insertion_mm=[6.95,7.05],
            effective_flange_bore_depth_mm=[7.15,7.25],
            resulting_motor_insertion_mm=[2.7,3.3],
            worst_motor_bottom_clearance_mm=.7,
            worst_flange_bottom_clearance_mm=.1,
            instruction="Control flange insertion depth, not simultaneous exact insertion and protrusion; standard pin length has a tolerance."),
        minimum_webs_mm=dict(blind_bottom_to_flange_end=82.5-BORE_END_Y,
            dowel_bore_to_radial_tap=distance(pins, taps),
            dowel_bore_to_rotor_counterbore=distance(pins, bolts)),
        bore_process="D4 H7 effective cylindrical bore to Y80.2; flat-bottom CNC interpolation. Do not substitute a 118deg drill tip without reviewing residual wall.",
        fit_scope="DIN6325 m6 pin; verify all three pin locations against the actual motor. Motor drawing D4 +0.02/+0.04.",
        preserved_datums=True, strength_validated=False)
    (out/"coupling_v81_review.json").write_text(json.dumps(report, indent=2)+"\n")
    if collisions:
        raise ValueError(f"V8.1 coupling collisions: {collisions}")
    return report
