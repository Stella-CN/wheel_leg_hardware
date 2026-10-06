"""V6 continuous full-height curved enclosure with a vertical service split.

Two printed shells enclose a re-packed five-piece CNC load frame. There is no
separate upper electronics box or lid. Motor datums and leg geometry stay
unchanged; the D435 sits in the main front panel at X100, centre Z19.
"""
from __future__ import annotations
import json
import math
from pathlib import Path
import cad_v5_chassis as core
import cad_v3_profiles as profiles
import cad_v6_jetson_mount as jetson_mount

App,Part,V=core.App,core.Part,core.V
box,cyl,fuse,cut=core.box,core.cyl,core.fuse,core.cut
hip_stator_mount=core.hip_stator_mount
hip_hardware=core.hip_hardware
BOTTOM_FASTENERS=tuple((x,y) for x in (-70.,-35.,35.,70.) for y in (-67.,67.))
TRAY_FASTENERS=tuple((x,y) for x in (-74.,38.) for y in (-48.,48.))
SHELL_FASTENERS=tuple((y,z) for y in (-62.,62.) for z in (-40.,41.))
SHOULDER_FASTENERS=tuple((x,z) for x in (-45.,45.) for z in (35.,))
SPLIT_X=-20.
PROFILE=(( -52.,202.,158.,18.,-6.),(-38.,210.,164.,22.,-5.),
         (30.,210.,164.,22.,-5.),(60.,202.,158.,24.,-5.),(82.,186.,146.,28.,-4.))


def _xy_wire(dx,dy,radius,z=0,cx=0):
    shape=core.prior._rounded_prism(dx,dy,.1,z,radius)
    face=next(f for f in shape.Faces if abs(f.CenterOfMass.z-z)<1e-6)
    wire=face.OuterWire.copy();wire.translate(V(cx,0,0))
    return wire


def _loft(sections):
    return Part.makeLoft([_xy_wire(dx,dy,r,z,cx) for z,dx,dy,r,cx in sections],True,False)


def _inner(offset=3,top=79):
    sections=[]
    for i,(z,dx,dy,r,cx) in enumerate(PROFILE):
        if i==0:z=-53
        if i==len(PROFILE)-1:z=top
        sections.append((z,dx-2*offset,dy-2*offset,r-offset,cx))
    return _loft(sections)


def _outer():
    return cut(_loft(PROFILE),[box(100,-110,-60,35,220,150),box(-145,-110,-60,35,220,150)])


def _bottom(lightweight=True):
    shape=core.prior._rounded_prism(174,144,3,-50,8)
    shape=fuse([shape]+[cyl(6,8,(x,y,-47)) for x,y in core.BATTERY_FASTENERS])
    tools=[core.counterbore_clearance((x,y,-50),(0,0,1),3) for x,y in BOTTOM_FASTENERS]
    tools.extend(core.tap_drill((x,y,-39),(0,0,-1)) for x,y in core.BATTERY_FASTENERS)
    if lightweight:
        pocket=core.prior._rounded_prism(162,120,1.1,-48,5)
        pocket=cut(pocket,[cyl(10,1.3,(x,y,-48.1)) for x,y in core.BATTERY_FASTENERS])
        tools.append(pocket)
    return cut(shape,tools)


def _side(right=True,lightweight=True):
    skin=core.rounded_pocket_xz(-86,86,-47,47,72,3,5)
    pieces=[skin,box(-79.5,61,-47,159,11,8),box(-79.5,65,39,159,7,8)]
    # Tray supports are carried by the side frames outside the hip-motor disk,
    # leaving the entire lowered camera and its four rear arms unobstructed.
    for x in (-74,38):pieces.append(box(x-5.5,43,22,11,29,8))
    for x,z in SHOULDER_FASTENERS:pieces.append(cyl(5,6,(x,66,z),(0,1,0)))
    shape=fuse(pieces)
    tools=[cyl(33,6,(0,70,0),(0,1,0))]
    tools.extend(cyl(2.2,6,(x,70,z),(0,1,0)) for x in (-30,30) for z in (-30,30))
    for x in (-82,82):
        for z in (-25,25):tools.append(core.counterbore_clearance((x,75,z),(0,-1,0),3))
    for x in (-70,-35,35,70):tools.append(core.tap_drill((x,67,-47),(0,0,1)))
    for x in (-74,38):tools.append(core.tap_drill((x,48,30),(0,0,-1)))
    # Keep the front shelf clear of the upper-front hip M4 washer and nut.
    # The D11 pocket also accepts a thin-wall AF7 holding socket before the
    # electronics tray is fitted; the 3 mm hip-frame skin remains intact.
    tools.append(cyl(5.5,29.1,(30,42.9,30),(0,1,0)))
    for x,z in SHOULDER_FASTENERS:tools.append(core.tap_drill((x,75,z),(0,-1,0),6.5))
    if lightweight:
        for a,b in ((-78,-39),(39,78)):
            tools.append(core.rounded_pocket_xz(a,b,-34,15,71.9,1.6,3))
    shape=cut(shape,tools)
    return shape if right else core.mirror(shape,(0,1,0))


