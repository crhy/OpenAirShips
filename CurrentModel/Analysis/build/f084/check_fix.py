import sys, os, math, time
SL="/home/rhy/strata-fleet/repos/OpenAirShips/CurrentModel/CAD Files/SimplifiedSlice"
sys.path.insert(0, SL); os.environ.setdefault("OAS_VARIANT","8T")
import cadquery as cq, airship_slice as G
t=time.time()
cut = G.windows()
print("windows(): %d cutters in %.0f s" % (len(cut), time.time()-t))
air = G.at_seams(G.duct_air_keepout())
print("air keep-out volume %.0f mm3" % air.Volume())
worst = []
for i, w in enumerate(cut):
    d = w.distance(air)
    worst.append((d, i))
worst.sort()
print("closest cutter -> duct air keep-out: %s" % ["#%d %.3f mm" % (j,d) for d,j in worst[:6]])
walls, bore = G.duct_solids()
ab = G.at_seams(bore)
worst2 = sorted((w.distance(ab), i) for i, w in enumerate(cut))
print("closest cutter -> duct BORE: %s" % ["#%d %.3f mm" % (j,d) for d,j in worst2[:6]])
w_, b_ = G.duct_solids()
print("duct walls %.1f mm3 bore %.1f mm3 (unchanged check)" % (G.at_seams(w_).Volume(), G.at_seams(b_).Volume()))
