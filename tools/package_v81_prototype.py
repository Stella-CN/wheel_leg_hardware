"""Audit and package the current, reviewed single-prototype deliverables."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'mechanical/v8_1'


def data(name):
    return json.loads((OUT/name).read_text())


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda:source.read(1024*1024),b''):
            h.update(block)
    return h.hexdigest()


def main():
    required=['README.md','MANUFACTURING_LIST.md','MODULE_ASSEMBLY.md','LEG_ASSEMBLY.md',
        'LEG_FITS.md','BODY_ASSEMBLY.md','BATTERY.md','BATTERY_SOURCE_REVIEW.md',
        'MASS.md','MOTOR_LOAD.md','采购与制造BOM.xlsx','BOM完整.csv','制造件分类.csv',
        '标准与目录件采购汇总.csv','wheel_leg_v8_1.FCStd','wheel_leg_assembly.step',
        'wheel_leg_assembly.stl','battery_integration_review.json']
    assert all((OUT/name).is_file() for name in required)
    assert not data('validation.json')['collisions']
    assert data('preserved_geometry_review.json')['all_pass']
    assert data('body_detail_review.json')['pass_all']
    assert data('print_mesh_validation.json')['all_passed']
    assert data('battery_integration_review.json')['all_pass']
    assert not data('module_access_review.json')['failures']
    assert not data('native_hardware_placement_validation.json')['errors']
    audit=data('bom_cad_audit.json')
    assert not audit['missing'] and not audit['duplicate']
    workbook=data('bom_workbook_review.json')
    assert workbook['source_sha256']==sha(OUT/'bom_master.json')
    assert workbook['renderer_review_required'] is False
    assert workbook['standard_types']==20 and workbook['standard_quantity']==238
    for filename,expected in data('baseline_preservation.json')['before'].items():
        assert sha(ROOT/'mechanical/v8'/filename)==expected,filename
    files=[p for p in OUT.rglob('*') if p.is_file() and not any(
        s in p.name for s in ('.FCBak','.FCStd.','.DS_Store','.pyc')) and '__pycache__' not in p.parts]
    files=[p for p in files if p.name not in ('package_manifest.json','package_validation.json')]
    hashes={str(p.relative_to(OUT)):sha(p) for p in files}
    manifest=dict(revision='V8.1',contains_latest_battery_drawing=True,
        source_bom_sha256=sha(OUT/'bom_master.json'),files=hashes)
    (OUT/'package_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    files.append(OUT/'package_manifest.json')
    destination=ROOT/'mechanical/wheel_leg_v8_1_prototype.zip'
    with zipfile.ZipFile(destination,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for path in sorted(files):
            archive.write(path,Path('wheel_leg_v8_1')/path.relative_to(OUT))
    with zipfile.ZipFile(destination) as archive:
        assert archive.testzip() is None
        count=len(archive.infolist())
    report=dict(package=str(destination),file_count=count,bytes=destination.stat().st_size,
        sha256=sha(destination),crc_pass=True,required_deliverables_present=True,
        current_bom_reconciled=True,baseline_v8_unchanged=True)
    (OUT/'package_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
