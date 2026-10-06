"""V6 two-part enclosing OB shell, CNC crank and nested bearing joints.

The motor flange is D57. The OA passes through the inner motor seat, while
an integral deep-pocket outer OB surrounds the inner frame and locates the
OA nose in a clearance bore. A sector side mouth admits the moving crank.
This is a geometry review, not a verified structural or jumping rating.
"""
from __future__ import annotations
import json
import math

import build_printable_robot as cad
import cad_v3_profiles as profiles
from build_reference_robot import profile_fillet, ring

App, Part, V = cad.App, cad.Part, cad.V
cyl, box, cut, union, bar = cad.cyl, cad.box, cad.cut, cad.union, cad.bar
L, R, BW = 130.0, 45.0, 105.0
POSTS = ((-10.5,-55), (10.5,-55), (-10.5,-82), (10.5,-82))
CAP_HOLES = tuple(cad.points(12, 3, 0))


def S():
    return float(cad.P['knee_stator_face_y'])


def Y(offset):
    return S()+offset


def configure():
    s=S()
    return dict(carrier_y=[s,s+4], outer_OB_y=[s+.2,s+23],
                fork_inner_y=[s+4.5,s+7.5], fork_outer_y=[s+16.5,s+19.5],
                A_fork_inner_y=[s+4.5,s+7.5], A_fork_outer_y=[s+16.5,s+19.5],
                driven_links_y=[s+8,s+16], coupler_link_y=[s+8,s+16],
                hub_stator_face_y=s+16, wheel_center_y=s+42, wheel_track=2*(s+42),
                bearing='NSK626ZZ1 single per A/B/C, mechanically retained; not load rated',
                bearing_bore=19.0,bearing_seat_fit='19H7; match purchased bearing',
                bearing_web_bore=16.8,bushing_bore=8.0,cnc_bushing_bore=8.0,
                leg_structure_width=23,OA_material='6061-T6 CNC one-piece fork',
                oa_register_diameter=35.05,joint_bushing_length=2.5,
                inner_race_spacer_outer_diameter=8.4,
                shaft='D6 steel female M2 both ends, L14.05, two low-head retainers',
                joint_support='OB deep-pocket outer shell encloses inner frame; A/C forks and B inward supports',
                axis_retainer='NBK SETS-M2-4, D4 head x0.5; OD9 t0.2 steel washers',
                bearing_retainer='OD28 ID16.8 t0.8 steel cover, 3 M2 at PCD24',
                ob_motor_head_diameter=57,oa_nose_diameter=35,
                ob_nose_clearance_diameter=35.4,ob_seat_step_diameter=50,
                ob_shell_pocket_depth=19.8,
                oa_stop_track_radius=23,oa_stop_slot_width=4.6,oa_stop_track_xz_degrees=[135,221.5],
                oa_stop_track_motor_relative_degrees=[-135,-48.5],
                oa_stop_pin_shoulder_diameter=4,oa_stop_pin_head_diameter=7,
                oa_stop_pin_outer_offset=24.7,
                oa_stop_scope='Assembly limit only; impact strength and controller limits must be validated')


def _ob_contour(inner=False):
    radius=28.5
    q=radius/math.sqrt(2)
    width=14.8 if inner else 18.5
    foot=15.5 if inner else 18.0
    return (profiles._Contour((q,-q)).arc((0,radius),(-q,-q))
            .bezier((-16,-25),(-width,-38),(-width,-50))
            .bezier((-width,-75),(-foot,-109),(-foot,-L))
            .arc((0,-L-foot),(foot,-L))
            .bezier((foot,-109),(width,-75),(width,-50))
            .bezier((width,-38),(16,-25),(q,-q)))


def _lightening(y,thickness):
    polygons=(((-7,-39),(7,-39),(-7,-48)),
              ((7,-64),(7,-78),(-7,-78)),
              ((-7,-103),(7,-103),(-7,-114)))
    return [profiles._rounded_polygon(p,2).prism(y,thickness) for p in polygons]


def _axis_bore(shape,z,inner=False,outer=False):
    shape=cut(shape,cyl(4,Y(-1),25,z=z))
    if inner: shape=cut(shape,cyl(4.6,Y(-1),6,z=z))
    if outer: shape=cut(shape,cyl(4.6,Y(19),5,z=z))
    return shape


