"""Official HI13R2 enclosure, positioned from its published IMU datum.

All units are millimetres. The vendor STEP has its housing top toward -Z.
The transformation is a proper rotation (not a mirrored mesh). By default,
the Type-C socket faces robot -X and the published IMU point is (0, 0, 85).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import build_printable_robot as cad

App, Part, V = cad.App, cad.Part, cad.V
SOURCE = cad.ROOT / "mechanical/v7/source/hi13r2"
VENDOR_STEP = SOURCE / "HI13XX-USB.STEP"
BASE_Z = 79.0
MASS_G = 11.0  # Conservative bound: the manufacturer specifies <11 g.
SOURCE_IMU_POINT = (-40.00155697274189, 1.47316173360338, 0.0)
MOUNT_XY = ((10.1, -10.1), (-10.1, 10.1))
SENSOR_TO_ROBOT_ROTATION = ((0, -1, 0), (1, 0, 0), (0, 0, 1))


def placement(base_z: float = BASE_Z):
    """Place the original, unscaled manufacturer model into robot coordinates."""
    sx, sy, sz = SOURCE_IMU_POINT
    matrix = App.Matrix(0, -1, 0, sy,
                        -1, 0, 0, sx,
                        0, 0, -1, base_z + 6.0 + sz,
                        0, 0, 0, 1)
    return App.Placement(matrix)


def shape(base_z: float = BASE_Z):
    """The two original enclosure solids; no reconstruction or rescaling."""
    result = Part.Shape()
    result.read(str(VENDOR_STEP))
    result.Placement = placement(base_z)
    return result


def sensor_origin(base_z: float = BASE_Z):
    """Manufacturer's nominal red IMU point, not an estimated volume centroid."""
    return V(0, 0, base_z + 6.0)


def mount_holes(base_z: float = BASE_Z):
    """Two vertical hole-axis datums at the mounting plane (hole diameter 2.6)."""
    return [V(x, y, base_z) for x, y in MOUNT_XY]


def cable_clearance(base_z: float = BASE_Z):
    """Design keep-out only; not a manufacturer-defined USB plug model.

    It reserves a compact right-angle/short plug region behind the socket.
    A selected cable must be measured before routing is released.
    """
    return cad.box(-34, -6, base_z + 1.0, 20, 12, 9)


def payload(base_z: float = BASE_Z):
    return (
        "HI13R2_official",
        shape(base_z),
        MASS_G,
        "HiPNUC official HI13XX-USB STEP, downloaded 2026-09-22; "
        "HI13R2-USB-000, mass budget11g for manufacturer specification<11g. "
        "Published IMU datum is XY=(0,0), Z=base+6mm. "
        "Type-C points CAD-X; sensorRFU->CAD rotation=[[0,-1,0],[1,0,0],[0,0,1]]. "
        "Nominal hole pitch20.2x20.2, two diagonal2.6mm bores."
    )


def payloads(base_z: float = BASE_Z):
    return [payload(base_z)]


