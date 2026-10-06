"""Render actual V8 FreeCAD geometry; no illustrative geometry in assembly."""
from __future__ import annotations

import math
import sys
sys.modules['flatmesh']=None
import render_nested_robot as view

App,Gui,Part=view.App,view.Gui,view.Part
OUT=view.ROOT/'mechanical/v8'
view.OUT,view.PREVIEWS=OUT,OUT/'previews'
view.EXACT_CAPTURE_ORIENTATION=True


def feature(obj):
    return obj.TypeId in ('Part::Feature','Mesh::Feature') and getattr(obj,'ExportRole','')!='collision_and_mass_proxy_only'


def color(obj):
    if obj.TypeId=='Mesh::Feature':
        obj.ViewObject.ShapeColor=(.32,.35,.39)
        obj.ViewObject.DisplayMode='Shaded';obj.ViewObject.Visibility=True
        return
    view.color_feature(obj)
    name=obj.Name
    c=None
    if name.startswith('chassis_') and getattr(obj,'Material','')=='PETG':c=(.77,.81,.83)
    elif name.startswith('chassis_'):c=(.32,.36,.40)
    elif 'shoulder_fairing' in name:c=(.68,.74,.77)
    elif name.startswith('OB_outer'):c=(.63,.68,.71)
    elif name.startswith('OB_inner'):c=(.37,.43,.48)
    elif name.startswith('CW_'):c=(.39,.47,.52)
    elif name.startswith('AC_'):c=(.69,.72,.73)
    elif name.startswith('OA_'):c=(.10,.50,.56)
    elif name=='display_front_bezel':c=(.13,.20,.24)
    elif name=='Display_GK_HD_5in_supplier_envelope':c=(.055,.09,.12)
    elif 'display_case_cradle' in name:c=(.22,.27,.30)
    elif name=='HI13R2_official':c=(.19,.28,.34)
    elif name=='HI13R2_rigid_bridge':c=(.56,.61,.65)
    elif name=='Battery_400g_envelope':c=(.21,.32,.46)
    if c is not None:obj.ViewObject.ShapeColor=c
    if name=='Jetson_Orin_Nano_official':
        colors=[]
        special={2:(.15,.34,.22),268:(.45,.48,.50),273:(.12,.13,.15),274:(.14,.43,.25),1266:(.17,.18,.20)}
        for i,solid in enumerate(obj.Shape.Solids):colors.extend([special.get(i,(.60,.62,.64))]*len(solid.Faces))
        obj.ViewObject.DiffuseColor=colors;obj.ViewObject.LineWidth=.5
    elif name=='D435_clearance_envelope':obj.ViewObject.Visibility=False
    if name.startswith(('chassis_front_shell','chassis_rear_cover','shoulder_fairing')):
        obj.ViewObject.LineWidth=1.2


def main():
    Gui.showMainWindow()
    import PartGui,Mesh,MeshGui  # noqa: F401
    doc=App.openDocument(str(OUT/'wheel_leg_v8.FCStd'))
    for group in (doc.Robot,doc.PurchasedParts):group.ViewObject.Visibility=True
    doc.Parameters.LegLength=180;doc.Parameters.Beta=0;doc.recompute()
    features=[o for o in doc.Objects if feature(o)]
    expressions={o.Name:list(o.ExpressionEngine) for o in features}
    for obj in doc.Objects:
        if obj.TypeId in ('Part::Feature','Mesh::Feature'):color(obj)
    full=App.Rotation(App.Vector(-1,1.35,0),App.Vector(-.7425,-.55,2.8225),App.Vector(1.35,1,.55),'ZXY').Q
    front=App.Rotation(App.Vector(0,1,0),App.Vector(0,0,1),App.Vector(1,0,0),'ZXY').Q
    rear=App.Rotation(App.Vector(1,-1.2,0),App.Vector(.8,.67,2.44),App.Vector(-1.2,-1,.8),'ZXY').Q
    view.FRAME_MARGIN=1.10
    view.save_view(doc,'assembly.png',full,2000,1550)
    view.save_view(doc,'assembly_front.png',front,1700,1700)
    for obj in features:
        obj.ViewObject.Visibility=(getattr(obj,'KinematicRole','fixed')=='fixed' or obj.Name.startswith('J4310_knee_'))
    view.save_view(doc,'body_oblique.png',full,1900,1450)
    view.save_view(doc,'body_front.png',front,1700,1500)
    for obj in features:
        obj.ViewObject.Visibility=(getattr(obj,'KinematicRole','fixed')=='fixed' and
            not obj.Name.startswith(('chassis_front_shell','chassis_rear_cover','shoulder_fairing','display_front_bezel')))
    view.save_view(doc,'electronics_layout.png',rear,1950,1500)
    view.save_view(doc,'imu_top_layout.png',App.Rotation().Q,1800,1600)
    for obj in features:
        obj.ViewObject.Visibility=obj.Name.startswith(('HI13','IMU_bridge','chassis_hip_frame','Jetson_Orin','electronics_tray'))
    view.save_view(doc,'imu_mount.png',rear,1800,1400)
    for obj in features:
        obj.ViewObject.Visibility=obj.Name.startswith(('display_','Display_GK_HD_5','D435_','chassis_front_shell'))
    view.save_view(doc,'front_panel_inside.png',rear,1800,1550)
    for obj in features:obj.ViewObject.Visibility=True
    view.save_view(doc,'assembly.png',full,2000,1550)
    assert expressions=={o.Name:list(o.ExpressionEngine) for o in features}
    doc.save()
    from PySide import QtCore,QtGui,QtSvg
    svg=QtSvg.QSvgRenderer(str(OUT/'previews/display_dimensions.svg'))
    canvas=QtGui.QImage(1100,810,QtGui.QImage.Format_ARGB32)
    canvas.fill(QtGui.QColor('white'))
    painter=QtGui.QPainter(canvas);svg.render(painter);painter.end()
    canvas.save(str(OUT/'previews/display_dimensions.png'))
    print('V8_PREVIEWS_COMPLETE',flush=True)


if __name__=='__main__':main()
