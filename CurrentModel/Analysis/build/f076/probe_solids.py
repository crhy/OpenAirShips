#!/usr/bin/env python
"""f076: what is in the built slice? Every solid's volume, faces and bbox.

Run from SimplifiedSlice with the cadquery venv:
  OAS_VARIANT=8T OAS_SLICES=8 OAS_SCALE=1 python probe_solids.py [module]
"""
import sys
import math
import importlib

mod = importlib.import_module(sys.argv[1] if len(sys.argv) > 1 else "airship_slice")
s = mod.build()
print("total volume %.1f mm3  solids %d  faces %d  valid %s"
      % (s.Volume(), len(s.Solids()), len(s.Faces()), s.isValid()))
for i, so in enumerate(s.Solids()):
    bb = so.BoundingBox()
    print("  solid %d  vol %10.1f mm3  faces %5d  shells %d  bbox %.1f x %.1f x %.1f at (%.0f,%.0f,%.0f)"
          % (i, so.Volume(), len(so.Faces()), len(so.Shells()),
             bb.xmax - bb.xmin, bb.ymax - bb.ymin, bb.zmax - bb.zmin, bb.xmin, bb.ymin, bb.zmin))
cut = mod.windows()
u = cut[0]
for w in cut[1:]:
    u = u.fuse(w)
print("windows: %d cutters, union volume %.1f mm3, union solids %d"
      % (len(cut), u.Volume(), len(u.Solids())))
