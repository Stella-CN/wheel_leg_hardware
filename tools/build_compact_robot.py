"""Build V4 after reference decomposition: nested coupling and shared leg layers.

Run with the installed FreeCAD Python from the project root. Original motor
references remain in references. Each geometry module owns its interfaces;
the common builder exports and checks the complete assembled mechanism.
"""
from __future__ import annotations

import json

import build_printable_robot as cad
import cad_v4_coupling as coupling
import cad_v4_leg as leg
from build_nested_robot import bushing_coupon, translated
from build_reference_robot import ring


def bearing_coupon():
    """Four seats for the selected 13 mm OD 686AZZ1, ordered along +X."""
    shape = cad.box(0, 0, 0, 80, 26, 6)
    for index, diameter in enumerate((13.00, 13.10, 13.15, 13.20)):
        shape = shape.cut(cad.Part.makeCylinder(diameter/2, 8,
                          cad.V(10+20*index, 13, -1)))
    return shape.removeSplitter()


def main():
    out = cad.ROOT / "mechanical/v4"
    cad.configure(out)
    cad.P.update(leg.configure())
    cad.P.update(revision="v4_compact_nested", cnc_material="6061-T6 aluminum",
                 coupling="D39 neck / D43 male spigot in D57 cup; four radial M3 screws",
                 rotor_dowels="3 x D4 on PCD24.30; original motor drawing and STEP verified")
    for obsolete in ("development_status", "coupler_split_y", "A_pin_sweep_track",
                     "print_register_diameter", "profile_corner_radius"):
        cad.P.pop(obsolete, None)
    cad.P["coupler_nesting_y"] = [80.5, 87.5]
    hub_offset = cad.P["hub_stator_face_y"] - 164.0
    cad.P["wheel_center_y"] = 190.0 + hub_offset
    cad.P["wheel_track"] = 2 * cad.P["wheel_center_y"]
    (out / "design_parameters.json").write_text(json.dumps(cad.P, indent=2)+"\n")
    rim = translated(cad.union(cad.wheel_rim(), ring(45, 34.4, 206, 2, 0)), hub_offset)
    designs = {"hip_stator_mount": (cad.motor_mount(), "fixed", "PETG")}
    designs.update(coupling.designs())
    designs.update(leg.designs())
    designs["wheel_rim"] = (rim, "wheel", "PETG")
    leg.export_hardware()
    dowel = cad.cyl(2, 0, 9)
    dowel.exportStep(str(out / "metal_hardware/dowel_D4_L9.step"))
    (out / "metal_hardware/dowel_specification.json").write_text(json.dumps({
        "part": "dowel_D4_L9", "quantity": 6, "diameter_nominal_mm": 4,
        "length_mm": 9, "material": "steel locating dowel",
        "motor_insertion_mm": 3, "flange_insertion_mm": 6,
        "fit": "Confirm fixed fit in CNC flange and removable fit in motor D4(+0.02/+0.04) holes",
        "source": "motor_interface_review.json; full insertion checked in coupling_review.json"
    }, indent=2)+"\n")
    hardware = coupling.hardware() + leg.hardware()
    doc = cad.build(designs, hardware=hardware,
                    reverse_faces=("OA_inner_hub", "CW_main_inner"),
                    mirrored_print_parts=("hip_rotor_cnc", "knee_stator_cnc", "OB_inner_full", "OB_outer_full", "CW_main_inner", "CW_outer_fork"),
                    hub_offset=hub_offset, check_hardware_pairs=True,
                    coupons={"bearing_fit_coupon": bearing_coupon(),
                             "bushing_fit_coupon": bushing_coupon()})
    errors = []
    for length in (120, cad.P["leg_length"], 225):
        doc.Parameters.LegLength = length
        doc.recompute()
        for name, shape, role in hardware:
            for side in ("right", "left"):
                original = shape if side == "right" else cad.mirror(shape)
                expected = cad.transform(original, role, cad.pose(length))
                # FreeCAD prefixes names beginning with a digit (e.g. 626).
                # The explicit label assigned by put() retains the part name.
                matches = doc.getObjectsByLabel(f"{name}_{side}".replace("_", " "))
                if len(matches) != 1:
                    raise ValueError(f"Expected one native hardware object: {name}_{side}")
                actual = matches[0].Shape
                error = (actual.BoundBox.Center-expected.BoundBox.Center).Length
                if error > 0.001:
                    errors.append({"part": name, "side": side, "length": length, "error_mm": error})
    doc.Parameters.LegLength = cad.P["leg_length"]
    doc.recompute()
    doc.save()
    report = {"poses_mm": [120, cad.P["leg_length"], 225],
              "hardware_objects": 2*len(hardware), "placement_tolerance_mm": 0.001,
              "errors": errors}
    (out / "native_hardware_placement_validation.json").write_text(json.dumps(report, indent=2)+"\n")
    if errors:
        raise ValueError("V4 native hardware expressions do not match the independent pose")


if __name__ == "__main__":
    main()
