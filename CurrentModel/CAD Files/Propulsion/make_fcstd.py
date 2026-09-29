"""Collect the propulsion parts in one FreeCAD file and write watertight STLs.

Run with `freecadcmd make_fcstd.py` after `python3 propulsion.py`.
"""
import glob
import os
import FreeCAD as App
import MeshPart
import Part

HERE = os.path.dirname(os.path.abspath(__file__))
FOUR = os.environ.get("OAS_VARIANT", "8T").upper() == "4T"
SCALE = float(os.environ.get("OAS_SCALE", "1"))
N = int(os.environ.get("OAS_SLICES", "8"))
LARGE = os.environ.get("OAS_THRUSTER", "L" if FOUR else "S").upper() == "L"
if FOUR:                                     # same folders as propulsion.py: 4T/[small/][12s/][x1.9/]
    HERE = os.path.join(HERE, "4T")
    if not LARGE:
        HERE = os.path.join(HERE, "small")
if N != 8:
    HERE = os.path.join(HERE, f"{N}s")
if SCALE != 1:
    HERE = os.path.join(HERE, f"x{SCALE:g}")
OUT = os.path.join(HERE, "propulsion 926" + (" 4T" if FOUR else "") + ("" if not FOUR or LARGE else " small")
                   + ("" if N == 8 else f" {N}s") + ("" if SCALE == 1 else f" x{SCALE:g}") + ".FCStd")

doc = App.newDocument("propulsion_926_4T" if FOUR else "propulsion_926")
for step in sorted(glob.glob(os.path.join(HERE, "*.step"))):
    name = os.path.splitext(os.path.basename(step))[0]
    shape = Part.Shape()
    shape.read(step)
    doc.addObject("Part::Feature", name).Shape = shape

    posed = Part.Shape()
    posed.read(os.path.join(HERE, "print", name + ".step"))
    mesh = MeshPart.meshFromShape(Shape=posed, LinearDeflection=0.02,
                                  AngularDeflection=0.1, Relative=False)
    mesh.write(os.path.join(HERE, "print", name + ".stl"))
    print(f"{name:14} valid {shape.isValid()}  stl solid {mesh.isSolid()}")

doc.recompute()
if os.path.exists(OUT):
    os.remove(OUT)                           # no .FCBak backup next to it
doc.saveAs(OUT)
for f in glob.glob(os.path.join(HERE, "print", "*.step")):
    os.remove(f)
