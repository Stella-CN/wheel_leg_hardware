"""V6 native FreeCAD views, cover removal, and individually separated parts."""
from __future__ import annotations

import json
import math
import sys

# This bundled optional flattening extension loads a second Python runtime
# and crashes its GIL initialization when FreeCAD is embedded. Mesh display
# does not use it; the Mesh workbench handles this optional ImportError.
sys.modules['flatmesh']=None

import render_compact_robot as coupling_view
import render_nested_robot as view

App, Gui, Part = view.App, view.Gui, view.Part
OUT = view.ROOT/'mechanical/v6'
view.OUT, view.PREVIEWS = OUT, OUT/'previews'
view.EXACT_CAPTURE_ORIENTATION = True
coupling_view.OUT = OUT


def color(obj):
    if obj.TypeId=='Mesh::Feature':
        obj.ViewObject.ShapeColor=(.35,.37,.40)
        obj.ViewObject.DisplayMode='Shaded'
        obj.ViewObject.Visibility=True
        return
    view.color_feature(obj)
    if 'OB_inner_carrier' in obj.Name:
        obj.ViewObject.ShapeColor=(.39,.78,.34)
    elif 'OB_outer_shell' in obj.Name:
        obj.ViewObject.ShapeColor=(.62,.84,.49)
    if 'OA_one_piece' in obj.Name:
        obj.ViewObject.ShapeColor=(.49,.38,.79)
    if obj.Name=='Jetson_Orin_Nano_official':
        colors=[]
        special={2:(.15,.34,.22),268:(.45,.48,.50),273:(.12,.13,.15),
                 274:(.14,.43,.25),1266:(.17,.18,.20)}
        for index,solid in enumerate(obj.Shape.Solids):
            colors.extend([special.get(index,(.60,.62,.64))]*len(solid.Faces))
        obj.ViewObject.DiffuseColor=colors
        obj.ViewObject.DisplayMode='Flat Lines'
        obj.ViewObject.LineWidth=.5
    elif obj.Name=='D435_clearance_envelope':
        obj.ViewObject.ShapeColor=(.35,.37,.39)
        obj.ViewObject.Visibility=False
    elif obj.Name=='Battery_400g_envelope':
        obj.ViewObject.ShapeColor=(.25,.38,.66)
    elif obj.Name=='IMU_envelope':
        obj.ViewObject.ShapeColor=(.77,.46,.22)
    elif 'shoulder_fairing' in obj.Name:
        obj.ViewObject.ShapeColor=(.28,.38,.48)
    elif obj.Name.startswith('chassis_') and obj.Material=='PETG':
        obj.ViewObject.ShapeColor=(.84,.87,.90)
    elif obj.Name.startswith('chassis_') and obj.Material=='CNC':
        obj.ViewObject.ShapeColor=(.29,.33,.38)


def is_visible_feature(obj):
    return obj.TypeId in ('Part::Feature','Mesh::Feature') and getattr(obj,'ExportRole','')!='collision_and_mass_proxy_only'


