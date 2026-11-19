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
TAG = os.environ.get("OAS_TAG", "")   # same OAS_TAG airship_slice.py uses (f118 item 5)
FCSTD_ONLY = os.environ.get("OAS_FCSTD_ONLY", "").upper() in ("1", "TRUE", "YES")
HAND = ("left" if SIDE == "L" else "right")
NAME = ("airship pie slice 1026" + (f" 4T {HAND}" if FOUR else "")
        + (f" {TAG}" if TAG else ("" if SCALE == 1 else f" x{SCALE:g}")))
STL = ("PieSlice1026-v0.2.1-" + (f"4T-{HAND}" if FOUR else "8T")
       + (f"-{TAG}" if TAG else ("" if SCALE == 1 else "-KobraMax")) + ".stl")

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
for lin, ang in ((0.01, 0.03), (0.015, 0.05), (0.02, 0.08), (0.03, 0.1), (0.05, 0.1)):
    # f156 item 4 (rhY, crop 10: wavy streaks on the INSIDE of the duct tube). Measured
    # (build/f156/ductgeom.py): the bore's own geometry is a BSpline sweep whose surface
    # stays within 0.006 mm of a true R = DUCT_BORE / 2 tube over a 24 x 24 sample grid -
    # no segment seam, no crest-band or lattice cut grazing it, no boss. Measured on the
    # print STL (build/f156/ductblemish.py): the same surface sits 0.029 mm inside that
    # tube, facet by facet, with no ridge at any fixed place along or round the duct - the
    # streaks are the tessellation of a curved surface, not the model. So the deflection
    # comes down: 0.03 mm / 0.1 rad put 1.2-1.7 mm facets on a 12 mm radius (a chord of
    # 1.2 mm on R 12 sags 0.03 mm, which is exactly the reading). 0.01 mm / 0.03 rad gives
    # ~0.7 mm facets and 0.01 mm of sag, and the STL stays far under the 90 MB the task
    # sets (bench 8T: 115,658 facets / 5.9 MB before, 262,884 / 13.5 MB after).
    # 0.03 mm first used to be the fix for the bulb-dome crease (f148): at 0.015-0.02 the
    # tessellation put facets within 0.01 mm of the seam face where the bulb's dome crosses
    # it and the wall ray read 0.005-0.12 mm there. f151's GRAZE_DEG = 10 deg guard in
    # Analysis/check_outputs.py is what makes the finer mesh safe now; the wall map is
    # re-run on both print sizes to confirm it.
    mesh = MeshPart.meshFromShape(Shape=pose, LinearDeflection=lin,
                                  AngularDeflection=ang, Relative=False)
    if mesh.isSolid():
        print("mesh deflection %.3f mm / %.2f rad: %d facets, %.1f MB"
              % (lin, ang, mesh.CountFacets, 84 * mesh.CountFacets / 1e6))
        break
mesh.write(os.path.join(HERE, "..", "..", "Print Files", STL))
print("stl solid", mesh.isSolid(), "bounds", mesh.BoundBox)
