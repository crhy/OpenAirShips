"""f084 probe 1b: the mesh checker's thin points -> the BREP faces there -> the
generator tool whose boundary each face lies on. (probe 1's whole-shape face
scan was too slow; this one only looks where the mesh says the wall is thin.)

Run: /home/rhy/.venvs/cadquery/bin/python step_probe2.py thin_points.json
"""
import json
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
POINTS = json.load(open(sys.argv[1]))

t0 = time.time()
shape = cq.importers.importStep(STEP).val()
faces = shape.Faces()
areas = [f.Area() for f in faces]
centers = [f.Center() for f in faces]
bb = [f.BoundingBox() for f in faces]
print("read STEP in %.1f s: %d faces, volume %.1f" % (time.time() - t0, len(faces), shape.Volume()))
sys.stdout.flush()

# the lattice, rebuilt, tagged: which window cutter is near which thin point?
t0 = time.time()
cut = G.windows()
print("%d window cutters in %.1f s" % (len(cut), time.time() - t0))
sys.stdout.flush()

walls, bore = G.duct_solids()
aw = G.at_seams(walls)
tools = []
for i, w in enumerate(cut):
    tools.append(("windows()[%d]" % i, w))
tools.append(("duct_solids() walls at_seams", aw))
tools.append(("duct_solids() bore at_seams", G.at_seams(bore)))
stem, servo = G.stem_and_servo_holes()
tools.append(("stem hole at_seams", G.at_seams(stem)))
tools.append(("servo hole", servo.rotate((0, 0, 0), (0, 0, 1), -G.HALF)))
tools.append(("hatch_hole()", G.hatch_hole()))
kp = G.outlet_keepout()
if kp is not None:
    tools.append(("outlet_keepout()", kp))
jp = G.joint_parts()
for kind, seq in (("hole", jp[1]), ("boss", jp[0]), ("sleeve", jp[3]), ("peg", jp[2])):
    for i, s in enumerate(seq):
        tools.append(("joint_parts() %s[%d]" % (kind, i), s))
print("%d tools" % len(tools))
sys.stdout.flush()
print("%d tools" % len(tools))
sys.stdout.flush()


def near_point(p, tol):
    out = []
    for i, b in enumerate(bb):
        dx = max(b.xmin - p[0], p[0] - b.xmax, 0.0)
        dy = max(b.ymin - p[1], p[1] - b.ymax, 0.0)
        dz = max(b.zmin - p[2], p[2] - b.zmax, 0.0)
        if math.sqrt(dx * dx + dy * dy + dz * dz) <= tol:
            out.append(i)
    return out


rows = []
for p in POINTS:
    x, y, z, wall = p["at"][0], p["at"][1], p["at"][2], p["wall"]
    v = cq.Vertex.makeVertex(x, y, z)
    near = []
    for i in near_point((x, y, z), 0.45):
        d = faces[i].distance(v)
        if d < 0.45:
            near.append((d, i))
    near.sort()
    line = ("point (%7.2f,%7.2f,%7.2f) wall %.3f mm: faces "
            % (x, y, z, wall))
    detail = []
    for d, i in near[:4]:
        c = centers[i]
        detail.append("face %d area %.4f mm2 centre (%.2f,%.2f,%.2f) d=%.3f"
                      % (i, areas[i], c.x, c.y, c.z, d))
    # which tools' boundary is this point on?
    hits = []
    for name, tool in tools:
        try:
            d = v.distance(tool)
        except Exception:
            continue
        if d < 0.05:
            hits.append((d, name))
    hits.sort()
    rows.append((wall, x, y, z, detail, hits))
    print(line + "; " + " | ".join(detail))
    for d, name in hits[:5]:
        print("      on tool %-40s (%.3f mm)" % (name, d))
    sys.stdout.flush()

print("\n== summary: thin point -> nearest cutter ==")
for wall, x, y, z, detail, hits in sorted(rows):
    print("%.3f mm (%7.1f,%7.1f,%7.1f)  %s" % (wall, x, y, z,
          "; ".join(n for _, n in hits[:3]) or "no tool boundary"))
    sys.stdout.flush()
