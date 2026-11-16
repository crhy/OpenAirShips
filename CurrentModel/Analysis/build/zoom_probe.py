#!/usr/bin/env python
"""Zoom into a spot of a STEP: every face near a point, with its wire.

Run: flatpak run --command=freecadcmd org.freecad.FreeCAD \
        CurrentModel/Analysis/build/zoom_probe.py --pass "'<path>.step' x,y,z [radius]"
"""
import math
import os
import shlex
import sys

import Part

me = os.path.splitext(os.path.abspath(__file__))[0]
argv = [a for a in shlex.split(" ".join(sys.argv[1:]))
        if a != "--pass" and os.path.splitext(os.path.abspath(a))[0] != me]
path = argv[0]
px, py, pz = [float(v) for v in argv[1].split(",")]
rad = float(argv[2]) if len(argv) > 2 else 6.0

s = Part.Shape()
s.read(path)
print("{}: faces {}".format(os.path.basename(path), len(s.Faces)))
def dist(c):
    return math.sqrt((c.x - px) ** 2 + (c.y - py) ** 2 + (c.z - pz) ** 2)


near = [f for f in s.Faces if dist(f.CenterOfMass) < rad]
print("{} faces within {} mm of ({}, {}, {})".format(len(near), rad, px, py, pz))
for f in sorted(near, key=lambda f: f.Area):
    c = f.CenterOfMass
    print("  area {:9.4f} {:22} closed {}  centre ({:8.2f},{:7.2f},{:7.2f})".format(
        f.Area, f.Surface.__class__.__name__, f.isClosed(), c.x, c.y, c.z))
    for w in f.Wires:
        vs = w.Vertexes
        print("     wire {} verts {}".format("outer" if w.isClosed() else "open", len(vs)),
              " ".join("({:.2f},{:.2f},{:.2f})".format(v.X, v.Y, v.Z) for v in vs[:14]))
