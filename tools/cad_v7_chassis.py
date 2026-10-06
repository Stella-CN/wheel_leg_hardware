"""V7 faceted full-height chassis for an embedded 7-inch display and D435.

All dimensions are mm. The five-piece metal load frame and payload tray datums
are inherited from V6. The two printed enclosure halves use ruled armour faces,
a tapered belly, a raked roof and a vertical service split. No upper compartment
is added. Display and IMU assemblies are supplied by separate V7 modules.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import cad_v6_chassis as prior

core, App, Part, V = prior.core, prior.App, prior.Part, prior.V
box, cyl, fuse, cut = prior.box, prior.cyl, prior.fuse, prior.cut
hip_stator_mount, hip_hardware = prior.hip_stator_mount, prior.hip_hardware
BOTTOM_FASTENERS, TRAY_FASTENERS = prior.BOTTOM_FASTENERS, prior.TRAY_FASTENERS
SHELL_FASTENERS, SHOULDER_FASTENERS = prior.SHELL_FASTENERS, prior.SHOULDER_FASTENERS
SPLIT_X = -20.
SCREEN_PADS = tuple((y,z) for y in (-89.,89.) for z in (-38.,8.,54.))
CAMERA_PADS = tuple((y,z) for y in (-50.,50.) for z in (80.5,96.5))
IMU_BRIDGE_HOLES = tuple((x,y) for x in (-10.,10.) for y in (-68.,68.))
SIDE_WINDOWS = {
    'front': ((-10.,58.),(24.,58.),(35.,68.),(35.,80.),(22.,91.),(-10.,91.)),
    'rear': ((-81.,61.),(-71.,53.),(-39.,53.),(-34.,58.),(-34.,86.),
             (-44.,96.),(-75.,96.),(-81.,88.)),
}
# Each outline has matching vertices; true ruled surfaces preserve crisp faces.
# z, front X, rear X, front Y half width, cheek half width, shoulder half width.
PROFILE = ((-55.,110.,-104.,87.,94.,80.),
           (-53.,122.,-110.,96.,104.,86.),
           (68.,122.,-110.,96.,104.,86.),
           (102.,122.,-104.,66.,79.,75.),
           (114.,91.,-89.,61.,70.,68.))


def _outline(section):
    z,front,rear,face,cheek,shoulder = section
    # The hip station is narrower than the screen cheeks, while the rear
    # tapers in plan. The lower/upper section changes form the chin and brow.
    positive = [(front,face),(front-12,cheek),(72 if z<103 else 68,cheek-4),
                (48,shoulder),(-56,shoulder-4),(rear+16,shoulder-8),
                (rear,shoulder-25)]
    return positive + [(x,-y) for x,y in reversed(positive)]


def _inset_polygon(points, distance):
    """Constant normal offset of straight edges; avoids thin diagonal walls."""
    area=sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(points,points[1:]+points[:1]))
    orient=1 if area>0 else -1
    shifted=[]
    for a,b in zip(points,points[1:]+points[:1]):
        dx,dy=b[0]-a[0],b[1]-a[1];length=(dx*dx+dy*dy)**.5
        nx,ny=-orient*dy/length*distance,orient*dx/length*distance
        shifted.append(((a[0]+nx,a[1]+ny),(dx,dy)))
    output=[]
    for i in range(len(points)):
        p,u=shifted[i-1];q,v=shifted[i]
        cross=u[0]*v[1]-u[1]*v[0]
        if abs(cross)<1e-9:output.append(q);continue
        t=((q[0]-p[0])*v[1]-(q[1]-p[1])*v[0])/cross
        output.append((p[0]+t*u[0],p[1]+t*u[1]))
    return output


def _loft(inset=0., bottom=None, top=None):
    wires=[]
    for i,section in enumerate(PROFILE):
        z=section[0]
        if inset and i==len(PROFILE)-2:z-=inset
        if i==0 and bottom is not None:z=bottom
        if i==len(PROFILE)-1 and top is not None:z=top
        pts=_outline(section)
        if inset:pts=_inset_polygon(pts,inset)
        vectors=[V(x,y,z) for x,y in pts]
        wires.append(Part.makePolygon(vectors+[vectors[0]]))
    return Part.makeLoft(wires,True,True)


def _side(right=True,lightweight=True):
    shape=prior._side(right,lightweight)
    sign=1 if right else -1
    return cut(shape,[core.tap_drill((x,68*sign,47),(0,0,-1),6)
                      for x in (-10,10)])


def _bezel_blank(x=119,depth=3,clearance=0):
    y,z0,z1=94+clearance,-51-clearance,67+clearance
    pts=[(-y+8,z0),(y-8,z0),(y,z0+8),(y,z1-8),
         (y-8,z1),(-y+8,z1),(-y,z1-8),(-y,z0+8)]
    vertices=[V(x,a,b) for a,b in pts]
    return Part.Face(Part.makePolygon(vertices+[vertices[0]])).extrude(V(depth,0,0))


def _bezel():
    shape=cut(_bezel_blank(),[core.rounded_pocket_yz(-78.5,78.5,-36.5,52.5,118.8,3.4,1)])
    return cut(shape,[cyl(1.7,3.4,(118.8,y,z),(1,0,0)) for y,z in SCREEN_PADS])


def _body_cutters():
    tools=[]
    for side in (-1,1):
        tools.append(cyl(36.2,55,(0,60*side,0),(0,side,0)))
        crown=[(36.3,4.5),(36.3,17.5),(24.4,35.5),(0,40.6),
               (-24.4,35.5),(-36.3,17.5),(-36.3,4.5)]
        vectors=[V(x,60*side,z) for x,z in crown]
        tools.append(Part.Face(Part.makePolygon(vectors+[vectors[0]])).extrude(V(0,55*side,0)))
        relief=core.rounded_pocket_xz(-39.5,39.5,-39.5,39.5,74.9,3.6,1)
        tools.append(relief if side>0 else core.mirror(relief,(0,1,0)))
        for x,z in SHOULDER_FASTENERS:
            tools.append(cyl(1.7,25,(x,74.9*side,z),(0,side,0)))
            # Recess leaves a precise Y86 seating plane for the existing
            # shoulder fastener chain even where the faceted cheek widens.
            tools.append(cyl(9,30,(x,86*side,z),(0,side,0)))
    # Detachable front bezel exposes the active screen area. The main shell
    # opening passes the full 165 x 110 device, with 0.5 mm per side clearance.
    tools.append(core.rounded_pocket_yz(-83,83,-47.5,63.5,98.5,20.6,.4))
    tools.append(_bezel_blank(119,3.4,.2))
    # Screen and camera mounting pads retain full contact and through holes.
    for y,z in SCREEN_PADS:tools.append(cyl(1.7,6.4,(115.8,y,z),(1,0,0)))
    # Rear adjustable screen washer plates slide +/-2 mm. Locally pocket the
    # internal mounting webs, preserving X86..92.7 (6.7 mm) of each web.
    for y in (-75.31885,75.31885):
        for z in (8-46.69225,8+46.69225):
            tools.append(box(92.7,y-9.2,z-9.2,1.4,18.4,18.4))
    tools.append(core.rounded_pocket_yz(-45.3,45.3,75.2,100.8,118.8,5,.3))
    # Hidden rear relief keeps the camera body clear of the thicker raked brow.
    tools.append(box(96.5,-45.6,74.95,22.5,91.2,26.1))
    for y,z in CAMERA_PADS:
        tools.append(cyl(1.7,3.4,(118.8,y,z),(1,0,0)))
        tools.append(box(108,y-4.2,z-4.2,11,8.4,8.4))
    # Roof louvres are isolated slots, with a solid central IMU service spine.
    for x in (-66,-54,-42,42,54,66):
        for side in (-1,1):
            tools.append(box(x-2,-49 if side<0 else 22,100,4,27,20))
    # Faceted openings expose the real metal/electronics core rather than a
    # decorative painted pocket. Only the non-load-bearing PETG wall is cut.
    for side in (-1,1):
        for outline in SIDE_WINDOWS.values():
            vertices=[V(x,70*side,z) for x,z in outline]
            tools.append(Part.Face(Part.makePolygon(vertices+[vertices[0]])).extrude(V(0,42*side,0)))
    # Rear ventilation avoids the lower electronics and frame fastening pads.
    for z in (61,70,79,88):
        tools.append(core.rounded_pocket_yz(-49,49,z-2,z+2,-116,24,1.8))
    return tools


def _shell_pair():
    outer=_loft();inner=_loft(3,bottom=-56,top=110)
    shell=cut(outer,[inner])
    # The existing metal belly is reached by an integral lower perimeter lip.
    # The metal plate is Z-50..-47; lip ends at -50 to avoid interference.
    lip=outer.common(box(-120,-115,-55,250,230,5))
    aperture=core.prior._rounded_prism(170,140,7,-56,6)
    shell=fuse([shell,cut(lip,[aperture])])
    additions=[]
    for side in (-1,1):
        for x,z in SHOULDER_FASTENERS:
            additions.append(cyl(8,11,(x,75*side,z),(0,side,0)))
    # Four internal bolts are tightened through the empty screen aperture
    # before mounting the screen. Their heads end at X97, behind screen X99.
    for y,z in SHELL_FASTENERS:
        additions.append(cyl(5,8,(86,y,z),(1,0,0)))
        web=box(86,57 if y>0 else -108,z-5,8,51,10)
        additions.append(web.common(outer))
        additions.append(cyl(5,24,(-110,y,z),(1,0,0)))
    for y,z in SCREEN_PADS:additions.append(cyl(6,6,(116,y,z),(1,0,0)))
    for y,z in CAMERA_PADS:additions.append(cyl(4.5,3,(119,y,z),(1,0,0)))
    shell=fuse([shell]+additions)
    cutters=_body_cutters()
    for y,z in SHELL_FASTENERS:
        cutters.extend((cyl(1.7,8.4,(85.8,y,z),(1,0,0)),
                        cyl(1.7,25,(-110.5,y,z),(1,0,0))))
    for x,y in BOTTOM_FASTENERS:cutters.append(cyl(4,6,(x,y,-55.5)))
    shell=cut(shell,cutters)
    front=shell.common(box(SPLIT_X,-120,-60,155,240,180)).removeSplitter()
    rear=shell.common(box(-125,-120,-60,105,240,180)).removeSplitter()
    # Tongue built directly against the faceted inner wall at the vertical seam.
    guide=cut(_loft(2.8,bottom=-54.8,top=110.2),[_loft(5,bottom=-55.1,top=108)])
    guide=guide.common(box(-24,-115,-54.8,4.5,230,170))
    guide=cut(guide,_body_cutters())
    front=fuse([front,guide])
    receiver=_loft(2.5,bottom=-55.2,top=110.5).common(box(-24.3,-115,-55.2,4.4,230,170))
    rear=cut(rear,[receiver])
    return front,rear


def _shoulder(right=True):
    # A four-plane armour crown retains the original R33 motor swept clearance.
    points=[(35.8,5),(35.8,17),(24,35),(0,40),(-24,35),(-35.8,17),(-35.8,5)]
    vectors=[V(x,78.2,z) for x,z in points]
    plate=Part.Face(Part.makePolygon(vectors+[vectors[0]])).extrude(V(0,51.8,0))
    shell=cut(plate,[cyl(33,54,(0,77,0),(0,1,0))])
    pieces=[shell]
    for sign in (-1,1):
        pieces.append(prior._beam_xz((28*sign,25),(45*sign,35),7,86,3))
        pieces.append(cyl(8.5,3,(45*sign,86,35),(0,1,0)))
    shape=cut(fuse(pieces),[cyl(33,54,(0,77,0),(0,1,0))])
    shape=cut(shape,[cyl(1.7,4,(x,85.5,z),(0,1,0)) for x,z in SHOULDER_FASTENERS])
    for y in (97,110,123):shape=cut(shape,[box(-15,y-2,33.5,30,4,9)])
    return shape if right else core.mirror(shape,(0,1,0))


def materials():
    result=prior.materials()
    result['display_front_bezel']='PETG'
    return result


def build_chassis(lightweight=True):
    front,rear=_shell_pair()
    parts={'chassis_belly_plate':prior._bottom(lightweight),
           'chassis_hip_frame_right':_side(True,lightweight),
           'chassis_hip_frame_left':_side(False,lightweight),
           'chassis_front_crossframe':prior._crossframe(True,lightweight),
           'chassis_rear_crossframe':prior._crossframe(False,lightweight),
           'chassis_front_shell':front,'chassis_rear_cover':rear,
           'display_front_bezel':_bezel(),
           'shoulder_fairing_right':_shoulder(True),'shoulder_fairing_left':_shoulder(False),
           'battery_tray':core.prior._battery_tray(),'electronics_tray':prior._tray()}
    parts.update(prior.jetson_mount.designs())
    for name,shape in parts.items():core._check(name,shape)
    return parts


def chassis_hardware():
    items=list(prior.jetson_mount.hardware())
    for side in (-1,1):
        for i,(x,z) in enumerate(SHOULDER_FASTENERS):
            screw=fuse([cyl(1.5,14,(x,75*side,z),(0,side,0)),
                        cyl(2.75,3,(x,89*side,z),(0,side,0))])
            items.append((f'shoulder_{side}_M3x20_{i}',screw,'fixed'))
    for i,(y,z) in enumerate(SHELL_FASTENERS):
        front=fuse([cyl(1.5,8,(86,y,z),(1,0,0)),cyl(2.75,3,(94,y,z),(1,0,0))])
        rear=fuse([cyl(1.5,24,(-110,y,z),(1,0,0)),cyl(2.75,3,(-113,y,z),(1,0,0))])
        items.extend(((f'front_shell_M3x14_{i}',front,'fixed'),(f'rear_cover_M3x30_{i}',rear,'fixed')))
    return items


def fastener_specification():
    specs=prior.fastener_specification()
    for spec in specs:
        if spec['location']=='continuous front shell to front crossframe':
            spec.update(spec='M3x14 socket',grip=8,engagement=6,
                        access='through 166 x 111 screen opening before display installation; screen fastener tool path not qualified; modeled grip and head',
                        head_seat_x=94,head_end_x=97,screen_rear_x=99)
    specs.append(dict(location='IMU bridge feet to upper sideframe beams',quantity=4,
                      spec='M3x8 socket; grip3, engagement5',centres_xy=IMU_BRIDGE_HOLES,
                      tapping_face_z=47,tapping_pilot_diameter=2.5,tapping_depth=6,
                      note='cylindrical tapping pilot plus drill point modeled; bridge owns fasteners'))
    return specs


def export_review(folder):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    parts=build_chassis();hardware=chassis_hardware()
    report=dict(units='mm',source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        architecture='One full-height faceted enclosure, raked roof and tapered belly, vertical X-20 service split',
        parts={},collisions=[],hardware_collisions=[],fasteners=fastener_specification(),
        display=dict(front_panel_x=122,front_glass_x=119,rear_x=99,centre_z=8,
                     body_size_yz=[165,110],bezel_window_yz=[157,89],shell_device_aperture_yz=[166,111],
                     bezel_outer_yz=[188,118],bezel_x=[119,122],pads=SCREEN_PADS,
                     pad_contact_x=116,pad_thickness=3,bezel_thickness=3,hole_diameter=3.4,
                     assembly_limit='Only bare 165 x 110 screen envelope insertion is checked. Carrier/washer/fastener/tool sequence remains conditional on actual mounting lugs.'),
        camera=dict(front_x=122,centre_z=88,window_y=[-45.3,45.3],window_z=[75.2,100.8],
                    pad_contact_x=119,pads=CAMERA_PADS),
        electronics=dict(tray_x=[-86,66],tray_y=[-54,54],tray_z=[30,33],
                         tray_support_centres=TRAY_FASTENERS),
        imu=dict(bridge_holes_xy=IMU_BRIDGE_HOLES,metal_face_z=47,roof_top=114),
        shoulder=dict(y_range=[78.2,130],motor_clearance_radius=33,body_mount_y=86),
        qualification='Local rigid chassis geometry only; full payload/leg motion checks owned by integrated build. No strength, drop or thermal qualification.')
    for name,shape in parts.items():
        bb=shape.BoundBox
        report['parts'][name]=dict(valid=shape.isValid(),solids=len(shape.Solids),volume_mm3=shape.Volume,
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
    sweep=box(99,-82.5,-47,60,165,110)
    insertion_overlap=sweep.common(parts['chassis_front_shell']).Volume
    report['bare_screen_insertion']=dict(
        method='Exact straight prismatic sweep along X, bezel removed',
        screen_rear_x_start=139,screen_rear_x_end=99,overlap_mm3=insertion_overlap,
        pass_geometry=insertion_overlap<.001,
        limit='Bare envelope only; mounted carriers, washers, leads and driver access are not covered.')
    wall_samples=[]
    for part_name,stations in (
            ('chassis_front_shell',((-13,75),(0,55),(0,94),(38,75))),
            ('chassis_rear_cover',((-84,75),(-55,50),(-31,75),(-60,99)))):
        for side in (-1,1):
            for x,z in stations:
                line=Part.makeLine(V(x,65*side,z),V(x,115*side,z))
                lengths=[edge.Length for edge in parts[part_name].common(line).Edges]
                wall_samples.append(dict(part=part_name,x=x,z=z,side=side,
                                         wall_chords_along_y_mm=lengths,
                                         pass_geometry=bool(lengths) and min(lengths)>=2.9))
    report['side_windows']=dict(outlines_xz=SIDE_WINDOWS,
        front_window_to_split_mm=10,rear_window_to_full_thickness_seam_land_mm=9.7,
        sample_method='Exact Y-directed solid chords beside each window; local checks, not a global wall-thickness or strength qualification',
        local_wall_samples=wall_samples,
        all_sampled_wall_chords_at_least_2p9_mm=all(s['pass_geometry'] for s in wall_samples),
        note='Open ventilation/inspection windows; no dust or splash protection claim.')
    (folder/'chassis_review.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__=='__main__':
    out=Path(__file__).resolve().parents[1]/'mechanical/v7'
    result=export_review(out)
    print(json.dumps({k:result[k] for k in ('parts','collisions','hardware_collisions')},indent=2))
