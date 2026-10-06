"""Document added V8 purchased fasteners; no invented display mounting holes."""
import json
import build_rounded_robot as build
import cad_v8_chassis as chassis


def main():
    out=build.cad.ROOT/'mechanical/v8/metal_hardware';out.mkdir(exist_ok=True)
    rows=dict(
        display_interface='../display_interface.json',
        added_standard_hardware=[
            dict(part='M3x22 socket head (or M3x25 shortened to22)',quantity=4,location='front panel to screen metal-case cradle'),
            dict(part='M3 hex nut AF5.5/t2.4',quantity=4,location='screen cradle captive pockets'),
            dict(part='M3x12 socket head',quantity=4,location='complete front face to shell'),
            dict(part='M3 hex nut AF5.5/t2.4',quantity=4,location='shell front-face bosses'),
            dict(part='M3x8 socket head',quantity=4,location='IMU bridge feet',grip_mm=3,engagement_mm=5),
            dict(part='M2.5x16 socket head',quantity=2,location='HI13R2'),
            dict(part='M2.5 hex nut AF5/t2',quantity=2,location='under IMU bridge'),
            dict(part='Compliant adhesive pad 4x8x0.5mm',quantity=4,location='screen case rear corner contacts',modelled=False)],
        chassis_fasteners=chassis.fastener_specification(),
        limitations='Screen manufacturer holes absent from datasheet: no screw enters device. Confirm four front stops land on metal rather than glass. Final cable/plug sizes require measurement; unmodelled threaded engagement stays per mechanical fastener schedule.')
    (out/'v8_additions.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
    print('V8_ADDED_HARDWARE_EXPORTED')


if __name__=='__main__':main()
