"""Print files for a pieces build (OAS_PIECES=1): one watertight STL per piece,
laid on its seam the way it prints, the intake tubes standing upright, and a
FreeCAD document per slice type holding its pieces.

Run with `freecadcmd make_pieces.py` after `python3 airship_slice.py` for each
slice type (same OAS_* settings), e.g. for the double-Kobra build:
  OAS_VARIANT=4T OAS_SLICES=12 OAS_THRUSTER=S OAS_PIECES=1 OAS_SCALE=3.8
`OAS_FCSTD_ONLY=1` rebuilds just the three .FCStd documents from the piece
STEP files already on disk and writes no STL.
"""
import glob
import os
import sys

import FreeCAD as App
import MeshPart
import Part

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))          # CAD Files/fcstd_doc.py
import fcstd_doc

N = int(os.environ.get("OAS_SLICES", "8"))
HALF = 180.0 / N
SCALE = float(os.environ.get("OAS_SCALE", "1"))
FCSTD_ONLY = os.environ.get("OAS_FCSTD_ONLY", "").upper() in ("1", "TRUE", "YES")
OUT = os.path.join(HERE, "..", "..", "Print Files", os.environ.get("OAS_PRINT_DIR", "v0.2.1 double Kobra"))
os.makedirs(OUT, exist_ok=True)


def mesh(shape):
    for lin in (0.02, 0.015, 0.03, 0.01, 0.05):     # retry until the mesh is watertight
        m = MeshPart.meshFromShape(Shape=shape, LinearDeflection=lin, AngularDeflection=0.1, Relative=False)
        if m.isSolid():
            return m
    m = MeshPart.meshFromShape(Shape=shape, LinearDeflection=0.02, AngularDeflection=0.1, Relative=False)
    m.removeDuplicatedPoints()                       # then close the few tessellation gaps
    m.fillupHoles(200)
    m.harmonizeNormals()
    return m


tubes_done = False
for d in sorted(glob.glob(os.path.join(HERE, "pieces", f"*{N}s*x{SCALE:g}"))):
    kind = os.path.basename(d).split(" 4T ")[-1].split(" ")[0]      # left / right / plain
    doc = fcstd_doc.new_document(f"airship pie slice 1026 v0.2.1 {kind} (pieces)")
    for step in sorted(glob.glob(os.path.join(d, "*.step"))):
        name = os.path.splitext(os.path.basename(step))[0]
        shape = Part.Shape()
        shape.read(step)
        if name.startswith("intake_tube"):
            if tubes_done or FCSTD_ONLY:
                continue
            pose = shape.copy()                      # stands upright on its foot
            pose.translate(App.Vector(0, 0, -pose.BoundBox.ZMin))
            out = os.path.join(OUT, f"PieSlice1026-v0.2.1-{name.replace('_', '-')}.stl")
        else:
            fcstd_doc.add_part(doc, name, shape)
            if FCSTD_ONLY:
                continue
            pose = shape.copy()                      # lies on its -HALF seam
            pose.rotate(App.Vector(), App.Vector(0, 0, 1), HALF)
            pose.rotate(App.Vector(), App.Vector(1, 0, 0), 90)
            pose.translate(App.Vector(-pose.BoundBox.XMin, -pose.BoundBox.YMin, -pose.BoundBox.ZMin))
            out = os.path.join(OUT, f"PieSlice1026-v0.2.1-{kind}-{name.replace('_', '-')}.stl")
        m = mesh(pose)
        m.write(out)
        bb = pose.BoundBox
        print(f"{os.path.basename(out):48} solid {m.isSolid()}  {bb.XLength:.0f} x {bb.YLength:.0f} x {bb.ZLength:.0f} mm")
    tubes_done = True
    path = os.path.join(HERE, "pieces", f"airship pie slice 1026 v0.2.1 {kind} (pieces).FCStd")
    fcstd_doc.save(doc, path)
    print(f"{os.path.basename(path):52} parts {len(doc.Objects)}")
