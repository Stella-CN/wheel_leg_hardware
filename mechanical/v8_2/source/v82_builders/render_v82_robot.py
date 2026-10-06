"""Render the actual electrical-integration FreeCAD assembly."""
from __future__ import annotations
import os
import sys
sys.modules['flatmesh'] = None
import render_nested_robot as view
import render_modular_robot as style

App, Gui = view.App, view.Gui
OUT = view.ROOT / 'mechanical/v8_2'
view.OUT, view.PREVIEWS = OUT, OUT / 'previews'
view.EXACT_CAPTURE_ORIENTATION = True
view.FRAME_MARGIN = 1.10


def main():
    Gui.showMainWindow()
    import PartGui, MeshGui  # noqa:F401
    doc = App.openDocument(str(OUT/'wheel_leg_v8_2.FCStd'))
    for group in doc.Objects:
        if group.TypeId in ('App::Part','App::DocumentObjectGroup'):
            group.ViewObject.Visibility = True
    all_features = [o for o in doc.Objects if o.TypeId in ('Part::Feature','Mesh::Feature')]
    features = [o for o in all_features if getattr(o,'ExportRole','') != 'collision_and_mass_proxy_only'
                and getattr(o,'Material','') != 'routing_allowance']
    for o in all_features:
        style.color(o)
        colors = {'electrical_service_carrier':(.21,.40,.45),'USB_hub_rear_clamp':(.25,.34,.39),
                  'USB_hub_104x30x10':(.38,.42,.48),'Power_switch_M16_latching':(.58,.62,.66),
                  'USB2CANFD_Dual_bare_official':(.12,.33,.28),
                  'Distribution_PCB1_user_STEP':(.14,.31,.56),
                  'DCDC_24_to_19_drawing_envelope':(.41,.43,.46),
                  'DC_charge_replaceable_plate':(.19,.25,.28)}
        if o.Name in colors:
            o.ViewObject.ShapeColor = colors[o.Name]
    frontiso = App.Rotation(App.Vector(-1,1.35,0),App.Vector(-.7425,-.55,2.8225),App.Vector(1.35,1,.55),'ZXY').Q
    reariso = App.Rotation(App.Vector(1,-1.2,0),App.Vector(.8,.67,2.44),App.Vector(-1.2,-1,.8),'ZXY').Q
    rear = App.Rotation(App.Vector(0,-1,0),App.Vector(0,0,1),App.Vector(-1,0,0),'ZXY').Q
    def show(predicate):
        for o in all_features:
            o.ViewObject.Visibility = o in features and predicate(o)
    show(lambda o: True)
    view.save_view(doc,'assembly_front.png',frontiso,1850,1500)
    view.save_view(doc,'assembly_rear.png',reariso,1850,1500)
    show(lambda o: getattr(o,'KinematicRole','fixed')=='fixed')
    view.save_view(doc,'rear_interfaces.png',rear,1800,1400)
    show(lambda o: getattr(o,'KinematicRole','fixed')=='fixed' and not o.Name.startswith(('chassis_front_shell','chassis_rear_cover','shoulder_', 'rear_cover_', 'front_shell_')))
    view.save_view(doc,'internal_layout.png',frontiso,2000,1500)
    view.save_view(doc,'internal_rear.png',reariso,2000,1500)
    view.save_view(doc,'internal_top.png',App.Rotation().Q,1800,1600)
    show(lambda o: o in doc.M07.Group)
    view.save_view(doc,'electrical_service_module.png',frontiso,1800,1400)
    show(lambda o: o in doc.M08.Group or o.Name in ('chassis_rear_cover','USB_hub_rear_clamp','DC_charge_replaceable_plate'))
    view.save_view(doc,'rear_cover_inside.png',frontiso,1800,1400)
    show(lambda o: True)
    for o in all_features:
        if getattr(o,'Material','')=='routing_allowance':
            o.ViewObject.Visibility = False
    # Save the full assembly framing, not the preceding rear-cover close-up.
    view.save_view(doc,'assembly_front.png',frontiso,1850,1500)
    doc.save()
    App.closeDocument(doc.Name)
    print('V82_RENDER_COMPLETE',flush=True)


if __name__=='__main__':
    main()
    # All document writes are closed. Avoid the known macOS embedded Qt
    # destructor crash after successful FreeCAD image generation.
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(0)
