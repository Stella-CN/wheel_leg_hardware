"""V5 shallow-machined panel chassis and thin hip stator mount (millimetres).

The nine fixed parts retain a 200 x 150 mm footprint and extend to Z85.
The CNC lower panels end at Z47; a detachable PETG upper electronics bay
receives the embedded front D435 and the taller Orin host.
Structural bottom and walls are CNC 6061-T6; lid and removable trays are PETG.
M3 blind threads are represented by D2.5 tapping drills and 118-degree tips.
Only hip-mount hardware is modelled here. Fixed chassis fastener specifications
are exported separately; chassis_hardware() deliberately returns no duplicates.
"""
from __future__ import annotations
import json
import math
import sys
from pathlib import Path
sys.path.insert(0, "/Applications/FreeCAD.app/Contents/Resources/lib")
import FreeCAD as App
import Part
import cad_chassis as prior

V = App.Vector
WALL = 3.0
HIP_WINDOW = 66.0
LID_FASTENERS = tuple((x, y) for x in (-80., -40., 40., 80.) for y in (-67., 67.))
BOTTOM_FASTENERS = LID_FASTENERS
CORNER_FASTENERS = tuple((x, z) for x in (-92.5, 92.5) for z in (-25., 25.))
BATTERY_FASTENERS = prior.BATTERY_FASTENERS
ELECTRONICS_FASTENERS = tuple((x, y) for x in (-88., 88.) for y in (-45., 45.))


def box(x, y, z, dx, dy, dz):
    return Part.makeBox(dx, dy, dz, V(x, y, z))


def cyl(radius, length, origin, axis=(0, 0, 1)):
    return Part.makeCylinder(radius, length, V(*origin), V(*axis))


def fuse(shapes):
    return shapes[0].multiFuse(shapes[1:]).removeSplitter() if len(shapes)>1 else shapes[0]


def cut(shape, tools):
    return shape.cut(Part.makeCompound(tools)).removeSplitter()


def mirror(shape, axis):
    return shape.mirror(V(0, 0, 0), V(*axis))


def rounded_pocket_xz(x0, x1, z0, z1, y0, depth, radius=3):
    shape=prior._rounded_prism(x1-x0,z1-z0,depth,0,radius)
    shape.rotate(V(),V(1,0,0),90)
    shape.translate(V((x0+x1)/2,y0+depth,(z0+z1)/2))
    return shape


def rounded_pocket_yz(y0, y1, z0, z1, x0, depth, radius=3):
    shape=prior._rounded_prism(z1-z0,y1-y0,depth,0,radius)
    shape.rotate(V(),V(0,1,0),90)
    shape.translate(V(x0,(y0+y1)/2,(z0+z1)/2))
    return shape


def tap_drill(face, inward, depth=6.5, diameter=2.5):
    """Blind tapping pilot; depth is cylindrical length, excluding drill point."""
    p, n = V(*face), V(*inward)
    radius = diameter/2
    tip = radius/math.tan(math.radians(59))
    stem = Part.makeCylinder(radius, depth+.1, p-n*.1, n)
    return stem.fuse(Part.makeCone(radius, 0, tip, p+n*depth, n))


def counterbore_clearance(face, inward, thickness, clearance=3.4,
                          head_diameter=6.4, head_depth=1.5):
    """90-degree countersink opening on an accessible outside plane."""
    p, n = V(*face), V(*inward)
    drill = Part.makeCylinder(clearance/2, thickness+.2, p-n*.1, n)
    sink = Part.makeCone(head_diameter/2, clearance/2, head_depth, p, n)
    return drill.fuse(sink)


def hip_stator_mount():
    """Right mount; ring Y72..75, outer ears Y75..78 with a D58 cup window."""
    ring = cyl(31, 3, (0, 72, 0), (0, 1, 0))
    plate = box(-39, 75, -39, 78, 3, 78)
    plate = cut(plate, [cyl(29, 3.2, (0, 74.9, 0), (0, 1, 0))])
    shape = cut(fuse([ring, plate]), [cyl(20.2, 8, (0, 71, 0), (0, 1, 0))])
    tools = []
    for i in range(6):
        t = math.radians(30+60*i)
        x, z = 25*math.cos(t), 25*math.sin(t)
        tools.append(counterbore_clearance((x, 75, z), (0, -1, 0), 3))
    for x in (-30, 30):
        for z in (-30, 30):
            tools.append(counterbore_clearance((x, 78, z), (0, -1, 0), 3,
                                               4.4, 9.0, 2.3))
    shape = cut(shape, tools)
    _check('hip_stator_mount', shape)
    return shape


