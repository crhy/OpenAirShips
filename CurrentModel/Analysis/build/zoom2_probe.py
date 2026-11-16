#!/usr/bin/env python
"""One face of a STEP, edge by edge, with the faces on the other side of each
edge. Run: freecadcmd zoom2.py --pass "'<path>.step' x,y,z [radius]"
"""
import math
import os
import shlex
import sys

import Part

me = os.path.splitext(os.path.abspath(__file__))[0]
argv = [a for a in shlex.split(" ".join(sys.argv[1:]))
        if a != "--pass" and os.path.splitext(os.path.abspath(a))[0] != me]
path, xyz = argv[0], argv[1]
px, py, pz = [float(v) for v in xyz.split(",")]
rad = float(argv[2]) if len(argv) > 2 else 1.5

s = Part.Shape()
s.read(path)
c0 = Part.Vertex(px, py, pz)
near = sorted([f for f in s.Faces if math.sqrt(
    (f.CenterOfMass.x - px) ** 2 + (f.CenterOfMass.y - py) ** 2 + (f.CenterOfMass.z - pz) ** 2) < rad],
    key=lambda f: f.Area)
print("{} faces near".format(len(near)))
allf = s.Faces
for f in near:
    print("FACE area {:9.4f} {} closed {}".format(f.Area, f.Surface.__class__.__name__, f.isClosed()))
    for e in f.Edges:
        c = e.CenterOfMass
        nb = []
        for g in allf:
            if g.isSame(f):
                continue
            shared = [x for x in g.Edges if x.isSame(e)]
            if shared:
                nb.append("{:9.4f}:{}".format(g.Area, g.Surface.__class__.__name__))
        print("   edge {:6.3f} long {:22} at ({:7.2f},{:6.2f},{:6.2f})  neighbours {}".format(
            e.Length, e.Curve.__class__.__name__, c.x, c.y, c.z, " | ".join(nb) or "NONE (boundary)"))