def ob_inner():
    # D57 flange plus a narrow lower frame. The D50 front step nests inside
    # the outer shell; bolt access notches interrupt the register locally.
    shape=union(_ob_contour(True).prism(Y(0),3),cyl(28.5,Y(0),4),
                cyl(25,Y(3.9),2.1),cyl(8.5,Y(2.9),4.6,z=-L))
    shape=cut(shape,cyl(20.2,Y(-1),8),cyl(22.2,Y(4.1),2.1),
              box(-30,Y(4.1),-30,30,2.1,60),*_lightening(Y(-1),9))
    shape=_axis_bore(shape,-L,inner=True)
    shape=cad.bolt_pattern(shape,25,6,30,Y(-1),8)
    for x,z in cad.points(25,6,30):
        shape=cut(shape,cyl(2.4,Y(2),5,x,z))
        # Break the 0.4 mm residual lip into intentional, machinable register
        # segments. Only the front lip is relieved; the 4 mm flange stays.
        relief=union(cyl(2.4,Y(4),2.2,x=25),cyl(2.4,Y(4),2.2,x=21.3),
                     box(21.3,Y(4),-2.4,3.7,2.2,4.8))
        relief.rotate(V(0,0,0),cad.YAXIS,-math.degrees(math.atan2(z,x)))
        shape=cut(shape,relief)
    # Four flush screws enter from the motor side, outside the motor envelope.
    # The receiving bosses are integral with the outer shell skirt.
    for x,z in POSTS:
        shape=cut(shape,cyl(1.7,Y(-1),5,x,z),
                  Part.makeCone(3.2,1.7,1.5,V(x,Y(0),z),cad.YAXIS))
    return shape


def _oa_side_mouth(y,thickness):
    # Open the left-hand shell sector throughout the crank travel. The front
    # face remains a continuous ring around the guide bore.
    return box(-45,y,-34,45,thickness,70)


def _angular_slot(y,thickness):
    def polar(radius,degrees):
        angle=math.radians(degrees)
        return radius*math.cos(angle),radius*math.sin(angle)
    start,mid,end=135.,178.25,221.5
    c=(profiles._Contour(polar(25.3,start))
       .arc(polar(25.3,mid),polar(25.3,end))
       .line(polar(20.7,end))
       .arc(polar(20.7,mid),polar(20.7,start))
       .line(polar(25.3,start)))
    caps=[cyl(2.3,y,thickness,*polar(23,angle)) for angle in (start,end)]
    return union(c.prism(y,thickness),*caps)


def ob_outer():
    outer=_ob_contour(False).prism(Y(.2),22.8)
    # The lower pocket follows the narrow inner frame, producing real side
    # walls along its edges instead of four disconnected distance posts.
    pocket=_ob_contour(True).prism(Y(-1),21)
    # Offset the pocket linearly in X to provide nominal 0.25 mm side play.
    p2=pocket.copy();p2.translate(V(.25,0,0))
    p3=pocket.copy();p3.translate(V(-.25,0,0))
    shape=cut(outer,union(pocket,p2,p3))
    # At O the rear mouth clears D57 until +4.2; then it surrounds the D50
    # inner register with D50.2 and leaves a D57 wall up to the front face.
    shape=union(shape,ring(28.5,25.1,Y(4.2),15.9,0))
    shape=cut(shape,cyl(28.75,Y(-1),5.2),_oa_side_mouth(Y(4.1),15.9))
    # The CW must leave the B support on both sides. Keep only the central
    # front cheek around the bearing axis; the side skirt ends above B.
    shape=cut(shape,box(-40,Y(-1),-170,80,21,82))
    # Integral receiving bosses join each side wall and the front skin.
    shape=union(shape,*(cyl(6,Y(3.0),17.1,x,z) for x,z in POSTS),
                cyl(8.5,Y(16.5),3.6,z=-L))
    # Nose limit/guide: radial 0.2 mm and shoulder axial 0.4 mm clearances.
    shape=cut(shape,cyl(19,Y(19.9),1.1),cyl(17.7,Y(20.9),3.1),
              *_lightening(Y(19.9),4),_angular_slot(Y(19.9),4))
    shape=_axis_bore(shape,-L,outer=True)
    for x,z in POSTS: shape=cut(shape,cyl(1.25,Y(2.9),8.2,x,z))
    return shape


