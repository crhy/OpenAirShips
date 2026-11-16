"""Experiment: cut the windows with a slab extruded along each outline point's
own skin normal (a ruled loft), instead of a flat prism trimmed by the faceted
skin shell. Every wall then meets the skin at 90 degrees, so no cut surface can
graze another surface.

Run from the repo root, cadquery venv, with the variant's OAS_* set.
"""
import math
import os
import sys

import cadquery as cq

_CUR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(_CUR, "CAD Files", "SimplifiedSlice"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import airship_slice as h          # noqa: E402
from exp_thin import report        # noqa: E402

MARG = float(os.environ.get("MARG", "0.5"))


def skin_cutter(pts):
    d = h.T / 2 + MARG
    n = len(pts)

    def ring(off):
        r = [p + nv * off for p, nv in pts]
        return cq.Wire.assembleEdges([cq.Edge.makeLine(r[i], r[(i + 1) % n]) for i in range(n)])

    slab = cq.Solid.makeLoft([ring(-d), ring(d)], ruled=True)
    if slab.Volume() < 1.0:
        c = sum((p for p, _ in pts), cq.Vector()) * (1 / n)
        print("warning: empty window cutter at {:.0f}, {:.0f}, {:.0f}".format(c.x, c.y, c.z))
    return slab


h.skin_cutter = skin_cutter
s = h.build()
print("slice faces {} valid {}".format(len(s.Faces()), s.isValid()))
if h.PIECES:
    for k, v in h.pieces(s).items():
        report(k, v)
else:
    report("whole", s)