def hex_nut(x, y, z, across_flats, thickness, bore):
    r = across_flats/math.sqrt(3)
    pts = [V(x+r*math.cos(math.radians(30+60*i)), y,
             z+r*math.sin(math.radians(30+60*i))) for i in range(6)]
    shape = Part.Face(Part.makePolygon(pts+[pts[0]])).extrude(V(0, thickness, 0))
    return shape.cut(cyl(bore/2, thickness+.2, (x, y-.1, z), (0, 1, 0)))


def hip_hardware():
    """Right side only, role 'fixed'; caller mirrors to create the left side."""
    items = []
    for i in range(6):
        t = math.radians(30+60*i)
        x, z = 25*math.cos(t), 25*math.sin(t)
        # DIN7991-style M3x6: head top Y75; full tip Y69. Motor-engaged
        # Y69..72 is omitted because manufacturer STEP threads are static.
        screw = fuse([cyl(1.5, 1.3, (x, 72, z), (0, 1, 0)),
                      Part.makeCone(1.5, 3, 1.5, V(x, 73.3, z), V(0, 1, 0)),
                      cyl(3, .2, (x, 74.8, z), (0, 1, 0))])
        items.append((f'hip_stator_M3x6_CS_{i}', screw, 'fixed'))
    for i, (x, z) in enumerate(( (x,z) for x in (-30,30) for z in (-30,30) )):
        # DIN7991 D8 x k2.3 head seats 0.2mm below Y78 in the D9 sink.
        # Head top77.8 / length12 -> tip65.8; nut tip projection2.2mm.
        screw = fuse([cyl(2, 9.7, (x, 65.8, z), (0, 1, 0)),
                      Part.makeCone(2, 4, 2, V(x, 75.5, z), V(0, 1, 0)),
                      cyl(4, .3, (x, 77.5, z), (0, 1, 0))])
        washer = cut(cyl(4.5, .8, (x, 71.2, z), (0, 1, 0)),
                     [cyl(2.15, 1, (x, 71.1, z), (0, 1, 0))])
        nut = hex_nut(x, 68, z, 7, 3.2, 4)
        items.extend(((f'hip_case_M4x12_CS_{i}', screw, 'fixed'),
                      (f'hip_case_M4_washer_{i}', washer, 'fixed'),
                      (f'hip_case_M4_nut_{i}', nut, 'fixed')))
    return items


def _side_wall(right=True, lightweight=True):
    # Machined from a 14mm slab: a 3mm skin and 11mm inward ledges.
    skin = box(-97, 72, -47, 194, 3, 94)
    ledges = [box(-86, 61, z, 172, 11, 8) for z in (-47, 39)]
    shape = fuse([skin]+ledges)
    # Radius2 at each ledge root; these are real inside cutter radii.
    edges = [e for e in shape.Edges if abs(e.CenterOfMass.y-72)<1e-6 and
             ((e.Length>170 and min(abs(e.CenterOfMass.z-z) for z in (-39,39))<1e-6) or
              (abs(e.Length-8)<1e-6 and abs(abs(e.CenterOfMass.x)-86)<1e-6))]
    shape = shape.makeFillet(2, edges)
    tools = [cyl(HIP_WINDOW/2, 5, (0,71,0),(0,1,0))]
    tools.extend(cyl(2.2, 5, (x,71,z),(0,1,0)) for x in (-30,30) for z in (-30,30))
    tools.extend(counterbore_clearance((x,75,z),(0,-1,0),3)
                 for x,z in CORNER_FASTENERS)
    for x in (-80., -40., 40., 80.):
        tools.append(tap_drill((x,67,47),(0,0,-1)))
        tools.append(tap_drill((x,67,-47),(0,0,1)))
    # Keep the hip load frame full thickness; shallow pockets only fore/aft.
    if lightweight:
        tools.extend(rounded_pocket_xz(a,b,-36,36,71.9,1.6,3)
                     for a,b in ((-87,-40),(40,87)))
    shape = cut(shape, tools)
    return shape if right else mirror(shape, (0,1,0))


