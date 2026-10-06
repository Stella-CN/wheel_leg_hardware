"""V6 purchased electronics: official Jetson solids and official D435 mesh.

The camera's analytic clearance volume is deliberately separate from its
vendor visualization mesh. Battery and IMU remain stated assumptions.
"""
from __future__ import annotations

import json
import build_printable_robot as cad
import cad_v5_payload as prior

V, Part = cad.V, cad.Part
SOURCE = cad.ROOT / 'mechanical/v6/source'
CAMERA_REAR = 74.95
CAMERA_CENTER_Z = 19.0
CAMERA_FRAME_Z = (11.5,27.5)


def camera_bracket():
    pieces=[cad.box(70.95,-54,CAMERA_CENTER_Z-5,3,108,10)]
    for y in (-50,50):
        for z in CAMERA_FRAME_Z:
            pieces.append(cad.box(70.95,y-4,z-4,26.05,8,8))
    shape=cad.union(*pieces)
    cuts=[prior.xcyl(1.7,70.8,3.3,y,CAMERA_CENTER_Z) for y in (-22.5,22.5)]
    for y in (-50,50):
        for z in CAMERA_FRAME_Z:
            cuts.extend((prior.xcyl(1.7,70.8,26.4,y,z),
                         prior.xhex(70.8,22.2,y,z,5.8)))
    return cad.cut(shape,*cuts)


def camera_hardware():
    items=prior.camera_hardware()[2:]
    for _,shape,_ in items:
        shape.translate(V(0,0,CAMERA_CENTER_Z-prior.CAMERA_CENTER_Z))
    for i,y in enumerate((-22.5,22.5)):
        screw=cad.union(prior.xcyl(1.5,70.95,6,y,CAMERA_CENTER_Z),
                        prior.xcyl(2.75,67.95,3,y,CAMERA_CENTER_Z))
        shim=cad.cut(prior.xcyl(4,73.95,1,y,CAMERA_CENTER_Z),
                     prior.xcyl(1.7,73.85,1.2,y,CAMERA_CENTER_Z))
        items.extend(((f'D435_rear_M3x6_{i}',screw,'fixed'),
                      (f'D435_depth_shim_1mm_{i}',shim,'fixed')))
    return items


def jetson():
    shape = Part.Shape()
    shape.read(str(SOURCE / 'jetson/jetson_devkit_solids.brep'))
    shape.rotate(V(), V(0, 0, 1), 90)
    # The source BRep control-box minimum is below the actual plastic foot.
    # Its real bottom datum is -4.9mm, so +37.9 puts it onto the Z33 tray.
    shape.translate(V(1.66325103033625, -46, 37.9))
    return shape


def payloads():
    old = prior.payloads()
    camera=cad.box(CAMERA_REAR,-45.075,CAMERA_CENTER_Z-12.575,100-CAMERA_REAR,90.15,25.15)
    camera=cad.cut(camera,*(prior.xcyl(1.6,CAMERA_REAR-.1,3.1,y,CAMERA_CENTER_Z)
                            for y in (-22.5,22.5)))
    return [
        ('Jetson_Orin_Nano_official', jetson(), 175,
         'NVIDIA official P3766 developer-kit STEP, 20230320 release. '
         'Includes carrier, SOM envelope, heatsink/fan and base. '
         'Only source solids retained; auxiliary open surfaces excluded. '
         'Mass is manufacturer complete-kit nominal, not uniform CAD density.'),
        ('D435_clearance_envelope', camera, 75,
         'Analytic clearance and mass proxy from manufacturer dimensions. '
         'Hidden in final assembly; official ROS camera mesh is shown separately. '
         'Rear 2x M3 spacing45, maximum engagement3mm. This assembly uses '
         '2018 ROS rear datum X74.95 with removable1mm shims; newer26.05mm '
         'datasheet configuration removes shims and uses M3x5.'),
        *old[2:],
    ]


