#!/usr/bin/env python3
"""f156 item 2's checker: does the servo pad / equator brace stand PROUD of the hull?

rhY at the CR-10 Pro print (2026-11-19, crop 8): "Brace around the servo looks stupid and
isn't flush with the outer hull ellipse." The pad and the beam are fused tools; a tool whose
top cap sits above the skin's outer face leaves its whole footprint standing proud of the
ellipsoid, which breaks rule 14 (nothing but the window holes, the round stem/servo holes and
the four joint pegs may break the outer ellipsoid) and is what the slicer shows as a raised
patch. The wall map in Analysis/check_outputs.py cannot see it: it measures the thickness
BEHIND a facet, not how far the facet stands out.

This samples the print STLs' outer surface over the servo pad + beam region and reports the
radial deviation from the hull ellipse (scaled): dev = rho - A * sqrt(1 - (z / B)^2), in mm,
positive OUTSIDE the ellipsoid. It exits 1 if any outer point stands more than 0.05 mm proud.

    /home/rhy/.venvs/cadquery/bin/python -I CurrentModel/Analysis/check_flush.py
    ... check_flush.py --report          # more detail, no pass/fail print
"""
import math
import os
import sys

import numpy as np
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "CAD Files", "SimplifiedSlice"))
import airship_slice as h          # noqa: E402  (import only: nothing is built here)

REPO = os.path.abspath(os.path.join(HERE, ".."))          # CurrentModel/
PRINT = os.path.join(REPO, "Print Files")
# the two slices the gate prints, with the OAS_SCALE each was built at
FILES = [("PieSlice1026-v0.2.1-8T.stl", 1.0),
         ("PieSlice1026-v0.2.1-8T-CR10Pro.stl", 1.41)]
A0, B0 = h.A, h.B            # hull semi-axes at OAS_SCALE 1 (CONSTRUCTION-NOTES 1.1):
                             #   A is the RADIUS semi-axis, B the half-height
PROUD = 0.05                       # mm allowed past the ellipsoid before this fails
BAND = 0.25                        # the equatorial band sampled: |z| <= BAND * B
SEAM_MARGIN = 0.75                 # deg inside each seam plane (the slice's own side faces)


def to_model(v, half_deg):
    """Undo print_pose(): the STL lies on its -HALF seam (rotate +HALF about Z, then 90
    about X), so the model frame is -90 about X, then -HALF about Z (CONSTRUCTION-NOTES 1.3)."""
    x, y, z = v[:, 0], v[:, 1], v[:, 2]
    # -90 about X: (x, y, z) -> (x, z, -y)
    a, b, c = x, z, -y
    ang = math.radians(-half_deg)
    ca, sa = math.cos(ang), math.sin(ang)
    return np.column_stack([a * ca - b * sa, a * sa + b * ca, c])


def check(path, scale, report=False):
    A, B = A0 * scale, B0 * scale
    mesh = trimesh.load(path)
    v = to_model(np.asarray(mesh.vertices, dtype=float), h.HALF)
    rho = np.hypot(v[:, 0], v[:, 1])
    az = np.degrees(np.arctan2(v[:, 1], v[:, 0]))
    z = v[:, 2]
    # the pad + beam region: the equatorial band of the slice, inside both seam planes.
    # The pad spans az -18.3 .. -6.6 and the brace -11.1 .. 18.5 at bench (servo_pad /
    # brace_span), so this is a superset of both; the seam faces themselves are excluded
    # because a flat side face is not the hull's outer surface.
    in_reg = (np.abs(z) <= BAND * B) & (np.abs(az) <= h.HALF - SEAM_MARGIN)
    zz = np.clip(z[in_reg] / B, -1.0, 1.0)
    dev = rho[in_reg] - A * np.sqrt(1.0 - zz * zz)
    n, imax = len(dev), int(np.argmax(dev))
    worst = dev[imax]
    allv = to_model(np.asarray(mesh.vertices, dtype=float), h.HALF)
    allrho = np.hypot(allv[:, 0], allv[:, 1])
    allz = allv[:, 2]
    alldev = allrho - A * np.sqrt(1.0 - np.clip(allz / B, -1, 1) ** 2)
    print("%-40s scale %-5g  %6d verts in the pad+beam band (|z| <= %.0f mm, |az| <= %.1f deg):"
          "  max dev %+0.3f mm  min %+0.3f  over %.2f mm: %d"
          % (os.path.basename(path), scale, n, BAND * B, h.HALF - SEAM_MARGIN,
             worst, dev.min(), PROUD, int((dev > PROUD).sum())))
    at = v[in_reg][imax]
    print("      worst at az %+7.2f deg  z %+7.2f mm  r %8.2f (ellipse %8.2f)"
          % (math.degrees(math.atan2(at[1], at[0])), at[2], math.hypot(at[0], at[1]),
             A * math.sqrt(max(0.0, 1 - (at[2] / B) ** 2))))
    if report:
        for lo, hi in ((-1, -0.05), (-0.05, -0.005), (-0.005, 0.005), (0.005, 0.05), (0.05, 10)):
            print("      dev in [%+0.3f, %+0.3f): %6d" % (lo, hi, int(((dev >= lo) & (dev < hi)).sum())))
        print("      whole part: max dev %+0.3f mm over the ellipsoid (%d verts > %.2f)"
              % (alldev.max(), int((alldev > PROUD).sum()), PROUD))
    return worst


def main():
    report = "--report" in sys.argv
    bad = []
    for name, scale in FILES:
        p = os.path.join(PRINT, name)
        if not os.path.exists(p):
            print("MISSING %s" % p)
            bad.append((name, None))
            continue
        worst = check(p, scale, report)
        if worst > PROUD:
            bad.append((name, worst))
    if bad:
        for name, w in bad:
            print("FAIL %s: outer surface stands %s mm proud of the hull ellipse (limit %.2f)"
                  % (name, "unknown" if w is None else "%.3f" % w, PROUD))
        return 1
    print("PASS: no outer point of the servo pad / beam region stands more than %.2f mm off "
          "the hull ellipse" % PROUD)
    return 0


sys.exit(main())
