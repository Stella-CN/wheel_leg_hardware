"""V8.1 leg detail wrapper: preserve all five link solids; add rim fasteners.

The wheel rotor drawing specifies six M3 tapped holes, depth 5, on PCD28.
The V8 rim has 4 mm grip at those holes, so ISO4762 M3x8 gives 4 mm nominal
engagement and 1 mm nominal bottom clearance. Motor-engaged threads remain
omitted from nominal collision solids, as in the inherited motor hardware.
"""
from __future__ import annotations

import json
from pathlib import Path

import build_printable_robot as cad
import cad_v6_leg as prior
import build_enclosed_robot as wheel

designs = prior.designs


def configure():
    result = prior.configure()
    result.update(joint_bush="One-piece flanged bronze bushes, two handed axial profiles",
                  shaft="D6 steel female M2 both ends L14.05; full thread depth >=4.3, flat cylindrical pilot depth4.6",
                  joint_inner_race_axial_clearance_nominal=.05)
    return result


def female_pin(y=None, z=0):
    if y is None:
        y = prior.Y(5)
    return cad.cut(cad.cyl(3, y, 14.05, z=z),
                   cad.cyl(.8, y-.1, 4.7, z=z),
                   cad.cyl(.8, y+14.05-4.6, 4.7, z=z))


def flanged_bush(inner=True, y=0, z=0):
    """Small clearance step in flange avoids touching the bearing shield."""
    ring = prior.ring
    if inner:
        return cad.union(ring(4, 3.025, y, 2.5, z),
                         ring(4.2, 3.1, y+2.5, 1.25, z))
    return cad.union(ring(4.2, 3.1, y, 1.7, z),
                     ring(4, 3.025, y+1.7, 2.5, z))


def wheel_hardware():
    face = cad.P["hub_stator_face_y"] + 44.5
    seat = face + 4.0
    items = []
    for i, (x, z) in enumerate(cad.points(14, 6, 30)):
        screw = cad.union(cad.cyl(1.5, face, 4, x, z),
                          cad.cyl(2.75, seat, 3, x, z))
        screw = cad.cut(screw, cad.hex_pocket(x, z, seat+1.5, 1.6, 2.5))
        items.append((f"wheel_rim_ISO4762_M3x8_{i}", screw, "wheel"))
    return items


def hardware():
    items = [(n, s, r) for n, s, r in prior.hardware()
             if not n.startswith(("bronze_sleeve_", "race_spacer_", "female_pin_"))]
    for name, holder, z in (("A", "oa", -45), ("C", "output", 45),
                            ("B", "hip", -130)):
        items.extend(((f"female_pin_{name}", female_pin(z=z), holder),
                      (f"flanged_bush_{name}_inner", flanged_bush(True, prior.Y(5), z), holder),
                      (f"flanged_bush_{name}_outer", flanged_bush(False, prior.Y(14.8), z), holder)))
    return items + wheel_hardware()


def export_hardware():
    if cad.OUT.name != "v8_1":
        raise ValueError("V8.1 hardware exports must not overwrite earlier revisions")
    folder = cad.OUT/"metal_hardware"
    folder.mkdir(parents=True, exist_ok=True)
    for stale in ("bronze_bush_D8_d6_05_L2_5.step", "race_spacer_D8_4_d6_2_L1_25.step",
                  "race_spacer_D8_4_d6_2_L1_70.step"):
        (folder/stale).unlink(missing_ok=True)
    specs = []

    def save(name, shape, quantity, material, **kw):
        assert shape.isValid() and len(shape.Solids) == 1, name
        shape.exportStep(str(folder/(name+".step")))
        specs.append(dict(part=name, quantity=quantity, material=material,
                          supply_type="custom", **kw))

    save("OA_angular_stop_M3_D4", prior.angular_stop_pin(0, 0, True), 2, "steel",
         thread="M3x3", shoulder_diameter=4, shoulder_length=4.2,
         head_diameter=7, head_height=1,
         caution="Assembly stop only; not a rated landing or powered impact stop")
    save("female_pin_D6_L14_05", female_pin(0), 6, "steel",
         outer_diameter=6, length=14.05, full_thread_depth_min_mm=4.3,
         flat_cylindrical_pilot_depth_mm=4.6, nominal_center_web_mm=4.85,
         end_threads="M2x0.4 each end", screw_nominal_engagement_mm=3.8)
    save("bearing_keeper_D28_D16_8_t0_8", prior.keeper(0, 0), 6, "stainless steel",
         outer_diameter=28, inner_diameter=16.8, thickness=.8,
         holes="3 D2.2 PCD24")
    save("flanged_bush_inner_D8_D8p4_L3p75", flanged_bush(True), 6, "bearing bronze",
         sleeve="OD8 ID6.05 L2.50", flange="OD8.4 ID6.2 L1.25",
         overall_length=3.75)
    save("flanged_bush_outer_D8_D8p4_L4p20", flanged_bush(False), 6, "bearing bronze",
         sleeve="OD8 ID6.05 L2.50", flange="OD8.4 ID6.2 L1.70",
         overall_length=4.2, bearing_inner_race_gap_nominal=.05)
    save("axis_washer_D9_d2_2_t0_2", prior.ring(4.5, 1.1, 0, .2, 0), 12,
         "steel shim", outer_diameter=9, inner_diameter=2.2, thickness=.2,
         classification="Custom axial retention plate, not a standard purchase washer")
    (folder/"specification.json").write_text(json.dumps(specs, indent=2)+"\n")


def export_review(out):
    out = Path(out)
    rim = wheel.wheel_rim()
    screws = wheel_hardware()
    overlaps = [{"part": name, "volume_mm3": cad.interference_volume(rim, shape)}
                for name, shape, _ in screws]
    report = dict(revision="v8_1", unchanged_link_solids=list(designs()),
        added_hardware_each_wheel=6, added_hardware_whole_robot=12,
        hardware_spec="ISO4762 M3x8 8.8 black oxide; no washer in rigid CNC rim joint",
        rotor_thread="6xM3 depth5 on PCD28, supplied manufacturer drawing 2025-12-03",
        nominal_grip_mm=4.0, nominal_engagement_mm=4.0,
        nominal_bottom_clearance_mm=1.0, rim_screw_intersections=overlaps,
        integrated_bushes=dict(removed_each_robot={"bronze_sleeves":12,"steel_race_spacers":12},
            added_each_robot={"inner_flanged_bush":6,"outer_flanged_bush":6},
            net_piece_reduction=12, inner_sleeve_y_offset=[5,7.5],
            inner_flange_y_offset=[7.5,8.75], bearing_y_offset=[8.75,14.75],
            outer_flange_y_offset=[14.8,16.5], outer_sleeve_y_offset=[16.5,19],
            nominal_axial_gap_mm=.05, preload="None; M2 end screws retain pin, not preload bearing"),
        notes="CAD excludes motor-engaged threads; do not count CAD partial shank length as purchased screw length.")
    (out/"leg_v81_review.json").write_text(json.dumps(report, indent=2)+"\n")
    if any(item["volume_mm3"] > .001 for item in overlaps):
        raise ValueError("Wheel screw overlaps CNC rim")
    return report
