#!/usr/bin/env freecadcmd
"""f162: face pairs closer than MAXD inside a region (fault probes).
  STEP=<step> MAXD=0.05 [R0=195 R1=215 AZ0=-10 AZ1=8 Z0=0 Z1=12]"""
import math, os, Part
step = os.environ["STEP"]; MAXD = float(os.environ.get("MAXD", "0.05"))
R0, R1 = float(os.environ.get("R0", 195)), float(os.environ.get("R1", 215))
A0, A1 = float(os.environ.get("AZ0", -10)), float(os.environ.get("AZ1", 8))
Z0, Z1 = float(os.environ.get("Z0", 0)), float(os.environ.get("Z1", 12))
shape = Part.Shape(); shape.read(step)
print("volume %.1f mm3 faces %d valid %s solids %d" % (shape.Volume, len(shape.Faces), shape.isValid(), len(shape.Solids)))
def pol(p): return math.hypot(p[0], p[1]), math.degrees(math.atan2(p[1], p[0])), p[2]
sel = []
for i, f in enumerate(shape.Faces):
    r, a, z = pol(f.CenterOfMass)
    if R0 <= r <= R1 and A0 <= a <= A1 and Z0 <= z <= Z1:
        sel.append((i, f))
print("%d faces in region r %.0f..%.0f az %.0f..%.0f z %.0f..%.0f" % (len(sel), R0, R1, A0, A1, Z0, Z1))
pairs = []
for i in range(len(sel)):
    for j in range(i + 1, len(sel)):
        try: d = sel[i][1].distToShape(sel[j][1])[0]
        except Exception: continue
        if MAXD > d > 1e-4: pairs.append((d, sel[i], sel[j]))
pairs.sort()
print("%d region pairs closer than %.4f mm" % (len(pairs), MAXD))
for d, (i, f1), (j, f2) in pairs[:60]:
    r1, a1, z1 = pol(f1.CenterOfMass); r2, a2, z2 = pol(f2.CenterOfMass)
    print("  %.4f mm  f%d (%s %.4f mm2, r %.2f az %.2f z %.2f) <-> f%d (%s %.4f mm2, r %.2f az %.2f z %.2f)"
          % (d, i, type(f1.Surface).__name__, f1.Area, r1, a1, z1, j, type(f2.Surface).__name__, f2.Area, r2, a2, z2))
