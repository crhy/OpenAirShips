"""Scratch probe: list the tiny faces (slivers) in a STEP and where they are."""
import math, os, sys
import Part

CUR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
stls = [a for a in sys.argv[1:] if a.lower().endswith(".step")]
PATH = stls[0] if stls else os.path.join(CUR, "CAD Files", "SimplifiedSlice", "airship pie slice 1026.step")
A, B = 207.765, 104.0

s = Part.Shape()
s.read(PATH)
print(f"{PATH}: {len(s.Faces)} faces, volume {s.Volume:.1f}")
small = [f for f in s.Faces if f.Area < 2.0]
print(f"{len(small)} faces with area < 2 mm2")
small.sort(key=lambda f: f.Area)
for f in small[:30]:
    c = f.CenterOfMass
    r = math.hypot(c.x, c.y)
    # signed distance to the outer skin ellipsoid (negative = inside)
    psi = math.atan2(c.z * A, r * B)
    nx, nz = B * math.cos(psi), A * math.sin(psi)
    L = math.hypot(nx, nz)
    rr = math.hypot(*[(A * math.cos(psi)) - c.x, (B * math.sin(psi)) - c.z])
    d = math.copysign(rr, (A * math.cos(psi) - c.x) * nx + (B * math.sin(psi) - c.z) * nz)
    print("  area %8.4f  edges %d  w %.2f h %.2f  xyz %8.2f %8.2f %8.2f  r %7.2f phi %6.2f z %7.2f  skin %7.3f"
          % (f.Area, len(f.Edges), f.BoundBox.XLength, f.BoundBox.ZLength,
             c.x, c.y, c.z, r, math.degrees(math.atan2(c.y, c.x)), c.z, d))
# also: the shortest distance between distinct faces (thin walls in the BREP)
print("nearest face pairs:")
fs = s.Faces
import random
random.seed(1)
cand = [i for i, f in enumerate(fs) if f.Area < 50]
best = []
for i in cand:
    for j in cand:
        if i >= j:
            continue
        d = fs[i].distToShape(fs[j])[0]
        if d < 0.40:
            best.append((d, i, j))
best.sort()
print(f"{len(best)} face pairs closer than 0.40 mm (among the {len(cand)} faces under 50 mm2)")
for d, i, j in best[:15]:
    print("  %7.4f mm  face %d (area %.3f) vs face %d (area %.3f)" % (d, i, fs[i].Area, j, fs[j].Area))