def _crossframe(front=True,lightweight=True):
    skin=core.rounded_pocket_yz(-72,72,-47,47,83,3,5)
    rails=[box(80,y,-47,3,14,94) for y in (-72,58)]
    shape=fuse([skin]+rails)
    # D435 body, all four Y46..54 arms and the rear transverse bridge pass
    # through this 116x70 opening, with room above and around the camera.
    opening=core.rounded_pocket_yz(-58,58,-35,35,79,8,5)
    shape=cut(shape,[opening])
    shape=fuse([shape]+[cyl(5,6,(80,y,z),(1,0,0)) for y,z in SHELL_FASTENERS])
    tools=[]
    for side in (-1,1):
        for z in (-25,25):tools.append(core.tap_drill((82,72*side,z),(0,-side,0)))
    for y,z in SHELL_FASTENERS:tools.append(cyl(1.25,6.2,(79.9,y,z),(1,0,0)))
    shape=cut(shape,tools)
    return shape if front else core.mirror(shape,(1,0,0))


def _tray():
    shape=core.prior._rounded_prism(152,108,3,30,3)
    shape.translate(V(-10,0,0))
    return cut(shape,[cyl(1.7,3.2,(x,y,29.9)) for x,y in TRAY_FASTENERS]+jetson_mount.tray_hole_tools())


def _body_cutters():
    tools=[]
    for side in (-1,1):
        tools.append(cyl(36.2,35,(0,60*side,0),(0,side,0)))
        # The metal hip seat has square ears outside the motor circle. A
        # shallow inside relief clears them without opening the outer skin.
        seat_relief=core.rounded_pocket_xz(-39.5,39.5,-39.5,39.5,74.9,3.6,1)
        tools.append(seat_relief if side>0 else core.mirror(seat_relief,(0,1,0)))
        for x,z in SHOULDER_FASTENERS:
            tools.append(cyl(1.7,15,(x,74.9*side,z),(0,side,0)))
    tools.append(box(96,-45.3,6.2,7,90.6,25.6))
    for y in (-50,50):
        for z in (11.5,27.5):
            tools.append(cyl(1.7,7,(96,y,z),(1,0,0)))
            # Four bracket-arm corners fit a shallow inner pocket. Keep the
            # X97 contact plane and its 3 mm front pad fully load-bearing.
            tools.append(box(86,y-4.2,z-4.2,11,8.4,8.4))
    for x in (-63,-53,-43,-33,-23,-13,-3,7,17):
        tools.append(fuse([box(x-2.4,-30.6,77,4.8,61.2,7),
                           cyl(2.4,7,(x,-30.6,77)),cyl(2.4,7,(x,30.6,77))]))
    for side in (-1,1):
        for z in (52,63):
            tools.append(core.rounded_pocket_xz(-60,12,z-2.4,z+2.4,
                                                71 if side>0 else -90,19,2.3))
    return tools


