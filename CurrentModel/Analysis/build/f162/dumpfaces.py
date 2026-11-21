#!/usr/bin/env freecadcmd
import Part, sys, os
step = os.environ.get("STEP", "CurrentModel/Analysis/build/f159/mount-1.41.step")
sh = Part.Shape(); sh.read(step)
faces = list(sh.Faces)
print("faces", len(faces), "solids", len(sh.Solids), "valid", sh.isValid())
for idx in [int(x) for x in os.environ.get("IDXS", "86,89,1220,1223,1226,1227,1132,1122,1127").split(",")]:
    f = faces[idx]
    print("f%d %s area %.4f bbox (%.2f..%.2f, %.2f..%.2f, %.2f..%.2f)"
          % (idx, type(f.Surface).__name__, f.Area,
             f.BoundBox.XMin, f.BoundBox.XMax, f.BoundBox.YMin, f.BoundBox.YMax,
             f.BoundBox.ZMin, f.BoundBox.ZMax))
    print("   vertices:", ["(%.2f,%.2f,%.2f)" % (v.X, v.Y, v.Z) for v in f.Vertexes][:8])
    try:
        print("   edges", len(f.Edges), "area/edge:", ["%.3f" % e.Length for e in f.Edges][:6])
    except Exception:
        pass
