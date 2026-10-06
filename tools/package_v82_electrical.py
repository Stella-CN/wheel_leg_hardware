"""Package reviewed CAD, manufacturing files, BOM and source evidence."""
import hashlib
import json
import shutil
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'mechanical/v8_2'
BASE=ROOT/'mechanical/v8_1'


def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    for name,key in [('print_mesh_validation.json','all_passed'),
                     ('electrical_final_validation.json','all_pass'),
                     ('routing_validation.json','all_clear')]:
        data=json.loads((OUT/name).read_text())
        assert data[key], name
    bom=json.loads((OUT/'bom_cad_audit.json').read_text())
    assert not bom['missing'] and not bom['duplicate'], 'BOM coverage'
    assert bom['native_sha256']==digest(OUT/'wheel_leg_v8_2.FCStd'), 'BOM must match final native file'
    illustration=json.loads((OUT/'source/internal_layout_render_source.json').read_text())
    assert illustration['native_sha256']==digest(OUT/'wheel_leg_v8_2.FCStd'), 'Illustration must match final native file'
    source=OUT/'source/electrical'
    source.mkdir(exist_ok=True)
    images = ('switch_user_drawing.png', 'converter_user_drawing.png',
              'wiring_user_drawing.png', 'hub_user_drawing.png')
    provenance=[]
    for name in images:
        p=ROOT/'references/user_supplied'/name
        if p.exists():
            shutil.copy2(p,source/name)
            provenance.append(dict(file=name,original=str(p),sha256=digest(p),authority='User supplied drawing'))
    for p in (ROOT / 'references/user_supplied/3D_PCB1_2026-09-28.step',
              ROOT / 'references/dm-tools/USB2CANFD_Dual/模型/usb2canfd_v2_1-double.stp',
              ROOT / 'references/dm-tools/USB2CANFD_Dual/DM-USB2CANFD_Dual 模块使用说明书 V1.0.pdf'):
        if p.exists():
            shutil.copy2(p,source/p.name)
            provenance.append(dict(file=p.name,original=str(p),sha256=digest(p),authority='Provided model or local manufacturer manual'))
    (source/'provenance.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2)+'\n')
    for name in ('battery_interface.json','imu_interface.json','payload_interfaces.json','display_interface.json','LEG_FITS.md'):
        if (BASE/name).exists():shutil.copy2(BASE/name,OUT/name)
    imu=json.loads((OUT/'imu_interface.json').read_text())
    imu.get('interface',{}).pop('typical_power_mW',None)
    imu.setdefault('interface',{})['maximum_power_mW']=300
    imu['power_consumption_mW_max']=300
    imu['power_consumption_source']='HI13 official datasheet table11 maximum column; not a typical value.'
    (OUT/'imu_interface.json').write_text(json.dumps(imu,ensure_ascii=False,indent=2)+'\n')
    snapshot=OUT/'source/v82_builders'
    snapshot.mkdir(exist_ok=True)
    for p in (ROOT/'tools').glob('*v82*'):
        if p.is_file() and p.suffix in ('.py','.mjs'):shutil.copy2(p,snapshot/p.name)
    summary=dict(revision='V8.2',native_sha256=digest(OUT/'wheel_leg_v8_2.FCStd'),
        native_file='wheel_leg_v8_2.FCStd',physical_bom_objects=bom.get('physical_cad_objects'),
        checked=['Physical geometry preservation and hub module insertion','24-pose leg-motion evidence plus documented final geometric deltas','All print STL topology/bed size','Routing corridors versus rigid solids','BOM per-instance reconciliation'],
        limitations=['Routing is not flexible cable or selected connector qualification','DC jack pilot is not final selected jack hole','Unknown switch DC rating/converter power/PCB netlist remain open','Not validated for jumping or thermal operation'])
    (OUT/'release_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    archive=ROOT/'mechanical/wheel_leg_v8_2_electrical.zip'
    files=[]
    for p in sorted(OUT.rglob('*')):
        if not p.is_file() or p.suffix in ('.FCBak','.pyc','.tmp') or '__pycache__' in p.parts:continue
        if p.name.endswith('.FCStd.tmp'):continue
        files.append(p)
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in files:z.write(p,Path('v8_2')/p.relative_to(OUT))
    with zipfile.ZipFile(archive) as z:assert z.testzip() is None
    sha=digest(archive)
    archive.with_suffix('.sha256').write_text(sha+'  '+archive.name+'\n')
    print(json.dumps(dict(file=str(archive),files=len(files),bytes=archive.stat().st_size,sha256=sha),indent=2))


if __name__=='__main__':main()
