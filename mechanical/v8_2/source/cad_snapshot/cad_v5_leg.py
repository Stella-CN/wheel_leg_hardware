"""V5 enclosed, nested CNC leg: complete OB plates surround a one-piece OA.

All axial coordinates are relative to the knee front stator plane S. A/C use
one-piece forks; each passive pivot retains one NSK626ZZ1 mechanically.
These solids establish geometry, not a jumping load rating.
"""
from __future__ import annotations
import json
import math

import build_printable_robot as cad
import cad_v3_profiles as profiles
import build_nested_robot as prior
from build_reference_robot import profile_fillet, ring

App, Part, V = cad.App, cad.Part, cad.V
cyl, box, cut, union, bar = cad.cyl, cad.box, cad.cut, cad.union, cad.bar
L, R = 130.0, 35.0
POSTS = ((31, 12), (31, -12), (0, -66), (0, -93))
CAP_HOLES = tuple(cad.points(12, 3, 0))


def S():
    return float(cad.P['knee_stator_face_y'])


def Y(offset):
    return S()+offset


def configure():
    s = S()
    return dict(carrier_y=[s, s+3], outer_OB_y=[s+19, s+22],
                fork_inner_y=[s+3.5, s+6.5], fork_outer_y=[s+15.5, s+18.5],
                A_fork_inner_y=[s+3.5, s+6.5], A_fork_outer_y=[s+15.5, s+18.5],
                driven_links_y=[s+7, s+15], coupler_link_y=[s+7, s+15],
                hub_stator_face_y=s+15, wheel_center_y=s+41, wheel_track=2*(s+41),
                bearing='NSK626ZZ1 single per A/B/C, mechanically retained; not load rated',
                bearing_bore=19.0, bearing_seat_fit='19H7; match purchased bearing',
                bearing_web_bore=16.8, bushing_bore=8.0, cnc_bushing_bore=8.0,
                leg_structure_width=22, OA_material='6061-T6 CNC one-piece fork',
                oa_register_diameter=35.05, joint_bushing_length=2.5,
                inner_race_spacer_outer_diameter=8.4,
                shaft='D6 steel female M2 both ends, L14.05, two low-head retainers',
                joint_support='Complete OB plates enclose OA; A/C monolithic forks; B inward supports',
                axis_retainer='NBK SETS-M2-4, D4 head x0.5; OD9 t0.2 steel washers',
                bearing_retainer='OD28 ID16.8 t0.8 steel cover, 3 M2 at PCD24',
                print_register_diameter=35.3)


def _plate_profile(y, thickness):
    # Complete rounded head covers the OA fork's R35+R13 sweep. No V4 sector cut.
    shape = union(profiles.ob_outer_prism(y, thickness), cyl(50.5, y, thickness))
    return cut(shape, *profiles.ob_window_tools(y-1, thickness+2))


def _axis_bore(shape, z, inner=False, outer=False):
    shape = cut(shape, cyl(4, Y(-1), 24, z=z))
    if inner:
        shape = cut(shape, cyl(4.6, Y(-1), 5, z=z))
    if outer:
        shape = cut(shape, cyl(4.6, Y(18), 5, z=z))
    return shape


def ob_inner():
    shape = _plate_profile(Y(0), 3)
    # Integral frame posts replace separate tubes and long through bolts.
    shape = union(shape, *(cyl(4.5, Y(2.9), 16.1, x, z) for x, z in POSTS),
                  cyl(8.5, Y(2.9), 3.6, z=-L))
    shape = cut(shape, cyl(20.2, Y(-1), 5))
    shape = _axis_bore(shape, -L, inner=True)
    shape = cad.bolt_pattern(shape, 25, 6, 30, Y(-1), 5)
    for x, z in cad.points(25, 6, 30):
        shape = cut(shape, Part.makeCone(1.7, 3.2, 1.5, V(x,Y(1.5),z),cad.YAXIS))
    for x, z in POSTS:
        shape = cut(shape, cyl(1.25, Y(13), 6.2, x, z))
    return shape


def ob_outer():
    shape = union(_plate_profile(Y(19), 3), cyl(8.5, Y(15.5), 3.6, z=-L))
    # A small center viewing/tool hole leaves the crank cover complete.
    shape = cut(shape, cyl(6, Y(18), 5))
    shape = _axis_bore(shape, -L, outer=True)
    for x,z in POSTS:
        shape = cut(shape, cyl(1.7,Y(18),5,x,z),
                    Part.makeCone(1.7,3.2,1.5,V(x,Y(20.5),z),cad.YAXIS))
    return shape


def _crank_ear(y, thickness):
    return prior.crank_profile(y, thickness)


def oa_fork():
    shape = union(_crank_ear(Y(3.5),3), _crank_ear(Y(15.5),3),
                  cyl(18.5,Y(3.4),15.2),cyl(19.5,Y(.2),3.4))
    shape = cut(shape, cyl(17.525,Y(-1),2), cyl(6,Y(-1),21))
    shape = _axis_bore(shape,-R,inner=True,outer=True)
    # Deep counterbores accept M3x16: 12 mm external grip, 4 mm motor thread.
    shape = cad.bolt_pattern(shape,13.5,6,0,Y(0),20)
    for x,z in cad.points(13.5,6,0):
        shape=cut(shape,cyl(2.9,Y(13),7,x,z))
    return shape


