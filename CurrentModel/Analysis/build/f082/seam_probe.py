"""f082 probe: the seam face, cut open, and where its material is thicker than
one wall T.

The checker's inward ray measures a wall from a surface, so a solid block fused
between two walls hides from it. This cuts the actual solid with the seam plane
(section), chains the edges into closed loops, rasterises them on a 0.5 mm grid
in (r, z), and runs a distance transform: how far each material point is from
air. Anything whose interior reaches beyond one wall is thick material, and it
is reported in the model's own coordinates (r, z), with the joint positions
marked on the map.

  flatpak run --command=freecadcmd org.freecad.FreeCAD \
      CurrentModel/Analysis/build/f082/seam_probe.py --pass "[STEP path] [peg|hole]"
"""
import math
import sys

import FreeCAD as App
import Part

STEP = ("/home/rhy/strata-fleet/repos/OpenAirShips/CurrentModel/CAD Files/"
        "SimplifiedSlice/airship pie slice 1026.step")
args = [a for a in sys.argv[1:] if a not in ("--pass", "") and not a.endswith(".py")]
path = args[0] if args else STEP

# the 8T bench slice's constants (airship_slice.py, 8T, SCALE 1)
T, HALF, A, B = 0.86, 22.5, 207.765, 104.0
SHAFT_R, IMP_TIP_R, FLOOR_Z = 33.0, 44.0, -71.3
HATCH_R, LUG_R = 47.0, 44.6
DUCT_BORE, DUCT_MOUTH_R, DUCT_W = 24.0, 60.0, 0.86

s = Part.Shape()
s.read(path)
print("%s: solids %d volume %.2f cm3" % (path, len(s.Solids), s.Volume / 1000))
s.rotate(App.Vector(), App.Vector(0, 0, 1), HALF)     # the -HALF seam -> y = 0
face = Part.Face(Part.makePolygon([App.Vector(-5, 0, -B - 6), App.Vector(A + 6, 0, -B - 6),
                                   App.Vector(A + 6, 0, B + 6), App.Vector(-5, 0, B + 6),
                                   App.Vector(-5, 0, -B - 6)]))
sec = s.section(face)
chains = Part.sortEdges(sec.Edges)
print("section: %d edges in %d loops, total length %.0f mm"
      % (len(sec.Edges), len(chains), sec.Length))

loops = []
for ch in chains:
    dense = []
    for e in ch:
        n = max(2, int(e.Length / 0.25))
        try:
            pts = e.discretize(n + 1)
        except Exception:
            pts = e.discretize(Deflection=0.2)
        for p in pts:
            dense.append((p.x, p.z))
    if len(dense) > 2:
        loops.append(dense)
print("loops: %s" % ", ".join("%d pts %.0f mm" % (len(l),
      sum(math.hypot(l[i][0]-l[(i+1) % len(l)][0], l[i][1]-l[(i+1) % len(l)][1])
        for i in range(len(l)))) for l in loops))


def inside(poly, x, y):
    n, inside_ = len(poly), False
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside_ = not inside_
        j = i
    return inside_


box = [(min(p[0] for p in l), max(p[0] for p in l),
       min(p[1] for p in l), max(p[1] for p in l)) for l in loops]


cell = 0.5
r0, r1 = 0.0, A + 4
z0, z1 = -B - 4, B + 4
nr, nz = int((r1 - r0) / cell) + 1, int((z1 - z0) / cell) + 1
grid = [[0] * nz for _ in range(nr)]
for i in range(nr):
    r = r0 + i * cell
    for j in range(nz):
        z = z0 + j * cell
        k = 0
        for li, l in enumerate(loops):
            b = box[li]
            if b[0] <= r <= b[1] and b[2] <= z <= b[3] and inside(l, r, z):
                k += 1
        grid[i][j] = k % 2

INF = 1e9
dist = [[INF if grid[i][j] else 0.0 for j in range(nz)] for i in range(nr)]
for i in range(nr):
    for j in range(nz):
        d = dist[i][j]
        if i and dist[i - 1][j] + cell < d:
            d = dist[i - 1][j] + cell
        if j and dist[i][j - 1] + cell < d:
            d = dist[i][j - 1] + cell
        dist[i][j] = d
for i in range(nr - 1, -1, -1):
    for j in range(nz - 1, -1, -1):
        d = dist[i][j]
        if i + 1 < nr and dist[i + 1][j] + cell < d:
            d = dist[i + 1][j] + cell
        if j + 1 < nz and dist[i][j + 1] + cell < d:
            d = dist[i][j + 1] + cell
        dist[i][j] = d

THICK = T + 0.25
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
for area, thick, rc, zc, rmin, rmax, zmin, zmax in blobs[:20]:
    print("  %7.1f mm2  local thickness %5.2f mm  centre r=%6.1f z=%7.1f  "
          "r %.0f..%.0f z %.0f..%.0f" % (area, thick, rc, zc, rmin, rmax, zmin, zmax))

# the map: # material one wall thick, B thicker than one wall, . air
print("\nseam face (r across, 2 mm; z up, 2 mm): # = one wall, B = thick, . = air")
mark = {}
for r, z, tag in [(SHAFT_R + T + 3.3 / 2 + 0.6, -63.3 + 4.0, "S"),      # shaft joint
                  (IMP_TIP_R, FLOOR_Z + T + 3.5 - 0.5, "H"),           # housing ceiling
                  (53.0, -100.0, "K")]:                                # keel joint
    mark[(int((r - r0) / cell), int((z - z0) / cell))] = tag
step = 4
for j in range(nz - 1, -1, -step):
    row = []
    for i in range(0, nr, step):
        key = (i, j)
        if key in mark:
            row.append("@")
        elif not grid[i][j]:
            row.append(".")
        elif dist[i][j] > THICK / 2:
            row.append("B")
        else:
            row.append("#")
    print("z=%7.1f %s" % (z0 + j * cell, "".join(row)))
print("PROBE DONE")
