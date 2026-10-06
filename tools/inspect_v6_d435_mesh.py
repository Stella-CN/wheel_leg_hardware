"""Convert the official RealSense ROS D435 COLLADA triangles to millimetre STL.

The vendor mesh is neither repaired nor turned into a claimed solid CAD model.
Scene transforms and primitive types are explicitly checked before conversion.
Run with the installed FreeCAD Python; the original DAE remains unchanged.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, "/Applications/FreeCAD.app/Contents/Resources/lib")
import FreeCAD as App
import Mesh

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "mechanical/v6/source/d435"
SOURCE = DEST / "d435_official_ros.dae"
OUTPUT = DEST / "d435_official_ros_mm.stl"
NS = {"c": "http://www.collada.org/2005/11/COLLADASchema"}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_triangles():
    root = ET.parse(SOURCE).getroot()
    unit = root.find("c:asset/c:unit", NS)
    multiplier = float(unit.attrib["meter"]) * 1000
    transforms = [element for node in root.findall(".//c:visual_scene//c:node", NS)
                  for element in node if element.tag.rsplit("}", 1)[-1] in
                  {"matrix", "translate", "rotate", "scale", "lookat", "skew"}]
    if transforms:
        raise ValueError("Scene transforms need explicit handling; refusing to silently ignore them")
    instantiated = [node.attrib["url"].lstrip("#")
                    for node in root.findall(".//c:visual_scene//c:instance_geometry", NS)]
    geometries = {node.attrib["id"]: node for node in root.findall(".//c:geometry", NS)}
    if len(instantiated) != len(set(instantiated)) or set(instantiated) != set(geometries):
        raise ValueError("Unexpected repeated or uninstantiated geometry")
    triangles, rows = [], []
    for name in instantiated:
        geometry = geometries[name]
        mesh = geometry.find("c:mesh", NS)
        sources = {}
        for source in mesh.findall("c:source", NS):
            floats = [float(value) for value in source.find("c:float_array", NS).text.split()]
            accessor = source.find("c:technique_common/c:accessor", NS)
            stride = int(accessor.get("stride", "1"))
            offset = int(accessor.get("offset", "0"))
            count = int(accessor.attrib["count"])
            sources[source.attrib["id"]] = [floats[offset + i * stride:offset + (i + 1) * stride]
                                              for i in range(count)]
        vertices = {}
        for vertex in mesh.findall("c:vertices", NS):
            position = next(entry for entry in vertex.findall("c:input", NS)
                            if entry.attrib["semantic"] == "POSITION")
            vertices[vertex.attrib["id"]] = sources[position.attrib["source"].lstrip("#")]
        before = len(triangles)
        for primitive in mesh:
            tag = primitive.tag.rsplit("}", 1)[-1]
            if tag in {"source", "vertices", "extra"}:
                continue
            if tag != "triangles":
                raise ValueError(f"Unexpected primitive {tag}; source topology must not be silently changed")
            inputs = primitive.findall("c:input", NS)
            stride = 1 + max(int(entry.get("offset", "0")) for entry in inputs)
            position_input = next(entry for entry in inputs if entry.attrib["semantic"] == "VERTEX")
            position_offset = int(position_input.get("offset", "0"))
            positions = vertices[position_input.attrib["source"].lstrip("#")]
            indices = [int(value) for value in primitive.find("c:p", NS).text.split()]
            expected = int(primitive.attrib["count"])
            if len(indices) != expected * 3 * stride:
                raise ValueError("COLLADA triangle count does not match indexed data")
            for index in range(expected):
                triangle = []
                for corner in range(3):
                    vertex_index = indices[(index * 3 + corner) * stride + position_offset]
                    xyz = positions[vertex_index]
                    if len(xyz) < 3:
                        raise ValueError("Position source has fewer than three coordinates")
                    triangle.append(tuple(multiplier * value for value in xyz[:3]))
                triangles.append(tuple(triangle))
        rows.append(dict(id=name, source_triangles=len(triangles) - before))
    return triangles, rows, dict(unit_name=unit.get("name"), source_meter_scale=float(unit.attrib["meter"]),
                                 applied_coordinate_scale_to_mm=multiplier,
                                 up_axis=root.find("c:asset/c:up_axis", NS).text,
                                 source_created=root.find("c:asset/c:created", NS).text,
                                 scene_transform_count=0)


def topology_report(mesh):
    points, facets = mesh.Topology
    incidence = Counter()
    duplicate_facets = Counter()
    degenerate = 0
    for facet in facets:
        a, b, c = facet
        duplicate_facets[tuple(sorted(facet))] += 1
        if len(set(facet)) != 3:
            degenerate += 1
        else:
            cross = (points[b] - points[a]).cross(points[c] - points[a])
            if cross.Length <= 1e-12:
                degenerate += 1
        for edge in ((a, b), (b, c), (c, a)):
            incidence[tuple(sorted(edge))] += 1
    b = mesh.BoundBox
    return dict(points=len(points), facets=len(facets), components=mesh.countComponents(),
                is_solid=mesh.isSolid(), has_nonmanifolds=mesh.hasNonManifolds(),
                has_nonuniform_orientation=mesh.hasNonUniformOrientedFacets(),
                nonuniform_oriented_facets=mesh.countNonUniformOrientedFacets(),
                boundary_edges=sum(count == 1 for count in incidence.values()),
                nonmanifold_edges=sum(count > 2 for count in incidence.values()),
                degenerate_facets=degenerate,
                duplicate_facets=sum(count - 1 for count in duplicate_facets.values()),
                bounds_mm=[b.XMin, b.XMax, b.YMin, b.YMax, b.ZMin, b.ZMax],
                dimensions_mm=[b.XLength, b.YLength, b.ZLength])


def main():
    triangles, geometries, metadata = read_triangles()
    # The source explicitly models the two back mounting holes. Inspect the
    # original vertices, without using an inferred box depth as their datum.
    vertices = {point for triangle in triangles for point in triangle}
    back_holes = []
    for centre_x in (-22.5, 22.5):
        circular_points = [point for point in vertices
                           if abs(((point[0] - centre_x)**2 + point[1]**2)**.5 - 1.25) < .0002
                           and point[2] < -20]
        if not circular_points:
            raise ValueError("Expected source back-hole geometry was not found")
        back_holes.append(dict(source_centre_xy_mm=[centre_x, 0.], source_radius_mm=1.25,
                               measured_back_z_mm=min(point[2] for point in circular_points),
                               measured_inside_z_mm=max(point[2] for point in circular_points),
                               sampled_vertices=len(circular_points)))
    mesh = Mesh.Mesh(triangles)
    if mesh.CountFacets != len(triangles):
        raise ValueError("FreeCAD altered the facet count during construction")
    before = topology_report(mesh)
    mesh.write(str(OUTPUT))
    restored = Mesh.Mesh(str(OUTPUT))
    after = topology_report(restored)
    if restored.CountFacets != len(triangles):
        raise ValueError("STL export changed the facet count")
    notice = ["RealSense D435 official ROS mesh conversion", "",
              "Source: https://github.com/realsenseai/realsense-ros/tree/ros2-master/realsense2_description",
              "Original d435.dae is retained unchanged.",
              "Derived d435_official_ros_mm.stl: COLLADA position coordinates multiplied by 1000 (metres to millimetres), original triangle order/winding retained; STL omits COLLADA material/colour data.",
              "No hole filling, mesh repair, smoothing, decimation, or substitute solid geometry was performed.",
              "The derived STL is a visualization mesh, not manufacturer solid CAD or a printable structural component.",
              "Repository/package license: Apache License 2.0; see LICENSE.realsense-ros and realsense2_description.package.xml."]
    (DEST / "NOTICE.conversion.txt").write_text("\n".join(notice) + "\n")
    report = dict(source_file=SOURCE.name, source_sha256=sha(SOURCE),
        source_url="https://raw.githubusercontent.com/realsenseai/realsense-ros/ros2-master/realsense2_description/meshes/d435.dae",
        repository="https://github.com/realsenseai/realsense-ros",
        retrieved_local_date="2026-09-22", license="Apache License 2.0",
        license_url="https://raw.githubusercontent.com/realsenseai/realsense-ros/ros2-master/LICENSE",
        source_metadata=metadata, geometry_count=len(geometries), geometries=geometries,
        rear_mount_interface=dict(source_holes=back_holes,
            transformed_back_plane_x_mm=74.95,
            transformed_hole_centres_mm=[[74.95,-22.5,19.],[74.95,22.5,19.]],
            official_drawing_depth_mm=26.05, mesh_back_plane_depth_mm=25.05,
            discrepancy_mm=1.,
            evidence="2025 D400 datasheet Figure10-9/page140 specifies26.05mm depth and2xM3 maximum3mm insertion; 2018 ROS mesh has back hole plane at sourcez=-25.05mm",
            interpretation="The official visualization mesh and mechanical drawing differ by1mm in depth; no inference that the mesh hole depth is the permissible screw engagement",
            mounting_option="Keep front atX100 and optical/body centreZ19. For25.05mm ROS-model depth use1mm removable spacers between bracketX73.95 and rearX74.95, withM3x6 through3mm bracket+1mm spacer giving2mm insertion. For26.05mm drawing-depth unit remove spacers and useM3x5 through3mm bracket, also2mm insertion. Confirm supplied camera dimensions; both remain below3mm specified maximum."),
        derived_file=OUTPUT.name, derived_sha256=sha(OUTPUT), derivation=notice[4:7],
        before_STL=before, after_STL=after,
        recommended_assembly=dict(rule="(source x,y,z) mm -> (z+100, x, y+19) mm",
                                  rotation_matrix_rows=[[0,0,1],[1,0,0],[0,1,0]],
                                  translation_mm=[100,0,19],
                                  expected_front_x_mm=100),
        analytic_envelope_configurations=[
            dict(camera_depth_mm=25.05, bounds_mm=[74.95,100,-45.075,45.075,6.425,31.575],
                 removable_shim_mm=1, screw="M3x6", nominal_engagement_mm=2, selected=True),
            dict(camera_depth_mm=26.05, bounds_mm=[73.95,100,-45.075,45.075,6.425,31.575],
                 removable_shim_mm=0, screw="M3x5", nominal_engagement_mm=2, selected=False)],
        collision_and_mass_method="Use explicitly labelled 75g analytic envelope for collision/mass: selected25.05mm configuration X74.95..100, Y±45.075, Z6.425..31.575mm. The alternative26.05mm depth reaches rearX73.95, removes1mm shims and usesM3x5. Do not infer mass from open mesh volume; original ROS mesh has a0.0047mm local rear protrusion beyond its nominal25.05mm plane.")
    (DEST / "mesh_inspection.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(dict(file=OUTPUT.name, sha256=report["derived_sha256"], **after), indent=2))


if __name__ == "__main__":
    main()