def interface_data(base_z: float = BASE_Z):
    return {
        "model": "HI13R2-USB-000",
        "vendor_family_STEP": VENDOR_STEP.name,
        "datasheet_revision": "1.5, 2026-03-14",
        "source_STEP_file_date": "2026-03-16",
        "source_STEP_sha256": hashlib.sha256(VENDOR_STEP.read_bytes()).hexdigest(),
        "source_STEP_solids": 2,
        "manufacturer_envelope_mm": [26, 24, 12],
        "main_housing_mm": [24, 24, 12],
        "source_STEP_IMU_point_mm": list(SOURCE_IMU_POINT),
        "robot_IMU_point_mm": list(sensor_origin(base_z)),
        "robot_mounting_plane_z_mm": base_z,
        "mass_budget_g": MASS_G,
        "mass_basis": "Manufacturer specifies <11g; use11g conservative purchased-component mass.",
        "mounting": {
            "hole_centres_XY_mm": [list(xy) for xy in MOUNT_XY],
            "bore_diameter_mm": 2.6,
            "bore_range_mm": [2.55, 2.65],
            "hole_pitch_XY_mm": [20.2, 20.2],
            "pitch_range_mm": [20.0, 20.4],
            "screw_nominal": "M2.5",
            "screw_head_seat_z_mm": base_z + 10.4,
            "head_corner_relief_radius_mm": 2.3,
            "bridge_3mm_fastener_example": "M2.5x16, bridge clearance2.7mm, underside nut2mm; verify actual head/nut dimensions.",
            "front_2xM2": "Type-C locking plate holes, 15mm pitch; not the vertical mounting holes."
        },
        "origin_evidence": {
            "page": 17,
            "figure": "9: HI13 mechanical dimensions and IMU position",
            "nominal": "Red IMU dot: D4=12,E3=12,A3=6 from body datum edges/bottom.",
            "dimension_table_ranges_mm": {"D4": [11.8, 12.2], "E3": [11.8, 12.2], "A3": [5.8, 6.2]},
            "limit": "Published nominal module datum, not per-unit calibrated die-centre metrology; assembly and sensor extrinsic calibration remain required."
        },
        "orientation": {
            "type_c_exit_robot_axis": "-X",
            "vendor_default_body_axes": "RFU: Right/Forward/Up",
            "sensor_X_in_robot": [0, 1, 0],
            "sensor_Y_in_robot": [-1, 0, 0],
            "sensor_Z_in_robot": [0, 0, 1],
            "sensor_vector_to_robot_matrix": [list(row) for row in SENSOR_TO_ROBOT_ROTATION],
            "proper_rotation_determinant": 1,
            "note": "Directions refer to existing numerical CAD axes. Matrix must be applied to raw vectors; attitude conversion needs explicit frame convention. No reflections."
        },
        "interface": {"type": "USB Type-C, internal UART bridge", "supply_V": [4.5, 5.5], "typical_power_mW": 300},
        "sensor_configuration": "R2 has accelerometer+gyroscope, no magnetometer, no barometer.",
        "mounting_guidance": "Rigid flat mounting; avoid concentrated heat and cable stress; validate vibration on assembled robot. Do not add unqualified soft isolation in control IMU path.",
        "usb_keep_out": "Design allowance20x12x9mm only, not measured cable geometry."
    }


def validate(base_z: float = BASE_Z):
    placed = shape(base_z)
    bound = placed.BoundBox
    checks = {
        "official_solids_retained": len(placed.Solids) == 2,
        "valid_shape": placed.isValid(),
        "envelope_mm": [bound.XLength, bound.YLength, bound.ZLength],
        "bottom_plane_z_mm": bound.ZMin,
        "top_plane_z_mm": bound.ZMax,
        "published_sensor_point_world_mm": list(placement(base_z).multVec(V(*SOURCE_IMU_POINT))),
        "hole_axis_geometry": [],
    }
    for x, y in MOUNT_XY:
        # The published bores extend 10.4mm from the underside to the head seat.
        bore_probe = Part.makeCylinder(1.25, 10.2, V(x, y, base_z + .1))
        collision = sum(solid.common(bore_probe).Volume for solid in placed.Solids)
        support_probe = Part.makeCylinder(2.2, .05, V(x, y, base_z + 10.35)).cut(
            Part.makeCylinder(1.4, .1, V(x, y, base_z + 10.3)))
        support = sum(solid.common(support_probe).Volume for solid in placed.Solids)
        checks["hole_axis_geometry"].append({"XY_mm": [x, y], "bore_probe_collision_mm3": collision,
                                              "seat_annulus_material_mm3": support})
        assert collision < 1e-7 and support > .1
    assert placed.isValid() and len(placed.Solids) == 2
    assert abs(bound.ZMin - base_z) < 1e-7
    assert all(abs(a-b)<1e-7 for a,b in zip(checks["envelope_mm"], (26,24,12)))
    assert (placement(base_z).multVec(V(*SOURCE_IMU_POINT))-sensor_origin(base_z)).Length<1e-7
    checks["pass"] = True
    return checks


if __name__ == "__main__":
    SOURCE.mkdir(parents=True, exist_ok=True)
    for filename, data in (("interfaces.json", interface_data()), ("model_validation.json", validate())):
        (SOURCE / filename).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    shape().exportBrep(str(SOURCE / "hi13r2_placed_z79.brep"))
    print("HI13R2 official model, origin, hole axes and mounting face verified.")