def separate(source, rotation):
    doc=App.newDocument('V6_Separate_Manufactured_Parts')
    doc.Label='V6 independent parts — review layout, not assembly placement'
    places=(('OB_inner_carrier',0,0),('OB_outer_shell',130,0),
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
    doc=App.newDocument('V6_Exploded_Leg')
    offsets={'J4310_hip':-70,'hip_stator_mount':-55,'hip_rotor_cnc':-35,
             'knee_stator_cnc':-10,'J4310_knee':20,'OB_inner_carrier':65,
             'OA_one_piece':115,'AC_bearing_link':165,'CW_one_piece':215,
             'OB_outer_shell':280,'H6215':340,'wheel_rim':390,'elastic_tyre':390}
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


def assembly_stages(doc,rotation):
    selected={'J4310_knee_right','OB_inner_carrier_right'}
    features=[o for o in doc.Objects if is_visible_feature(o)]
    for index,name in enumerate((None,'OA_one_piece_right','OB_outer_shell_right'),1):
        if name:selected.add(name)
        for obj in features:obj.ViewObject.Visibility=obj.Name in selected
        view.save_view(doc,f'assembly_stage_{index}.png',rotation,1500,1100)
    shell=App.newDocument('V6_OB_Shell_Inside')
    obj=shell.addObject('Part::Feature','OB_outer_shell')
    shape=doc.OB_outer_shell_right.Shape.copy();shape.Placement=App.Placement()
    obj.Shape=shape;color(obj)
    back=App.Rotation(App.Vector(1,-1,0),App.Vector(.7,.7,2),
                      App.Vector(-1,-1,.7),'ZXY').Q
    view.save_view(shell,'OB_shell_inside.png',back,1500,1100)
    shell.saveAs(str(OUT/'OB_shell_inside.FCStd'))
    App.setActiveDocument(doc.Name)


def linkage_svg():
    import build_printable_robot as cad
    cad.configure(OUT)
    state=cad.pose(cad.P['leg_length'])
    nodes={'O':(0,0),'A':state['a'],'B':state['b'],
           'C':(state['a'][0]+state['b'][0],state['a'][1]+state['b'][1]),
           'W':state['w']}
    def xy(name):
        x,z=nodes[name]
        return 500+x*2.8,160-z*2.8
    elements=['<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="880" viewBox="0 0 1000 880">',
              '<rect width="1000" height="880" fill="#f5f7fa"/>',
              '<g font-family="Arial, sans-serif" fill="#263648">',
              '<text x="55" y="60" font-size="30">V6 / 130–105–45 mm linkage</text>']
    for a,b,col,width in (('O','B','#70a959',18),('O','A','#8e78c4',15),
                          ('A','C','#ce7f7f',12),('C','B','#58b4b8',15),
                          ('B','W','#58b4b8',18)):
        x,y=xy(a);xx,yy=xy(b)
        elements.append(f'<path d="M{x},{y} L{xx},{yy}" stroke="{col}" stroke-width="{width}" stroke-linecap="round"/>')
    for name in nodes:
        x,y=xy(name)
        elements.append(f'<circle cx="{x}" cy="{y}" r="6" fill="white" stroke="#263648" stroke-width="2"/><text x="{x+13}" y="{y-12}" font-size="24">{name}</text>')
    x,y=xy('W')
    elements.append(f'<circle cx="{x}" cy="{y}" r="140" fill="none" stroke="#64717c" stroke-width="6"/>')
    lines=['OB = AC = 130 mm','BW = 105 mm','OA = BC = 45 mm',
           f'Nominal hip–wheel distance: {cad.P["leg_length"]:.0f} mm',
           'Unequal OB / BW: new inverse kinematics',
           'Diagram is a kinematic skeleton, not a CAD section.']
    for i,line in enumerate(lines):elements.append(f'<text x="55" y="{700+i*27}" font-size="19">{line}</text>')
    elements.append('</g></svg>')
    (OUT/'previews/linkage_layout.svg').write_text('\n'.join(elements))


def main():
    Gui.showMainWindow()
    import PartGui  # noqa: F401
    import Mesh  # noqa: F401; initialize Mesh before its native GUI module
    import MeshGui  # noqa: F401
    coupling_view.show_coupling()
    doc=App.openDocument(str(OUT/'wheel_leg_v6.FCStd'))
    for obj in doc.Objects:
        if getattr(obj,'ExportRole','')=='collision_and_mass_proxy_only':
            obj.ViewObject.Visibility=False
    features=[o for o in doc.Objects if is_visible_feature(o)]
    expressions={o.Name:list(o.ExpressionEngine) for o in features}
    for group in (doc.Robot,doc.PurchasedParts):group.ViewObject.Visibility=True
    for obj in features:color(obj)
    leg_rotation=App.Rotation(App.Vector(-1,1,0),App.Vector(-.7,-.7,2),
                             App.Vector(1,1,.7),'ZXY').Q
    full=App.Rotation(App.Vector(-1,1.35,0),App.Vector(-.7425,-.55,2.8225),
                      App.Vector(1.35,1,.55),'ZXY').Q
    view.FRAME_MARGIN=1.15
    view.save_view(doc,'assembly.png',full)
    for obj in features:
        if (obj.Name.startswith('chassis_') and getattr(obj,'Material','')=='PETG') or 'shoulder_fairing' in obj.Name:
            obj.ViewObject.Visibility=False
    view.save_view(doc,'electronics_layout.png',full)
    for obj in features:
        obj.ViewObject.Visibility=(getattr(obj,'KinematicRole','fixed')=='fixed'
                                  or obj.Name.startswith('J4310_knee_'))
    view.save_view(doc,'body_oblique.png',full)
    front=App.Rotation(App.Vector(0,1,0),App.Vector(0,0,1),
                       App.Vector(1,0,0),'ZXY').Q
    view.save_view(doc,'body_front.png',front)
    view.FRAME_MARGIN=1.0
    leg_prefixes=('J4310_','H6215_','hip_stator_mount_','hip_rotor_cnc_',
                  'knee_stator_cnc_','OB_','OA_','AC_','CW_','wheel_rim_',
                  'elastic_tyre_')
    for obj in features:
        obj.ViewObject.Visibility=(obj.Name.endswith('_right') and
            (obj.Name.startswith(leg_prefixes) or getattr(obj,'KinematicRole','fixed')!='fixed'))
    view.save_view(doc,'right_leg.png',leg_rotation)
    view.save_view(doc,'right_leg_side.png',App.Rotation(0,math.sqrt(.5),math.sqrt(.5),0).Q)
    doc.OB_outer_shell_right.ViewObject.Visibility=False
    view.save_view(doc,'OA_inside_OB.png',leg_rotation)
    doc.OB_inner_carrier_right.ViewObject.Transparency=65
    view.save_view(doc,'nested_joints_cutaway.png',leg_rotation)
    doc.OB_inner_carrier_right.ViewObject.Transparency=0
    assembly_stages(doc,leg_rotation)
    exploded(doc,leg_rotation)
    separate(doc,leg_rotation)
    App.setActiveDocument(doc.Name)
    for obj in features:obj.ViewObject.Visibility=True
    view.FRAME_MARGIN=1.15
    view.save_view(doc,'assembly.png',full)
    assert expressions=={o.Name:list(o.ExpressionEngine) for o in features}
    doc.save()
    linkage_svg()
    print('FREECAD_V6_PREVIEWS_COMPLETE',flush=True)


if __name__=='__main__':main()
