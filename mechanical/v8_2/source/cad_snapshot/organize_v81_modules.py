"""Create a modular FreeCAD tree and independently aligned module STEP files."""
from __future__ import annotations

import json
import build_printable_robot as cad

OUT = cad.ROOT / 'mechanical/v8_1'
MODULES = {
    'M01': '左腿预装总成', 'M02': '右腿预装总成',
    'M03': '承力机架与总装接口件', 'M04': '电器仓子模块',
    'M05': '屏幕相机前脸总成', 'M06': '外壳套件',
}


def module_for(name):
    if name.startswith(('hip_case_M4_washer_', 'hip_case_M4_nut_')):
        return 'M03'  # Fit during final joining, never trap nuts in a leg first.
    if name.startswith(('shoulder_', 'front_shell_', 'rear_cover_', 'front_face_M3_nut_')):
        return 'M06'
    if name in ('chassis_front_shell', 'chassis_rear_cover'):
        return 'M06'
    if name.startswith(('display_', 'Display_', 'D435_', 'front_face_M3x')):
        return 'M05'
    if name.startswith(('HI13', 'IMU_', 'Jetson_', 'Battery_', 'battery_', 'electronics_')):
        return 'M04'
    if name.startswith(('chassis_', 'belly_frame_', 'crossframe_')):
        return 'M03'
    if name.endswith('_left'):
        return 'M01'
    if name.endswith('_right'):
        return 'M02'
    raise ValueError(f'Unclassified assembly item: {name}')


def snapshot(obj):
    shape = obj.Shape if obj.TypeId == 'Part::Feature' else obj.Mesh
    bb = shape.BoundBox
    return dict(bounds=[getattr(bb, a) for a in ('XMin', 'YMin', 'ZMin', 'XMax', 'YMax', 'ZMax')],
                expressions=list(obj.ExpressionEngine))


def main():
    doc = cad.App.openDocument(str(OUT / 'wheel_leg_v8_1.FCStd'))
    doc.Parameters.LegLength = 180
    doc.Parameters.Beta = 0
    doc.recompute()
    features = [o for o in doc.Objects if o.TypeId in ('Part::Feature', 'Mesh::Feature')]
    before = {o.Name: snapshot(o) for o in features}
    doc.Robot.Group = []
    doc.PurchasedParts.Group = []
    groups = {}
    for key, label in MODULES.items():
        group = doc.getObject(key) or doc.addObject('App::DocumentObjectGroup', key)
        group.Label = f'{key} {label}'
        group.Group = []
        doc.Robot.addObject(group)
        groups[key] = group
    for obj in features:
        key = module_for(obj.Name)
        groups[key].addObject(obj)
        if 'AssemblyModule' not in obj.PropertiesList:
            obj.addProperty('App::PropertyString', 'AssemblyModule', 'Manufacturing')
        obj.AssemblyModule = f'{key} {MODULES[key]}'
    doc.recompute()
    after = {o.Name: snapshot(o) for o in features}
    for name, previous in before.items():
        current = after[name]
        assert previous['expressions'] == current['expressions'], name
        assert max(abs(a-b) for a, b in zip(previous['bounds'], current['bounds'])) < 1e-6, name
    destination = OUT / 'modules'
    destination.mkdir(exist_ok=True)
    rows = []
    for key, group in groups.items():
        # STEP uses the documented D435 analysis solid; native mesh is visual.
        solids = [o for o in group.Group if o.TypeId == 'Part::Feature']
        cad.Part.export(solids, str(destination / f'{key}.step'))
        rows.append(dict(id=key, name=MODULES[key], objects=[o.Name for o in group.Group],
                         STEP=f'modules/{key}.step', placement='Shared robot coordinates, mm; do not recenter separately'))
    (OUT/'module_manifest.json').write_text(json.dumps(dict(
        modules=rows, regrouping_preserves_geometry_and_expressions=True,
        scope='Logical assembly/service modules, not automatic physical mating constraints. External shells are installed sequentially.'), ensure_ascii=False, indent=2)+'\n')
    doc.save()
    cad.App.closeDocument(doc.Name)
    print('V81_MODULES_EXPORTED', flush=True)


if __name__ == '__main__':
    main()