def _shell_pair():
    outer=_outer();inner=_inner()
    shape=outer.cut(inner)
    # A continuous printed lower lip overlaps the metal belly plate by 2 mm.
    lip=outer.common(box(-120,-100,-52,230,200,2))
    hole=core.prior._rounded_prism(170,140,3,-52.5,6)
    shape=fuse([shape,lip.cut(hole)])
    pieces=[shape]
    for side in (-1,1):
        for x,z in SHOULDER_FASTENERS:
            pieces.append(cyl(8,11,(x,75*side,z),(0,side,0)))
    for y,z in SHELL_FASTENERS:
        pieces.append(cyl(5,14,(86,y,z),(1,0,0)))
        pieces.append(cyl(5,24,(-110,y,z),(1,0,0)))
    for y in (-50,50):
        for z in (11.5,27.5):pieces.append(cyl(4.5,3,(97,y,z),(1,0,0)))
    shape=fuse(pieces)
    tools=_body_cutters()
    for y,z in SHELL_FASTENERS:
        tools.extend((cyl(1.7,15,(85.8,y,z),(1,0,0)),cyl(1.7,25,(-110.5,y,z),(1,0,0))))
    for x,y in BOTTOM_FASTENERS:tools.append(cyl(4,3,(x,y,-52.5)))
    shape=cut(shape,tools)
    front=shape.common(box(SPLIT_X,-110,-60,140,220,150)).removeSplitter()
    rear=shape.common(box(-130,-110,-60,110,220,150)).removeSplitter()
    # A shallow internal tongue follows the actual curved wall, rather than
    # adding an external horizontal seam. The rear pocket has 0.3 mm play.
    guide=cut(_inner(2.8,79.2),[_inner(5,77)])
    guide=guide.common(box(-24,-110,-52,4.5,220,137))
    guide=cut(guide,_body_cutters())
    front=fuse([front,guide])
    receiver=_inner(2.5,79.5).common(box(-24.3,-110,-53,4.4,220,137))
    rear=cut(rear,[receiver])
    return front,rear


def _beam_xz(p,q,radius,y,depth):
    dx,dz=q[0]-p[0],q[1]-p[1];length=math.hypot(dx,dz)
    ux,uz=dx/length,dz/length
    nx,nz=-uz*radius,ux*radius
    contour=(profiles._Contour((p[0]+nx,p[1]+nz))
             .line((q[0]+nx,q[1]+nz))
             .arc((q[0]+ux*radius,q[1]+uz*radius),(q[0]-nx,q[1]-nz))
             .line((p[0]-nx,p[1]-nz))
             .arc((p[0]-ux*radius,p[1]-uz*radius),(p[0]+nx,p[1]+nz)))
    return contour.prism(y,depth)


def _shoulder(right=True):
    xo,xi=math.sqrt(36**2-5**2),math.sqrt(33**2-5**2)
    outline=(profiles._Contour((xo,5)).arc((0,36),(-xo,5)).line((-xi,5))
             .arc((0,33),(xi,5)).line((xo,5)))
    shell=outline.prism(78.2,51.8)
    inner=cyl(33,54,(0,77,0),(0,1,0))
    pieces=[shell]
    for sign in (-1,1):
        pieces.append(_beam_xz((28*sign,25),(45*sign,35),7,86,3))
        pieces.append(cyl(8.5,3,(45*sign,86,35),(0,1,0)))
    shape=fuse(pieces)
    shape=cut(shape,[inner])
    shape=cut(shape,[cyl(1.7,4,(x,85.5,z),(0,1,0)) for x,z in SHOULDER_FASTENERS])
    for y in (96,110,123):shape=cut(shape,[box(-16,y-2,29,32,4,12)])
    return shape if right else core.mirror(shape,(0,1,0))


def materials():
    return {name:('CNC' if name in ('chassis_belly_plate','chassis_hip_frame_right','chassis_hip_frame_left',
                                   'chassis_front_crossframe','chassis_rear_crossframe') else 'PETG')
            for name in ('chassis_belly_plate','chassis_hip_frame_right','chassis_hip_frame_left',
                         'chassis_front_crossframe','chassis_rear_crossframe',
                         'chassis_front_shell','chassis_rear_cover','shoulder_fairing_right','shoulder_fairing_left',
                         'battery_tray','electronics_tray','Jetson_base_retainer_right','Jetson_base_retainer_left')}


def build_chassis(lightweight=True):
    front,rear=_shell_pair()
    parts={'chassis_belly_plate':_bottom(lightweight),
           'chassis_hip_frame_right':_side(True,lightweight),'chassis_hip_frame_left':_side(False,lightweight),
           'chassis_front_crossframe':_crossframe(True,lightweight),'chassis_rear_crossframe':_crossframe(False,lightweight),
           'chassis_front_shell':front,'chassis_rear_cover':rear,
           'shoulder_fairing_right':_shoulder(True),'shoulder_fairing_left':_shoulder(False),
           'battery_tray':core.prior._battery_tray(),'electronics_tray':_tray()}
    parts.update(jetson_mount.designs())
    for name,shape in parts.items():
        try:core._check(name,shape)
        except Exception as exc:raise ValueError(f'{name}: {exc}') from exc
    return parts


