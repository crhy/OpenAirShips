import sys, os, math
SL="/home/rhy/strata-fleet/repos/OpenAirShips/CurrentModel/CAD Files/SimplifiedSlice"
sys.path.insert(0, SL); os.environ.setdefault("OAS_VARIANT","8T")
import cadquery as cq, airship_slice as G
pts = G.duct_path()
path = cq.Wire.assembleEdges([cq.Edge.makeSpline(pts)])
print("path edges:", len(path.Edges()), "length", path.Length())
# true parallel curve: skin_point(psi, depth)
depth = G.T + G.DUCT_BORE/2 + G.DUCT_W - G.DUCT_FUSE
p0 = math.asin(G.DUCT_Z_IN/G.B); p1 = math.asin(G.OUT_Z/G.B)
worst = 0.0
for i in range(401):
    psi = p0 + (p1-p0)*i/401
    x,z = G.skin_point(psi, depth)
    v = cq.Vertex.makeVertex(x, 0, z)
    d = path.distance(v)
    worst = max(worst, d)
print("max deviation of the spline centreline from the skin's %.2f mm parallel: %.3f mm" % (depth, worst))
# same with more sample points
for n in (32, 64, 128):
    q = [cq.Vector(*G.skin_point(p0 + (p1-p0)*i/n, depth)[:2][::-1][::-1], 0) for i in range(n+1)]
    q = [cq.Vector(G.skin_point(p0 + (p1-p0)*i/n, depth)[0], 0, G.skin_point(p0 + (p1-p0)*i/n, depth)[1]) for i in range(n+1)]
    w = cq.Wire.assembleEdges([cq.Edge.makeSpline(q)])
    worst = max(w.distance(cq.Vertex.makeVertex(*reversed([G.skin_point(p0+(p1-p0)*j/400, depth)[1], 0, G.skin_point(p0+(p1-p0)*j/400, depth)[0]]))) for j in range(401))
    print("n=%d: max deviation %.4f mm, length %.1f" % (n, worst, w.Length()))
