"""Probe: what does each window cutter's outline look like?

Run:  /home/rhy/.venvs/cadquery/bin/python CurrentModel/Analysis/build/probe_windows.py
Records every outline handed to skin_cutter() and measures its minimum feature
size with shapely (opening by r removes every feature narrower than 2r).
"""
import os
import sys

import cadquery as cq

_CUR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(_CUR, "CAD Files", "SimplifiedSlice"))

import airship_slice as h
from shapely.geometry import Polygon


def project(pts):
    """Same flat projection skin_cutter() uses, so the uv polygon is the one
    that actually gets extruded."""
    c = sum((p for p, _ in pts), cq.Vector()) * (1 / len(pts))
    nrm = sum((nv for _, nv in pts), cq.Vector()).normalized()
    xd = (pts[0][0] - c)
    xd = (xd - nrm * xd.dot(nrm)).normalized()
    yd = nrm.cross(xd)
    return [(float((p - c).dot(xd)), float((p - c).dot(yd))) for p, _ in pts]


def stats(pts):
    g = Polygon(project(pts))
    if not g.is_valid:
        g = g.buffer(0)
    a = g.area
    out = ["area {:8.2f}".format(a), "per {:7.1f}".format(g.length)]
    for r in (0.1, 0.2, 0.3, 0.5):
        o = g.buffer(-r).buffer(r)
        out.append("lost@{} {:6.1f}%".format(r, 100 * (1 - o.area / a) if a > 0 else 0))
    return " ".join(out)


orig = h.skin_cutter


def patched(pts):
    try:
        s = stats(pts)
    except Exception as exc:
        s = "stats failed: {}".format(exc)
    c = sum((p for p, _ in pts), cq.Vector()) * (1 / len(pts))
    print("cut at {:8.1f} {:8.1f} {:8.1f}  n {:3d}  {}".format(c.x, c.y, c.z, len(pts), s))
    return orig(pts)


h.skin_cutter = patched

print("variant {} side {} N {} scale {} pieces {} rib {}".format(
    h.VARIANT, h.SIDE, h.N, h.SCALE, h.PIECES, h.RIB))
w = h.windows()
print("{} cutters".format(len(w)))
