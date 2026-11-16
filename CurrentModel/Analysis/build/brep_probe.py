#!/usr/bin/env python
"""Tiny faces on a STEP: where are the boolean slivers?

Run: flatpak run --command=freecadcmd org.freecad.FreeCAD \
        CurrentModel/Analysis/build/brep_probe.py --pass "'<path>.step' [area-limit]"
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
lim = float(argv[1]) if len(argv) > 1 else 2.0

s = Part.Shape()
s.read(path)
print("{}: faces {} solids {} valid {}".format(os.path.basename(path), len(s.Faces),
                                               len(s.Solids), s.isValid()))
bb = s.BoundBox
print("bbox {:.0f} x {:.0f} x {:.0f}  min ({:.0f},{:.0f},{:.0f})".format(
    bb.XLength, bb.YLength, bb.ZLength, bb.XMin, bb.YMin, bb.ZMin))
small = [f for f in s.Faces if f.Area < lim]
print("faces under {} mm2: {}".format(lim, len(small)))
for f in sorted(small, key=lambda f: f.Area):
    c = f.CenterOfMass
    r = math.hypot(c.x, c.y)
    print("  area {:8.4f}  at ({:8.1f},{:7.1f},{:7.1f}) r {:7.1f}  {} {}".format(
        f.Area, c.x, c.y, c.z, r, f.Surface.__class__.__name__,
        "closed" if f.isClosed() else ""))
