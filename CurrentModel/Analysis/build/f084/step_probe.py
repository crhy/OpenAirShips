"""f084 step 2 probe: for every thin point the mesh checker reported, find the
BREP faces there and the generator tool whose boundary they lie on.

Run: /home/rhy/.venvs/cadquery/bin/python step_probe.py thin_points.json
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
POINTS = json.load(open(sys.argv[1])) if len(sys.argv) > 1 else []

t0 = time.time()
shape = cq.importers.importStep(STEP).val()
print("read %s in %.1f s: faces %d solids %d volume %.1f"
      % (os.path.basename(STEP), time.time() - t0, len(shape.Faces()),
         len(shape.Solids()), shape.Volume()))
sys.stdout.flush()

faces = shape.Faces()
areas = [f.Area() for f in faces]
centers = [f.Center() for f in faces]
bb = [f.BoundingBox() for f in faces]


def near_point(p, tol):
    """faces whose bounding box comes within tol of the point"""
    out = []
    for i, b in enumerate(bb):
        dx = max(b.xmin - p[0], p[0] - b.xmax, 0.0)
        dy = max(b.ymin - p[1], p[1] - b.ymax, 0.0)
        dz = max(b.zmin - p[2], p[2] - b.zmax, 0.0)
        if math.sqrt(dx * dx + dy * dy + dz * dz) <= tol:
            out.append(i)
    return out


def near_face(fi, i, tol):
    """faces whose bounding box comes within tol of face i's bbox"""
    b = bb[i]
    out = []
    for j, o in enumerate(bb):
        if j == i:
            continue
        dx = max(b.xmin - o.xmax, o.xmin - b.xmax, 0.0)
        dy = max(b.ymin - o.ymax, o.ymin - b.ymax, 0.0)
        dz = max(b.zmin - o.zmax, o.zmin - b.zmax, 0.0)
        if math.sqrt(dx * dx + dy * dy + dz * dz) <= tol:
            out.append(j)
    return out


# ---- the tools the generator uses, tagged, so a face can be pointed at code ---
def tag_tools():
    tools = []
    for i, w in enumerate(G.windows()):
        tools.append(("windows()[%d]" % i, w, w.Center()))
    walls, bore = G.duct_solids()
    aw, ab = G.at_seams(walls), G.at_seams(bore)
    tools.append(("duct_solids() walls (at_seams)", aw, aw.Center()))
    tools.append(("duct_solids() bore (at_seams)", ab, ab.Center()))
    stem, servo = G.stem_and_servo_holes()
    st = G.at_seams(stem)
    tools.append(("stem_and_servo_holes() stem (at_seams)", st, st.Center()))
    if G.has_servo():
        sv = servo.rotate((0, 0, 0), (0, 0, 1), -G.HALF)
        tools.append(("stem_and_servo_holes() servo", sv, sv.Center()))
    bosses, holes, pegs, sleeves = G.joint_parts()
    for i, h in enumerate(holes):
        tools.append(("joint_parts() hole[%d]" % i, h, h.Center()))
    for i, b in enumerate(bosses):
        tools.append(("joint_parts() boss[%d]" % i, b, b.Center()))
    for i, s in enumerate(sleeves):
        tools.append(("joint_parts() sleeve[%d]" % i, s, s.Center()))
    for i, p in enumerate(pegs):
        tools.append(("joint_parts() peg[%d]" % i, p, p.Center()))
    tools.append(("hatch_hole()", G.hatch_hole(), G.hatch_hole().Center()))
    return tools


t0 = time.time()
tools = tag_tools()
print("tools built in %.1f s: %d" % (time.time() - t0, len(tools)))
sys.stdout.flush()


def tools_on(face):
    """which tools' boundary this face lies on (a cut face sits on its tool)"""
    out = []
    for name, tool, tc in tools:
        try:
            d = face.distance(tool)
        except Exception:
            continue
        if d < 1e-6:
            out.append("%s centre (%.1f,%.1f,%.1f)" % (name, tc.x, tc.y, tc.z))
    return out


print("\n== face pairs closer than MIN_WEB (0.4 mm): the slivers in the BREP ==")
sys.stdout.flush()
small = [i for i, a in enumerate(areas) if a < 1.0]
print("%d faces under 1 mm2 of %d" % (len(small), len(faces)))
thin_pairs = []
for i in small:
    fi = faces[i]
    best = None
    for j in near_face(fi, i, 0.4):
        d = fi.distance(faces[j])
        if best is None or d < best[0]:
            best = (d, j)
    if best and best[0] < 0.4:
        thin_pairs.append((best[0], i, best[1]))
thin_pairs.sort()
print("%d small faces have another face within 0.4 mm of them" % len(thin_pairs))
for d, i, j in thin_pairs[:45]:
    c, c2 = centers[i], centers[j]
    print("  %.3f mm  face %-5s area %7.4f at (%7.2f,%7.2f,%7.2f)  <-> face %-5s "
          "area %7.4f at (%7.2f,%7.2f,%7.2f)"
          % (d, i, areas[i], c.x, c.y, c.z, j, areas[j], c2.x, c2.y, c2.z))
    for s in tools_on(faces[i])[:4]:
        print("      face %s on tool %s" % (i, s))
    for s in tools_on(faces[j])[:4]:
        print("      face %s on tool %s" % (j, s))
    sys.stdout.flush()

print("\n== thin points from the mesh scan ==")
for p in POINTS:
    x, y, z, wall = p["at"][0], p["at"][1], p["at"][2], p["wall"]
    v = cq.Vector(x, y, z)
    near = []
    for i in near_point((x, y, z), 0.45):
        d = faces[i].distance(v)
        if d < 0.45:
            near.append((d, i))
    near.sort()
    print("point (%7.2f,%7.2f,%7.2f) mesh wall %.3f mm: %d faces within 0.45 mm"
          % (x, y, z, wall, len(near)))
    for d, i in near[:6]:
        c = centers[i]
        print("   face %-5s area %7.4f mm2 centre (%7.2f,%7.2f,%7.2f) dist %.4f"
              % (i, areas[i], c.x, c.y, c.z, d))
        for s in tools_on(faces[i])[:6]:
            print("        on tool %s" % s)
    sys.stdout.flush()
