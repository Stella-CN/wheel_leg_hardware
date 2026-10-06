"""V8: small-radius rectangular body,5in screen face, unchanged V6 legs."""
from __future__ import annotations

import argparse
import json
import shutil
import build_printable_robot as cad
import build_enclosed_robot as wheel
import build_sleeved_robot as native
import cad_v6_leg as leg
import cad_v5_coupling as coupling
import cad_v8_chassis as chassis
import cad_v8_payload as payload


def configure():
    out=cad.ROOT/'mechanical/v8';out.mkdir(parents=True,exist_ok=True)
    p=json.loads((cad.ROOT/'mechanical/v6/design_parameters.json').read_text())
    p.update(revision='v8_rounded_5inch',
        profile='Small R5 rectangular enclosure, removable whole front panel,5in GK-HD and D435',
        imu_origin=[0,0,85],display_center_z=-4,camera_center_z=61,
        display_inches=5,display_mass_assumption_g=200,
        validation_scope='Discrete geometry and load screening; display casing contact/active area/mass/real plugs unverified; no jump or thermal qualification')
    (out/'design_parameters.json').write_text(json.dumps(p,indent=2)+'\n')
    cad.configure(out)
    return out


def components():
    fixed=chassis.build_chassis();fixed.update(payload.designs())
    materials=chassis.materials();materials.update(payload.materials())
    designs={'hip_stator_mount':(chassis.hip_stator_mount(),'fixed','CNC')}
    designs.update(coupling.designs());designs.update(leg.designs())
    designs['wheel_rim']=(wheel.wheel_rim(),'wheel','CNC')
    return fixed,materials,designs,coupling.hardware()+leg.hardware()+chassis.hip_hardware(),chassis.chassis_hardware()+payload.hardware()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--integration-check',action='store_true')
    args=parser.parse_args();out=configure()
    fixed,materials,designs,hardware,global_hardware=components()
    leg.export_hardware();payload.export_notes(out)
    lengths=[100,180,215] if args.integration_check else list(range(100,216,5))
    doc=cad.build(designs,hardware=hardware,
        mirrored_print_parts=tuple(name for name in designs if name!='wheel_rim'),
        hub_offset=cad.P['hub_stator_face_y']-164,
        knee_translation_y=cad.P['knee_motor_translation_y'],
        chassis_parts=fixed,chassis_materials=materials,chassis_process='CNC',
        global_hardware=global_hardware,payloads=payload.payloads(),coupons={},
        reference_stls=True,check_hardware_pairs=True,validation_lengths=lengths)
    native.native_hardware_check(doc,hardware,global_hardware)
    payload.install_camera_mesh(doc);chassis.export_review(out)
    source=cad.ROOT/'mechanical/v7/source/inherited_v6'
    shutil.copytree(source,out/'source/inherited_v6',dirs_exist_ok=True)
    (out/'inherited_subsystems.json').write_text(json.dumps(dict(
        unchanged='V6 legs, motor datums, coupling, wheels; V7 rigid IMU bridge and official devices',
        updated='Rounded body, complete removable front panel, GK-HD5 display support and camera placement',
        historical_evidence='source/inherited_v6; subsystem evidence only'),indent=2)+'\n')
    print('V8_BUILD_COMPLETE',flush=True)


if __name__=='__main__':main()
