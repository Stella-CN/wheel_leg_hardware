"""Export V7 added custom metal washers/spacers and their purchase notes."""
import json
import build_faceted_robot as build
import cad_v7_display as display
import cad_v7_payload as payload
import cad_v7_chassis as chassis


def main():
    cad=build.cad;cad.configure(cad.ROOT/'mechanical/v7')
    out=cad.OUT/'metal_hardware';out.mkdir(exist_ok=True)
    items={name:shape for name,shape,_ in display.hardware()}
    custom=[('display_adjustable_washer_0','display_washer_14x14_t1_d2p8',4),
            ('display_spacer_D8_d3_t2_0','display_spacer_D8_d3_t2',4)]
    for source,name,qty in custom:
        shape=items[source].copy();b=shape.BoundBox
        shape.translate(cad.V(-b.XMin,-b.YMin,-b.ZMin))
        shape.exportStep(str(out/(name+'.step')))
    notes=dict(custom_metal=[dict(part=name,quantity=qty,source_assembly_part=source,
                                  material='steel washer/spacer; dimensional review before purchase')
                            for source,name,qty in custom],
        added_standard_hardware=[
            dict(part='M3x16 socket head',quantity=6,location='display bezel/shell/carriers'),
            dict(part='M3 hex nut',quantity=6,location='display carriers'),
            dict(part='M2.5 through screw, length TBD',quantity=4,location='screen mounting ears',
                 status='Not modelled: measure actual lug thickness/plane first'),
            dict(part='M2.5 locking nut',quantity=4,location='screen mounting ears',status='length/access selection pending'),
            dict(part='M3x8 socket head',quantity=4,location='IMU bridge to metal sideframes',grip_mm=3,thread_engagement_mm=5),
            dict(part='M2.5x16 socket head',quantity=2,location='HI13R2',head_diameter_mm=4.5,head_height_mm=2.5),
            dict(part='M2.5 nut, AF5/thickness2',quantity=2,location='under IMU bridge')],
        chassis_fasteners=chassis.fastener_specification(),
        limitations='Visible thread engagement may be omitted in reference solids. Screen fastener lengths are deliberately unresolved; do not infer from the20mm enclosure depth.')
    (out/'v7_additions.json').write_text(json.dumps(notes,ensure_ascii=False,indent=2)+'\n')
    print('V7_ADDED_HARDWARE_EXPORTED')


if __name__=='__main__':main()
