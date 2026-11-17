#!/usr/bin/env python
"""f076 probe: which clip line bites which window, and by how much?

Replicates clip_window's three constraints step by step for every oval and
junction of the 8T bench build. Run from SimplifiedSlice:
  OAS_VARIANT=8T OAS_SLICES=8 OAS_SCALE=1 python probe_clip.py
"""
import math
import airship_slice as S
from shapely.geometry import Polygon


def lines_for(psi, theta, poly, x0):
    psi_lo, psi_hi, th_half = S.lattice_band()
    u_lo, v_lo, u_hi, v_hi = poly.bounds
    out = []
    for ps in (psi_hi - S.MIN_WEB / S.ds_dpsi(psi_hi), psi_lo + S.MIN_WEB / S.ds_dpsi(psi_lo)):
        span = (max(abs(u_lo), abs(u_hi)) + 2 * S.MIN_WEB) / x0
        out.append(("band", [S.skin_frame(psi, theta)[0](S.surface(ps, theta - span + 2 * span * i / 12)[0])
                             for i in range(13)], (0.0, 0.0)))
    for th_side, inward in ((th_half, -1.0), (-th_half, 1.0)):
        span = (max(abs(v_lo), abs(v_hi)) + 2 * S.MIN_WEB) / S.ds_dpsi(psi)
        ps_vals = [psi - span + 2 * span * i / 12 for i in range(13)]
        rho_min = min(S.skin_point(q, S.T / 2)[0] for q in ps_vals)
        sin_d = max(-1.0, min(1.0, S.MIN_WEB * x0 / rho_min ** 2))
        out.append(("seam", [S.skin_frame(psi, theta)[0](S.surface(q, th_side + inward * math.asin(sin_d))[0])
                             for q in ps_vals], (inward, 0.0)))
    return out


rows = S.skin_ribs()
ovals = {k: [S.oval_on_skin(rows[k], rows[k + 1], sd) for sd in (-1, 1)] for k in range(len(rows) - 1)}
print("ovals: %d cells" % (2 * len(ovals)))
for k in sorted(ovals):
    for side, ring in ((-1, ovals[k][0]), (1, ovals[k][1])):
        psi = (rows[k] + rows[k + 1]) / 2
        to_uv, to_skin, sgn = S.skin_frame(psi, 0.0)
        poly = Polygon([to_uv(p) for p, _ in ring]).buffer(-0.6).buffer(0.6)
        a0 = poly.area
        x0 = S.skin_point(psi, S.T / 2)[0]
        lost = []
        for name, line, inside in lines_for(psi, 0.0, poly, x0):
            hp = S.half_plane(line, inside)
            q = poly.intersection(hp)
            lost.append((name, round(a0 - q.area, 2)))
            poly = q
        if any(abs(v) > 0.01 for _, v in lost):
            print("  row %d side %+d psi %.3f  area %.1f  lost %s" % (k, side, psi, a0, lost))
        # and what the round trip does to the outline
        ring2 = [to_skin(x, y) for x, y in poly.exterior.coords[:-1]]
        d = max((p[0] - q[0]).Length for p, q in zip(ring, ring2)) if len(ring) == len(ring2) else None
print("\nround trip check: an oval's own outline, mapped out and back")
k = 5
psi = (rows[k] + rows[k + 1]) / 2
to_uv, to_skin, sgn = S.skin_frame(psi, 0.0)
ring = ovals[k][0]
back = [to_skin(*to_uv(p)) for p, _ in ring]
print("  worst displacement %.3f mm over %d points"
      % (max((p - q).Length for p, q in zip(ring, back)), len(ring)))
