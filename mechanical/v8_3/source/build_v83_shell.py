"""V8.3 cosmetic shell, preserving every V8.2 mechanical/electrical datum.

Run using the installed FreeCAD Python.  Three existing manufactured solids
change; the two static decorative hands are integral with the front shell.
No purchase fastener or independent moving object is added.
"""
from __future__ import annotations

import hashlib
import json
import shutil

import build_printable_robot as cad
import cad_v81_chassis as chassis
from review_v82_integration import is_physical, preserve

App, Part, V = cad.App, cad.Part, cad.V
BASE = cad.ROOT / 'mechanical/v8_2'
OUT = cad.ROOT / 'mechanical/v8_3'
CHANGED = ('chassis_front_shell', 'chassis_rear_cover', 'display_front_bezel')
box, cut, fuse = cad.box, cad.cut, cad.union
yz = chassis.core.rounded_pocket_yz
xz = chassis.core.rounded_pocket_xz


def rounded_box(x0, y0, z0, x1, y1, z1, radius):
    s = box(x0, y0, z0, x1-x0, y1-y0, z1-z0)
    return s.makeFillet(radius, s.Edges)


def capsule_xy(x0, x1, y0, y1, z, height, r):
    s = yz(y0, y1, x0, x1, 0, height, r)
    # x'=z, y'=y, z'=-x: turn the original YZ outline into XY.
    s.rotate(V(), V(0,1,0), 90)
    s.translate(V(0,0,z+height))
    return s


def top_recess(x0, x1, y0, y1, bottom, r=1.):
    return capsule_xy(x0, x1, y0, y1, bottom, 100.25-bottom, r)


def static_hand(side):
    # The root attaches to the outer border, never the removable faceplate.
    root = rounded_box(111, 75, -47, 136, 90.5, -5, 6.5)
    # Keep every protruding cuff/finger outside Y=74.8: the Y=74 faceplate
    # must still withdraw forwards as a complete screen/camera module.
    cuff = rounded_box(119, 74.8, -49, 154, 104, -8, 6.5)
    opening = rounded_box(128, 79.3, -44.5, 160, 99.5, -12.5, 3.5)
    cuff = cut(cuff, opening)
    fingers = [rounded_box(144, y, -58, 169, y+7.4, -19, 3.3)
               for y in (79.7, 91.5)]
    hand = fuse(root, cuff, *fingers)
    # Front-face M3 access stays available with hands present.
    hand = cut(hand, Part.makeCylinder(4., 50, V(110,68,-44), V(1,0,0)))
    # Small shallow paint pocket; orange is paint, not unselected electronics.
    hand = cut(hand, capsule_xy(126,146,87.7,91.2,-8.45,.7,1.5))
    return hand if side > 0 else hand.mirror(V(), V(0,1,0))


def style_shell(shape, front):
    if front:
        # Extending the rim backwards maintains solid overlap with the
        # deeper R16 body curvature, without entering the faceplate aperture.
        lip = cut(yz(-85,85,-58,103,109.5,15.,18.),
                  yz(-74.4,74.4,-49.4,95.4,109.3,15.4,4.4))
        front_edges=[e for e in lip.Edges if abs(e.BoundBox.XMin-124.5)<1e-6 and abs(e.BoundBox.XMax-124.5)<1e-6]
        lip=lip.makeFillet(2.5,front_edges)
        shape = fuse(shape, lip, static_hand(1), static_hand(-1))
    # Existing slot envelopes are only opened slightly at their square ends.
    for x in ((42.,54.,66.) if front else (-66.,-54.,-42.)):
        for y in (-48.,-22.,22.,48.):
            shape = cut(shape, Part.makeCylinder(2.,3.5,V(x,y,96.8)))
    # A shallow panel witness line gives the top a removable-panel appearance
    # while keeping the original service split and internal wall untouched.
    xa, xb = (-13.,88.) if front else (-76.,-28.)
    outline = cut(top_recess(xa,xb,-55,55,99.6,4.),
                  top_recess(xa+1.,xb-1.,-54,54,99.4,3.))
    shape = cut(shape, outline)
    if front:
        shape = cut(shape, top_recess(97.,101.,-54.,54.,99.25,1.9))
        for side in (-1,1):
            # Side accent stays clear of the wire exit at X89/Z54.
            groove = xz(102,104.5,-4,67,81.35,1.,1.2)
            shape = cut(shape, groove if side > 0 else groove.mirror(V(),V(0,1,0)))
            for x0,x1,z in ((-9.,25.,99.45),(25.5,53.5,99.25),(54.,85.,99.45)):
                ya,yb = (60.,65.) if side > 0 else (-65.,-60.)
                shape = cut(shape, top_recess(x0,x1,ya,yb,z,2.))
    return shape.removeSplitter()


