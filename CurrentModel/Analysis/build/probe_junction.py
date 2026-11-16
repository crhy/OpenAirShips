"""Dump one junction window's outline in its own (u, v) plane.

Run from the repo root, cadquery venv, with the variant's OAS_* set:
  ... CurrentModel/Analysis/build/probe_junction.py
"""
import math
import os
import sys

import cadquery as cq

_CUR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(_CUR, "CAD Files", "SimplifiedSlice"))
import airship_slice as h          # noqa: E402

orig = h.junction


def wrapper(psi, theta, ovals, keep_side=0):
    pts = orig(psi, theta, ovals, keep_side)
    if pts is None:
        print("junction psi={:.4f} theta={:.0f} keep={} -> None".format(psi, math.degrees(theta), keep_side))
        return pts
    origin, nrm = h.surface(psi, theta)
    u = cq.Vector(-math.sin(theta), math.cos(theta), 0)
    v = nrm.cross(u)
    uv = [(float((p - origin).dot(u)), float((p - origin).dot(v))) for p, _ in pts]
    xs = [a for a, _ in uv]
    ys = [b for _, b in uv]
    print("junction psi={:.4f} theta={:.0f} keep={}  n={}  u[{:6.1f},{:6.1f}] v[{:6.1f},{:6.1f}]".format(
        psi, math.degrees(theta), keep_side, len(pts), min(xs), max(xs), min(ys), max(ys)))
    # consecutive-point spacing and the polygon's own area/perimeter
    per = sum(math.dist(uv[i], uv[(i + 1) % len(uv)]) for i in range(len(uv)))
    print("   perimeter {:.1f}  min step {:.2f}".format(
        per, min(math.dist(uv[i], uv[(i + 1) % len(uv)]) for i in range(len(uv)))))
    return pts


h.junction = wrapper
print("cut ribs", {k: round(v, 4) for k, v in h.cut_ribs().items()})
print("ribs", [round(r, 4) for r in h.skin_ribs()])
w = h.windows()
print("{} cutters".format(len(w)))
