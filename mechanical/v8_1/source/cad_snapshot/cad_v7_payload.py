"""V7 purchased components and rigid HI13R2 mounting bridge."""
from __future__ import annotations

import json
import math
import build_printable_robot as cad
import cad_v6_payload as previous
import cad_v7_imu as imu
import cad_v7_display as display

V, Part = cad.V, cad.Part
CAMERA_SHIFT = V(22, 0, 69)


def moved(shape, offset=CAMERA_SHIFT):
    result=shape.copy(); result.translate(offset)
    return result


def camera_bracket():
    return moved(previous.camera_bracket())


def zcyl(r,z,h,x,y):
    return Part.makeCylinder(r,h,V(x,y,z))


def zhex(x,y,z,h,af):
    r=af/math.sqrt(3)
    pts=[V(x+r*math.cos(math.radians(30+i*60)),
           y+r*math.sin(math.radians(30+i*60)),z) for i in range(6)]
    return Part.Face(Part.makePolygon(pts+[pts[0]])).extrude(V(0,0,h))


def imu_bridge():
    # Integral CNC portal bolted directly to the two metal hip frames.
    pieces=[cad.box(-18,-71.5,76,36,143,3)]
    for sy in (-1,1):
        y0=64.5 if sy>0 else -71.5
        pieces.append(cad.box(-18,y0,47,36,7,3))
        for x in (-18,14):
            pieces.append(cad.box(x,y0,50,4,7,26))
    shape=cad.union(*pieces)
    cuts=[zcyl(1.35,75.8,3.4,p.x,p.y) for p in imu.mount_holes()]
    for sy in (-1,1):
        for x in (-10,10):cuts.append(zcyl(1.7,46.8,3.4,x,68*sy))
        # Rounded, open windows keep the centre datum pad and two side rails.
        y0=16 if sy>0 else -60
        window=cad.box(-7,y0,75.8,14,44,3.4)
        window=cad.union(window,zcyl(3,75.8,3.4,-7,y0+3),
                         zcyl(3,75.8,3.4,7,y0+3),
                         zcyl(3,75.8,3.4,-7,y0+41),
                         zcyl(3,75.8,3.4,7,y0+41),
                         cad.box(-10,y0+3,75.8,20,38,3.4))
        cuts.append(window)
    return cad.cut(shape,*cuts)


def imu_hardware():
    items=[]
    for i,p in enumerate(imu.mount_holes()):
        screw=cad.union(zcyl(1.25,73.4,16,p.x,p.y),zcyl(2.25,89.4,2.5,p.x,p.y))
        nut=cad.cut(zhex(p.x,p.y,74,2,5),zcyl(1.25,73.9,2.2,p.x,p.y))
        items += [(f'HI13R2_M2p5x16_{i}',screw,'fixed'),(f'HI13R2_M2p5_nut_{i}',nut,'fixed')]
    for i,(x,y) in enumerate(( (x,y) for x in (-10,10) for y in (-68,68) )):
        # Show free grip only; the5mm threaded engagement is specified, not
        # intersected with the D2.5 tapping pilot as a false clash.
        screw=cad.union(zcyl(1.5,47,3,x,y),zcyl(2.75,50,3,x,y))
        items.append((f'IMU_bridge_M3x8_{i}',screw,'fixed'))
    return items


def designs():
    return {'D435_embedded_bracket':camera_bracket(),'HI13R2_rigid_bridge':imu_bridge(),
            **display.designs()}


def materials():
    return {name:('CNC' if name=='HI13R2_rigid_bridge' else 'PETG') for name in designs()}


def hardware():
    return [(name,moved(shape),role) for name,shape,role in previous.camera_hardware()]+imu_hardware()+display.hardware()


def payloads():
    existing=previous.payloads()
    camera=existing[1]
    return [existing[0],(camera[0],moved(camera[1]),camera[2],camera[3]+' V7 frontX122, centreZ88.'),
            existing[2],imu.payload(),display.payload()]


def install_camera_mesh(doc):
    previous.install_camera_mesh(doc)
    obj=doc.getObject('D435_official_ROS_mesh')
    obj.Placement.Base += CAMERA_SHIFT
    doc.recompute(); doc.save()


def export_notes(out):
    # Reuse device provenance while updating all moved camera datums.
    previous.export_notes()
    path=out/'payload_interfaces.json'
    data=json.loads(path.read_text())
    data['d435'].update(rear_mounting_plane_x=96.95,center_z=88,
        chassis_bracket_holes_z=[80.5,96.5],bracket_contact_plane_x=95.95,
        front_face_x=122)
    data['imu']=imu.interface_data()
    data['display']=dict(file='display_interface.json',mass_g=265,model='user-dimensional envelope')
    data['limits']='Screen lug datums and plugs, all cable routing, actual battery and thermal airflow remain unverified. HI13R2 is official STEP at manufacturer nominal datum.'
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    display.export_notes(out)
    (out/'imu_interface.json').write_text(json.dumps(imu.interface_data(),ensure_ascii=False,indent=2)+'\n')
    (out/'IMU.md').write_text('\n'.join([
        '# HI13R2 安装与坐标','',
        '采用超核官方HI13XX-USB STEP，原始两实体完整导入，不缩放、不镜像。型号HI13R2-USB-000，'
        '26×24×12mm（铝壳主体24×24×12），质量按厂商<11g取11g预算。','',
        '厂家规格书Rev1.5图9红点给出名义IMU位置：距壳体平面两边各12mm、距底6mm。'
        'CAD将该点放在**(X0,Y0,Z85)mm**，与左右髋轴中点的俯视投影重合；安装底面Z79。'
        '这是底盘运动学中心，并非修改外形后不规则轮廓的面积重心。官方尺寸公差和实际装配误差仍需标定。','',
        'IMU通过2颗M2.5×16和桥下M2.5螺母固定于3mm铝合金桥板，孔心(+10.1,−10.1)、(−10.1,+10.1)，'
        '设备孔Ø2.6，桥孔Ø2.7。CNC桥用4颗M3×8直接固定到金属侧框，入口X±10/Y±68/Z47，'
        '夹持3mm，名义入牙5mm，侧框底孔深6mm。'
        '桥板Z76..79，主机最高约Z67.766，名义垂向间隙8.234mm。','',
        'Type-C朝−X。厂家默认RFU轴在现有数值CAD坐标中为Xs→+Y、Ys→−X、Zs→+Z；'
        '向量变换 R=[[0,−1,0],[1,0,0],[0,0,1]]。姿态四元数还需明确世界/机体约定，不能仅交换欧拉角。'
        'R2为加速度计＋陀螺仪，无磁力计。','',
        '设计为刚性安装，不在控制IMU下默认添加软垫。桥上方开窗/通风不代表热验证，'
        '线材弯曲半径、振动传递和Jetson风扇气流均需实物验证。','',
        '[官方机械资料与来源](source/hi13r2/PROVENANCE.md) · [完整坐标参数](imu_interface.json)'])+'\n')