def _crank_ear(y,thickness):
    return profile_fillet(union(cyl(22,y,thickness),bar(0,-R,9,y,thickness),
                                 cyl(13,y,thickness,z=-R)),3)


def oa_fork():
    shape=union(_crank_ear(Y(4.5),3),_crank_ear(Y(16.5),3),
                cyl(18.5,Y(4.4),16.2),cyl(19.5,Y(.2),4.4),
                cyl(17.5,Y(20.5),2.5))
    shape=cut(shape,cyl(17.525,Y(-1),2),cyl(6,Y(-1),25))
    shape=_axis_bore(shape,-R,inner=True,outer=True)
    shape=cad.bolt_pattern(shape,13.5,6,0,Y(0),25)
    for x,z in cad.points(13.5,6,0): shape=cut(shape,cyl(2.9,Y(13),12,x,z))
    shape=cut(shape,cyl(1.25,Y(16.4),3.2,z=-23))
    return shape


def bearing_seat(shape,z):
    # Shoulder contacts only the outer race. The removable cover is modeled
    # separately, in the recessed upper face; its heads remain inside the fork.
    shape=cut(shape,cyl(8.4,Y(7.9),8.4,z=z),
              cyl(cad.P['bearing_bore']/2,Y(8.75),6.1,z=z),
              cyl(14.1,Y(14.8),1.4,z=z))
    for x,dz in CAP_HOLES:
        shape=cut(shape,cyl(.8,Y(11),3.9,x,z+dz))
    return shape


def ac_link():
    radius=15.5
    h=(radius**2-8**2)**.5
    drop=1.5*8/h
    c=profiles._Contour((8,-h))
    c.arc((0,radius),(-8,-h))
    c.bezier((-6.5,-h-drop),(-7,-23),(-7,-32))
    c.bezier((-7,-48),(-6.2,-57),(-6.2,-65))
    c.bezier((-6.2,-73),(-7,-82),(-7,-98))
    c.bezier((-7,-107),(-6.5,-L+h+drop),(-8,-L+h))
    c.arc((0,-L-radius),(8,-L+h))
    c.bezier((6.5,-L+h+drop),(7,-107),(7,-98))
    c.bezier((7,-82),(6.2,-73),(6.2,-65))
    c.bezier((6.2,-57),(7,-48),(7,-32))
    c.bezier((7,-23),(6.5,-h-drop),(8,-h))
    shape=c.prism(Y(8),8)
    for z in (0,-L):shape=bearing_seat(shape,z)
    return shape


def _cb_ear(y,thickness):
    shape=profile_fillet(union(bar(0,R,9,y,thickness),cyl(13,y,thickness,z=R),
                              cyl(17,y,thickness)),3)
    return cut(shape,cyl(9.5,y-1,thickness+2),cyl(4,y-1,thickness+2,z=R))


def _cw_lower(y,thickness):
    c=(profiles._Contour((17,0))
       .bezier((17,-26),(16,-52),(18,-77))
       .bezier((19,-91),(22,-92),(22,-BW))
       .arc((0,-BW-22),(-22,-BW))
       .bezier((-22,-92),(-15,-89),(-15,-77))
       .bezier((-15,-52),(-17,-26),(-17,0))
       .arc((0,17),(17,0)))
    shape=c.prism(y,thickness)
    for p in (((-7,-26),(7,-26),(-7,-40)),
              ((7,-42),(7,-59),(-7,-59)),
              ((-6,-66),(8,-66),(-6,-80))):
        shape=cut(shape,profiles._rounded_polygon(p,2).prism(y-1,thickness+2))
    return shape


def cw_fork():
    shape=union(_cw_lower(Y(8),8),_cb_ear(Y(4.5),3),_cb_ear(Y(16.5),3),
                ring(17,9.5,Y(7.4),9.2,0))
    shape=_axis_bore(shape,R,inner=True,outer=True)
    shape=bearing_seat(shape,0)
    for x,dz in cad.points(8.75,3,90):
        shape=cut(shape,cyl(1.7,Y(7),10,x,dz-BW),cyl(2.9,Y(7.9),3.1,x,dz-BW))
    return shape