def _end_wall(front=True, lightweight=True):
    skin = box(97, -75, -47, 3, 150, 94)
    rails = [box(88, y, -47, 9, 8, 94) for y in (-72,64)]
    # Electronics support plane Z30: above the stator's Z28.5 envelope.
    shelves = [box(82.5, y-5.5, 22, 14.5, 11, 8) for y in (-45,45)]
    shape = fuse([skin]+rails+shelves)
    # Long corner rails use the same R2 inside milling radius.
    edges = [e for e in shape.Edges if e.Length>90 and
             abs(e.CenterOfMass.x-97)<1e-6 and
             min(abs(e.CenterOfMass.y-y) for y in (-64,64))<1e-6]
    shape = shape.makeFillet(2, edges)
    # The small shelves are milled from the inside with R2 roots.
    edges = [e for e in shape.Edges if abs(e.CenterOfMass.x-97)<1e-6 and
             ((abs(e.Length-11)<1e-5 and min(abs(e.CenterOfMass.z-z) for z in (22,30))<1e-6) or
              (abs(e.Length-8)<1e-5 and abs(e.CenterOfMass.z-26)<1e-6))]
    shape = shape.makeFillet(2, edges)
    tools=[]
    for side in (-1,1):
        for z in (-25,25):
            tools.append(tap_drill((92.5,72*side,z),(0,-side,0)))
    for y in (-45,45):
        tools.append(tap_drill((88,y,30),(0,0,-1)))
    # Lower cable aperture; camera brackets attach to the PETG upper shell.
    tools.append(cyl(6, 5, (96,0,20),(1,0,0)))
    for y in (-55,-35,35,55):
        slot=fuse([box(96,y-1.6,4.6,5,3.2,13.8),
                   cyl(1.6,5,(96,y,4.6),(1,0,0)),cyl(1.6,5,(96,y,18.4),(1,0,0))])
        tools.append(slot)
    # Leave a 1.5mm skin, uncut corner rails, shelf backing, and 3mm web ribs.
    if lightweight:
        tools.append(rounded_pocket_yz(-30,30,-39,39,96.9,1.6,3))
        for a,b in ((-61,-33),(33,61)):
            tools.append(rounded_pocket_yz(a,b,-39,17,96.9,1.6,3))
    shape=cut(shape,tools)
    return shape if front else mirror(shape,(1,0,0))


def _bottom(lightweight=True):
    shape=box(-100,-75,-50,200,150,3)
    # Battery ears retain the existing Z-39 mounting plane; posts are shallow.
    shape=fuse([shape]+[cyl(6,8,(x,y,-47)) for x,y in BATTERY_FASTENERS])
    roots=[e for e in shape.Edges if abs(e.CenterOfMass.z+47)<1e-6 and
           abs(e.Length-2*math.pi*6)<1e-5]
    shape=shape.makeFillet(2,roots)
    tools=[counterbore_clearance((x,y,-50),(0,0,1),3) for x,y in BOTTOM_FASTENERS]
    tools.extend(tap_drill((x,y,-39),(0,0,-1)) for x,y in BATTERY_FASTENERS)
    # 2mm floor, with the continuous side ledge seats and battery post lands
    # retained at 3mm. Round islands preserve each post root and bolt load path.
    if lightweight:
        pocket=prior._rounded_prism(188,116,1.1,-48,3)
        pocket=cut(pocket,[cyl(10,1.3,(x,y,-48.1)) for x,y in BATTERY_FASTENERS])
        tools.append(pocket)
    return cut(shape,tools)


