#!/usr/bin/env python
"""f082 probe: where is the material thicker than one wall T?

The checker's inward ray measures a wall from a surface; a solid block fused
between two walls hides from it (every face of the block is bounded by another
surface). So this probe cuts the actual solid: a grid of points in the seam
plane, in/out of the material, and a distance transform that says how far each
material point is from air. Blobs whose interior reaches beyond one wall are
the thick material, in the model's own coordinates.

  /home/rhy/.venvs/cadquery/bin/python CurrentModel/Analysis/build/f082/thick_probe.py
"""
import math
import os
import sys

import cadquery as cq

HERE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
STEP = os.path.join(HERE, "CurrentModel", "CAD Files", "SimplifiedSlice",
                    "airship pie slice 1026.step")

sys.path.insert(0, os.path.join(HERE, "CurrentModel", "CAD Files", "SimplifiedSlice"))
import airship_slice as h   # noqa: E402

STEPFILE = sys.argv[1] if len(sys.argv) > 1 else STEP
s = cq.importers.importStep(STEPFILE).val()
print("shape", STEPFILE, "solids", len(s.Solids()), "volume", round(s.Volume() / 1000, 2), "cm3")

# the seam plane: phi = -HALF (the hole seam, the face the slice prints on)
phi = math.radians(-h.HALF)
cphi, sphi = math.cos(phi), math.sin(phi)
cell = 1.0
r0, r1 = 0.0, h.A + 6
z0, z1 = -h.B - 4, h.B + 4
nr, nz = int((r1 - r0) / cell) + 1, int((z1 - z0) / cell) + 1
print("grid %d x %d at %.1f mm in the seam plane phi=%.1f deg" % (nr, nz, cell, -h.HALF))

solid = s.Solids()[0] if len(s.Solids()) == 1 else s
grid = [[0] * nz for _ in range(nr)]
for i in range(nr):
    r = r0 + i * cell
    for j in range(nz):
        z = z0 + j * cell
        p = cq.Vector(r * cphi, r * sphi, z)
        if solid.isInside(p, 1e-6):
            grid[i][j] = 1

# distance transform: how far this material point is from air (in mm)
INF = 1e9
dist = [[INF if grid[i][j] else 0.0 for j in range(nz)] for i in range(nr)]
for i in range(nr):                       # chamfer pass 1: up and left
    for j in range(nz):
        d = dist[i][j]
        if i and dist[i - 1][j] + cell < d:
            d = dist[i - 1][j] + cell
        if j and dist[i][j - 1] + cell < d:
            d = dist[i][j - 1] + cell
        dist[i][j] = d
for i in range(nr - 1, -1, -1):           # chamfer pass 2: down and right
    for j in range(nz - 1, -1, -1):
        d = dist[i][j]
        if i + 1 < nr and dist[i + 1][j] + cell < d:
            d = dist[i + 1][j] + cell
        if j + 1 < nz and dist[i][j + 1] + cell < d:
            d = dist[i][j + 1] + cell
        dist[i][j] = d

# blobs of material whose interior is thicker than one wall
THICK = h.T + 0.25
seen = [[False] * nz for _ in range(nr)]
blobs = []
for i in range(nr):
    for j in range(nz):
        if grid[i][j] and not seen[i][j] and dist[i][j] > THICK / 2:
            stack, pts = [(i, j)], []
            seen[i][j] = True
            while stack:
                a, b = stack.pop()
                pts.append((a, b))
                for di, dj in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    c_, d_ = a + di, b + dj
                    if 0 <= c_ < nr and 0 <= d_ < nz and grid[c_][d_] \
                            and dist[c_][d_] > THICK / 2 and not seen[c_][d_]:
                        seen[c_][d_] = True
                        stack.append((c_, d_))
            area = len(pts) * cell * cell
            thick = 2 * max(dist[a][b] for a, b in pts)
            rs = [r0 + a * cell for a, _ in pts]
            zs = [z0 + b * cell for _, b in pts]
            blobs.append((area, thick, sum(rs) / len(rs), sum(zs) / len(zs),
                          min(rs), max(rs), min(zs), max(zs)))
blobs.sort(key=lambda b_: -b_[0])
print("\n%d thick blobs (material whose interior is over %.2f mm from air):"
      % (len(blobs), THICK / 2))
for area, thick, rc, zc, rmin, rmax, zmin, zmax in blobs[:25]:
    print("  %7.0f mm2  local thickness %5.2f mm  centre r=%6.1f z=%7.1f  "
          "r %.0f..%.0f z %.0f..%.0f" % (area, thick, rc, zc, rmin, rmax, zmin, zmax))

# an ASCII map of the seam cross-section, 4 mm cells, so the shape is visible
print("\nseam cross-section map (# material, . air, B thick interior):")
step = 4
for j in range(nz - 1, -1, -step):
    row = []
    for i in range(0, nr, step):
        if not grid[i][j]:
            row.append(".")
        elif dist[i][j] > THICK / 2:
            row.append("B")
        else:
            row.append("#")
    print("z=%7.1f %s" % (z0 + j * cell, "".join(row)))
print("PROBE DONE")
