"""Verify the official plastic-base datum and peripheral capture independently."""
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
import cad_v6_jetson_mount as mount
import cad_v6_payload as payload
import cad_v5_chassis as prior

kit = mount.official_kit()
payload_kit = payload.jetson()
base = kit.Solids[1266]
tray = prior._electronics_tray().cut(mount.Part.makeCompound(mount.tray_hole_tools())).removeSplitter()
retainers = mount.designs()
report = dict(
    scope="True official-base contact at Z33 and sampled translation capture; final reshaped tray/outer shell checked separately",
    source_sha256={name: hashlib.sha256((ROOT/'tools'/name).read_bytes()).hexdigest()
                   for name in ('cad_v6_jetson_mount.py','cad_v6_payload.py')},
    source_base_solid_index=1266, official_solids=len(kit.Solids),
    selected_vertical_translation_mm=37.9,
    actual_minimum_base_vertex_z_mm=min(vertex.Point.z for vertex in base.Vertexes),
    base_to_reference_tray_distance_mm=base.distToShape(tray)[0],
    initial_base_overlap_mm3=base.common(tray).Volume,
    initial_retainer_overlap_mm3={name:base.common(shape).Volume for name,shape in retainers.items()},
    mount_vs_payload_placement_max_bound_error_mm=max(
        abs(getattr(kit.BoundBox,key)-getattr(payload_kit.BoundBox,key))
        for key in ('XMin','XMax','YMin','YMax','ZMin','ZMax')),
    probes=[],
    notes=["The previous +38.03851112444 transform followed a loose BRep bound and left the real base0.13849mm above the tray.",
           "Only the installation transform changed; the official solid geometry is unmodified.",
           "Retainer lip undersideZ40 is0.5mm above the actual base rim, so +Z0.6 rather than0.5 tests positive capture.",
           "These are translations of the original plastic base, not collision against PCB components; no impact capacity is established."])
for direction,offset in (('+X',(1.,0,0)),('-X',(-1.,0,0)),('+Y',(0,1.,0)),('-Y',(0,-1.,0)),('+Z',(0,0,.6)),('-Z',(0,0,-.05))):
    moved=base.copy();moved.translate(mount.V(*offset))
    targets={'reference_Z33_tray':tray} if direction=='-Z' else retainers
    overlaps={name:moved.common(shape).Volume for name,shape in targets.items()}
    report['probes'].append(dict(direction=direction,offset_mm=offset,overlap_mm3=overlaps,
                                 translation_captured=any(volume>.001 for volume in overlaps.values())))
report['pass']=dict(
    true_base_supported=report['base_to_reference_tray_distance_mm']<.001 and report['initial_base_overlap_mm3']<.001,
    no_initial_base_interference=all(value<.001 for value in report['initial_retainer_overlap_mm3'].values()),
    all_six_translations_captured=all(row['translation_captured'] for row in report['probes']),
    two_payload_implementations_match=report['mount_vs_payload_placement_max_bound_error_mm']<.001)
(ROOT/'mechanical/v6/jetson_base_contact_independent_review.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
