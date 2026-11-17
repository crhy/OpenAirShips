"""f084 probe 4: which generator tools stand closer than MIN_WEB (0.4 mm) to
each other? A pair at 0.00-0.39 mm leaves a fin of skin that thin between the
two cuts - that is what the mesh checker calls a wall under the nozzle.

Run: /home/rhy/.venvs/cadquery/bin/python tool_pairs.py
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

tools = []
for i, w in enumerate(G.windows()):
    tools.append(("windows()[%d]" % i, w))
walls, bore = G.duct_solids()
tools.append(("duct_solids() walls", G.at_seams(walls)))
tools.append(("duct_solids() bore", G.at_seams(bore)))
stem, servo = G.stem_and_servo_holes()
tools.append(("stem_and_servo_holes() stem", G.at_seams(stem)))
tools.append(("stem_and_servo_holes() servo", servo.rotate((0, 0, 0), (0, 0, 1), -G.HALF)))
kp = G.outlet_keepout()
if kp is not None:
    tools.append(("outlet_keepout()", kp))
jp = G.joint_parts()
for kind, seq in (("hole", jp[1]), ("boss", jp[0]), ("sleeve", jp[3]), ("peg", jp[2])):
    for i, s in enumerate(seq):
        tools.append(("joint_parts() %s[%d]" % (kind, i), s))
tools.append(("hatch_hole()", G.hatch_hole()))

bb = [t.BoundingBox() for _, t in tools]


def bb_near(a, b, tol):
    dx = max(a.xmin - b.xmax, b.xmin - a.xmax, 0.0)
    dy = max(a.ymin - b.ymax, b.ymin - a.ymax, 0.0)
    dz = max(a.zmin - b.zmax, b.zmin - a.zmax, 0.0)
    return math.sqrt(dx * dx + dy * dy + dz * dz) <= tol


print("%d tools" % len(tools))
sys.stdout.flush()
pairs = []
t0 = time.time()
for i in range(len(tools)):
    for j in range(i + 1, len(tools)):
        if not bb_near(bb[i], bb[j], 1.0):
            continue
        d = tools[i][1].distance(tools[j][1])
        if d < G.MIN_WEB:
            pairs.append((d, tools[i][0], tools[j][0]))
    print("  %d/%d tools in %.0f s, %d close pairs so far"
          % (i, len(tools), time.time() - t0, len(pairs)))
    sys.stdout.flush()

print("\n%d pairs closer than MIN_WEB %.2f mm" % (len(pairs), G.MIN_WEB))
for d, a, b in sorted(pairs):
    print("  %.3f mm  %-34s <-> %s" % (d, a, b))