def _upper_shell():
    outer=prior._rounded_prism(200,150,35,47,4)
    cavity=prior._rounded_prism(194,144,35.2,46.9,1)
    body=outer.cut(cavity)
    additions=[body]
    for x,y in LID_FASTENERS:
        # Bottom feet bolt directly to the CNC ledges at Z47.
        additions.append(cyl(6,3,(x,y,47)))
        # Top nut bosses remain outside the Orin central envelope.
        additions.append(cyl(6,8,(x,y,74)))
    body=fuse(additions)
    tools=[]
    for x,y in LID_FASTENERS:
        tools.append(cyl(1.7,3.2,(x,y,46.9)))
        tools.append(cyl(1.7,8.2,(x,y,73.9)))
        pts=[V(x+5.8/math.sqrt(3)*math.cos(math.radians(30+60*i)),
               y+5.8/math.sqrt(3)*math.sin(math.radians(30+60*i)),73.9) for i in range(6)]
        tools.append(Part.Face(Part.makePolygon(pts+[pts[0]])).extrude(V(0,0,4.5)))
    # Full rectangular clearance preserves the camera's entire 90x25 outline.
    tools.append(box(96,-45.3,50.7,5,90.6,25.6))
    for y in (-50,50):
        for z in (56,72):
            tools.append(cyl(1.7,5,(96,y,z),(1,0,0)))
    # Side intake slots, below the captive top nuts and clear of the device.
    for side in (-1,1):
        for z in (58,68):
            y=71 if side>0 else -76
            tools.append(fuse([box(-62.6,y,z-2.4,75.2,5,4.8),
                               cyl(2.4,5,(-62.6,y,z),(0,1,0)),
                               cyl(2.4,5,(12.6,y,z),(0,1,0))]))
    return cut(body,tools)


def _lid():
    plate=prior._rounded_prism(200,150,3,82,4)
    tools=[counterbore_clearance((x,y,85),(0,0,-1),3)
           for x,y in LID_FASTENERS]
    # Exhaust above the Orin host, leaving at least 5.2mm ribs between slots.
    for x in (-62,-52,-42,-32,-22,-12,-2,8,18):
        tools.append(fuse([box(x-2.4,-35.6,81.9,4.8,71.2,3.2),
                           cyl(2.4,3.2,(x,-35.6,81.9)),
                           cyl(2.4,3.2,(x,35.6,81.9))]))
    return cut(plate,tools)


def _electronics_tray():
    shape=prior._rounded_prism(188,108,3,30,3)
    tools=[cyl(1.7,3.2,(x,y,29.9)) for x,y in ELECTRONICS_FASTENERS]
    tools.extend(prior._slot_z(x,y,29.9,16,3.4,3.2)
                 for x in (-60,-20,20,60) for y in (-38,38))
    return cut(shape,tools)


def materials():
    return {name: ('PETG' if name in ('chassis_lid','chassis_upper_shell','battery_tray','electronics_tray') else 'CNC')
            for name in ('chassis_lower_shell','chassis_side_right','chassis_side_left',
                         'chassis_front_wall','chassis_rear_wall','chassis_upper_shell','chassis_lid',
                         'battery_tray','electronics_tray')}


def _check(name, shape):
    shape.check(True)
    if not shape.isValid() or len(shape.Solids)!=1:
        raise ValueError(f'{name}: expected one valid solid, got {len(shape.Solids)}')


def build_chassis(lightweight=True):
    parts={'chassis_lower_shell':_bottom(lightweight),
           'chassis_side_right':_side_wall(True,lightweight), 'chassis_side_left':_side_wall(False,lightweight),
           'chassis_front_wall':_end_wall(True,lightweight), 'chassis_rear_wall':_end_wall(False,lightweight),
           'chassis_upper_shell':_upper_shell(), 'chassis_lid':_lid(), 'battery_tray':prior._battery_tray(),
           'electronics_tray':_electronics_tray()}
    for name,shape in parts.items():
        _check(name,shape)
    return parts


def chassis_hardware():
    """No chassis screws modelled yet; see fastener_specification()."""
    return []


def fastener_specification():
    return [
      dict(location='bottom to metal side ledges',quantity=8,spec='M3x8 90deg countersunk',grip=3,engagement=5,access='underside before battery tray'),
      dict(location='PETG upper enclosure feet to metal side ledges',quantity=8,spec='M3x8 socket head',grip=3,engagement=5,access='from above'),
      dict(location='PETG lid to upper enclosure captive nuts',quantity=8,spec='M3x10 90deg countersunk + M3 nut t2.4',grip=6.6,engagement=2.4,access='from top; nuts inserted from underside before upper shell fit'),
      dict(location='metal side walls to end-wall rails',quantity=8,spec='M3x8 90deg countersunk',grip=3,engagement=5,access='from outside left/right before hip mounts'),
      dict(location='battery tray to metal bottom posts',quantity=4,spec='M3x8 socket head',grip=3,engagement=5,access='from open top'),
      dict(location='electronics tray to metal end-wall shelves',quantity=4,spec='M3x8 socket head',grip=3,engagement=5,access='from open top; mounting face Z30'),
      dict(location='hip mounts to hip stators',quantity=12,spec='DIN7991 M3x6, head D6 x 1.7; not larger ISO10642 head',grip=3,engagement=3,access='from outside before motor cup; top Y75'),
      dict(location='hip mounts to side walls',quantity=8,spec='DIN7991 M4x12, head D8 x 2.3 + washer t0.8 + M4 nut t3.2',grip=6.6,engagement=3.2,access='outside driver plus inside nut before tray; head top77.8',tip_projection=2.2),
    ]


