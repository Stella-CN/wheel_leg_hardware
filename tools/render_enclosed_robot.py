"""V5 native FreeCAD views, cover removal, and individually separated parts."""
from __future__ import annotations

import json
import math

import render_compact_robot as coupling_view
import render_nested_robot as view

App, Gui, Part = view.App, view.Gui, view.Part
OUT = view.ROOT/'mechanical/v5'
view.OUT, view.PREVIEWS = OUT, OUT/'previews'
coupling_view.OUT = OUT


def color(obj):
    view.color_feature(obj)
    if 'OA_one_piece' in obj.Name:
        obj.ViewObject.ShapeColor=(.49,.38,.79)
    if obj.Name=='Orin_Nano_envelope':
        obj.ViewObject.ShapeColor=(.28,.47,.32)
    elif obj.Name=='D435_envelope':
        obj.ViewObject.ShapeColor=(.35,.37,.39)
    elif obj.Name=='Battery_400g_envelope':
        obj.ViewObject.ShapeColor=(.25,.38,.66)
    elif obj.Name=='IMU_envelope':
        obj.ViewObject.ShapeColor=(.77,.46,.22)
    elif obj.Name=='chassis_upper_shell':
        obj.ViewObject.ShapeColor=(.84,.87,.90)


def separate(source, rotation):
    doc=App.newDocument('V5_Separate_Manufactured_Parts')
    doc.Label='V5 independent parts — review layout, not assembly placement'
    places=(('OB_inner_full',0,0),('OB_outer_full',130,0),
            ('OA_one_piece',265,0),('AC_bearing_link',360,0),
            ('CW_one_piece',470,0),('hip_rotor_cnc',0,-225),
            ('knee_stator_cnc',145,-225))
    for name,x,z in places:
        src=source.getObject(name+'_right')
        shape=src.Shape.copy();shape.Placement=App.Placement()
        bb=shape.BoundBox
        shape.translate(App.Vector(x-bb.XMin,-bb.YMax,z-bb.ZMax))
        obj=doc.addObject('Part::Feature',name);obj.Shape=shape
        obj.addProperty('App::PropertyString','Material');obj.Material=src.Material
        color(obj)
    view.save_view(doc,'part_breakdown.png',App.Rotation(0,math.sqrt(.5),math.sqrt(.5),0).Q,2000,1500)
    view.save_view(doc,'part_breakdown_oblique.png',rotation,2000,1500)
    doc.saveAs(str(OUT/'part_breakdown.FCStd'))
    Part.export(doc.Objects,str(OUT/'part_breakdown.step'))


def exploded(source, rotation):
    doc=App.newDocument('V5_Exploded_Leg')
    offsets={'J4310_hip':-70,'hip_stator_mount':-55,'hip_rotor_cnc':-35,
             'knee_stator_cnc':-10,'J4310_knee':20,'OB_inner_full':65,
             'OA_one_piece':115,'AC_bearing_link':165,'CW_one_piece':215,
             'OB_outer_full':280,'H6215':340,'wheel_rim':390,'elastic_tyre':390}
    for src in source.Objects:
        if src.TypeId!='Part::Feature' or not src.Name.endswith('_right'):
            continue
        base=src.Name[:-6]
        if base not in offsets:
            continue
        obj=doc.addObject('Part::Feature',src.Name)
        obj.Shape=Part.makeCompound([src.Shape.copy()])
        obj.Placement.Base=App.Vector(0,offsets[base],0)
        obj.addProperty('App::PropertyString','Material');obj.Material=src.Material
        color(obj)
    view.save_view(doc,'right_leg_exploded.png',rotation,2200,1500)
    doc.saveAs(str(OUT/'leg_exploded_review.FCStd'))


def main():
    Gui.showMainWindow()
    import PartGui  # noqa: F401
    coupling_view.show_coupling()
    doc=App.openDocument(str(OUT/'wheel_leg_v5.FCStd'))
    features=[o for o in doc.Objects if o.TypeId=='Part::Feature']
    expressions={o.Name:list(o.ExpressionEngine) for o in features}
    for group in (doc.Robot,doc.PurchasedParts):group.ViewObject.Visibility=True
    for obj in features:color(obj)
    leg_rotation=App.Rotation(App.Vector(-1,1,0),App.Vector(-.7,-.7,2),
                             App.Vector(1,1,.7),'ZXY').Q
    full=App.Rotation(.364705,.279848,.115917,.880476).Q
    view.FRAME_MARGIN=1.15
    view.save_view(doc,'assembly.png',full)
    for name in ('chassis_lid','chassis_upper_shell'):
        doc.getObject(name).ViewObject.Visibility=False
    view.save_view(doc,'electronics_layout.png',full)
    view.FRAME_MARGIN=1.0
    for obj in features:
        obj.ViewObject.Visibility=obj.Name.endswith('_right') and not obj.Name.startswith('chassis_')
    view.save_view(doc,'right_leg.png',leg_rotation)
    view.save_view(doc,'right_leg_side.png',App.Rotation(0,math.sqrt(.5),math.sqrt(.5),0).Q)
    doc.OB_outer_full_right.ViewObject.Visibility=False
    view.save_view(doc,'OA_inside_OB.png',leg_rotation)
    doc.OB_inner_full_right.ViewObject.Transparency=65
    view.save_view(doc,'nested_joints_cutaway.png',leg_rotation)
    doc.OB_inner_full_right.ViewObject.Transparency=0
    exploded(doc,leg_rotation)
    separate(doc,leg_rotation)
    App.setActiveDocument(doc.Name)
    for obj in features:obj.ViewObject.Visibility=True
    view.FRAME_MARGIN=1.15
    view.save_view(doc,'assembly.png',full)
    assert expressions=={o.Name:list(o.ExpressionEngine) for o in features}
    doc.save()
    view.linkage_svg(json.loads((OUT/'design_parameters.json').read_text()))
    path=view.PREVIEWS/'linkage_layout.svg'
    path.write_text(path.read_text().replace('V3 四杆','V5 四杆'))
    print('FREECAD_V5_PREVIEWS_COMPLETE',flush=True)


if __name__=='__main__':main()