def install_camera_mesh(doc):
    import Mesh
    proxy = doc.getObject('D435_clearance_envelope')
    proxy.addProperty('App::PropertyString', 'ExportRole', 'Manufacturing')
    proxy.ExportRole = 'collision_and_mass_proxy_only'
    if cad.App.GuiUp:
        proxy.ViewObject.Visibility = False
    obj = doc.addObject('Mesh::Feature', 'D435_official_ROS_mesh')
    obj.Label = 'D435 official ROS visualization mesh'
    obj.Mesh = Mesh.Mesh(str(SOURCE / 'd435/d435_official_ros_mm.stl'))
    matrix = cad.App.Matrix(0,0,1,100, 1,0,0,0, 0,1,0,CAMERA_CENTER_Z, 0,0,0,1)
    obj.Placement = cad.App.Placement(matrix)
    obj.addProperty('App::PropertyString', 'Source', 'Manufacturing')
    obj.Source = 'https://github.com/realsenseai/realsense-ros/blob/ros2-master/realsense2_description/meshes/d435.dae'
    obj.addProperty('App::PropertyString', 'Material', 'Manufacturing')
    obj.Material = 'Purchased camera visualization; mass assigned to hidden proxy'
    doc.PurchasedParts.addObject(obj)
    doc.recompute()
    doc.save()


def export_notes():
    prior.export_notes()
    target = cad.OUT / 'payload_interfaces.json'
    data = json.loads(target.read_text())
    data['status'] = 'Official Jetson STEP solids + official D435 ROS mesh; camera analytic clearance volume checked independently'
    data['jetson'].update(dict(
        source='https://developer.nvidia.com/downloads/assets/embedded/secure/jetson/orin_nano/docs/jetson_orin_nano_devkit_3d_step_model.zip/',
        model_revision='20230320, P3766-P3768SKU4-P3767ENVELOPE',
        model_dimensions_mm=[103.379004121345,91.052502061514,34.90451112444],
        mounting_bottom_plane_z_mm=33,
        top_z_mm=67.766,
        vertical_translation_mm=37.9,
        source_solids=1393,
        mounting='Retain original plastic base; removable perimeter retention and tray, not assumed through-base holes'))
    data['d435'].update(dict(
        envelope_dimensions=[90.15,25.15,25.05],
        selected_screw='M3x6 with 1mm removable metal shim',
        bracket_grip=4,
        nominal_insertion=2,
        rear_mounting_plane_x=74.95,
        center_z=CAMERA_CENTER_Z,
        chassis_bracket_holes_z=CAMERA_FRAME_Z,
        bracket_contact_plane_x=73.95,
        model_drawing_difference='2018 official ROS mesh depth25.05 versus 2025 manufacturer drawing26.05; no mesh scaling used',
        alternate_current_drawing_configuration='Remove1mm shims and selectM3x5 for26.05mm-deep camera; nominal engagement2mm. Measure supplied hardware before installation.',
        official_CAD_source='https://dev.realsenseai.com/download/41950',
        official_CAD_format='D435_Solid.SLDPRT; retained as supplied, not read by this FreeCAD installation',
        assembly_visual_source='https://github.com/realsenseai/realsense-ros/blob/ros2-master/realsense2_description/meshes/d435.dae',
        model_in_FCStd_and_STL='Official ROS mesh, original metres converted to mm; not a reverse-engineered box',
        STEP_representation='Conservative analytic clearance volume; official SolidWorks source provided separately'))
    data['limits'] = ('Actual USB/DC plug shapes and strain relief, battery envelope, IMU mounts and thermal airflow '
                      'require selected components and physical validation. Visual mesh is not a machining datum.')
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n')
    shim=cad.cut(prior.xcyl(4,0,1,0,0),prior.xcyl(1.7,-.1,1.2,0,0))
    shim.exportStep(str(cad.OUT/'metal_hardware/D435_depth_shim_D8_d3p4_t1.step'))
    hardware_path=cad.OUT/'metal_hardware/specification.json'
    hardware=json.loads(hardware_path.read_text())
    hardware=[row for row in hardware if row['part']!='D435_depth_shim_D8_d3p4_t1']
    hardware.append(dict(part='D435_depth_shim_D8_d3p4_t1',quantity=2,
                         material='steel shim',outer_diameter=8,inner_diameter=3.4,
                         thickness=1,
                         assembly='Used with 25.05mm camera model and M3x6; remove for26.05mm camera and use M3x5'))
    hardware_path.write_text(json.dumps(hardware,indent=2)+'\n')
