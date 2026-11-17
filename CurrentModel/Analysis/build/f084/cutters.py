import sys, os, math
SL = "/home/rhy/strata-fleet/repos/OpenAirShips/CurrentModel/CAD Files/SimplifiedSlice"
sys.path.insert(0, SL); os.environ.setdefault("OAS_VARIANT","8T")
import cadquery as cq, airship_slice as G
cut = G.windows()
rows = G.skin_ribs()
print("rows (%d): %s" % (len(rows), " ".join("%.4f" % r for r in rows)))
print("nrows %d -> ovals %d, junctions %d" % (len(rows)-1, 2*(len(rows)-1), len(cut)-2*(len(rows)-1)))
for i, w in enumerate(cut):
    c = w.Center()
    print("%3d  vol %8.1f  centre (%8.2f,%8.2f,%8.2f)  r=%7.1f z=%7.1f az=%6.1f"
          % (i, w.Volume(), c.x, c.y, c.z, math.hypot(c.x,c.y), c.z, math.degrees(math.atan2(c.y,c.x))))
