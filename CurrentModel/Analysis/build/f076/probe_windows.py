#!/usr/bin/env python
"""f076 probe: what does windows() ask the kernel to cut, and where?

Instruments skin_cutter so every window outline is measured before it becomes
a solid. Run from the SimplifiedSlice folder with the cadquery venv:
  OAS_VARIANT=8T OAS_SLICES=8 OAS_SCALE=1 python probe_windows.py
"""
import math
import airship_slice as S

def psi_of(p):
    return math.atan2(p.z * S.A, math.hypot(p.x, p.y) * S.B)

def az_of(p):
    return math.atan2(p.y, p.x)

def seam_dist(p):
    """perpendicular distance from each of the slice's two seam planes"""
    r = math.hypot(p.x, p.y)
    a = az_of(p)
    return min(abs(r * math.sin(math.radians(S.HALF) - a)),
               abs(r * math.sin(math.radians(-S.HALF) - a)))

rows = S.skin_ribs()
print("skin ribs psi %.4f .. %.4f (%d ribs, %d rows); bellmouth psi %.4f"
      % (rows[0], rows[-1], len(rows), len(rows) - 1, S.intake()[1]))
print("T %.2f RIB %.2f A %.1f B %.1f N %d HALF %.1f PIECES %s"
      % (S.T, S.RIB, S.A, S.B, S.N, S.HALF, S.PIECES))

rec = []
orig = S.skin_cutter
def patched(pts):
    out = orig(pts)
    ps = [psi_of(p) for p, _ in pts]
    ds = [seam_dist(p) for p, _ in pts]
    rec.append((out, min(ps), max(ps), min(ds), len(pts)))
    return out
S.skin_cutter = patched
cut = S.windows()
S.skin_cutter = orig

print("\n%d window cutters" % len(cut))
top, bot = rows[-1], rows[0]
over = under = near_seam = 0
print("outline psi range vs the band [%.4f, %.4f], and min distance to a seam plane:" % (bot, top))
for out, p0, p1, dmin, n in rec:
    sh = out
    tag = []
    if p1 > top:
        over += 1
        tag.append("over top %+.1f mm" % ((p1 - top) * S.B))
    if p0 < bot:
        under += 1
        tag.append("under first rib %+.1f mm" % ((p0 - bot) * S.B))
    if dmin < 0.4:
        near_seam += 1
        tag.append("seam %.3f mm" % dmin)
    c = out.Center()
    print("  n=%3d vol %8.1f at (%7.1f,%7.1f,%7.1f) psi %.3f..%.3f seam %.2f  %s"
          % (n, out.Volume(), c.x, c.y, c.z, p0, p1, dmin, "; ".join(tag)))
print("\ncutters past the top rib %d, past the first rib %d, within 0.4 mm of a seam %d"
      % (over, under, near_seam))
