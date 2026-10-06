"""Validate exported printable STL topology and bounds with system FreeCAD."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, "/Applications/FreeCAD.app/Contents/Resources/lib")
import FreeCAD
import Mesh

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--revision", choices=("v1", "v2", "v3", "v4", "v5", "v6", "v7", "v8", "v8_1"), default="v2")
args = parser.parse_args()
root = Path(__file__).resolve().parents[1] / "mechanical" / args.revision
results = []
for path in sorted((root / "print").glob("*.stl")):
    mesh = Mesh.Mesh(str(path))
    bb = mesh.BoundBox
    result = dict(file=path.name, facets=mesh.CountFacets, closed=mesh.isSolid(),
                  non_manifold=mesh.hasNonManifolds(),
                  self_intersections=mesh.hasSelfIntersections(),
                  inconsistent_normals=mesh.hasNonUniformOrientedFacets(),
                  dimensions_mm=[bb.XLength, bb.YLength, bb.ZLength],
                  on_bed=abs(bb.ZMin) < 1e-5)
    result["fits_bed"] = all(a <= b+1e-5 for a, b in zip(result["dimensions_mm"], (220, 220, 250)))
    result["passed"] = (result["closed"] and result["on_bed"] and result["fits_bed"]
                         and not any(result[k] for k in
                                     ("non_manifold", "self_intersections", "inconsistent_normals")))
    results.append(result)
    print(path.name, "PASS" if result["passed"] else "FAIL", flush=True)
report = dict(units="mm", results=results, all_passed=all(r["passed"] for r in results))
(root / "print_mesh_validation.json").write_text(json.dumps(report, indent=2)+"\n")
if not report["all_passed"] or not results:
    raise RuntimeError("Print STL validation failed")
