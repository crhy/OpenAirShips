#!/usr/bin/env python
"""f076: mesh volume / watertightness of the STLs named after --pass."""
import sys
import shlex
import Mesh

argv = sys.argv[1:]
paths = shlex.split(" ".join(a for a in argv if a != "--pass"))
for p in paths:
    m = Mesh.Mesh(p)
    print("%-60s facets %7d  volume %10.1f mm3  solid %s  open %s"
          % (p, m.CountFacets, m.Volume, m.isSolid(), m.hasNonManifolds()))
