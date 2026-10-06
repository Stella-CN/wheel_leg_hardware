"""Export every custom part for a non-powered, nominal-geometry FDM fit trial.

Run with the installed FreeCAD Python. Purchased devices and standard hardware
are deliberately not tessellated. Each SKU has one STL; quantity is explicit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil

import build_printable_robot as cad

ROOT = Path(__file__).resolve().parents[1]
V, App, Part = cad.V, cad.App, cad.Part
CUSTOM = {"定制金属件", "3D打印件"}
BED = (220., 220., 250.)
MODULE_DIRS = {
    "M01": "01_left_leg", "M02": "02_right_leg",
    "M01、M02": "00_shared_leg_parts", "M03": "03_chassis",
    "M04": "04_electronics_bay", "M05": "05_front_face",
    "M06": "06_shell", "M07": "07_service_carrier",
    "M08": "08_rear_usb",
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dims(shape):
    b = shape.BoundBox
    return [b.XLength, b.YLength, b.ZLength]


def bottom_area(shape):
    """Planar contact area only; this is not a slicer support calculation."""
    z = shape.BoundBox.ZMin
    return sum(f.Area for f in shape.Faces
               if f.BoundBox.ZLength < 1e-5
               and abs(f.BoundBox.ZMin-z) < .01)


def orient(shape, part_id):
    # Open shell service edges are selected intentionally. Remaining parts use
    # their largest axis-aligned planar contact face; never scale a fit model.
    prescribed = {"P05": ((0, 1, 0), -90), "P06": ((0, 1, 0), 90)}
    choices = [prescribed[part_id]] if part_id in prescribed else [
        ((1, 0, 0), 0), ((1, 0, 0), 90), ((1, 0, 0), -90),
        ((1, 0, 0), 180), ((0, 1, 0), 90), ((0, 1, 0), -90),
    ]
    candidates = []
    for axis, angle in choices:
        for yaw in (0, 90):
            copy = shape.copy()
            copy.rotate(V(), V(*axis), angle)
            copy.rotate(V(), V(0, 0, 1), yaw)
            d = dims(copy)
            if any(x > limit + 1e-5 for x, limit in zip(d, BED)):
                continue
            contact = bottom_area(copy)
            candidates.append(((round(contact, 4), -d[2], -yaw), copy,
                               dict(axis=list(axis), angle_deg=angle,
                                    yaw_deg=yaw, planar_contact_area_mm2=round(contact, 3))))
    if not candidates:
        raise ValueError(f"{part_id}: no allowed orientation fits {BED}")
    _, best, rotation = max(candidates, key=lambda item: item[0])
    b = best.BoundBox
    translation = [-b.XMin, -b.YMin, -b.ZMin]
    best.translate(V(*translation))
    rotation["translation_mm"] = translation
    rotation["basis"] = ("Service split edge on bed; internal removable support required"
                          if part_id in prescribed else
                          "Largest axis-aligned planar contact face; support still requires slicer review")
    return best, rotation


def profile(part_id):
    if part_id == "LC05":
        return dict(layer_mm=.20, first_layer_mm=.20, perimeters=3,
                    infill_percent=100, support="禁用支撑；仅0.20mm厚，单层试片",
                    fit_note="精密薄片打印成功率低；不能加厚。优先同厚PET/钢薄片裁切替代；本件仍提供名义STL。")
    if part_id.startswith("LC"):
        return dict(layer_mm=.10, first_layer_mm=.10, perimeters=4,
                    infill_percent=100, support="平面朝下；轴孔与小凸肩处避免支撑残留",
                    fit_note="仅手动形状试装；小孔复测，打印螺纹/0.05mm游隙不作为验收依据。")
    if part_id in {"P05", "P06", "P07", "P08", "P30"}:
        return dict(layer_mm=.20, first_layer_mm=.20, perimeters=4,
                    infill_percent=20, support="按切片悬空区生成可拆支撑；手指开口、内台阶和螺母槽须清理",
                    fit_note="外壳只轻拧；前手为固定外观件，不作把手或支承点。")
    return dict(layer_mm=.16, first_layer_mm=.20, perimeters=4,
                infill_percent=30, support="必要时局部可拆支撑；禁止将支撑留在轴承座/止口/叉耳之间",
                fit_note="关节座、销孔、止口及螺纹须校准和手工后处理；不以塑料试件判断金属配合公差。")


def export_mesh(shape, path):
    mesh = cad.MeshPart.meshFromShape(Shape=shape, LinearDeflection=.025,
                                     AngularDeflection=.12, Relative=False)
    mesh.write(str(path))
    check = cad.Mesh.Mesh(str(path))
    b = check.BoundBox
    checks = dict(closed=check.isSolid(), non_manifold=check.hasNonManifolds(),
                  self_intersections=check.hasSelfIntersections(),
                  inconsistent_normals=check.hasNonUniformOrientedFacets(),
                  on_bed=abs(b.ZMin) < 1e-4,
                  fits_bed=all(a <= c+1e-4 for a, c in zip(dims(check), BED)),
                  facets=check.CountFacets,
                  dimensions_mm=[round(v, 4) for v in dims(check)])
    checks["passed"] = (checks["closed"] and checks["on_bed"] and checks["fits_bed"]
                        and not any(checks[k] for k in
                                    ("non_manifold", "self_intersections", "inconsistent_normals")))
    if not checks["passed"]:
        raise ValueError(f"Invalid print mesh {path.name}: {checks}")
    return checks


def calibration_coupon(out):
    """Optional coupon. It is not a new robot part or a global compensation."""
    shape = cad.box(0, 0, 0, 108, 92, 4)
    holes = []
    for yi, extra in enumerate((0., .15, .30)):
        for x, nominal in zip((14, 37, 60, 90), (4, 6, 8, 19)):
            y = 15 + 29*yi
            actual = nominal + extra
            holes.append(dict(x_mm=x, y_mm=y, nominal_mm=nominal,
                              diameter_mm=actual, diameter_addition_mm=extra))
            shape = cad.cut(shape, Part.makeCylinder(actual/2, 6, V(x, y, -1)))
    # Asymmetric notch makes +Y and the rows identifiable after removal.
    shape = cad.cut(shape, cad.box(0, 87, -1, 5, 5, 6))
    folder = out/'00_optional_calibration'
    folder.mkdir(exist_ok=True)
    path = folder/'CALI_hole_coupon_108x92_x01.stl'
    checks = export_mesh(shape, path)
    config = dict(file=str(path.relative_to(out)), quantity=1, holes=holes,
                  orientation="槽口朝左上：下/中/上排分别增加直径0/.15/.30；从左到右名义4/6/8/19mm",
                  note="先用同一喷嘴/材料/参数测试；与实际标准销、轴承比较。不能将某孔结果用作整件缩放比例。",
                  validation=checks)
    (folder/'孔位说明.json').write_text(json.dumps(config, ensure_ascii=False, indent=2)+'\n')
    return config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', default='mechanical/v8_3')
    parser.add_argument('--out', default='mechanical/v8_3_print_trial')
    args = parser.parse_args()
    source, out = ROOT/args.source, ROOT/args.out
    out.mkdir(parents=True, exist_ok=True)
    (out/'STEP_reference').mkdir(exist_ok=True)
    source_bom = source/'bom_master.json'
    data = json.loads(source_bom.read_text())
    native = source/f'wheel_leg_{source.name}.FCStd'
    initial_native = sha(native) if native.exists() else None
    rows, validation = [], []
    for row in data['rows']:
        if row['supply_type'] not in CUSTOM:
            continue
        source_step = source/row['source']
        if not source_step.is_file():
            raise FileNotFoundError(source_step)
        original = Part.read(str(source_step))
        if not original.isValid() or len(original.Solids) != 1:
            raise ValueError(f"{row['id']}: expected one valid solid")
        oriented, rotation = orient(original, row['id'])
        if abs(oriented.Volume-original.Volume) > max(1e-4, original.Volume*1e-8):
            raise ValueError('Orientation changed solid volume')
        folder = out/'STL'/MODULE_DIRS[row['module']]
        folder.mkdir(parents=True, exist_ok=True)
        stem = f"{source_step.stem}_x{row['quantity']:02d}"
        path = folder/f'{stem}.stl'
        checks = export_mesh(oriented, path)
        reference = out/'STEP_reference'/source_step.name
        shutil.copy2(source_step, reference)
        info = {k: row[k] for k in ('id', 'module', 'name', 'quantity', 'material', 'process', 'supply_type')}
        info.update(stl=str(path.relative_to(out)), source_step=str(source_step),
                    source_step_sha256=sha(source_step),
                    reference_step=str(reference.relative_to(out)), stl_sha256=sha(path),
                    nominal_volume_mm3=original.Volume, orientation=rotation,
                    print_profile=profile(row['id']), validation=checks,
                    geometry_changed=False, scale=1., model_instances=row.get('model_instances', []))
        rows.append(info)
        validation.append(dict(id=row['id'], **checks))
        print('PRINT_EXPORT', row['id'], row['quantity'], checks['dimensions_mm'], flush=True)
    expected = [r for r in data['rows'] if r['supply_type'] in CUSTOM]
    assert len(rows)==len(expected) and len({r['id'] for r in rows})==len(rows)
    assert all(r['quantity'] > 0 for r in rows)
    assert not native.exists() or sha(native)==initial_native
    calibration = calibration_coupon(out)
    manifest = dict(revision='V8.3 printing fit trial', units='mm', print_bed_mm=list(BED),
                    nozzle_mm=.4, material='PETG', scale=1., support_generated=False,
                    intended_use='Unpowered supported manual assembly trial only; no standing, powered motion or jumping',
                    source_bom_sha256=sha(source_bom), native_sha256=initial_native,
                    source_native=str(native), part_types=len(rows),
                    required_pieces=sum(r['quantity'] for r in rows), rows=rows,
                    calibration=calibration,
                    excluded='Purchased motors/electronics/tyres/standard screws, nuts, washers, bearings, dowels and routing placeholders')
    (out/'print_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n')
    (out/'print_validation.json').write_text(json.dumps(dict(all_passed=all(r['passed'] for r in validation),
        records=validation, part_types=len(rows), required_pieces=manifest['required_pieces'],
        scope='STL topology, nominal dimensions, rigid reorientation and build-volume checks; not a slicer/support/strength qualification'),
        ensure_ascii=False, indent=2)+'\n')
    print('PRINT_PACKAGE_GEOMETRY_READY', len(rows), manifest['required_pieces'], flush=True)


if __name__ == '__main__':
    main()
