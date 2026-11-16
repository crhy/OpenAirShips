"""Experiment: keep the lattice's window cutters out of the joint bosses.

Run from the repo root, cadquery venv, with the variant's OAS_* set:
  CurrentModel/Analysis/build/exp_keepout.py [piece ...]
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

MARG = float(os.environ.get("MARG", "1.0"))


def joint_keepout():
    """A collar of solid skin round every joint: the seam bosses and pegs, and
    the bosses / pegs / holes that cross a piece cut. A window must not cut
    inside it, so the web between a window and a joint is >= MARG."""
    parts = []
    ph, pp = math.radians(-h.HALF), math.radians(h.HALF)
    for r, z in h.joints():
        for phi in (ph, pp):
            p, t = h.seam_axis(r, z, phi)
            parts.append(cq.Solid.makeCylinder(h.BOSS_D / 2 + MARG, 24, p - t * 12, t))
    for key, p, ax in h.cut_joints():
        parts.append(cq.Solid.makeCylinder(h.BOSS_D / 2 + MARG, 2 * h.BOSS_L + 20,
                                           p - ax * (h.BOSS_L + 10), ax))
    keep = parts[0]
    for q in parts[1:]:
        keep = keep.fuse(q)
    return keep


orig = h.outlet_keepout
h.outlet_keepout = lambda: (orig() if orig() is None else orig().fuse(joint_keepout()))

s = h.build()
for k, v in h.pieces(s).items():
    report(k, v)
