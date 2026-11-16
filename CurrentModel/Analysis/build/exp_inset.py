"""Experiment: pull the lattice's ovals back from the rib lines and column
edges by INSET mm, so no cut boundary is tangent to a rib.

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

INSET = float(os.environ.get("INSET", "0.5"))


def column_bounds(psi, side):
    x = h.skin_point(psi, h.T / 2)[0]
    m = math.asin((h.RIB / 2 + INSET) / x)
    th_in, th_out = m, math.radians(h.HALF) - m
    return (th_in, th_out) if side > 0 else (-th_out, -th_in)


def oval_on_skin(p0, p1, side, n=96):
    q0 = p0 + (h.RIB / 2 + INSET) / h.ds_dpsi(p0)
    q1 = p1 - (h.RIB / 2 + INSET) / h.ds_dpsi(p1)
    out = []
    for i in range(n):
        t = 2 * math.pi * i / n
        c_, s_ = math.cos(t), math.sin(t)
        a_ = math.copysign(abs(c_) ** (2 / h.OVAL_N), c_)
        b_ = math.copysign(abs(s_) ** (2 / h.OVAL_N), s_)
        psi = (q0 + q1) / 2 + b_ * (q1 - q0) / 2
        lo, hi = column_bounds(psi, side)
        out.append(h.surface(psi, (lo + hi) / 2 + a_ * (hi - lo) / 2))
    return out


h.column_bounds = column_bounds
h.oval_on_skin = oval_on_skin

s = h.build()
if h.PIECES:
    for k, v in h.pieces(s).items():
        report(k, v)
else:
    report("whole", s)
