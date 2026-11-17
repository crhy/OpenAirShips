# f082 scratch: the same clearance maths as Analysis/check_outputs.py --joints,
# but in plain Python against the generator's own profiles, so the joints can be
# checked in seconds instead of after a full build.
import math
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..",
                                                "..", "CAD Files", "SimplifiedSlice")))
import airship_slice as h   # noqa: E402


def seg_dist(p, a, b):
    ax, ay = p
    vx, vy = b[0] - a[0], b[1] - a[1]
    L2 = vx * vx + vy * vy
    t = max(0.0, min(1.0, ((ax - a[0]) * vx + (ay - a[1]) * vy) / L2)) if L2 else 0.0
    return math.hypot(ax - (a[0] + t * vx), ay - (a[1] + t * vy))


def poly_inside(poly, x, y):
    n, inside_ = len(poly), False
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside_ = not inside_
        j = i
    return inside_


def gap(cx, cy, rad, poly):
    if poly_inside(poly, cx, cy):
        return 0.0
    return max(0.0, min(seg_dist((cx, cy), poly[i], poly[i - 1])
                        for i in range(len(poly))) - rad)


jm = h.joint_map()
clear = [(c["name"], c["kind"], [tuple(p) for p in c["profile"]]) for c in jm["keep_clear"]]
print("variant %s scale %s, wall %.2f, %d joints"
      % (jm["variant"], jm["scale"], jm["nominal_wall"], len(jm["joints"])))
for j in jm["joints"]:
    r, z = j["r"], j["z"]
    line = ["%-16s r=%7.2f z=%7.2f" % (j["name"], r, z),
            "fused: %s" % " + ".join(j["fused_to"])]
    worst = None
    for name, kind, prof in clear:
        for tool, rad in (("boss", j["boss_d"] / 2), ("peg", j["peg_d"] / 2),
                          ("hole", j["hole_d"] / 2)):
            if kind != "air2d" and tool != "hole" and kind == "air":
                continue
            if kind == "air" and tool != "hole":
                continue
            d = gap(r, z, rad, prof)
            line.append("%s-%s %.2f" % (tool, name[:12], d))
            if kind == "joint" and (worst is None or d < worst):
                worst = d
            if kind.startswith("air") and tool == "hole" and (j.get("airw") is None
                                                             or d < j["airw"]):
                j["airw"] = d
    print("  " + "  ".join(line))
    print("      worst to fan/housing: %s mm (needs %.1f)" % (worst, jm["joint_clear"]))
    print("      wall to air path:     %s mm (needs %.1f)"
          % (j.get("airw"), jm["air_keep"]))

# the central joint's distance from its two neighbours on the same wall
js = {j["name"]: (j["r"], j["z"]) for j in jm["joints"]}
for a, b in (("duct_top", "bulb_groove"),):
    (r1, z1), (r2, z2) = js[a], js[b]
    print("  %-16s to %-16s : %6.1f mm" % (a, b, math.hypot(r2 - r1, z2 - z1)))
print("SCRATCH DONE")