def designs():
    return {'OB_inner_carrier':(ob_inner(),'hip','CNC'),
            'OB_outer_shell':(ob_outer(),'hip','CNC'),
            'OA_one_piece':(oa_fork(),'oa','CNC'),
            'AC_bearing_link':(ac_link(),'ac','CNC'),
            'CW_one_piece':(cw_fork(),'output','CNC')}


def keeper(z=0, y=None):
    if y is None:y=Y(14.8)
    shape=ring(14,8.4,y,.8,z)
    for x,dz in CAP_HOLES:shape=cut(shape,cyl(1.1,y-.1,1,x,z+dz))
    return shape


def female_pin(y=None,z=0):
    if y is None:y=Y(5)
    return cut(cyl(3,y,14.05,z=z),cyl(.8,y-.1,4.3,z=z),
               cyl(.8,y+9.75,4.4,z=z))


def angular_stop_pin(y=None,z=-23,include_thread=False):
    if y is None: y=Y(19.5)
    shape=union(cyl(2,y,4.2,z=z),cyl(3.5,y+4.2,1,z=z))
    if include_thread: shape=union(shape,cyl(1.5,y-3,3,z=z))
    # A 0.8-wide screwdriver slot, 0.5 deep, leaves a 0.5 mm head floor.
    return cut(shape,box(-4,y+4.7,z-.4,8,.6,.8))


def hardware():
    items=[]
    for name,holder,z,bearing_role,bearing_z in (
        ('A','oa',-R,'ac',0),('C','output',R,'ac',-L),('B','hip',-L,'output',0)):
        items.append((f'626_{name}',ring(9.5,3,Y(8.75),6,bearing_z),bearing_role))
        items.append((f'bearing_keeper_{name}',keeper(bearing_z),bearing_role))
        for i,(x,dz) in enumerate(CAP_HOLES):
            # Omit engaged M2 thread inside its modeled tapped hole.
            screw=union(cyl(1,Y(14.8),.8,x,bearing_z+dz),
                        cyl(2,Y(15.6),.5,x,bearing_z+dz))
            items.append((f'keeper_{name}_SETS_M2x4_{i}',screw,bearing_role))
        items.append((f'female_pin_{name}',female_pin(z=z),holder))
        for suffix,y in (('inner',5),('outer',16.5)):
            items.append((f'bronze_sleeve_{name}_{suffix}',ring(4,3.025,Y(y),2.5,z),holder))
        for suffix,y,thickness in (('inner',7.5,1.25),('outer',14.75,1.70)):
            items.append((f'race_spacer_{name}_{suffix}',ring(4.2,3.1,Y(y),thickness,z),holder))
        items.append((f'axis_washer_{name}_inner',ring(4.5,1.1,Y(4.8),.2,z),holder))
        items.append((f'axis_washer_{name}_outer',ring(4.5,1.1,Y(19.05),.2,z),holder))
        inner=union(cyl(2,Y(4.3),.5,z=z),cyl(1,Y(4.8),.2,z=z))
        outer=union(cyl(1,Y(19.05),.2,z=z),cyl(2,Y(19.25),.5,z=z))
        items.extend(((f'axis_{name}_SETS_M2x4_inner',inner,holder),
                      (f'axis_{name}_SETS_M2x4_outer',outer,holder)))
    items.append(('OA_angular_stop_shoulder_M3',
                  angular_stop_pin(),'oa'))
    for i,(x,z) in enumerate(POSTS):
        screw=union(Part.makeCone(3,1.5,1.5,V(x,Y(0),z),cad.YAXIS),
                    cyl(1.5,Y(1.5),1.5,x,z))
        items.append((f'OB_shell_DIN7991_M3x10_{i}',screw,'hip'))
    for i,(x,z) in enumerate(cad.points(25,6,30)):
        screw=union(cyl(1.5,Y(0),2,x,z),cyl(2.25,Y(2),2,x,z))
        items.append((f'OB_stator_SLH_M3x6_{i}',screw,'hip'))
    for i,(x,z) in enumerate(cad.points(13.5,6,0)):
        screw=union(cyl(1.5,Y(1),12,x,z),cyl(2.75,Y(13),3,x,z))
        items.append((f'OA_rotor_M3x16_{i}',screw,'oa'))
    for i,(x,dz) in enumerate(cad.points(8.75,3,90)):
        screw=union(cyl(1.5,Y(11),5,x,dz-BW),cyl(2.75,Y(8),3,x,dz-BW))
        items.append((f'H6215_stator_M3x8_{i}',screw,'output'))
    return items


