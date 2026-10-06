"""V8 GK-HD5 display and moved D435; official Jetson/HI13R2 retained."""
from __future__ import annotations

import json
import shutil
import build_printable_robot as cad
import cad_v6_payload as devices
import cad_v7_payload as bridge
import cad_v7_imu as imu
import cad_v8_display as display

V,Part=cad.V,cad.Part
CAMERA_SHIFT=V(17,0,42)
imu_bridge,imu_hardware=bridge.imu_bridge,bridge.imu_hardware


def moved(shape):
    result=shape.copy();result.translate(CAMERA_SHIFT)
    return result


def camera_bracket():return moved(devices.camera_bracket())


def designs():
    return {'D435_embedded_bracket':camera_bracket(),'HI13R2_rigid_bridge':imu_bridge(),**display.designs()}


def materials():
    return {name:('CNC' if name=='HI13R2_rigid_bridge' else 'PETG') for name in designs()}


def hardware():
    return [(name,moved(shape),role) for name,shape,role in devices.camera_hardware()]+imu_hardware()+display.hardware()


def payloads():
    existing=devices.payloads()
    name,shape,mass,note=existing[1]
    note=note.replace('X74.95','X91.95')+' V8 frontX117, centreZ61.'
    return [existing[0],(name,moved(shape),mass,note),existing[2],imu.payload(),display.payload()]


def install_camera_mesh(doc):
    devices.install_camera_mesh(doc)
    doc.getObject('D435_official_ROS_mesh').Placement.Base+=CAMERA_SHIFT
    doc.recompute();doc.save()


def export_notes(out):
    devices.export_notes()
    path=out/'payload_interfaces.json';data=json.loads(path.read_text())
    # Discard the inherited early envelope: use the installed official BRep.
    data['jetson'].pop('maximum_dimensions',None)
    bounds=devices.jetson().BoundBox
    data['jetson']['placed_BRep_bounds_xyz_mm']=[bounds.XMin,bounds.YMin,bounds.ZMin,bounds.XMax,bounds.YMax,bounds.ZMax]
    data['jetson']['placed_BRep_dimensions_xyz_mm']=[bounds.XLength,bounds.YLength,bounds.ZLength]
    data['jetson']['bounds_basis']='Conservative bounds of installed official solid BRep; actual foot datum, not control-box minimum, is on trayZ33.'
    data['d435'].update(rear_mounting_plane_x=91.95,center_z=61,
        chassis_bracket_holes_z=[53.5,69.5],bracket_contact_plane_x=90.95,front_face_x=117,
        bracket_grip_stack='3mm PETG plus1mm removable metal shim for25.05mm camera',
        alternate_26p05_rear_mounting_plane_x=90.95)
    data['imu']=imu.interface_data()
    data['display']=dict(file='display_interface.json',size_inches=5,
        mass_assumption_g=200,mass_sensitivity_range_g=[100,350],
        mass_source='Not supplied; engineering scenarios only')
    data['limits']='Display active area, mass, casing front-rim contact, plugs and cable geometry await physical measurement. Jetson and HI13R2 use official solid CAD; D435 uses official ROS mesh in FCStd/STL and an analysis envelope in STEP; display/battery are dimensional envelopes.'
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    display.export_notes(out)
    (out/'imu_interface.json').write_text(json.dumps(imu.interface_data(),ensure_ascii=False,indent=2)+'\n')
    shutil.copy2(cad.ROOT/'mechanical/v7/IMU.md',out/'IMU.md')
    shutil.copytree(cad.ROOT/'mechanical/v7/source/hi13r2',out/'source/hi13r2',dirs_exist_ok=True)

