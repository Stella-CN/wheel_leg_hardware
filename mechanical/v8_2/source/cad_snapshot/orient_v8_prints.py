"""Orient V8 housings and screen carriers for the220x220x250mm printer."""
from __future__ import annotations

import csv
import json
import build_printable_robot as cad

OUT=cad.ROOT/'mechanical/v8'


def main():
    rows=json.loads((OUT/'part_manifest.json').read_text())
    for row in rows:
        if row['process']!='PETG':continue
        name=row['part']
        shape=cad.Part.read(str(OUT/'step'/f'{name}.step'))
        axis,angle,description=(0,0,1),0,'Original lower face down; supports may be needed'
        if name in ('chassis_front_shell','chassis_rear_cover'):
            axis,angle=(0,1,0),(-90 if name.endswith('shell') else 90)
            description='Vertical service split down; removable internal support required'
        elif name in ('display_front_bezel','D435_embedded_bracket','display_case_cradle_right','display_case_cradle_left'):
            axis,angle=(0,1,0),90
            description='Front installation face down; clear nut pockets after printing'
        elif name.startswith('shoulder_fairing'):
            axis,angle=(1,0,0),(-90 if name.endswith('right') else 90)
            description='Outboard annular end down'
        shape.rotate(cad.V(),cad.V(*axis),angle)
        shape.tessellate(.06);b=shape.BoundBox
        shape.translate(cad.V(-b.XMin,-b.YMin,-b.ZMin))
        mesh=cad.MeshPart.meshFromShape(Shape=shape,LinearDeflection=.06,AngularDeflection=.18,Relative=False)
        b=mesh.BoundBox;dims=[b.XLength,b.YLength,b.ZLength]
        if not mesh.isSolid() or any(d>limit+1e-5 for d,limit in zip(dims,(220,220,250))):
            raise ValueError(f'Print geometry invalid: {name}: {dims}')
        mesh.write(str(OUT/'print'/f'{name}.stl'))
        row.update(dimensions_mm=[round(v,3) for v in dims],facets=mesh.CountFacets,
                   print_orientation=description,mesh_closed=True,fits_bed=True)
    (OUT/'part_manifest.json').write_text(json.dumps(rows,indent=2)+'\n')
    with (OUT/'parts.csv').open('w',newline='') as target:
        writer=csv.writer(target)
        writer.writerow(('part','process','quantity','print_X_mm','print_Y_mm','print_Z_mm','solid_mass_g_each'))
        for row in rows:writer.writerow((row['part'],row['process'],row['quantity'],*row['dimensions_mm'],row['nominal_solid_mass_g']))
    print('V8_PRINT_ORIENTATIONS_UPDATED',flush=True)


if __name__=='__main__':main()
