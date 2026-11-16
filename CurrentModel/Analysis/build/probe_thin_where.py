"""Scratch probe: where exactly are the thin walls in a shipped STL?
Same raycast as check_outputs.wall_thickness, but it reports the positions."""
import math, os, sys
import Mesh

CUR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
args = [a for a in sys.argv[1:] if a.lower().endswith(".stl")]
PATH = args[0] if args else os.path.join(CUR, "Print Files", "PieSlice1026-v0.2.1-8T.stl")
MAXD, CELL, SAMPLES = 4.0, 1.0, 20000

m = Mesh.Mesh(PATH)
pts, facets = m.Topology
P = [(p.x, p.y, p.z) for p in pts]
cen, nor, grid = {}, {}, {}
for i, f in enumerate(facets):
    a, b, c = (P[f[0]], P[f[1]], P[f[2]])
    ux, uy, uz = b[0]-a[0], b[1]-a[1], b[2]-a[2]
    vx, vy, vz = c[0]-a[0], c[1]-a[1], c[2]-a[2]
    nx, ny, nz = uy*vz-uz*vy, uz*vx-ux*vz, ux*vy-uy*vx
    ln = math.sqrt(nx*nx+ny*ny+nz*nz)
    cx, cy, cz = (a[0]+b[0]+c[0])/3.0, (a[1]+b[1]+c[1])/3.0, (a[2]+b[2]+c[2])/3.0
    cen[i] = (cx, cy, cz)
    if ln < 1e-12:
        continue
    nor[i] = (nx/ln, ny/ln, nz/ln)
    grid.setdefault((int(cx//CELL), int(cy//CELL), int(cz//CELL)), []).append(i)

reach = int(MAXD/CELL)+1
d2max = MAXD*MAXD
res = []
step = max(1, len(facets)//SAMPLES)
for i in range(0, len(facets), step):
    if i not in nor:
        continue
    c, n = cen[i], nor[i]
    ox, oy, oz = c[0]+n[0]*0.005, c[1]+n[1]*0.005, c[2]+n[2]*0.005
    dx, dy, dz = -n[0], -n[1], -n[2]
    kx, ky, kz = int(ox//CELL), int(oy//CELL), int(oz//CELL)
    best = None
    for gx in range(kx-reach, kx+reach+1):
        for gy in range(ky-reach, ky+reach+1):
            for gz in range(kz-reach, kz+reach+1):
                for j in grid.get((gx, gy, gz), ()):
                    if j == i:
                        continue
                    cc = cen[j]
                    ex, ey, ez = cc[0]-ox, cc[1]-oy, cc[2]-oz
                    if ex*ex+ey*ey+ez*ez > d2max:
                        continue
                    ax, ay, az = P[facets[j][0]]
                    e1 = (P[facets[j][1]][0]-ax, P[facets[j][1]][1]-ay, P[facets[j][1]][2]-az)
                    e2 = (P[facets[j][2]][0]-ax, P[facets[j][2]][1]-ay, P[facets[j][2]][2]-az)
                    pv = (dy*e2[2]-dz*e2[1], dz*e2[0]-dx*e2[2], dx*e2[1]-dy*e2[0])
                    det = e1[0]*pv[0]+e1[1]*pv[1]+e1[2]*pv[2]
                    if abs(det) < 1e-9:
                        continue
                    tx, ty, tz = ox-ax, oy-ay, oz-az
                    u = (tx*pv[0]+ty*pv[1]+tz*pv[2])/det
                    if u < -1e-9 or u > 1+1e-9:
                        continue
                    q = (ty*e1[2]-tz*e1[1], tz*e1[0]-tx*e1[2], tx*e1[1]-ty*e1[0])
                    v = (dx*q[0]+dy*q[1]+dz*q[2])/det
                    if v < -1e-9 or u+v > 1+1e-9:
                        continue
                    t = (e2[0]*q[0]+e2[1]*q[1]+e2[2]*q[2])/det
                    if t > 0.005 and t <= MAXD and (best is None or t < best):
                        best = t
    if best is not None:
        res.append((best, c))
res.sort()
thin = [r for r in res if r[0] < 0.40]
print(f"{PATH}\n{len(res)} rays hit, {len(thin)} under 0.40 mm, {sum(1 for r in res if r[0]<0.20)} under 0.20 mm")
for t, c in res[:25]:
    # STL pose = Rx(90) * Rz(22.5) * model point, so undo it for the model frame
    a = math.radians(-22.5)
    qx, qy, qz = c[0], c[2], -c[1]
    mx = qx * math.cos(a) - qy * math.sin(a)
    my = qx * math.sin(a) + qy * math.cos(a)
    r = math.hypot(mx, my)
    print("  %7.3f mm  stl %8.2f %8.2f %8.2f  model %8.2f %8.2f %8.2f  r %7.2f phi %7.2f"
          % (t, *c, mx, my, qz, r, math.degrees(math.atan2(my, mx))))
