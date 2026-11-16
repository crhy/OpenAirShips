"""Fast experiment loop: build one variant, mesh it, count thin facets.

Run from the repo root with the cadquery venv:
  OAS_VARIANT=4T OAS_SLICES=12 OAS_THRUSTER=S OAS_PIECES=1 OAS_SCALE=3.8 \
  OAS_RIB=1.2 OAS_SIDE=P /home/rhy/.venvs/cadquery/bin/python \
      CurrentModel/Analysis/build/exp_thin.py [piece ...]
Uses the same ray-cast wall scan as check_outputs.py, on the same tessellation
(LinearDeflection 0.02, AngularDeflection 0.1).
"""
import math
import os
import sys
import time

import cadquery as cq

_CUR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(_CUR, "CAD Files", "SimplifiedSlice"))
import airship_slice as h          # noqa: E402

NOZZLE, LAYER, MAXD, CELL = 0.40, 0.20, 4.0, 1.0


def scan(P, F):
    cen, nor, grid = {}, {}, {}
    for i, f in enumerate(F):
        a, b, c = (P[f[0]], P[f[1]], P[f[2]])
        ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
        vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
        nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
        ln = math.sqrt(nx * nx + ny * ny + nz * nz)
        cx, cy, cz = (a[0] + b[0] + c[0]) / 3.0, (a[1] + b[1] + c[1]) / 3.0, (a[2] + b[2] + c[2]) / 3.0
        cen[i] = (cx, cy, cz)
        nor[i] = (nx / ln, ny / ln, nz / ln) if ln > 1e-12 else None
        grid.setdefault((int(cx // CELL), int(cy // CELL), int(cz // CELL)), []).append(i)
    reach = int(MAXD / CELL) + 1
    res = []
    for i, f in enumerate(F):
        if nor[i] is None:
            continue
        c, n = cen[i], nor[i]
        ox, oy, oz = c[0] + n[0] * 0.005, c[1] + n[1] * 0.005, c[2] + n[2] * 0.005
        dx, dy, dz = -n[0], -n[1], -n[2]
        kx, ky, kz = int(ox // CELL), int(oy // CELL), int(oz // CELL)
        best = None
        for gx in range(kx - reach, kx + reach + 1):
            for gy in range(ky - reach, ky + reach + 1):
                for gz in range(kz - reach, kz + reach + 1):
                    for j in grid.get((gx, gy, gz), ()):
                        if j == i:
                            continue
                        cc = cen[j]
                        ex, ey, ez = cc[0] - ox, cc[1] - oy, cc[2] - oz
                        if ex * ex + ey * ey + ez * ez > MAXD * MAXD:
                            continue
                        ax, ay, az = P[F[j][0]]
                        e1 = (P[F[j][1]][0] - ax, P[F[j][1]][1] - ay, P[F[j][1]][2] - az)
                        e2 = (P[F[j][2]][0] - ax, P[F[j][2]][1] - ay, P[F[j][2]][2] - az)
                        pv = (dy * e2[2] - dz * e2[1], dz * e2[0] - dx * e2[2], dx * e2[1] - dy * e2[0])
                        det = e1[0] * pv[0] + e1[1] * pv[1] + e1[2] * pv[2]
                        if abs(det) < 1e-9:
                            continue
                        tx, ty, tz = ox - ax, oy - ay, oz - az
                        u = (tx * pv[0] + ty * pv[1] + tz * pv[2]) / det
                        if u < -1e-9 or u > 1 + 1e-9:
                            continue
                        q = (ty * e1[2] - tz * e1[1], tz * e1[0] - tx * e1[2], tx * e1[1] - ty * e1[0])
                        v = (dx * q[0] + dy * q[1] + dz * q[2]) / det
                        if v < -1e-9 or u + v > 1 + 1e-9:
                            continue
                        t = (e2[0] * q[0] + e2[1] * q[1] + e2[2] * q[2]) / det
                        if t > 0.005 and t <= MAXD and (best is None or t < best):
                            best = t
        if best is not None:
            res.append((best, cen[i]))
    return res


def report(name, shape):
    vs, tris = shape.tessellate(0.02, 0.1)
    P = [(v.x, v.y, v.z) for v in vs]
    res = scan(P, tris)
    res.sort()
    thin = [r for r in res if r[0] < NOZZLE]
    print("{:14} facets {:6d}  under {:.2f} {:4d}  min {:.4f}  faces {:5d}  valid {}".format(
        name, len(tris), NOZZLE, len(thin), res[0][0] if res else 0.0,
        len(shape.Faces()), shape.isValid()))
    for t, c in thin[:6]:
        print("      {:6.3f} mm at ({:7.1f},{:6.1f},{:6.1f})".format(t, c[0], c[1], c[2]))


if __name__ == "__main__":
    want = sys.argv[1:] or ["top_outer", "top_inner", "middle", "bottom_outer", "bottom_inner"]
    t0 = time.time()
    s = h.build()
    print("slice volume {:.0f} cm3 faces {}  build {:.0f}s".format(
        s.Volume() / 1000, len(s.Faces()), time.time() - t0))
    if h.PIECES:
        for k, v in h.pieces(s).items():
            if k in want:
                report(k, v)
    else:
        report("whole", s)
