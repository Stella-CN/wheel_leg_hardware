"""Native FreeCAD previews for V4, including separate coupling and leg parts."""
from __future__ import annotations

import argparse
import json
import math

import render_nested_robot as view

App, Gui, Part = view.App, view.Gui, view.Part
OUT = view.ROOT / "mechanical/v4"
view.OUT, view.PREVIEWS = OUT, OUT / "previews"


def show_coupling():
    doc = App.openDocument(str(OUT / "coupling_local_review.FCStd"))
    features = [o for o in doc.Objects if hasattr(o, "Shape")]
    rotation = App.Rotation(App.Vector(1, 1, 0), App.Vector(-.7, .7, 2),
                            App.Vector(1, -1, .7), "ZXY").Q
    for o in features:
        o.ViewObject.ShapeColor = ((.25, .27, .29) if "motor" in o.Name else
                                  (.70, .75, .82) if "rotor_cnc" in o.Name else (.83, .85, .87))
        o.ViewObject.LineColor = (.16, .18, .20)
        o.ViewObject.DisplayMode = "Flat Lines"
        o.ViewObject.Visibility = "motor" not in o.Name
    view.save_view(doc, "coupling_assembled.png", rotation, 1400, 1100)
    originals = {o.Name: o.Shape.copy() for o in features}
    for o in features:
        if o.Name == "hip_motor":
            delta = -38
        elif o.Name == "knee_motor":
            delta = 68
        elif "knee_stator" in o.Name or "coupling_knee" in o.Name or "coupling_radial" in o.Name:
            delta = 35
        else:
            delta = 0
        o.Shape = Part.makeCompound([originals[o.Name]])
        o.Placement.Base = App.Vector(0, delta, 0)
        o.ViewObject.Visibility = True
    view.save_view(doc, "coupling_exploded.png", rotation, 1800, 1100)
    for o in features:
        o.ViewObject.Visibility = ("motor" not in o.Name and
                                   (o.Name.endswith("cnc") or "dowel" in o.Name))
    view.save_view(doc, "coupling_parts.png", rotation, 1500, 1100)


def show_robot():
    doc = App.openDocument(str(OUT / "wheel_leg_v4.FCStd"))
    features = [o for o in doc.Objects if o.TypeId == "Part::Feature"]
    original = {o.Name: list(o.ExpressionEngine) for o in features}
    for group in (doc.Robot, doc.PurchasedParts):
        group.ViewObject.Visibility = True
    for o in features:
        view.color_feature(o)
    rotation = App.Rotation(App.Vector(-1, 1, 0), App.Vector(-.7, -.7, 2),
                            App.Vector(1, 1, .7), "ZXY").Q
    full = App.Rotation(.364705, .279848, .115917, .880476).Q
    view.save_view(doc, "assembly.png", full)
    for name in ("chassis_lid", "electronics_tray"):
        doc.getObject(name).ViewObject.Visibility = False
    view.save_view(doc, "open_chassis.png", full)
    for o in features:
        o.ViewObject.Visibility = o.Name.endswith("_right")
    view.save_view(doc, "right_leg.png", rotation)
    view.save_view(doc, "right_leg_side.png", App.Rotation(0, math.sqrt(.5), math.sqrt(.5), 0).Q)
    doc.OB_outer_full_right.ViewObject.Visibility = False
    for name in ("OA_outer_cheek_right", "CW_outer_fork_right"):
        doc.getObject(name).ViewObject.Transparency = 70
    view.save_view(doc, "nested_joints_cutaway.png", rotation)
    for name in ("OA_outer_cheek_right", "CW_outer_fork_right"):
        doc.getObject(name).ViewObject.Transparency = 0
    view.render_exploded(doc, rotation)
    show_separate_parts(doc)
    App.setActiveDocument(doc.Name)
    for o in features:
        o.ViewObject.Visibility = True
    view.save_view(doc, "assembly.png", full)
    assert original == {o.Name: list(o.ExpressionEngine) for o in features}
    doc.save()
    view.linkage_svg(json.loads((OUT / "design_parameters.json").read_text()))


def show_separate_parts(source):
    """A native, explicitly separated layout; these positions are for review."""
    layout = App.newDocument("V4_Separate_Manufactured_Parts")
    layout.Label = "V4 separate parts — review layout, not assembly or print placement"
    names = (("OB_inner_full", 0, 0), ("OB_outer_full", 105, 0),
             ("OA_inner_hub", 210, 0), ("OA_outer_cheek", 300, 0),
             ("AC_bearing_link", 395, 0), ("CW_main_inner", 0, -220),
             ("CW_outer_fork", 120, -220), ("hip_rotor_cnc", 240, -220),
             ("knee_stator_cnc", 345, -220))
    for name, x, z in names:
        original = source.getObject(name+"_right")
        raw = original.Shape.copy()
        raw.Placement = App.Placement()
        bounds = raw.BoundBox
        raw.translate(App.Vector(x-bounds.XMin, -bounds.YMax, z-bounds.ZMax))
        obj = layout.addObject("Part::Feature", name)
        obj.Shape = raw
        obj.addProperty("App::PropertyString", "Material")
        obj.Material = original.Material
        view.color_feature(obj)
    view.save_view(layout, "part_breakdown.png", App.Rotation(0, math.sqrt(.5), math.sqrt(.5), 0).Q,
                   1800, 1550)
    layout.saveAs(str(OUT / "part_breakdown.FCStd"))
    Part.export(layout.Objects, str(OUT / "part_breakdown.step"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coupling-only", action="store_true")
    args = parser.parse_args()
    view.PREVIEWS.mkdir(exist_ok=True, parents=True)
    Gui.showMainWindow()
    import PartGui  # noqa: F401
    show_coupling()
    if not args.coupling_only:
        show_robot()
    print("FREECAD_V4_PREVIEWS_COMPLETE", flush=True)


if __name__ == "__main__":
    main()