def export_hardware():
    folder=cad.OUT/'metal_hardware';folder.mkdir(parents=True,exist_ok=True)
    specs=[]
    def save(name,shape,qty,material,**kwargs):
        shape.check(True);shape.exportStep(str(folder/(name+'.step')))
        specs.append(dict(part=name,quantity=qty,material=material,**kwargs))
    save('OA_angular_stop_M3_D4',angular_stop_pin(0,0,True),2,'steel',
         thread='M3x3 into OA, material grade and impact capacity to verify',
         shoulder_diameter=4,shoulder_length=4.2,head_diameter=7,head_height=1,
         drive='Slotted, width 0.8 mm, depth 0.5 mm, 0.5 mm head floor; blade <=0.8 mm',
         assembly='Install after outer shell; nominal 0.7 mm under-head gap to shell face',
         caution='Not rated for powered hard-stop or landing impacts')
    save('female_pin_D6_L14_05',female_pin(0),6,'steel',length=14.05,
         outer_diameter=6,end_threads='M2 each end: >=4.0 mm full tap depth; 3.8 mm screw engagement',
         axial_end_clearance_nominal=.05)
    save('bearing_keeper_D28_D16_8_t0_8',keeper(0,0),6,'stainless steel',
         outer_diameter=28,inner_diameter=16.8,thickness=.8,holes='3 D2.2 PCD24')
    for name,outer,inner,length,qty,material in (
        ('bronze_bush_D8_d6_05_L2_5',8,6.05,2.5,12,'bearing bronze'),
        ('race_spacer_D8_4_d6_2_L1_25',8.4,6.2,1.25,6,'steel'),
        ('race_spacer_D8_4_d6_2_L1_70',8.4,6.2,1.70,6,'steel'),
        ('axis_washer_D9_d2_2_t0_2',9,2.2,.2,12,'steel shim')):
        save(name,ring(outer/2,inner/2,0,length,0),qty,material,
             outer_diameter=outer,inner_diameter=inner,length=length)
    (folder/'specification.json').write_text(json.dumps(specs,indent=2)+'\n')


def local_review():
    parts=designs();hw=hardware()
    result=dict(structural_width_mm=23,reference_plane=S(),parameters=configure(),
                parts={},collisions=[],minimum_clearances={},
                sampled_lengths_mm=[100,180,215],
                scope='Leg-only bodies and modeled leg hardware; no strength rating')
    for name,(shape,role,material) in parts.items():
        shape.check(True)
        result['parts'][name]=dict(valid=shape.isValid(),solids=len(shape.Solids),
                                  volume_mm3=shape.Volume,y_range=[shape.BoundBox.YMin,shape.BoundBox.YMax])
    for length in result['sampled_lengths_mm']:
        st=cad.pose(length)
        placed=[(n,cad.transform(shape,role,st)) for n,(shape,role,_) in parts.items()]
        for i,(a,sa) in enumerate(placed):
            for b,sb in placed[i+1:]:
                d=sa.distToShape(sb)[0];key=a+'/'+b
                result['minimum_clearances'][key]=min(d,result['minimum_clearances'].get(key,1e9))
                if d<1e-6:
                    v=sa.common(sb).Volume
                    if v>.05:result['collisions'].append(dict(length=length,a=a,b=b,mm3=v))
        if length in (100,180,215):
            for a,shape,role in hw:
                sa=cad.transform(shape,role,st);bb=sa.BoundBox
                for b,sb in placed:
                    bc=sb.BoundBox
                    if any(getattr(bb,k+'Max')<=getattr(bc,k+'Min')+1e-7 or
                           getattr(bc,k+'Max')<=getattr(bb,k+'Min')+1e-7 for k in 'XYZ'):continue
                    v=sa.common(sb).Volume
                    if v>.05:result['collisions'].append(dict(length=length,a=a,b=b,mm3=v))
    (cad.OUT/'leg_layout_review.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    cad.configure(cad.ROOT/'mechanical/v6');cad.P.update(configure())
    print(json.dumps(local_review(),indent=2))
