#!/usr/bin/env python
"""f076 probe: where are the sliver faces in a slice STEP, and what is thin?

Run:
  flatpak run --command=freecadcmd org.freecad.FreeCAD \
      CurrentModel/Analysis/build/f076/probe_slivers.py --pass "<step path>"
"""
import sys
import math
import Part

path = sys.argv[-1]
s = Part.Shape()
s.read(path)
print("shape", path)
print("  solids %d shells %d faces %d valid %s volume %.1f"
      % (len(s.Solids), len(s.Shells), len(s.Faces), s.isValid(), s.Volume))

faces = s.Faces
bb = []
for f in faces:
    b = f.BoundBox
    b.enlarge(0.4)
    bb.append(b)

order = sorted(range(len(faces)), key=lambda i: faces[i].Area)
print("\n15 smallest faces (area mm2, centre, nearest-face distance):")
for i in order[:15]:
    f = faces[i]
    c = f.CenterOfMass
    d = 9e9
    for j, b in enumerate(bb):
        if j == i:
            continue
        if not b.intersect(bb[i]):
            continue
        d = min(d, f.distToShape(faces[j])[0])
    print("  area %9.3f  at (%7.1f,%7.1f,%7.1f)  nearest face %.6f mm  edges %d"
          % (f.Area, c.x, c.y, c.z, d, len(f.Edges)))

# face pairs closer than 0.40 mm that share no edge: a wall thinner than the nozzle
print("\nface pairs under 0.40 mm apart (bbox prefilter, no shared edge):")
thin = []
for i in range(len(faces)):
    for j in range(i + 1, len(faces)):
        if not bb[i].intersect(bb[j]):
            continue
        f, g = faces[i], faces[j]
        if f.sharedEdges(g) or f.sharedVertices(g):
            continue
        d = f.distToShape(g)[0]
        if 0.0005 < d < 0.40:
            thin.append((d, f.CenterOfMass, g.CenterOfMass))
thin.sort(key=lambda t: t[0])
print("  %d pairs, %d under 0.05 mm" % (len(thin), sum(1 for t in thin if t[0] < 0.05)))
for d, a, b in thin[:20]:
    print("   %.3f mm  (%7.1f,%7.1f,%7.1f)  <->  (%7.1f,%7.1f,%7.1f)"
          % (d, a.x, a.y, a.z, b.x, b.y, b.z))
