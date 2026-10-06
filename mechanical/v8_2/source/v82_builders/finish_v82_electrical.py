"""Add explicit routing allowances and export the reviewed V8.2 geometry.

Routes indicate cable corridors, not validated connector/pin geometry. They
are excluded from purchase counts and from the assembled solid STEP/STL.
"""
from __future__ import annotations
import hashlib
import json
import shutil
import sys

import build_printable_robot as cad

App,Part,V = cad.App,cad.Part,cad.V
OUT = cad.ROOT/'mechanical/v8_2'


def tube(points,radius):
    vectors = [V(*p) for p in points]
    pieces = [Part.makeSphere(radius,p) for p in vectors]
    for p,q in zip(vectors,vectors[1:]):
        d=q-p
        pieces.append(Part.makeCylinder(radius,d.Length,p,d))
    return Part.makeCompound(pieces)


def main():
    cad.configure(OUT)
    doc=App.openDocument(str(OUT/'wheel_leg_v8_2.FCStd'))
    group=doc.getObject('Routing') or doc.addObject('App::DocumentObjectGroup','Routing')
    group.Label='走线路径预留（示意，非成品线束）'
    routes=[
        ('POWER_BAT_SWITCH',2.,[(43,0,26),(51,0,26),(51,0,47),(60,0,52)],
         '电池插头区域→托盘D10护线孔→顶部开关；电池真实座位置未给，起点为区域边界。'),
        ('POWER_CHARGE_BRANCH',2.,[(43,0,26),(46,-24,26),(-48,-24,26),(-49,-24,-25),(-73,-46,-25),(-90,-46,-25)],
         '总开关前充电支路，沿电池外侧后行；母座及实际分线头待选。'),
        ('POWER_SWITCH_PCB',2.,[(61,1,53),(70,10,47),(70,20,45),(70,21,28)],
         '开关输出→朝上的PCB电源口；含保护/保险位置待电气选型。'),
        ('POWER_DCDC_IN',1.8,[(69,20,43),(69,20,52),(83,20,52),(83,-70,52),(75,-70,56)],
         '开关后母线→侧方转换器，避开主机风扇；模块线根位置尚未标尺寸。'),
        ('POWER_19V_JETSON',1.5,[(25,-65,56),(20,-61,51),(20,-49,49),(28,-49,49),(42,-44,46)],
         '转换器19V输出→Jetson DC5.5x2.5；模块出线根坐标未给，起点为模块外连接区域。'),
        ('CAN_DUAL_PCB',1.8,[(60,0,44),(72,-1,45),(75,-1,20),(70,3,7)],
         '两路CAN通信线到配电板接口区域；实际独立通道/针脚须原理图确认，末端需分线到两座。'),
        ('LEG_LEFT_BUNDLE',3.3,[(70,51,1),(74,54.5,28),(74,54.5,82),(89,62,82),(89,74,54),(89,81,54)],
         '左腿动力+CAN沿托架正Y外缘上升，再从相机支架上方绕至正Y护线孔；机外运动软环需整行程实物布线。'),
        ('LEG_RIGHT_BUNDLE',3.3,[(70,-9,1),(74,0,28),(74,0,82),(74,-62,82),(89,-62,82),(89,-74,54),(89,-81,54)],
         '右腿动力+CAN穿托架10mm中央槽上升，从转换器上方绕至负Y护线孔；两条总线不得并接，板上接法须按网表确认。'),
        ('USB_HUB_EXTENSION',2.4,[(-77,53,5),(-73,38,14),(-75,25,18),(-75,25,71),(-42,58,71),(10,58,71),(40,44,65),(47,23,56),(45,9.6,52.2)],
         '拓展坞150mm原线+250mm USB-A延长线，沿正Y侧高位绕主机；终点为主机插头尾部预留。'),
        ('USB_CAN',1.5,[(60,-53,44),(57,-56,49),(43,-56,49),(43,-26,52),(43,-7.4,52.2)],
         '裸板Type-C朝负Y；使用低头弯向的短USB数据线；端口真实插头待实配。'),
        ('USB_IMU',1.8,[(43,42,40.2),(47,48,60),(33,42,83),(-20,21,86),(-19,0,85)],
         'Jetson Type-C Host→HI13R2；末端留软弯，传感器不承受线束拉力。'),
        ('USB_CAMERA',2.4,[(44,9.6,43.6),(48,25,54),(83,63,78),(95,62,61),(98,48,61)],
         'D435 USB3直连，沿前上方保留路径；相机插头包络待实配。'),
        ('VIDEO_DISPLAY',2.8,[(43,-27.2,41.9),(45,-18,51),(48,-15,58),(82,-18,52),(91,-25,52),(96,-37,2)],
         'DP转HDMI→屏幕；选短转接线，禁止把长硬转接头塞入预留空间。'),
        ('USB_DISPLAY',2.,[(44,-7.4,43.6),(45,0,50),(49,13,52),(84,17,43),(95,-28,3)],
         '屏幕USB供电/触摸，接口位置以实物为准。'),
    ]
    rows=[]
    for name,radius,points,note in routes:
        old=doc.getObject(name)
        if old: doc.removeObject(old.Name)
        obj=cad.put(doc,group,name,tube(points,radius),'fixed','routing_allowance',None,note)
        obj.addProperty('App::PropertyString','ExportRole','Manufacturing')
        obj.ExportRole='routing_allowance_only'
        length=sum((V(*q)-V(*p)).Length for p,q in zip(points,points[1:]))
        rows.append(dict(name=name,radius_mm=radius,points_xyz_mm=points,
                         polyline_length_mm=round(length,1),note=note))
    doc.recompute()
    # Actual body wall is 3 mm. Future selected bush must match this opening
    # and the required clear cable size; no commercial grommet invented.
    body=doc.chassis_front_shell
    for side in (-1,1):
        tool=Part.makeCylinder(5.,5.,V(89,78*side,54),V(0,side,0))
        body.Shape=cad.cut(body.Shape,tool)
    carrier=doc.electrical_service_carrier
    carrier.Shape=cad.cut(carrier.Shape,Part.makeCylinder(4.3,2.4,V(70,21,35.8)),
                          cad.box(48.,-5.,35.8,29.,10.,2.4))
    assert carrier.Shape.isValid() and len(carrier.Shape.Solids)==1
    # Open rear-edge U slot passes a captive USB cable without trying to
    # push its moulded Type-A connector through a small circular hole.
    tray=doc.electronics_tray
    tray.Shape=cad.cut(tray.Shape,cad.box(-86.2,21.5,29.8,11.2,7.,3.4),
                       Part.makeCylinder(3.5,3.4,V(-75,25,29.8)))
    clamp=doc.USB_hub_rear_clamp
    for y in (-47.,47.):
        clamp.Shape=cad.cut(clamp.Shape,Part.makeCylinder(5.2,5.2,V(-56,y,-.2)))
    (OUT/'routing_allowances.json').write_text(json.dumps(dict(routes=rows,
        body_exit_holes=dict(diameter_mm=10,centre_xz=[89,54],both_sides=True,panel_thickness_mm=3),
        tray_open_slot=dict(centre_xyz=[-75,25,31.5],width_mm=7,open_edge='rear'),
        carrier_central_channel=dict(bounds_xyz_mm=[48,-5,36,77,5,38],width_y_mm=10,
                                     purpose='6.6mm right-leg bundle allowance; 1.7mm nominal lateral margin'),
        scope='Planning corridors only. Polyline corners are not manufactured cable bend radii. Endpoints are plug/connection zones; no wire pinout or flexible-body sweep certification.',
        hub_extension='250mm USB-A male/female data extension in addition to150mm captive lead; bundle or shorten extra slack after fit.'),ensure_ascii=False,indent=2)+'\n')
    if '--routes-only' in sys.argv:
        doc.recompute();doc.save();App.closeDocument(doc.Name)
        print('V82_ROUTES_UPDATED',flush=True)
        return
    manifest=json.loads((OUT/'part_manifest.json').read_text())
    changed=json.loads((OUT/'electrical_build.json').read_text())
    names=changed['changed_existing']+['electrical_service_carrier','USB_hub_rear_clamp','DC_charge_replaceable_plate']
    for name in names:
        o=doc.getObject(name)
        material=o.Material
        if material not in ('PETG','CNC'): raise ValueError((name,material))
        row=cad.export_part(name,o.Shape,material,1,native_z=True)
        manifest=[r for r in manifest if r['part']!=name]+[row]
    (OUT/'part_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    modules=[]
    (OUT/'modules').mkdir(exist_ok=True)
    for key in ('M01','M02','M03','M04','M05','M06','M07','M08'):
        g=doc.getObject(key)
        shapes=[o for o in g.Group if o.TypeId=='Part::Feature']
        Part.export(shapes,str(OUT/'modules'/f'{key}.step'))
        modules.append(dict(id=key,name=g.Label,objects=[o.Name for o in g.Group],STEP=f'modules/{key}.step'))
    (OUT/'module_manifest.json').write_text(json.dumps(dict(modules=modules,scope='Logical preassembly modules; coordinates in mm unchanged'),ensure_ascii=False,indent=2)+'\n')
    solid=[o for o in doc.Objects if o.TypeId=='Part::Feature' and getattr(o,'Material','')!='routing_allowance']
    Part.export(solid,str(OUT/'wheel_leg_assembly.step'))
    Part.export([o for o in solid if o.Material in ('PETG','CNC')],str(OUT/'wheel_leg_structure.step'))
    Part.export(list(group.Group),str(OUT/'wiring_route_reference.step'))
    # Main assembled STL includes imported D435 mesh and excludes its proxy.
    import Mesh,MeshPart
    display_solid=[o.Shape for o in solid if getattr(o,'ExportRole','')!='collision_and_mass_proxy_only']
    mesh=MeshPart.meshFromShape(Shape=Part.makeCompound(display_solid),LinearDeflection=.12,AngularDeflection=.22,Relative=False)
    for obj in doc.Objects:
        if obj.TypeId=='Mesh::Feature': mesh.addMesh(obj.Mesh.copy())
    mesh.write(str(OUT/'wheel_leg_assembly.stl'))
    assert Mesh.Mesh(str(OUT/'wheel_leg_assembly.stl')).CountFacets==mesh.CountFacets
    (OUT/'assembly_stl_report.json').write_text(json.dumps(dict(units='mm',physical_solid_objects=len(solid),
       facets=mesh.CountFacets,purpose='Assembly viewing, not monolithic printing; separate print/*.stl and CNC STEP.',
       excluded=['routing allowance objects','D435 analytic proxy replaced by official mesh'],
       scope='Vendor motor, Jetson, HiPNUC, bareUSB2CAN and distributionPCB solids; dimensioned switch/converter/hub/battery/screen envelopes.'),indent=2)+'\n')
    doc.save()
    App.closeDocument(doc.Name)
    print('V82_EXPORT_COMPLETE',flush=True)


if __name__=='__main__': main()
