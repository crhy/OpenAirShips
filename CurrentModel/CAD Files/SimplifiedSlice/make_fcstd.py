"""Wrap the STEP in a FreeCAD document and write the print STL.

Run with `freecadcmd make_fcstd.py` after `python3 airship_slice.py`.
"""
import os
import FreeCAD as App
import MeshPart
import Part

HERE = os.path.dirname(os.path.abspath(__file__))
NAME = "airship pie slice 926"

doc = App.newDocument("airship_pie_slice_926")
shape = Part.Shape()
shape.read(os.path.join(HERE, NAME + ".step"))
base = doc.addObject("Part::Feature", "SimplifiedSlice")
base.Shape = shape
body = doc.addObject("PartDesign::Body", "Body")      # add features on top of it
body.BaseFeature = base

sheet = doc.addObject("Spreadsheet::Sheet", "Spreadsheet")
for i, (label, alias, value) in enumerate([
        ("Hull Thickness", "hulthickness", "0.86 mm"),
        ("Hull Radius", "hullradius", "207.765 mm"),
        ("Hull Half Height", "hullhalfheight", "104 mm"),
        ("Rib Width", "rib", "4 mm"),
        ("Peg", "pegdiameter", "3 mm"),
        ("Hole", "holediameter", "3.3 mm")], 1):
    sheet.set(f"A{i}", label)
    sheet.set(f"B{i}", f"={value}")
    sheet.setAlias(f"B{i}", alias)

doc.recompute()
doc.saveAs(os.path.join(HERE, NAME + ".FCStd"))
print("valid", body.Shape.isValid(), "volume", round(body.Shape.Volume))

# Print STL: lie on the -22.5 deg (hole) seam, so the seam is flat on the bed
# and the skin never overhangs more than 45 deg.
pose = shape.copy()
pose.rotate(App.Vector(), App.Vector(0, 0, 1), 22.5)
pose.rotate(App.Vector(), App.Vector(1, 0, 0), 90)
mesh = MeshPart.meshFromShape(Shape=pose, LinearDeflection=0.02,
                              AngularDeflection=0.1, Relative=False)
mesh.write(os.path.join(HERE, "..", "..", "Print Files", "PieSlice926.stl"))
print("stl solid", mesh.isSolid(), "bounds", mesh.BoundBox)
