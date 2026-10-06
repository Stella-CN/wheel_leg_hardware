"""Convert the supplied motor STEP assemblies into MuJoCo visual meshes.

The preferred converter is the FreeCAD Python executable supplied with the
application. ``auto`` falls back to FreeCAD's bundled Gmsh executable when
FreeCAD cannot start in a headless environment. Both paths read the original
STEP files; the generated STL uses millimetres and is a visual reference. These are historical visual assets; the current
MuJoCo project generates its motor visuals procedurally and does not load them.
"""
from __future__ import annotations

import argparse
import json
import os
import struct
import subprocess
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
FREECAD_PYTHON = Path("/Applications/FreeCAD.app/Contents/Resources/bin/python")
GMSH = FREECAD_PYTHON.with_name("gmsh")
MOTOR_SPECS = json.loads((PROJECT_DIR / "configs/motors.json").read_text())


def _source_and_output(motor: str, output_dir: Path) -> tuple[Path, Path]:
    spec = MOTOR_SPECS[motor]
    if not spec.get("step_model_path") or not spec.get("mesh_asset"):
        raise ValueError(f"{spec['name']} CAD path metadata is incomplete.")
    source = PROJECT_DIR / spec["step_model_path"]
    if not source.is_file():
        raise FileNotFoundError(f"STEP source does not exist: {source}")
    return source, output_dir / Path(spec["mesh_asset"]).name


def _check_output(path: Path) -> None:
    if not path.is_file() or path.stat().st_size < 1024:
        raise RuntimeError(f"CAD conversion produced no usable mesh: {path}")
    # MuJoCo 3.2.7 limits an STL asset to 200,000 triangular faces. Keep
    # conversion failures close to the source command instead of discovering
    # the limit only when compiling the MJCF model.
    with path.open("rb") as stream:
        stream.seek(80)
        count_data = stream.read(4)
    if len(count_data) == 4:
        face_count = struct.unpack("<I", count_data)[0]
        if face_count == 0 or face_count > 200_000:
            raise RuntimeError(
                f"STL face count {face_count} is outside MuJoCo's limit: {path}")


def _export_with_freecad(step_path: Path, output_path: Path,
                         deviation_mm: float) -> None:
    """Run inside FreeCAD Python and export all imported STEP shapes as one STL."""
    resource_dir = Path(sys.executable).resolve().parent.parent
    for module_dir in (resource_dir / "lib", resource_dir / "Ext",
                       resource_dir / "Mod"):
        if str(module_dir) not in sys.path:
            sys.path.insert(0, str(module_dir))
    import FreeCAD as App  # type: ignore[import-not-found]
    import Import  # type: ignore[import-not-found]
    import MeshPart  # type: ignore[import-not-found]
    import Part  # type: ignore[import-not-found]

    document_name = "motor_step_export"
    doc = App.newDocument(document_name)
    try:
        Import.insert(str(step_path), doc.Name)
        doc.recompute()
        shapes = [obj.Shape for obj in doc.Objects
                  if hasattr(obj, "Shape") and not obj.Shape.isNull()]
        if not shapes:
            raise RuntimeError(f"No solid shapes found in {step_path}")
        compound = Part.makeCompound(shapes)
        mesh = MeshPart.meshFromShape(
            Shape=compound,
            LinearDeflection=deviation_mm,
            AngularDeflection=0.3,
            Relative=False,
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        mesh.write(str(output_path))
    finally:
        App.closeDocument(doc.Name)


def _run_freecad(motor: str, output_dir: Path, deviation_mm: float) -> None:
    if not FREECAD_PYTHON.is_file():
        raise FileNotFoundError(f"FreeCAD Python not found: {FREECAD_PYTHON}")
    command = [
        str(FREECAD_PYTHON), str(Path(__file__).resolve()),
        "--engine", "freecad", "--motor", motor,
        "--output-dir", str(output_dir),
        "--deviation-mm", str(deviation_mm),
    ]
    resource_dir = FREECAD_PYTHON.parent.parent
    env = os.environ.copy()
    module_paths = [resource_dir / "lib", resource_dir / "Ext",
                    resource_dir / "Mod"]
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = os.pathsep.join(
        [str(path) for path in module_paths] +
        ([existing_pythonpath] if existing_pythonpath else [])
    )
    result = subprocess.run(command, capture_output=True, text=True,
                            timeout=300, check=False, env=env)
    if result.returncode != 0:
        details = (result.stderr or result.stdout).strip().splitlines()
        tail = "\n".join(details[-8:])
        raise RuntimeError(f"FreeCAD conversion failed for {motor}:\n{tail}")


def _run_gmsh(motor: str, output_dir: Path,
              max_element_mm: float | None) -> None:
    if not GMSH.is_file():
        raise FileNotFoundError(f"Gmsh fallback not found: {GMSH}")
    source, output = _source_and_output(motor, output_dir)
    command = [
        str(GMSH), "-v", "1", "-bin", "-format", "stl", "-2", "-o",
        str(output), str(source),
    ]
    if max_element_mm is not None:
        command[6:6] = ["-clmax", str(max_element_mm)]
    result = subprocess.run(command, capture_output=True, text=True,
                            timeout=600, check=False)
    if result.returncode != 0:
        details = (result.stderr or result.stdout).strip().splitlines()
        tail = "\n".join(details[-8:])
        raise RuntimeError(f"Gmsh conversion failed for {motor}:\n{tail}")
    _check_output(output)


def convert_one(motor: str, engine: str, output_dir: Path,
                deviation_mm: float, max_element_mm: float | None) -> str:
    source, output = _source_and_output(motor, output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    if engine in ("auto", "freecad"):
        try:
            if engine == "freecad":
                _export_with_freecad(source, output, deviation_mm)
            else:
                _run_freecad(motor, output_dir, deviation_mm)
            _check_output(output)
            return "FreeCAD"
        except (FileNotFoundError, RuntimeError, subprocess.SubprocessError) as exc:
            if engine == "freecad":
                raise
            print(f"FreeCAD unavailable for {motor}; using Gmsh fallback: {exc}")
    _run_gmsh(motor, output_dir, max_element_mm)
    return "Gmsh fallback"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--motor", choices=("all", *MOTOR_SPECS), default="all")
    parser.add_argument("--engine", choices=("auto", "freecad", "gmsh"),
                        default="auto")
    parser.add_argument("--output-dir", type=Path,
                        default=PROJECT_DIR / "assets/meshes")
    parser.add_argument("--deviation-mm", type=float, default=0.1,
                        help="FreeCAD linear tessellation deviation in mm")
    parser.add_argument("--gmsh-max-element-mm", type=float, default=1.1,
                        help="Gmsh maximum surface element size in mm (default: 1.1)")
    args = parser.parse_args()
    if args.deviation_mm <= 0 or (args.gmsh_max_element_mm is not None
                                  and args.gmsh_max_element_mm <= 0):
        parser.error("mesh tolerances must be positive")

    motors = tuple(MOTOR_SPECS) if args.motor == "all" else (args.motor,)
    for motor in motors:
        engine = convert_one(motor, args.engine, args.output_dir,
                             args.deviation_mm, args.gmsh_max_element_mm)
        _, output = _source_and_output(motor, args.output_dir)
        print(f"{motor}: {engine}; wrote {output.resolve()}")


if __name__ == "__main__":
    main()