def chassis_hardware():
    items=list(jetson_mount.hardware())
    for side in (-1,1):
        for i,(x,z) in enumerate(SHOULDER_FASTENERS):
            screw=fuse([cyl(1.5,14,(x,75*side,z),(0,side,0)),
                        cyl(2.75,3,(x,89*side,z),(0,side,0))])
            items.append((f'shoulder_{side}_M3x20_{i}',screw,'fixed'))
    for i,(y,z) in enumerate(SHELL_FASTENERS):
        front=fuse([cyl(1.5,14,(86,y,z),(1,0,0)),cyl(2.75,3,(100,y,z),(1,0,0))])
        rear=fuse([cyl(1.5,24,(-110,y,z),(1,0,0)),cyl(2.75,3,(-113,y,z),(1,0,0))])
        items.extend(((f'front_shell_M3x20_{i}',front,'fixed'),(f'rear_cover_M3x30_{i}',rear,'fixed')))
    return items


def fastener_specification():
    return [
        dict(location='belly plate to CNC side ledges',quantity=8,spec='DIN7991 M3x8',grip=3,engagement=5,access='underside; unmodeled'),
        dict(location='side frames to front/rear crossframe rails',quantity=8,spec='DIN7991 M3x8',grip=3,engagement=5,access='outside before shells; unmodeled'),
        dict(location='battery tray to belly posts',quantity=4,spec='M3x8 socket',grip=3,engagement=5,access='rear opening; unmodeled'),
        dict(location='electronics tray to side-frame shelves',quantity=4,spec='M3x8 socket',grip=3,engagement=5,access='rear opening; unmodeled',centres_xy=TRAY_FASTENERS),
        dict(location='continuous front shell to front crossframe',quantity=4,spec='M3x20 socket',grip=14,engagement=6,access='front outside; modeled'),
        dict(location='large rear cover to rear crossframe',quantity=4,spec='M3x30 socket',grip=24,engagement=6,access='rear outside; modeled'),
        dict(location='shoulder covers through main shell into side-frame bosses',quantity=4,spec='M3x20 socket',grip=14,engagement=6,access='lateral outside; modeled',metal_face_y_abs=75,body_face_y_abs=86,head_seat_y_abs=89),
        dict(location='Jetson original-base peripheral retainers',quantity=4,spec='M3x10 + washer0.5 + M3 nut2.4',grip=6,engagement=2.4,access='rear opening and under tray; modeled',source='jetson_mount_specification.json'),
    ]


def export_review(folder):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    parts=build_chassis();hardware=chassis_hardware()
    report=dict(units='mm',architecture='Full-height continuous curved front shell and rear cover; vertical split X-20; no stacked electronics enclosure',
        parts={},collisions=[],hardware_collisions=[],fasteners=fastener_specification(),
        camera=dict(front_x=100,centre_z=19,window_y=[-45.3,45.3],window_z=[6.2,31.8]),
        electronics=dict(tray_x=[-86,66],tray_y=[-54,54],tray_z=[30,33],actual_Jetson_top=67.766,
                         tray_support_centres=TRAY_FASTENERS),
        shoulder=dict(y_arc_range=[78.2,130],inner_radius=33,outer_radius=36,body_mount_y=86),
        qualification='Geometry and packaging only; impact, fatigue, thermal and print fit require physical validation')
    for n,s in parts.items():
        s.tessellate(.1);bb=s.BoundBox
        report['parts'][n]=dict(valid=s.isValid(),solids=len(s.Solids),volume_mm3=s.Volume,
                               bbox=[bb.XMin,bb.YMin,bb.ZMin,bb.XMax,bb.YMax,bb.ZMax])
    named=list(parts.items())
    for i,(an,a) in enumerate(named):
        for bn,b in named[i+1:]:
            if not a.BoundBox.intersect(b.BoundBox):continue
            volume=a.common(b).Volume
            if volume>.001:report['collisions'].append(dict(a=an,b=bn,volume=volume))
    for hn,h,_ in hardware:
        for pn,p in named:
            if not h.BoundBox.intersect(p.BoundBox):continue
            volume=h.common(p).Volume
            if volume>.001:report['hardware_collisions'].append(dict(hardware=hn,part=pn,volume=volume))
    (folder/'chassis_review.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__=='__main__':
    out=Path(__file__).resolve().parents[1]/'mechanical/v6'
    result=export_review(out)
    print(json.dumps({k:result[k] for k in ('collisions','hardware_collisions')},indent=2))
