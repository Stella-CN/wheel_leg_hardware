"""V8.1 payload interfaces: integral D435 backrest and standard screws."""
from __future__ import annotations

import json
import shutil
import build_printable_robot as cad
import cad_v6_payload as devices
import cad_v7_payload as bridge
import cad_v7_imu as imu
import cad_v81_display as display
import cad_v5_payload as primitive
import cad_v81_battery as battery

V,Part=cad.V,cad.Part
CAMERA_SHIFT=V(17,0,42)
imu_bridge,imu_hardware=bridge.imu_bridge,bridge.imu_hardware


def moved(shape):
    result=shape.copy();result.translate(CAMERA_SHIFT)
    return result


def camera_bracket(camera_depth=25.05):
    """One-piece print, selected for measured camera depth; front remains X117.

    The default matches the installed official 2018 ROS model. A 26.05 mm
    replacement is a mutually exclusive print, not an extra assembly part.
    Both use a 6 mm integral grip and an unmodified M3x8 screw (2 mm entry).
    """
    if camera_depth not in (25.05, 26.05):
        raise ValueError('Select measured D435 depth 25.05 or 26.05 mm')
    rear=117.-camera_depth
    back=rear-6.
    pieces=[cad.box(back,-54.,56.,6.,108.,10.)]
    for y in (-50.,50.):
        for z in (53.5,69.5):
            pieces.append(cad.box(back,y-4.,z-4.,114.-back,8.,8.))
    tools=[primitive.xcyl(1.7,back-.1,6.2,y,61.) for y in (-22.5,22.5)]
    for y in (-50.,50.):
        for z in (53.5,69.5):
            tools.extend((primitive.xcyl(1.7,back-.1,114.2-back,y,z),
                          primitive.xhex(back-.1,110.-back+.1,y,z,5.8)))
    return cad.cut(cad.union(*pieces),*tools)


def camera_hardware(camera_depth=25.05):
    back=117.-camera_depth-6.
    rows=[]
    for i,y in enumerate((-22.5,22.5)):
        screw=cad.union(primitive.xcyl(1.5,back,8.,y,61.),
                        primitive.xcyl(2.75,back-3.,3.,y,61.))
        rows.append((f'D435_rear_M3x8_{i}',screw,'fixed'))
    for i,(y,z) in enumerate(( (y,z) for y in (-50.,50.) for z in (53.5,69.5) )):
        screw=cad.union(primitive.xcyl(1.5,107.,10.,y,z),
                        primitive.xcyl(2.75,117.,3.,y,z))
        nut=cad.cut(primitive.xhex(107.6,2.4,y,z,5.5),
                    primitive.xcyl(1.5,107.5,2.6,y,z))
        rows.extend(((f'D435_frame_M3x10_{i}',screw,'fixed'),
                     (f'D435_frame_M3_nut_{i}',nut,'fixed')))
    return rows


def designs():
    return {'D435_embedded_bracket':camera_bracket(),'HI13R2_rigid_bridge':imu_bridge(),**display.designs()}


def materials():
    return {name:('CNC' if name=='HI13R2_rigid_bridge' else 'PETG') for name in designs()}


def hardware():
    return camera_hardware()+imu_hardware()+display.hardware()


def payloads():
    existing=devices.payloads()
    name,shape,mass,note=existing[1]
    note=('V8.1 D435 clearance/mass proxy; official ROS mesh shown separately. '
          'FrontX117, centreZ61, depth25.05, rearX91.95. Integral6mm PETG '
          'backrest with ISO4762 M3x8, nominal insertion2mm/max3mm. '
          'For measured26.05mm device select alternative one-piece bracket; '
          'no loose shims and no cut screws.')
    return [existing[0],(name,moved(shape),mass,note),battery.payload(),imu.payload(),display.payload()]


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
        chassis_bracket_holes_z=[53.5,69.5],bracket_contact_plane_x=91.95,front_face_x=117,
        selected_screw='ISO4762 M3x8',bracket_grip=6.,nominal_insertion=2.,
        bracket_grip_stack='6mm integral PETG backrest; no loose metal shims',
        alternate_26p05_rear_mounting_plane_x=90.95,
        alternate_current_drawing_configuration='Choose D435 bracket26.05 replacement; 6mm grip/backX84.95, same M3x8, nominal insertion2mm. One bracket only in BOM.')
    data['imu']=imu.interface_data()
    data['battery']=battery.interface_data()
    data['display']=dict(file='display_interface.json',size_inches=5,
        mass_assumption_g=200,mass_sensitivity_range_g=[100,350],
        mass_source='Not supplied; engineering scenarios only')
    data['limits']='Display active area, mass, casing front-rim contact, plugs and cable geometry await physical measurement. Jetson and HI13R2 use official solid CAD; D435 uses official ROS mesh in FCStd/STL and an analysis envelope in STEP; display/battery are dimensional envelopes.'
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    display.export_notes(out)
    battery.export_notes(out)
    # The inherited provenance writer also exports the obsolete loose shim.
    # Remove it only from this new revision's artifacts and hardware manifest.
    obsolete=out/'metal_hardware/D435_depth_shim_D8_d3p4_t1.step'
    obsolete.unlink(missing_ok=True)
    spec_path=out/'metal_hardware/specification.json'
    rows=json.loads(spec_path.read_text())
    spec_path.write_text(json.dumps([r for r in rows if r['part']!='D435_depth_shim_D8_d3p4_t1'],indent=2)+'\n')
    alternate=out/'alternates'
    alternate.mkdir(exist_ok=True)
    camera_bracket(26.05).exportStep(str(alternate/'D435_embedded_bracket_depth26p05.step'))
    (out/'imu_interface.json').write_text(json.dumps(imu.interface_data(),ensure_ascii=False,indent=2)+'\n')
    shutil.copy2(cad.ROOT/'mechanical/v7/IMU.md',out/'IMU.md')
    shutil.copytree(cad.ROOT/'mechanical/v7/source/hi13r2',out/'source/hi13r2',dirs_exist_ok=True)
