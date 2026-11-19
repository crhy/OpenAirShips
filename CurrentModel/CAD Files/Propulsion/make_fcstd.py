"""Collect the propulsion parts in one FreeCAD file and write watertight STLs.

Run with `freecadcmd make_fcstd.py` after `python3 propulsion.py`.
`OAS_FCSTD_ONLY=1` rebuilds just the .FCStd from the .step files already on disk:
it writes no STL, reads no `print/*.step` and removes nothing.
"""
import glob
import os
import sys

import MeshPart
import Part

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))          # CAD Files/fcstd_doc.py
import fcstd_doc

FOUR = os.environ.get("OAS_VARIANT", "8T").upper() == "4T"
SCALE = float(os.environ.get("OAS_SCALE", "1"))
N = int(os.environ.get("OAS_SLICES", "8"))
LARGE = os.environ.get("OAS_THRUSTER", "L" if FOUR else "S").upper() == "L"
FCSTD_ONLY = os.environ.get("OAS_FCSTD_ONLY", "").upper() in ("1", "TRUE", "YES")
if FOUR:                                     # same folders as propulsion.py: 4T/[small/][12s/][x1.9/]
    HERE = os.path.join(HERE, "4T")
    if not LARGE:
        HERE = os.path.join(HERE, "small")
if N != 8:
    HERE = os.path.join(HERE, f"{N}s")
if SCALE != 1:
    HERE = os.path.join(HERE, f"x{SCALE:g}")
STEM = ("propulsion 1026" + (" 4T" if FOUR else "") + ("" if not FOUR or LARGE else " small")
        + ("" if N == 8 else f" {N}s") + ("" if SCALE == 1 else f" x{SCALE:g}"))
OUT = os.path.join(HERE, STEM + ".FCStd")

doc = fcstd_doc.new_document(STEM)
for step in sorted(glob.glob(os.path.join(HERE, "*.step"))):
    name = os.path.splitext(os.path.basename(step))[0]
    shape = Part.Shape()
    shape.read(step)
    obj = fcstd_doc.add_part(doc, name, shape)
    print(f"{name:14} valid {obj.Shape.isValid()}  solids {len(obj.Shape.Solids)}")
    if FCSTD_ONLY:
        continue
    posed = Part.Shape()
    posed.read(os.path.join(HERE, "print", name + ".step"))
    mesh = MeshPart.meshFromShape(Shape=posed, LinearDeflection=0.02,
                                  AngularDeflection=0.1, Relative=False)
    mesh.write(os.path.join(HERE, "print", name + ".stl"))
    print(f"{name:14} stl solid {mesh.isSolid()}")

fcstd_doc.save(doc, OUT)
print(f"{STEM + '.FCStd':52} parts {len(doc.Objects)}")
if not FCSTD_ONLY:
    for f in glob.glob(os.path.join(HERE, "print", "*.step")):
        os.remove(f)
