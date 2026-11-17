"""f084 probe 3: what ARE the faces the thin points sit on?

For a list of face indices of the 8T slice STEP: geometry type, area, bbox,
distance to the hull's outer/inner surface and to the duct surfaces, and the
nearest window cutters (bbox-filtered). That names the face: outer skin, inner
skin, a duct wall, a window cutter's side face, or a sliver between two.

Run: /home/rhy/.venvs/cadquery/bin/python step_probe3.py 796,797,812
"""
import math
import os
import sys
import time

SL = "/home/rhy/strata-fleet/repos/OpenAirShips/CurrentModel/CAD Files/SimplifiedSlice"
sys.path.insert(0, SL)
import cadquery as cq

os.environ.setdefault("OAS_VARIANT", "8T")
os.environ.setdefault("OAS_SLICES", "8")
os.environ.setdefault("OAS_SCALE", "1")
import airship_slice as G

STEP = os.path.join(SL, "airship pie slice 1026.step")
shape = cq.importers.importStep(STEP).val()
faces = shape.Faces()

hull = G.wedge_edges(G.arc(G.A, G.B, -math.pi / 2, math.pi / 2), half=180)
inner = G.wedge_edges(G.arc(G.A - G.T, G.B - G.T, -math.pi / 2, math.pi / 2), half=180)
walls, bore = G.duct_solids()
aw, ab = G.at_seams(walls), G.at_seams(bore)
stem, servo = G.stem_and_servo_holes()
astem, aservo = G.at_seams(stem), G.at_seams(servo)
cut = G.windows()
cutbb = [(w.BoundingBox(), w) for w in cut]
print("loaded: %d faces, %d window cutters" % (len(faces), len(cut)))
sys.stdout.flush()


def bb_near(a, b, tol):
    dx = max(a.xmin - b.xmax, b.xmin - a.xmax, 0.0)
    dy = max(a.ymin - b.ymax, b.ymin - a.ymax, 0.0)
    dz = max(a.zmin - b.zmax, b.zmin - a.zmax, 0.0)
    return math.sqrt(dx * dx + dy * dy + dz * dz) <= tol


for i in [int(x) for x in sys.argv[1].split(",")]:
    f = faces[i]
    c, bb = f.Center(), f.BoundingBox()
    ds = []
    for j, (cb, w) in enumerate(cutbb):
        if bb_near(bb, cb, 2.0):
            ds.append((f.distance(w), j))
    ds.sort()
    print("face %-5s geom %-12s area %8.4f mm2 centre (%7.2f,%7.2f,%7.2f) "
          "bbox x[%.1f,%.1f] y[%.1f,%.1f] z[%.1f,%.1f]"
          % (i, f.geomType(), f.Area(), c.x, c.y, c.z,
             bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax))
    print("      to hull outer %.4f  to hull inner %.4f  to duct wall %.4f  "
          "to duct bore %.4f  to stem hole %.4f  to servo hole %.4f"
          % (f.distance(hull), f.distance(inner), f.distance(aw), f.distance(ab),
             f.distance(astem), f.distance(aservo)))
    print("      nearest cutters: " + ", ".join("#%d %.4f mm" % (j, d) for d, j in ds[:4]))
    sys.stdout.flush()
