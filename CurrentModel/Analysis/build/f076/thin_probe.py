#!/usr/bin/env python
"""f076: where are the thinnest walls in an STL? Same raycast as
check_outputs.py wall_thickness, but it keeps the positions.

  flatpak run --command=freecadcmd org.freecad.FreeCAD \
      CurrentModel/Analysis/build/f076/thin_probe.py --pass "<stl path>"
"""
import sys
import os
import shlex
import math
import Mesh

me = os.path.splitext(os.path.abspath(__file__))[0]
argv = [a for a in sys.argv[1:] if os.path.splitext(os.path.abspath(a))[0] != me]
path = shlex.split(" ".join(a for a in argv if a != "--pass"))[0]
print("opening", path)
m = Mesh.Mesh(path)
pts, facets = m.Topology
P = [(p.x, p.y, p.z) for p in pts]
cen, nor, grid = {}, {}, {}
cell = 1.0
for i, f in enumerate(facets):
    a, b, c = (P[f[0]], P[f[1]], P[f[2]])
    ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
    nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
    ln = math.sqrt(nx * nx + ny * ny + nz * nz)
    cx, cy, cz = (a[0] + b[0] + c[0]) / 3.0, (a[1] + b[1] + c[1]) / 3.0, (a[2] + b[2] + c[2]) / 3.0
    cen[i] = (cx, cy, cz)
    if ln < 1e-12:
        nor[i] = None
        continue
    nor[i] = (nx / ln, ny / ln, nz / ln)
    grid.setdefault((int(cx // cell), int(cy // cell), int(cz // cell)), []).append(i)

max_depth, samples = 4.0, 20000
step = max(1, len(facets) // samples)
reach = int(max_depth / cell) + 1
d2max = max_depth * max_depth
out = []
for i in range(0, len(facets), step):
    if nor.get(i) is None:
        continue
    c, n = cen[i], nor[i]
    ox, oy, oz = c[0] + n[0] * 0.005, c[1] + n[1] * 0.005, c[2] + n[2] * 0.005
    dx, dy, dz = -n[0], -n[1], -n[2]
    kx, ky, kz = int(ox // cell), int(oy // cell), int(oz // cell)
    best = None
    for gx in range(kx - reach, kx + reach + 1):
        for gy in range(ky - reach, ky + reach + 1):
            for gz in range(kz - reach, kz + reach + 1):
                for j in grid.get((gx, gy, gz), ()):
                    if j == i:
                        continue
                    cc = cen[j]
                    ex, ey, ez = cc[0] - ox, cc[1] - oy, cc[2] - oz
                    if ex * ex + ey * ey + ez * ez > d2max:
                        continue
                    ax, ay, az = P[facets[j][0]]
                    e1 = (P[facets[j][1]][0] - ax, P[facets[j][1]][1] - ay,
                          P[facets[j][1]][2] - az)
                    e2 = (P[facets[j][2]][0] - ax, P[facets[j][2]][1] - ay,
                          P[facets[j][2]][2] - az)
                    pv = (dy * e2[2] - dz * e2[1], dz * e2[0] - dx * e2[2],
                          dx * e2[1] - dy * e2[0])
                    det = e1[0] * pv[0] + e1[1] * pv[1] + e1[2] * pv[2]
                    if abs(det) < 1e-9:
                        continue
                    tx, ty, tz = ox - ax, oy - ay, oz - az
                    u = (tx * pv[0] + ty * pv[1] + tz * pv[2]) / det
                    if u < -1e-9 or u > 1 + 1e-9:
                        continue
                    q = (ty * e1[2] - tz * e1[1], tz * e1[0] - tx * e2[2],
                         tx * e1[1] - ty * e1[0])
                    v = (dx * q[0] + dy * q[1] + dz * q[2]) / det
                    if v < -1e-9 or u + v > 1 + 1e-9:
                        continue
                    t = (e2[0] * q[0] + e2[1] * q[1] + e2[2] * q[2]) / det
                    if t > 0.005 and t <= max_depth and (best is None or t < best):
                        best = t
    if best is not None:
        out.append((best, c, n))
out.sort()
print("%s: %d sampled facets, %d under 0.40 mm, %d under 0.20 mm"
      % (path, len(out), sum(1 for t, _, _ in out if t < 0.40),
         sum(1 for t, _, _ in out if t < 0.20)))
for t, c, n in out[:14]:
    r = math.hypot(c[0], c[1])
    print("  %.3f mm at (%7.2f,%7.2f,%7.2f)  r %6.1f z %6.1f  az %6.1f deg  normal (%5.2f,%5.2f,%5.2f)"
          % (t, c[0], c[1], c[2], r, c[2], math.degrees(math.atan2(c[1], c[0])), n[0], n[1], n[2]))
sys.stdout.flush()
