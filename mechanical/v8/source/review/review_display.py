"""Independent of chassis generator: verify the declared screen interface."""
import hashlib
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT/'tools'))
import cad_v8_display as d
cad = d.cad
out = ROOT/'mechanical/v8'
d.export_notes(out)
cradles=d.designs(); hw=d.hardware(); device=d.display()
rows=[]; failures=[]

def check(name, passed, **evidence):
    rows.append(dict(check=name,pass_=bool(passed),**evidence))
    if not passed: failures.append(name)

for name,shape in cradles.items():
    overlap=shape.common(device).Volume
    check(name+'_solid',shape.isValid() and len(shape.Solids)==1,volume_mm3=shape.Volume)
    check(name+'_case_clearance',overlap < 1e-7,overlap_mm3=overlap)
    boss=d.xcyl(4.5,107,7,68 if name.endswith('right') else -68,-44)
    check(name+'_panel_boss',shape.common(boss).Volume<1e-7,clearance_mm=shape.distToShape(boss)[0])
    for shift in (0,2,5,10,20):
        moved=shape.copy();moved.translate(d.V(0,shift if name.endswith('right') else -shift,0))
        check(name+f'_side_assembly_{shift}',moved.common(device).Volume<1e-7)

allparts=list(cradles.items())+[(name,s) for name,s,_ in hw]+[('display',device)]
collisions=[]
for i,(an,a) in enumerate(allparts):
    for bn,b in allparts[i+1:]:
        volume=a.common(b).Volume
        if volume>1e-5: collisions.append(dict(a=an,b=bn,overlap_mm3=volume))
check('display_subassembly_no_collisions',not collisions,collisions=collisions)
check('manufacturer_dimensions_only', [device.BoundBox.XLength,device.BoundBox.YLength,device.BoundBox.ZLength]==[14.5,122.,78.])
report=dict(source='tools/cad_v8_display.py',source_sha256=hashlib.sha256((ROOT/'tools/cad_v8_display.py').read_bytes()).hexdigest(),
    checks=rows,failures=failures,limitations=['No exact device connector CAD or front glass/metal boundary supplied.','Checks verify modeled geometry, not structural strength or vibration.'])
(out/'display_local_review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
if failures:raise SystemExit(1)
