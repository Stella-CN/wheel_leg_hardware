"""Render the native FreeCAD assembly using its own OpenGL view (macOS)."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, "/Applications/FreeCAD.app/Contents/Resources/lib")
import FreeCAD as App
import FreeCADGui as Gui
import Part
from PySide import QtWidgets

OUT = ROOT / "mechanical/v1"
Gui.showMainWindow()
import PartGui
doc = App.openDocument(str(OUT / "wheel_leg_v1.FCStd"))
doc.Robot.ViewObject.Visibility = True
doc.PurchasedParts.ViewObject.Visibility = True


def refresh():
    doc.recompute()
    Gui.updateGui()
    QtWidgets.QApplication.processEvents()


def save(name, rotation=None):
    view = Gui.activeDocument().activeView()
    # A direct quaternion avoids screenshots taken mid animated view change.
    view.setCameraOrientation(rotation or App.Rotation(0.364705, 0.279848, 0.115917, 0.880476).Q)
    refresh()
    view.fitAll()
    refresh()
    view.saveImage(str(OUT / "previews" / name), 1800, 1400, "White")


for obj in doc.Objects:
    if obj.TypeId != "Part::Feature":
        continue
    obj.ViewObject.Visibility = True
    obj.ViewObject.LineColor = (0.16, 0.19, 0.23)
    obj.ViewObject.LineWidth = 1.0
    obj.ViewObject.DisplayMode = "Flat Lines"
    name = obj.Name
    color = (0.70, 0.77, 0.80)
    if "motor" == getattr(obj, "Material", ""):
        color = (0.24, 0.26, 0.30)
        obj.ViewObject.DisplayMode = "Flat Lines"
    elif "cnc" in name:
        color = (0.79, 0.80, 0.83)
    elif "active_arm" in name:
        color = (0.94, 0.53, 0.20)
    elif "coupler_AC" in name:
        color = (0.22, 0.63, 0.70)
    elif "output_BCW" in name or "fixed_arm" in name:
        color = (0.19, 0.42, 0.60)
    elif "rim" in name:
        color = (0.31, 0.38, 0.46)
    elif "tyre" in name:
        color = (0.13, 0.14, 0.16)
    elif getattr(obj, "Material", "") == "steel":
        color = (0.74, 0.76, 0.79)
    obj.ViewObject.ShapeColor = color

save("assembly.png")
doc.chassis_lid.ViewObject.Visibility = False
doc.electronics_tray.ViewObject.Visibility = False
save("open_chassis.png")
doc.chassis_lid.ViewObject.Visibility = True
doc.electronics_tray.ViewObject.Visibility = True

# Show the complete right leg and real motors separately for interface review.
for obj in doc.Objects:
    if obj.TypeId == "Part::Feature":
        obj.ViewObject.Visibility = obj.Name.endswith("_right")
save("right_leg.png")

for obj in doc.Objects:
    if obj.TypeId == "Part::Feature":
        obj.ViewObject.Visibility = True
save("assembly.png")
doc.save()
print("FREECAD_PREVIEWS_COMPLETE", flush=True)
