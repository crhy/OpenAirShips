"""One junction window's cutter, on its own: does the cutter itself have slivers?

Run from the repo root, cadquery venv, with the variant's OAS_* set.
"""
import math
import os
import sys

import cadquery as cq

_CUR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(_CUR, "CAD Files", "SimplifiedSlice"))
import airship_slice as h          # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from exp_thin import scan          # noqa: E402

rows = h.skin_ribs()
nrows = len(rows) - 1


def turn(rings, deg):
    cs, sn = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    rot = lambda p: cq.Vector(p.x * cs - p.y * sn, p.x * sn + p.y * cs, p.z)
    return [[(rot(p), rot(nv)) for p, nv in r] for r in rings]


ovals = {k: [h.oval_on_skin(rows[k], rows[k + 1], sd) for sd in (-1, 1)] for k in range(nrows)}
c = h.cut_ribs()

for j, psi in enumerate(rows):
    if not (h.PIECES and any(abs(psi - q) < 1e-9 for q in c.values())):
        continue
    near = ovals.get(j - 1, []) + ovals.get(j, [])
    keep = 0 if 0 < j < nrows else (1 if j == 0 else -1)
    for th, around in [(0.0, near), (-h.HALF, near + turn(near, -2 * h.HALF)), (h.HALF, near + turn(near, 2 * h.HALF))]:
        for side_ in ((1, -1) if h.PIECES else (keep,)):
            pts = h.junction(psi, math.radians(th), around, side_)
            if pts is None:
                continue
            cut = h.skin_cutter(pts)
            if th != 0.0:
                cut = cut.intersect(h.column(0))
            print("psi={:.4f} theta={:.0f} side={:2d}  faces {:4d}  vol {:9.1f}  valid {}".format(
                psi, th, side_, len(cut.Faces()), cut.Volume(), cut.isValid()))
            small = [f for f in cut.Faces() if f.Area() < 8.0]
            vs, tris = cut.tessellate(0.02, 0.1)
            P = [(v.x, v.y, v.z) for v in vs]
            res = scan(P, tris)
            res.sort()
            thin = [r for r in res if r[0] < 0.40]
            print("   CUTTER thin: facets {} under 0.40 {} min {}".format(
                len(tris), len(thin), round(res[0][0], 4) if res else 0))
            for t, cc in thin[:4]:
                print("      {:6.3f} mm at ({:7.1f},{:6.1f},{:6.1f})".format(t, cc[0], cc[1], cc[2]))
            for f in sorted(small, key=lambda f: f.Area())[:8]:
                cc = f.Center()
                print("   sliver face area {:7.3f} {:20} at ({:7.1f},{:6.1f},{:6.1f})".format(
                    f.Area(), f.geomType(), cc.x, cc.y, cc.z))
