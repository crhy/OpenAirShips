"""Probe: is the outline that skin_cutter extrudes valid, and does it have
near-coincident points? Run with the variant's OAS_* set, cadquery venv.
"""
import math
import os
import sys

import cadquery as cq

_CUR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(_CUR, "CAD Files", "SimplifiedSlice"))
import airship_slice as h          # noqa: E402
from shapely.geometry import Polygon
from shapely.validation import explain_validity


def project(pts):
    c = sum((p for p, _ in pts), cq.Vector()) * (1 / len(pts))
    nrm = sum((nv for _, nv in pts), cq.Vector()).normalized()
    xd = (pts[0][0] - c)
    xd = (xd - nrm * xd.dot(nrm)).normalized()
    yd = nrm.cross(xd)
    return [(float((p - c).dot(xd)), float((p - c).dot(yd))) for p, _ in pts], c


orig = h.skin_cutter


def patched(pts):
    uv, c = project(pts)
    g = Polygon(uv)
    bad = [i for i in range(len(uv))
           for j in range(i + 2, len(uv))
           if not (i == 0 and j == len(uv) - 1) and math.dist(uv[i], uv[j]) < 0.4]
    print("cut at ({:7.1f},{:6.1f},{:6.1f}) n {:3d} valid {} area {:8.1f} per {:6.1f} "
          "closepairs {:3d} {}".format(
              c.x, c.y, c.z, len(uv), g.is_valid, g.area, g.length, len(bad),
              explain_validity(g) if not g.is_valid else ""))
    return orig(pts)


h.skin_cutter = patched
print("variant {} side {} N {} scale {} pieces {} rib {}".format(
    h.VARIANT, h.SIDE, h.N, h.SCALE, h.PIECES, h.RIB))
w = h.windows()
print("{} cutters".format(len(w)))
