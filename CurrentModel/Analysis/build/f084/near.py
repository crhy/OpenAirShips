import sys, os, math
SL="/home/rhy/strata-fleet/repos/OpenAirShips/CurrentModel/CAD Files/SimplifiedSlice"
sys.path.insert(0, SL); os.environ.setdefault("OAS_VARIANT","8T")
import cadquery as cq, airship_slice as G
walls, bore = G.duct_solids()
aw, ab = G.at_seams(walls), G.at_seams(bore)
cut = G.windows()
stem, servo = G.stem_and_servo_holes()
astem = G.at_seams(stem)
def near(a, b, tol=0.5):
    """points of a's bbox...: use vertices of the common of a grown and b grown"""
    d = a.distance(b)
    if d >= tol: return None
    # find the closest pair by growing b by tol and intersecting a
    try:
        ring = a.intersect(b)
    except Exception:
        return None
    return ring
for i in (2, 10, 11, 12, 13, 40, 41):
    w = cut[i]
    d = w.distance(ab)
    print("windows()[%d] <-> duct bore: %.4f mm" % (i, d))
    # closest points: bisect on the bbox corner nearest
    bbw, bbb = w.BoundingBox(), ab.BoundingBox()
    print("   cutter bbox x[%.1f,%.1f] y[%.1f,%.1f] z[%.1f,%.1f]" % (bbw.xmin,bbw.xmax,bbw.ymin,bbw.ymax,bbw.zmin,bbw.zmax))
    print("   bore bbox     x[%.1f,%.1f] y[%.1f,%.1f] z[%.1f,%.1f]" % (bbb.xmin,bbb.xmax,bbb.ymin,bbb.ymax,bbb.zmin,bbb.zmax))
    print("   cutter vol %.1f bore vol %.1f" % (w.Volume(), ab.Volume()))
    print("   stem hole bbox x[%.1f,%.1f] y[%.1f,%.1f] z[%.1f,%.1f]" % (lambda b:(b.xmin,b.xmax,b.ymin,b.ymax,b.zmin,b.zmax))(astem.BoundingBox()))