def export_review(folder):
    """Export local evidence without touching previous revisions."""
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    parts=build_chassis();parts['hip_stator_mount']=hip_stator_mount()
    report={'units':'mm','materials':materials(),'parts':{},'collisions':[],
            'M3_tap_drill':dict(diameter=2.5,cylindrical_depth=6.5,tip_angle=118,full_thread_required=5),
            'fasteners':fastener_specification(),'heat_set_inserts':0,
            'manufacturing_scope':'nominal shallow CNC panels; blind holes are tapping pilots, not real threads',
            'electronics':dict(tray_z=[30,33],tray_xy=[188,108],device_envelope_not_modelled=True,
                               upper_body_z=[47,82],lid_z=[82,85],device_base_z=33,maximum_device_top_z=68.86,nominal_clearance_to_lid=13.14),
            'D435_upper_panel':dict(front_x=100,opening_y=[-45.3,45.3],opening_z=[50.7,76.3],
                                    bracket_holes_diameter=3.4,bracket_holes_y=[-50,50],bracket_holes_z=[56,72]),
            'ventilation':dict(lid_capsule_slots=9,lid_slot_length=76,lid_slot_width=4.8,
                               side_capsule_slots=4,side_slot_length=80,side_slot_width=4.8,
                               thermal_performance_validated=False),
            'countersunk_screw_source':'https://eshop-tr.boellhoff.com/out/media/pdf/DIN_7991_Stahl_10.9_gv___en.pdf',
            'strength_validated':False}
    for name,shape in parts.items():
        _check(name,shape)
        bb=shape.BoundBox
        report['parts'][name]=dict(valid=True,solids=1,volume_mm3=shape.Volume,
                                  bbox=[bb.XMin,bb.YMin,bb.ZMin,bb.XMax,bb.YMax,bb.ZMax])
    named=list(parts.items())
    for i,(an,a) in enumerate(named):
        for bn,b in named[i+1:]:
            if not a.BoundBox.intersect(b.BoundBox):continue
            volume=a.common(b).Volume
            if volume>.001:report['collisions'].append(dict(a=an,b=bn,volume=volume))
    report['hip_hardware_collisions']=[]
    for name,shape,_ in hip_hardware():
        _check(name,shape)
        for part in ('hip_stator_mount','chassis_side_right'):
            vol=shape.common(parts[part]).Volume
            if vol>.001:report['hip_hardware_collisions'].append(dict(hardware=name,part=part,volume=vol))
    baseline=build_chassis(lightweight=False)
    metal_names=[n for n,m in materials().items() if m=='CNC']
    before=sum(baseline[n].Volume for n in metal_names)*.0027
    after=sum(parts[n].Volume for n in metal_names)*.0027
    report['lightweight_metal_panels']=dict(density_g_cm3=2.7,
        comparison='Same five lower panels with versus without the three families of shallow CNC pockets',
        baseline_mass_g=before,final_mass_g=after,reduction_g=before-after,
        pocket_floor_mm=dict(bottom=2,side_outside_hip_load_frame=1.5,front_rear=1.5),
        per_panel=[dict(name=n,baseline_g=baseline[n].Volume*.0027,final_g=parts[n].Volume*.0027)
                   for n in metal_names])
    (folder/'chassis_review.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__=='__main__':
    root=Path(__file__).resolve().parents[1]
    report=export_review(root/'mechanical/v5')
    print(json.dumps({k:report[k] for k in ('collisions','hip_hardware_collisions')},indent=2))