def bearing_seat(shape,z):
    # Shoulder contacts only the outer race. The removable cover is modeled
    # separately, in the recessed upper face; its heads remain inside the fork.
    shape=cut(shape,cyl(8.4,Y(6.9),8.4,z=z),
              cyl(cad.P['bearing_bore']/2,Y(7.75),6.1,z=z),
              cyl(14.1,Y(13.8),1.4,z=z))
    for x,dz in CAP_HOLES:
        shape=cut(shape,cyl(.8,Y(10),3.9,x,z+dz))
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
    shape=c.prism(Y(7),8)
    for z in (0,-L):shape=bearing_seat(shape,z)
    return shape


def _cb_ear(y, thickness):
    # Continuous C-to-B cheeks. There are no external fastening lobes or cap.
    shape=profile_fillet(union(bar(0,R,9,y,thickness),cyl(13,y,thickness,z=R),
                              cyl(17,y,thickness)),3)
    return cut(shape,cyl(9.5,y-1,thickness+2),cyl(4,y-1,thickness+2,z=R))


def cw_fork():
    lower=profiles.make_cw_profile(Y(7),8).common(box(-50,Y(6),-170,100,10,170))
    lower=union(lower,cyl(17,Y(7),8))
    shape=union(lower,_cb_ear(Y(3.5),3),_cb_ear(Y(15.5),3),
                ring(17,9.5,Y(6.4),9.2,0))
    shape=_axis_bore(shape,R,inner=True,outer=True)
    shape=bearing_seat(shape,0)
    for x,dz in cad.points(8.75,3,90):
        shape=cut(shape,cyl(1.7,Y(6),10,x,dz-L),cyl(2.9,Y(6.9),3.1,x,dz-L))
    # The original H6215 has a radial cable outlet in its stator, beyond this
    # mounting face. Keep the center solid so all M3 heads have full support.
    return shape


def designs():
    return {'OB_inner_full':(ob_inner(),'hip','CNC'),
            'OB_outer_full':(ob_outer(),'hip','CNC'),
            'OA_one_piece':(oa_fork(),'oa','CNC'),
            'AC_bearing_link':(ac_link(),'ac','CNC'),
            'CW_one_piece':(cw_fork(),'output','CNC')}


def keeper(z=0, y=None):
    if y is None:y=Y(13.8)
    shape=ring(14,8.4,y,.8,z)
    for x,dz in CAP_HOLES:shape=cut(shape,cyl(1.1,y-.1,1,x,z+dz))
    return shape


def female_pin(y=None,z=0):
    if y is None:y=Y(4)
    return cut(cyl(3,y,14.05,z=z),cyl(.8,y-.1,4.3,z=z),
               cyl(.8,y+9.75,4.4,z=z))


def hardware():
    items=[]
    for name,holder,z,bearing_role,bearing_z in (
        ('A','oa',-R,'ac',0),('C','output',R,'ac',-L),('B','hip',-L,'output',0)):
        items.append((f'626_{name}',ring(9.5,3,Y(7.75),6,bearing_z),bearing_role))
        items.append((f'bearing_keeper_{name}',keeper(bearing_z),bearing_role))
        for i,(x,dz) in enumerate(CAP_HOLES):
            # Omit engaged M2 thread inside its modeled tapped hole.
            screw=union(cyl(1,Y(13.8),.8,x,bearing_z+dz),
                        cyl(2,Y(14.6),.5,x,bearing_z+dz))
            items.append((f'keeper_{name}_SETS_M2x4_{i}',screw,bearing_role))
        items.append((f'female_pin_{name}',female_pin(z=z),holder))
        for suffix,y in (('inner',4),('outer',15.5)):
            items.append((f'bronze_sleeve_{name}_{suffix}',ring(4,3.025,Y(y),2.5,z),holder))
        for suffix,y,thickness in (('inner',6.5,1.25),('outer',13.75,1.70)):
            items.append((f'race_spacer_{name}_{suffix}',ring(4.2,3.1,Y(y),thickness,z),holder))
        items.append((f'axis_washer_{name}_inner',ring(4.5,1.1,Y(3.8),.2,z),holder))
        items.append((f'axis_washer_{name}_outer',ring(4.5,1.1,Y(18.05),.2,z),holder))
        inner=union(cyl(2,Y(3.3),.5,z=z),cyl(1,Y(3.8),.2,z=z))
        outer=union(cyl(1,Y(18.05),.2,z=z),cyl(2,Y(18.25),.5,z=z))
        items.extend(((f'axis_{name}_SETS_M2x4_inner',inner,holder),
                      (f'axis_{name}_SETS_M2x4_outer',outer,holder)))
    for i,(x,z) in enumerate(POSTS):
        screw=union(cyl(1.5,Y(19),1.3,x,z),
                    Part.makeCone(1.5,3,1.5,V(x,Y(20.3),z),cad.YAXIS),
                    cyl(3,Y(21.8),.2,x,z))
        items.append((f'OB_cover_M3x8_{i}',screw,'hip'))
    for i,(x,z) in enumerate(cad.points(25,6,30)):
        screw=union(cyl(1.5,Y(0),1.3,x,z),
                    Part.makeCone(1.5,3,1.5,V(x,Y(1.3),z),cad.YAXIS),
                    cyl(3,Y(2.8),.2,x,z))
        items.append((f'OB_stator_M3x6_{i}',screw,'hip'))
    for i,(x,z) in enumerate(cad.points(13.5,6,0)):
        screw=union(cyl(1.5,Y(1),12,x,z),cyl(2.75,Y(13),3,x,z))
        items.append((f'OA_rotor_M3x16_{i}',screw,'oa'))
    for i,(x,dz) in enumerate(cad.points(8.75,3,90)):
        screw=union(cyl(1.5,Y(10),5,x,dz-L),cyl(2.75,Y(7),3,x,dz-L))
        items.append((f'H6215_stator_M3x8_{i}',screw,'output'))
    return items


