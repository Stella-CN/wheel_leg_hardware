"""Export the native FreeCAD assembly as a single multi-shell STL in mm.

The STL preserves assembled positions. It is for assembly viewing, not a
replacement for the independently oriented printable parts.
"""
from pathlib import Path
import argparse
import json
import sys

sys.path.insert(0, "/Applications/FreeCAD.app/Contents/Resources/lib")
import FreeCAD as App
import Mesh
import MeshPart
import Part

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--revision", choices=("v1", "v2", "v3", "v4", "v5", "v6", "v7", "v8"), default="v1")
args = parser.parse_args()
OUT = ROOT / "mechanical" / args.revision
parameters = json.loads((OUT / "design_parameters.json").read_text())
doc = App.openDocument(str(OUT / f"wheel_leg_{args.revision}.FCStd"))
doc.recompute()
objects = [obj for obj in doc.Objects if obj.TypeId == "Part::Feature"
           and getattr(obj,'ExportRole','')!='collision_and_mass_proxy_only']
assembly = Part.makeCompound([obj.Shape for obj in objects])
mesh = MeshPart.meshFromShape(Shape=assembly, LinearDeflection=0.12,
                              AngularDeflection=0.22, Relative=False)
mesh_objects=[obj for obj in doc.Objects if obj.TypeId=='Mesh::Feature']
for obj in mesh_objects:
    # Like Part::Feature.Shape, Mesh::Feature.Mesh already includes Placement.
    part_mesh=obj.Mesh.copy()
    mesh.addMesh(part_mesh)
path = OUT / "wheel_leg_assembly.stl"
mesh.write(str(path))
roundtrip = Mesh.Mesh(str(path))
if roundtrip.CountFacets != mesh.CountFacets or roundtrip.CountFacets == 0:
    raise RuntimeError("Assembly STL did not round-trip correctly")
bb = roundtrip.BoundBox
report = {
    "filename": path.name,
    "units": "mm",
    "purpose": ("assembled multi-shell reference; CNC uses cnc/*.step; individual PETG parts use print/*.stl"
                if args.revision in ("v5", "v6") else
                "assembled multi-shell reference; use print/*.stl for individual PETG parts"),
    "objects": len(objects),
    "mesh_objects": [o.Name for o in mesh_objects],
    "facets": mesh.CountFacets,
    "file_bytes": path.stat().st_size,
    "dimensions_mm": [bb.XLength, bb.YLength, bb.ZLength],
    "coordinates": "X forward, Y lateral, Z up; hip axis at Z=0",
    "linear_deflection_mm": 0.12,
    "includes": (["custom CNC structure", "PETG electronics enclosure and trays", "approximate payload envelopes"] if args.revision in ("v5", "v6") else ["printed structure", "custom CNC parts"]) + ["original motor STEP geometry",
                 parameters.get("bearing", "joint bearing references"),
                 "modelled joint fasteners and spacers", "elastic tyre reference"],
    "not_modelled": ["unmodelled motor and chassis fasteners", "cables", "actual battery and controller"],
}
if args.revision in ('v6','v7','v8'):
    report['includes']=[item for item in report['includes'] if item!='approximate payload envelopes']
    report['includes'] += ['NVIDIA official developer-kit STEP solids',
                           'RealSense official D435 ROS visualization mesh',
                           'assumed 400g battery and unselected IMU envelopes']
    report['not_modelled']=['unmodelled motor and chassis fasteners',
                           'cables and connector plugs',
                           'actual battery and selected IMU geometry',
                           'power distribution and DC/DC hardware']
    report['mesh_scope']='Assembly visualization; vendor camera mesh may contain open surfaces. Individual manufactured-part meshes validated separately.'
if args.revision=='v7':
    report['purpose']='assembled multi-shell reference; CNC uses cnc/*.step; individual PETG parts use print/*.stl'
    report['includes']=['custom CNC load-bearing structure','PETG faceted enclosure and removable display bezel',
        'original motor STEP geometry','modelled joint hardware and tyres',
        'NVIDIA official developer-kit STEP solids','RealSense official D435 ROS visualization mesh',
        'HiPNUC official HI13XX-USB STEP at manufacturer IMU datum',
        'user-dimensioned screen envelope and assumed400g battery']
    report['not_modelled']=['selected display vendor CAD and mounting-lug geometry',
        'four display screw lengths awaiting lug thickness','unmodelled motor/chassis fasteners',
        'cables/connector plugs','actual battery','power distribution and DC/DC hardware']
if args.revision=='v8':
    report['purpose']='assembled multi-shell reference; CNC uses cnc/*.step; individual PETG parts use print/*.stl'
    report['includes']=['unchanged V6 CNC legs and original motors','PETG small-radius rectangular body and removable front panel',
        'NVIDIA official developer-kit STEP solids','RealSense official D435 ROS visualization mesh',
        'HiPNUC official HI13XX-USB STEP at centred datum','GK-HD5 dimensional envelope and assumed400g battery']
    report['not_modelled']=['supplier GK-HD5 detailed geometry/active area/actual mass',
        'unmodelled motor/chassis fasteners','cables/connector plugs','actual battery','power distribution/DC-DC']
(OUT / "assembly_stl_report.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
