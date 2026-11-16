"""Experiment: does insetting the window outline (or a finer skin shell)
remove the thin spikes from the cutters?

Run from the repo root, cadquery venv, with the variant's OAS_* set:
  INSET=0.4 SHELL_N=400 python CurrentModel/Analysis/build/exp_cutter_fix.py
"""
import math
import os
import sys

import cadquery as cq

_CUR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(_CUR, "CAD Files", "SimplifiedSlice"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import airship_slice as h          # noqa: E402
from exp_thin import scan          # noqa: E402

INSET = float(os.environ.get("INSET", "0"))
SHELL_N = int(os.environ.get("SHELL_N", "400"))
SHELL_M = float(os.environ.get("SHELL_M", "0.5"))


def rebuild_shell():
    """Same shell, but with the given segment count and margin."""
    top, n = math.pi / 2 - 0.02, SHELL_N
    ts = [-math.pi / 2 + (top + math.pi / 2) * i / n for i in range(n + 1)]
    outer = [((A + SHELL_M) * math.cos(t), (B + SHELL_M) * math.sin(t)) for t in ts]
    inner = [((A - T - SHELL_M) * math.cos(t), (B - T - SHELL_M) * math.sin(t)) for t in reversed(ts)]
    return h.wedge(outer + inner, half=h.HALF + 3)


A, B, T = h.A, h.B, h.T
h._SHELL = None
_orig_shell = h.skin_shell


def shell_patched():
    global A, B, T
    return rebuild_shell()


h.skin_shell = shell_patched

orig_cutter = h.skin_cutter


def cutter_patched(pts):
    """Inset the outline by INSET before extruding (a clamp, not a drop)."""
    if INSET == 0:
        return orig_cutter(pts)
    c = sum((p for p, _ in pts), cq.Vector()) * (1 / len(pts))
    nrm = sum((nv for _, nv in pts), cq.Vector()).normalized()
    xd = (pts[0][0] - c)
    xd = (xd - nrm * xd.dot(nrm)).normalized()
    yd = nrm.cross(xd)
    uv = [(float((p - c).dot(xd)), float((p - c).dot(yd))) for p, _ in pts]
    from shapely.geometry import Polygon
    g = Polygon(uv).buffer(-INSET, join_style=2)
    if g.is_empty:
        return None
    if g.geom_type != "Polygon":
        g = max(g.geoms, key=lambda q: q.area)
    ring = list(g.exterior.coords)[:-1]
    span = max((q.distance(r) for q in ring for r in ring))
    dev = max(abs((p - c).dot(nrm)) for p, _ in pts) + 0.25 * span + T + 3.0
    prism = (cq.Workplane(cq.Plane(origin=c, xDir=xd, normal=nrm)).polyline(ring).close()
             .extrude(dev, both=True).val())
    out = prism.intersect(h.skin_shell())
    return out


h.skin_cutter = cutter_patched

cut = h.windows()
tot_thin = 0
worst = 9.9
for sld in cut:
    vs, tris = sld.tessellate(0.02, 0.1)
    P = [(v.x, v.y, v.z) for v in vs]
    res = scan(P, tris)
    res.sort()
    thin = [r for r in res if r[0] < 0.40]
    tot_thin += len(thin)
    if res:
        worst = min(worst, res[0][0])
print("{} cutters  INSET {}  shell n {} margin {}:  thin facets {}  worst {:.4f} mm".format(
    len(cut), INSET, SHELL_N, SHELL_M, tot_thin, worst))
