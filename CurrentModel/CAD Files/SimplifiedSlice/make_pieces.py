"""Print files for a pieces build (OAS_PIECES=1): one watertight STL per piece,
laid on its seam the way it prints, the intake tubes standing upright, and a
FreeCAD document per slice type holding its pieces.

Run with `freecadcmd make_pieces.py` after `python3 airship_slice.py` for each
slice type (same OAS_* settings), e.g. for the double-Kobra build:
  OAS_VARIANT=4T OAS_SLICES=12 OAS_THRUSTER=S OAS_PIECES=1 OAS_SCALE=3.8
"""
import glob
import os

import FreeCAD as App
import MeshPart
import Part

HERE = os.path.dirname(os.path.abspath(__file__))
N = int(os.environ.get("OAS_SLICES", "8"))
HALF = 180.0 / N
SCALE = float(os.environ.get("OAS_SCALE", "1"))
OUT = os.path.join(HERE, "..", "..", "Print Files", os.environ.get("OAS_PRINT_DIR", "v0.2 double Kobra"))
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
    doc = App.newDocument(f"slice_{kind}")
    for step in sorted(glob.glob(os.path.join(d, "*.step"))):
        name = os.path.splitext(os.path.basename(step))[0]
        shape = Part.Shape()
        shape.read(step)
        if name.startswith("intake_tube"):
            if tubes_done:
                continue
            pose = shape.copy()                      # stands upright on its foot
            pose.translate(App.Vector(0, 0, -pose.BoundBox.ZMin))
            out = os.path.join(OUT, f"PieSlice926-v0.2-{name.replace('_', '-')}.stl")
        else:
            doc.addObject("Part::Feature", name).Shape = shape
            pose = shape.copy()                      # lies on its -HALF seam
            pose.rotate(App.Vector(), App.Vector(0, 0, 1), HALF)
            pose.rotate(App.Vector(), App.Vector(1, 0, 0), 90)
            pose.translate(App.Vector(-pose.BoundBox.XMin, -pose.BoundBox.YMin, -pose.BoundBox.ZMin))
            out = os.path.join(OUT, f"PieSlice926-v0.2-{kind}-{name.replace('_', '-')}.stl")
        m = mesh(pose)
        m.write(out)
        bb = pose.BoundBox
        print(f"{os.path.basename(out):48} solid {m.isSolid()}  {bb.XLength:.0f} x {bb.YLength:.0f} x {bb.ZLength:.0f} mm")
    tubes_done = True
    doc.recompute()
    path = os.path.join(HERE, "pieces", f"airship pie slice 926 v0.2 {kind} (pieces).FCStd")
    if os.path.exists(path):
        os.remove(path)
    doc.saveAs(path)