def style_face(shape):
    # Both capsule rims lie wholly outside the original camera aperture and
    # its screw heads.  The actual D435 mesh and all mounting holes remain.
    rim = cut(yz(-60.,60.,42.,80.,116.7,1.7,18.9),
              yz(-58.,58.,44.,78.,116.5,2.1,16.9))
    shape = fuse(shape, rim)
    for side in (-1,1):
        y0,y1 = (62.,65.) if side > 0 else (-65.,-62.)
        shape = cut(shape, yz(y0,y1,72.,83.,116.4,.8,1.4))
    return shape.removeSplitter()


def intersects(a,b):
    return all(min(getattr(a,k+'Max'),getattr(b,k+'Max')) >
               max(getattr(a,k+'Min'),getattr(b,k+'Min')) for k in 'XYZ')


def collision_check(doc, changed, targets):
    hits=[]; pairs=0; seen=set()
    for name in changed:
        a=doc.getObject(name).Shape
        for obj in targets:
            key=tuple(sorted((name,obj.Name)))
            if obj.Name==name or key in seen: continue
            seen.add(key); pairs+=1
            if not intersects(a.BoundBox,obj.Shape.BoundBox): continue
            vol=cad.interference_volume(a,obj.Shape)
            if vol > .001: hits.append(dict(a=name,b=obj.Name,overlap_mm3=vol))
    return dict(pairs=pairs,collisions=hits)


