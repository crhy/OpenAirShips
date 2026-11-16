"""Wrap the STEP in a FreeCAD document and write the print STL.

Run with `freecadcmd make_fcstd.py` after `python3 airship_slice.py`.
`OAS_FCSTD_ONLY=1` rebuilds just the .FCStd from the .step already on disk and
leaves the print files alone.
"""
import os
import sys

import FreeCAD as App
import MeshPart
import Part

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))          # CAD Files/fcstd_doc.py
import fcstd_doc

# the same variant settings as airship_slice.py (OAS_VARIANT, OAS_SIDE, OAS_SCALE)
FOUR = os.environ.get("OAS_VARIANT", "8T").upper() == "4T"
SIDE = os.environ.get("OAS_SIDE", "L").upper()
SCALE = float(os.environ.get("OAS_SCALE", "1"))
FCSTD_ONLY = os.environ.get("OAS_FCSTD_ONLY", "").upper() in ("1", "TRUE", "YES")
HAND = ("left" if SIDE == "L" else "right")
NAME = ("airship pie slice 1026" + (f" 4T {HAND}" if FOUR else "")
        + ("" if SCALE == 1 else f" x{SCALE:g}"))
STL = ("PieSlice1026-v0.2.1-" + (f"4T-{HAND}" if FOUR else "8T")
       + ("" if SCALE == 1 else "-KobraMax") + ".stl")

doc = fcstd_doc.new_document(NAME)
shape = Part.Shape()
shape.read(os.path.join(HERE, NAME + ".step"))
base = fcstd_doc.add_part(doc, "SimplifiedSlice", shape)

sheet = doc.addObject("Spreadsheet::Sheet", "Spreadsheet")
for i, (label, alias, value) in enumerate([
        ("Hull Thickness", "hulthickness", "0.86 mm"),
        ("Rows Above Equator", "rowsaboveeq", "6"),
        ("Hull Radius", "hullradius", f"{207.765 * SCALE:.3f} mm"),
        ("Hull Half Height", "hullhalfheight", f"{104 * SCALE:.3f} mm"),
        ("Thrusters", "thrusters", "4" if FOUR else "8"),
        ("Intake Shaft Diameter", "shaftd", "66 mm"),
        ("Duct Bore", "ductbore", "34 mm" if FOUR else "24 mm"),
        ("Rib Width", "rib", "2 mm"),
        ("Intake Bellmouth Radius", "intaker", "12 mm"),
        ("Fan Housing Radius At Keel", "housingr", "80 mm"),
        ("Peg", "pegdiameter", "3 mm"),
        ("Hole", "holediameter", "3.3 mm")], 1):
    sheet.set(f"A{i}", label)
    sheet.set(f"B{i}", f"={value}")
    sheet.setAlias(f"B{i}", alias)

fcstd_doc.save(doc, os.path.join(HERE, NAME + ".FCStd"))
print(f"{NAME + '.FCStd':52} valid {base.Shape.isValid()}  "
      f"solids {len(base.Shape.Solids)}  volume {round(base.Shape.Volume)}")

if FCSTD_ONLY:
    print(f"{STL:40} left as it is (OAS_FCSTD_ONLY=1)")
    raise SystemExit(0)

# Print STL: lie on the -22.5 deg (hole) seam, so the seam is flat on the bed
# and the skin never overhangs more than 45 deg.
pose = shape.copy()
pose.rotate(App.Vector(), App.Vector(0, 0, 1), 22.5)
pose.rotate(App.Vector(), App.Vector(1, 0, 0), 90)
for lin in (0.02, 0.015, 0.03, 0.01, 0.05):    # retry until the mesh is watertight
    mesh = MeshPart.meshFromShape(Shape=pose, LinearDeflection=lin,
                                  AngularDeflection=0.1, Relative=False)
    if mesh.isSolid():
        break
mesh.write(os.path.join(HERE, "..", "..", "Print Files", STL))
print("stl solid", mesh.isSolid(), "bounds", mesh.BoundBox)