def export_hardware():
    folder=cad.OUT/'metal_hardware';folder.mkdir(parents=True,exist_ok=True)
    specs=[]
    def save(name,shape,qty,material,**kwargs):
        shape.check(True);shape.exportStep(str(folder/(name+'.step')))
        specs.append(dict(part=name,quantity=qty,material=material,**kwargs))
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


def beam_sections(parts):
    """Conservative rail dimensions; do not model perforated plates as solid bars."""
    result={}
    for name,offset,zlow,zhigh,thickness,rails in (
        ('OB_inner_full',1.,-116,-40,3,2),
        ('OB_outer_full',19.5,-116,-40,3,2),
        ('AC_bearing_link',11.,-111,-19,8,1),
        ('CW_one_piece',11.,-99,-23,8,2)):
        shape=parts[name][0]
        candidates=[]
        for index in range(round((zhigh-zlow)/.2)+1):
            z=zlow+index*.2
            section=Part.makeLine(V(-65,Y(offset),z),V(65,Y(offset),z)).common(shape)
            intervals=sorted((edge.BoundBox.XMin,edge.BoundBox.XMax) for edge in section.Edges)
            if len(intervals)<rails:
                continue
            for side,interval in (('left',intervals[0]),('right',intervals[-1])):
                candidates.append(dict(z_mm=z,side=side,width_mm=interval[1]-interval[0],
                                       interval_x_mm=interval))
        minimum=min(candidates,key=lambda item:item['width_mm'])
        result[name]=dict(plate_thickness_mm=thickness,rails_in_plate=rails,
            minimum_edge_rail=minimum,conservative_rectangular_rail_area_mm2=minimum['width_mm']*thickness,
            sampled_z_range_mm=[zlow,zhigh],sample_spacing_mm=.2,
            conservative_unbraced_length_mm=130,
            length_assumption='Pivot span; diagonal ligaments/posts are not credited as fixed lateral supports.',
            method='Exact CAD line/solid intersections at plate mid-thickness every 0.2 mm along Z.',
            cautions='Sampling is not an analytical global minimum. Use rounded-down widths; joint eyes, drilled features and local buckling need separate assessment.')
    obhead=union(profiles.ob_outer_prism(0,1),cyl(50.5,0,1))
    outline=next(face.OuterWire for face in obhead.Faces if abs(face.CenterOfMass.y)<1e-6)
    for name,outer,polygons in (('OB',outline,profiles.OB_WINDOWS),
                               ('CW',profiles._cw_contour().wire(),profiles.CW_WINDOWS)):
        windows=[profiles._rounded_polygon(vertices).wire() for vertices in polygons]
        result[name+'_window_geometry']=dict(
            min_window_to_outline_mm=min(outer.distToShape(window)[0] for window in windows),
            windows_z_span_mm=[window.BoundBox.ZLength for window in windows],
            max_local_window_span_mm=max(window.BoundBox.ZLength for window in windows),
            max_span_scope='Window clear height only; diagonal webs are not assumed perfect lateral braces.')
    return result


def local_review():
    parts=designs();hw=hardware()
    result=dict(structural_width_mm=22,reference_plane=S(),parameters=configure(),
                parts={},collisions=[],minimum_clearances={},
                sampled_lengths_mm=[120,125,150,183.8477631085,210,225],
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
        if length in (120,183.8477631085,225):
            for a,shape,role in hw:
                sa=cad.transform(shape,role,st);bb=sa.BoundBox
                for b,sb in placed:
                    bc=sb.BoundBox
                    if any(getattr(bb,k+'Max')<=getattr(bc,k+'Min')+1e-7 or
                           getattr(bc,k+'Max')<=getattr(bb,k+'Min')+1e-7 for k in 'XYZ'):continue
                    v=sa.common(sb).Volume
                    if v>.05:result['collisions'].append(dict(length=length,a=a,b=b,mm3=v))
    result['beam_screening_sections']=beam_sections(parts)
    (cad.OUT/'leg_layout_review.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    cad.configure(cad.ROOT/'mechanical/v5');cad.P.update(configure())
    print(json.dumps(local_review(),indent=2))