def main():
    OUT.mkdir(exist_ok=True)
    for folder in ('step','cnc','print','manufacturing','metal_hardware','alternates'):
        if (BASE/folder).exists(): shutil.copytree(BASE/folder,OUT/folder,dirs_exist_ok=True)
    for filename in ('design_parameters.json','part_manifest.json','bom_master.json',
                     'module_manifest.json','manufacturing_aliases.json','LEG_FITS.md',
                     'MODULE_ASSEMBLY.md','ELECTRICAL_INTEGRATION.md','routing_allowances.json'):
        shutil.copy2(BASE/filename,OUT/filename)
    parameters=json.loads((OUT/'design_parameters.json').read_text())
    parameters.update(revision='V8.3',
        profile='Rounded enclosure: outer R16 / inner R13, front lip R18 / edge R2.5; enlarged fixed decorative hands; removable5in front module',
        manufacturing_scope='Preserve V8.2 kinematics, load frame, electronics and standard hardware; cosmetic P05/P06/P07 only',
        body_outer_radius_mm=16,body_inner_radius_mm=13,front_lip_outline_radius_mm=18,
        front_lip_edge_radius_mm=2.5,decorative_hand_total_width_mm=208)
    (OUT/'design_parameters.json').write_text(json.dumps(parameters,ensure_ascii=False,indent=2)+'\n')
    for folder in ('previews','source'):(OUT/folder).mkdir(exist_ok=True)
    for name in ('wheel_leg_front.png','wheel_leg.png'):
        shutil.copy2(cad.ROOT.parent.parent.parent/'Downloads'/name,OUT/'source'/name)
    cad.configure(OUT)
    original=App.openDocument(str(BASE/'wheel_leg_v8_2.FCStd'))
    baseline_hash=hashlib.sha256((BASE/'wheel_leg_v8_2.FCStd').read_bytes()).hexdigest()
    original.saveAs(str(OUT/'wheel_leg_v8_3.FCStd'))
    doc=original
    # Rebuild only the thin housing with larger, real three-dimensional
    # radii.  Recover V8.2 electrical additions/cuts by exact solid deltas
    # against V8.1, leaving their interface coordinates untouched.
    previous=App.openDocument(str(cad.ROOT/'mechanical/v8_1/wheel_leg_v8_1.FCStd'))
    chassis._outer=lambda: chassis._rounded_box(*chassis.BODY_BOUNDS,16.)
    chassis._inner=lambda offset=3.,top=97.: chassis._rounded_box(-94+offset,-82+offset,-57.,117-offset,82-offset,top,max(16-offset,.5))
    rounded_front,rounded_rear=chassis._shell_pair()
    # A larger outer bottom radius would otherwise eat the old underlap.
    # Restore the existing170x140 aperture as an internal2mm lip with its
    # top at the original belly-plate undersideZ-50. Clip to the R16 outer
    # envelope so this addition cannot square off the visible curvature.
    underlip=chassis._outer().common(box(-100,-90,-52,225,180,2.))
    aperture=chassis.core.prior._rounded_prism(170.,140.,4.,-53.,6.)
    underlip=cut(underlip,aperture,*[Part.makeCylinder(4.,4.,V(x,y,-53.)) for x,y in chassis.BOTTOM_FASTENERS])
    front_lip=underlip.common(box(-20,-90,-54,145,180,7))
    rear_lip=underlip.common(box(-100,-90,-54,80,180,7))
    receiver=chassis._inner(2.5,97.5).common(box(-24.3,-90,-55.2,4.4,180,160))
    rear_lip=cut(rear_lip,receiver)
    rounded_front=fuse(rounded_front,front_lip)
    rounded_rear=fuse(rounded_rear,rear_lip)
    for name,front in (('chassis_front_shell',True),('chassis_rear_cover',False)):
        print('STYLE',name,flush=True)
        old81=previous.getObject(name).Shape
        old82=doc.getObject(name).Shape
        added=old82.cut(old81)
        removed=old81.cut(old82)
        rounded=rounded_front if front else rounded_rear
        if added.Volume>.001:rounded=fuse(rounded,added)
        if removed.Volume>.001:rounded=cut(rounded,removed)
        doc.getObject(name).Shape=Part.makeCompound([style_shell(rounded,front)])
    App.closeDocument(previous.Name)
    doc.display_front_bezel.Shape=Part.makeCompound([style_face(doc.display_front_bezel.Shape.copy())])
    doc.recompute()
    manifest=json.loads((OUT/'part_manifest.json').read_text())
    modified=[]
    for name in CHANGED:
        o=doc.getObject(name); s=o.Shape
        assert s.isValid() and len(s.Solids)==1,(name,s.isValid(),len(s.Solids))
        s.check(True)
        s.exportStep(str(OUT/'step'/f'{name}.step'))
        oriented=s.copy()
        angle=90 if name=='chassis_rear_cover' else -90
        oriented.rotate(V(),V(0,1,0),angle)
        b=oriented.BoundBox;oriented.translate(V(-b.XMin,-b.YMin,-b.ZMin))
        mesh=cad.MeshPart.meshFromShape(Shape=oriented,LinearDeflection=.06,AngularDeflection=.18,Relative=False)
        assert mesh.isSolid(),name
        b=mesh.BoundBox; dimensions=[b.XLength,b.YLength,b.ZLength]
        assert all(d<=lim+.001 for d,lim in zip(dimensions,(220,220,250))),dimensions
        mesh.write(str(OUT/'print'/f'{name}.stl'))
        row=next(r for r in manifest if r['part']==name)
        row.update(dimensions_mm=[round(v,3) for v in dimensions],volume_mm3=round(s.Volume,3),
                   facets=mesh.CountFacets,brep_valid=True,mesh_closed=True,solids=1,fits_bed=True,
                   nominal_solid_mass_g=round(s.Volume*.00127,1),
                   print_orientation=('Front and rear shells: service split face down; removable support at hands, lip and interior fixtures. '
                                      'Faceplate: flat rear installation surface down, camera rim up.'))
        modified.append(dict(name=name,volume_mm3=s.Volume,dimensions_mm=dimensions))
        print('EXPORTED',name,dimensions,flush=True)
    (OUT/'part_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    bom=json.loads((OUT/'bom_master.json').read_text()); bom['revision']='V8.3'
    for row in bom['rows']:
        names=row.get('assembly_part_aliases',[])
        if names and names[0] in CHANGED:
            name=names[0]; target=OUT/row['source']
            shutil.copy2(OUT/'step'/f'{name}.step',target)
            shutil.copy2(OUT/'print'/f'{name}.stl',target.with_suffix('.stl'))
            r=next(r for r in manifest if r['part']==name)
            row['spec']=' × '.join(map(str,r['dimensions_mm']))+' mm 打印摆放包络；详见STEP'
            row['geometry_sha256']=hashlib.sha256(target.read_bytes()).hexdigest()
            row['notes']+=' V8.3外观件；沿用全部孔位。颜色为涂装区；前壳包含两只固定装饰手，无运动或夹持功能。'
            row['manufacturing_notes']=row['notes']
    (OUT/'bom_master.json').write_text(json.dumps(bom,ensure_ascii=False,indent=2)+'\n')
    doc.recompute(); doc.save()
    check_base=App.openDocument(str(BASE/'wheel_leg_v8_2.FCStd'))
    frozen=preserve(check_base,doc,set(CHANGED))
    solid=[o for o in doc.Objects if is_physical(o) and o.TypeId=='Part::Feature']
    static=collision_check(doc,CHANGED,solid)
    # The front module comes out after its four perimeter screws are removed.
    # Check actual solids against the fixed shell along the assembly direction.
    front_module=[o for o in doc.M05.Group if o.TypeId=='Part::Feature']
    removal=[]
    for travel in (0.,.25,1.,2.,4.,8.,16.,32.,64.,100.):
        hits=[]
        for obj in front_module:
            moving_shape=obj.Shape.copy();moving_shape.translate(V(travel,0,0))
            vol=cad.interference_volume(moving_shape,doc.chassis_front_shell.Shape)
            if vol>.001:hits.append(dict(moving=obj.Name,overlap_mm3=vol))
        removal.append(dict(travel_x_mm=travel,collisions=hits))
    print('FRONT_REMOVAL',sum(len(r['collisions']) for r in removal),flush=True)
    moving=[o for o in solid if getattr(o,'KinematicRole','fixed')!='fixed']
    motion=[]
    for length in (100.,180.,215.):
        for beta in (-15.,0.,15.):
            doc.Parameters.LegLength=length;doc.Parameters.Beta=beta;doc.recompute()
            res=collision_check(doc,CHANGED,moving)
            motion.append(dict(leg_length_mm=length,beta_deg=beta,**res))
            print('MOTION',length,beta,len(res['collisions']),flush=True)
    doc.Parameters.LegLength=180.;doc.Parameters.Beta=0;doc.recompute();doc.save()
    report=dict(changed=list(CHANGED),physical_object_count=len([o for o in doc.Objects if is_physical(o)]),
                preservation=frozen,static=static,motion_samples=motion,front_module_removal_samples=removal,
                all_pass=frozen['all_pass'] and not static['collisions'] and all(not m['collisions'] for m in motion) and all(not r['collisions'] for r in removal),
                scope='Nine sampled poses: leg lengths100/180/215mm with beta-15/0/+15deg; changed shell/face solids against all real solids. Beta angles are diagnostic samples, not certified operating limits. No continuous sweep or structural strength claim.',
                baseline_sha256=baseline_hash,modified_parts=modified,
                exterior_parameters=dict(body_outer_radius_mm=16,body_inner_radius_mm=13,nominal_wall_mm=3,
                    front_lip_outline_radius_mm=18,front_lip_front_edge_radius_mm=2.5,
                    front_lip_outer_yz_mm=[170,161],front_lip_x_mm=[109.5,124.5],
                    hand_cuff_xyz_mm=[35,29.2,41],hand_cuff_outer_radius_mm=6.5,hand_cuff_wall_mm=4.5,
                    finger_xyz_mm=[25,7.4,39],finger_edge_radius_mm=3.3,finger_gap_y_mm=4.4,
                    hand_total_width_mm=208,hand_inner_y_mm=74.8,
                    bottom_internal_underlap_mm=2,bottom_lip_z_mm=[-52,-50],
                    bottom_aperture_xy_mm=[170,140],new_standard_hardware=0),
                source_api='https://freecad.github.io/SourceDoc/d8/ded/classPart_1_1TopoShape.html')
    (OUT/'shell_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    assert hashlib.sha256((BASE/'wheel_leg_v8_2.FCStd').read_bytes()).hexdigest()==baseline_hash
    App.closeDocument(check_base.Name)
    App.closeDocument(doc.Name)
    print('V83_SHELL_BUILT',report['all_pass'],static['collisions'],flush=True)


if __name__=='__main__': main()
