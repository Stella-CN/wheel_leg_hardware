"""Inspect the unmodified NVIDIA Orin Nano full-developer-kit STEP for V6.

Run with the installed FreeCAD Python. No robot geometry is modified.
--render additionally produces a native FreeCAD preview of the source solids.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re
import sys

sys.path.insert(0, "/Applications/FreeCAD.app/Contents/Resources/lib")
import FreeCAD as App
import Part

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "mechanical/v6/source/jetson"
SOURCE = DEST / "P3766-P3768SKU4-P3767ENVELOPE.stp"
ZIP_NAME = "jetson_orin_nano_devkit_3d_step_model.zip"
MODEL_URL = "https://developer.nvidia.com/downloads/assets/embedded/secure/jetson/orin_nano/docs/jetson_orin_nano_devkit_3d_step_model.zip/"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bounds(shape):
    b = shape.BoundBox
    return dict(bounds_mm=[b.XMin, b.XMax, b.YMin, b.YMax, b.ZMin, b.ZMax],
                dimensions_mm=[b.XLength, b.YLength, b.ZLength])


def axial_cylinders(shape):
    rows = []
    for face in shape.Faces:
        surface = face.Surface
        if hasattr(surface, "Radius") and hasattr(surface, "Axis") and abs(abs(surface.Axis.z) - 1) < 1e-6:
            rows.append(dict(radius_mm=surface.Radius,
                             centre_mm=[surface.Center.x, surface.Center.y, surface.Center.z],
                             z_range_mm=[face.BoundBox.ZMin, face.BoundBox.ZMax]))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--render", action="store_true")
    args = parser.parse_args()
    source_hash = sha(SOURCE)
    if source_hash != "02dafef626d5ac6ee029d1ead431d6096c27c7c51fef6b49d5189e1765fb9d2f":
        raise ValueError("NVIDIA source changed; recheck component indices and provenance")
    source = Part.read(str(SOURCE))
    shapes = source.Solids
    solids = Part.makeCompound(shapes)
    if not source.isValid() or any(not shape.isValid() for shape in shapes):
        raise ValueError("Invalid source geometry")
    # Preserve original surfaces in the unmodified STEP. The assembly cache
    # retains every original solid, omitting only non-solid sheets/annotations.
    native_path = DEST / "jetson_devkit_native.brep"
    solids_path = DEST / "jetson_devkit_solids.brep"
    source.exportBrep(str(native_path))
    solids.exportBrep(str(solids_path))
    text = SOURCE.read_text(errors="replace")
    products = sorted(set(re.findall(r"PRODUCT\('([^']+)'", text)))
    entry = None
    download_json = DEST / "download_center.json"
    if download_json.exists():
        def visit(value):
            nonlocal entry
            if isinstance(value, dict):
                if value.get("title") == "Jetson Orin Nano Developer Kit 3D CAD STEP model":
                    entry = value
                for child in value.values():
                    visit(child)
            elif isinstance(value, list):
                for child in value:
                    visit(child)
        visit(json.loads(download_json.read_text()))
    inspection = dict(file=SOURCE.name, sha256=source_hash, valid=True,
                      solids=len(shapes), shells=len(source.Shells), faces=len(source.Faces),
                      **bounds(source))
    derived = dict(file=solids_path.name, sha256=sha(solids_path), valid=solids.isValid(),
                   solids=len(solids.Solids), shells=len(solids.Shells), faces=len(solids.Faces),
                   omitted_non_solid_shells=len(source.Shells) - len(solids.Shells),
                   derivation="Part.makeCompound(original_shape.Solids); no solid geometry resized or substituted",
                   **bounds(solids))
    carrier_holes = [row for row in axial_cylinders(shapes[274])
                     if abs(row["radius_mm"] - 1.375) < 1e-6]
    report = dict(source_url=MODEL_URL,
        referring_official_forum="https://forums.developer.nvidia.com/t/nvidia-orin-nx-fitment-to-sodimm-connector-on-carrier-pcb/344045/5",
        official_catalog_url="https://developer.nvidia.com/embedded/downloads.json",
        retrieved_local_date="2026-09-22", anonymous_HTTP_status=200,
        catalog_entry=entry, archive=dict(file=ZIP_NAME, sha256=sha(DEST / ZIP_NAME), bytes=(DEST / ZIP_NAME).stat().st_size),
        STEP_header_timestamp="2023-02-03T12:47:27", source_inspection=inspection,
        solid_only_cache=derived, product_names=products,
        completeness=dict(carrier_board="600-13768-0000-A04_ASM / P3768", module="P3767 module envelope, as declared by NVIDIA",
                          heatsink="095-0180-000-TS1_ASM", fan="3514_ASM_1112_ASM",
                          base="Included source solid index1266", optional_contents=["NVME-M-2_ASM", "330-0266-000_M2_WIFI_MODULE_ASM", "WiFi antenna assemblies"],
                          limitation="Full developer-kit mechanical reference, not a detailed internal thermal/inertial model; optional CAD contents need not equal the user's installed configuration"),
        recommended_pose=dict(rotation_axis=[0, 0, 1], rotation_deg=90,
                              translation_mm=[1.66325103075716, -46., 37.9],
                              rule="Rotate about source origin first, then translate; original front connector face -Y points to robot +X. Position the actual base support plane sourceZ=-4.9 at globalZ=33, not the lower B-rep control bounding box.",
                              resulting_BRep_control_bounds_mm=[-70.52625102991535, 20.526251031599, -51.68950206067251, 51.68950206067251, 32.86148887556, 67.766],
                              actual_source_base_support_plane_z_mm=-4.9,
                              actual_global_base_support_plane_z_mm=33.,
                              actual_global_top_z_mm=67.766,
                              source_BRep_bbox_underreach_mm=.13851112444),
        mounting=dict(carrier_through_hole_diameter_mm=2.75, carrier_hole_spacing_mm=[86., 58.],
                      carrier_hole_centres_source_mm=[[0,0,0],[86,0,0],[0,58,0],[86,58,0]],
                      source_surface_measurements=carrier_holes,
                      limitation="Carrier holes already fasten to the original base. Base has blind/moulded details underneath; these are not verified through-mount holes for the whole kit. Retain base and use a separate peripheral cradle/retainer unless the physical fastener stack is verified.",
                      recommended_chassis_fasteners="M3 for the new peripheral cradle only; no unverified replacement NVIDIA screw size is claimed"))
    (DEST / "provenance.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    if entry:
        (DEST / "official_catalog_entry.json").write_text(json.dumps(entry, ensure_ascii=False, indent=2) + "\n")
    if args.render:
        import FreeCADGui as Gui
        Gui.showMainWindow()
        import PartGui  # noqa: F401
        doc = App.newDocument("NVIDIA_Orin_Nano_Official_Kit")
        obj = doc.addObject("Part::Feature", "OfficialDeveloperKit")
        obj.Shape = solids
        obj.Label = "NVIDIA Orin Nano developer kit — official 20230320 STEP solids"
        colors = []
        special = {2: (.15,.34,.22), 268: (.45,.48,.50), 273: (.12,.13,.15),
                   274: (.14,.43,.25), 1266: (.17,.18,.20)}
        for index, shape in enumerate(shapes):
            colors.extend([special.get(index, (.60,.62,.64))] * len(shape.Faces))
        obj.ViewObject.DiffuseColor = colors
        obj.ViewObject.DisplayMode = "Flat Lines"
        obj.ViewObject.LineWidth = .5
        obj.ViewObject.LineColor = (.16,.17,.18)
        doc.recompute()
        view = Gui.activeDocument().activeView()
        view.viewAxonometric()
        view.fitAll()
        Gui.updateGui()
        view.saveImage(str(DEST / "official_devkit_preview.png"), 1500, 1100, "White")
    print(json.dumps(dict(source=inspection, derived=derived), indent=2))


if __name__ == "__main__":
    main()
