"""Actual CAD previews of V8.3; color represents paint, not extra parts."""
from __future__ import annotations
import os
import sys
sys.modules['flatmesh']=None
import render_nested_robot as view
import render_modular_robot as baseline

App, Gui = view.App, view.Gui
OUT=view.ROOT/'mechanical/v8_3'
view.OUT,view.PREVIEWS=OUT,OUT/'previews'
view.EXACT_CAPTURE_ORIENTATION=True
view.FRAME_MARGIN=1.08
WHITE=(.90,.92,.93)
BLACK=(.065,.076,.085)
ORANGE=(1.,.39,.055)


def color(obj):
    baseline.color(obj)
    v=obj.ViewObject
    v.DisplayMode='Shaded'
    if obj.TypeId!='Part::Feature': return
    if obj.Name.startswith(('chassis_front_shell','chassis_rear_cover','shoulder_fairing')):
        v.ShapeColor=WHITE
        colors=[]
        for face in obj.Shape.Faces:
            p=face.CenterOfMass; c=WHITE
            if obj.Name=='chassis_front_shell':
                if 96.8 < p.x < 101.2 and abs(p.y)<55 and 99.1<p.z<100.1: c=ORANGE
                if 101.8<p.x<104.7 and abs(p.y)>81.2 and -4.2<p.z<67.2: c=ORANGE
                if -9.2<p.x<85.2 and 59.9<abs(p.y)<65.2 and 99.1<p.z<100.1:
                    c=ORANGE if 25.4<p.x<53.6 else BLACK
                if 125.8<p.x<146.2 and 87.5<abs(p.y)<91.4 and -8.6<p.z<-8.1:c=ORANGE
                if p.x>143.5 and -58.2<p.z<-18.8 and (79.5<abs(p.y)<87.3 or 91.3<abs(p.y)<99.1):c=BLACK
            colors.append(c)
        v.DiffuseColor=colors
    elif obj.Name=='display_front_bezel':
        v.ShapeColor=BLACK
        colors=[]
        for face in obj.Shape.Faces:
            p=face.CenterOfMass;c=BLACK
            if p.x>117.05 and abs(p.y)<60.2 and 41.8<p.z<80.2:c=(.68,.72,.75)
            if 61.8<abs(p.y)<65.2 and 71.8<p.z<83.2 and p.x>116.3:c=ORANGE
            colors.append(c)
        v.DiffuseColor=colors
    elif obj.Name.startswith(('front_face_M3','display_case','D435_')):
        if obj.Name!='D435_clearance_envelope':
            v.ShapeColor=BLACK
            v.DiffuseColor=[BLACK]*len(obj.Shape.Faces)
    if obj.Name.startswith(('OB_','CW_','AC_')): v.ShapeColor=(.65,.70,.73)
    if obj.Name.startswith('OA_'):v.ShapeColor=(.08,.45,.50)
    v.LineColor=(.14,.16,.17);v.LineWidth=.6
    v.AngularDeflection=10.
    v.Deviation=.05


def main():
    Gui.showMainWindow()
    import PartGui,MeshGui
    doc=App.openDocument(str(OUT/'wheel_leg_v8_3.FCStd'))
    doc.Label='Wheel-Leg V8.3 外观与试装'
    for g in doc.Objects:
        if g.TypeId in ('App::Part','App::DocumentObjectGroup'):g.ViewObject.Visibility=True
    doc.Parameters.LegLength=180;doc.Parameters.Beta=0;doc.recompute()
    objects=[o for o in doc.Objects if o.TypeId in ('Part::Feature','Mesh::Feature')]
    for o in objects:color(o)
    features=[o for o in objects if getattr(o,'Material','')!='routing_allowance' and
              getattr(o,'ExportRole','')!='collision_and_mass_proxy_only']
    front=App.Rotation(App.Vector(0,1,0),App.Vector(0,0,1),App.Vector(1,0,0),'ZXY').Q
    iso=App.Rotation(App.Vector(-1,1.35,0),App.Vector(-.7425,-.55,2.8225),App.Vector(1.35,1,.55),'ZXY').Q
    rear=App.Rotation(App.Vector(1,-1.2,0),App.Vector(.8,.67,2.44),App.Vector(-1.2,-1,.8),'ZXY').Q
    def show(predicate):
        for o in objects:o.ViewObject.Visibility=o in features and predicate(o)
    show(lambda o:True)
    view.save_view(doc,'assembly_front.png',front,1800,1800)
    view.save_view(doc,'assembly_isometric.png',iso,2000,1650)
    view.save_view(doc,'assembly_rear.png',rear,1900,1600)
    show(lambda o:getattr(o,'KinematicRole','fixed')=='fixed')
    view.save_view(doc,'body_front.png',front,1800,1500)
    view.save_view(doc,'body_isometric.png',iso,2000,1550)
    show(lambda o:o.Name in ('chassis_front_shell','display_front_bezel'))
    view.save_view(doc,'shell_and_face.png',iso,1900,1500)
    show(lambda o:getattr(o,'KinematicRole','fixed')=='fixed' and not o.Name.startswith(
        ('chassis_front_shell','chassis_rear_cover','shoulder_','front_shell_','rear_cover_','display_front_bezel','front_face_')))
    view.save_view(doc,'internal_layout.png',iso,1900,1550)
    show(lambda o:True)
    view.save_view(doc,'assembly_isometric.png',iso,2000,1650)
    doc.save();App.closeDocument(doc.Name)
    print('V83_RENDER_COMPLETE',flush=True)


if __name__=='__main__':
    main();sys.stdout.flush();sys.stderr.flush();os._exit(0)
