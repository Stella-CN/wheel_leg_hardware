"""Lay the four curved V6 covers on their broad/end faces for printing.

Assembly and STEP placements remain unchanged. Only print STLs and their
manifest orientation metadata are updated; local support can still be needed.
"""
from pathlib import Path
import json
import sys

sys.path.insert(0,'/Applications/FreeCAD.app/Contents/Resources/lib')
import FreeCAD as App
import Part
import MeshPart

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'mechanical/v6'


def main():
    manifest=json.loads((OUT/'part_manifest.json').read_text())
    rotations={
        'chassis_front_shell':((0,1,0),-90,'service opening down; rear guide edge on bed; removable internal support required'),
        'chassis_rear_cover':((0,1,0),90,'service opening down; removable internal support required'),
        'shoulder_fairing_right':((1,0,0),-90,'outboard annular end down'),
        'shoulder_fairing_left':((1,0,0),90,'outboard annular end down'),
    }
    for name,(axis,angle,description) in rotations.items():
        shape=Part.read(str(OUT/'step'/f'{name}.step'))
        shape.rotate(App.Vector(),App.Vector(*axis),angle)
        shape.tessellate(.06)
        b=shape.BoundBox
        shape.translate(App.Vector(-b.XMin,-b.YMin,-b.ZMin))
        mesh=MeshPart.meshFromShape(Shape=shape,LinearDeflection=.06,AngularDeflection=.18,Relative=False)
        if not mesh.isSolid():raise ValueError(name+' mesh is not closed')
        b=mesh.BoundBox;dimensions=[b.XLength,b.YLength,b.ZLength]
        if any(a>limit+1e-5 for a,limit in zip(dimensions,(220,220,250))):
            raise ValueError(name+' exceeds print bed')
        mesh.write(str(OUT/'print'/f'{name}.stl'))
        row=next(row for row in manifest if row['part']==name)
        row.update(dimensions_mm=[round(v,3) for v in dimensions],facets=mesh.CountFacets,
                   print_orientation=description,mesh_closed=True,fits_bed=True)
    (OUT/'part_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    import csv
    with (OUT/'parts.csv').open('w',newline='') as target:
        writer=csv.writer(target)
        writer.writerow(('part','process','quantity','print_X_mm','print_Y_mm','print_Z_mm','solid_mass_g_each'))
        for row in manifest:
            writer.writerow((row['part'],row['process'],row['quantity'],*row['dimensions_mm'],row['nominal_solid_mass_g']))
    print('V6_PRINT_ORIENTATIONS_UPDATED')


if __name__=='__main__':main()
