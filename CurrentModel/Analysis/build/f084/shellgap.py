import math, sys, os
SL="/home/rhy/strata-fleet/repos/OpenAirShips/CurrentModel/CAD Files/SimplifiedSlice"
sys.path.insert(0, SL); os.environ.setdefault("OAS_VARIANT","8T")
import cadquery as cq, airship_slice as G
A,B,T=G.A,G.B,G.T
def ell_pt(t): return (A*math.cos(t), B*math.sin(t))
def dist_to_ellipse(p):
    # nearest point on the ellipse by sampling
    best=1e9
    for i in range(200001):
        t=-math.pi/2+(math.pi+1e-4)*i/200000
        q=ell_pt(t)
        d=math.hypot(p[0]-q[0], p[1]-q[1])
        if d<best: best=d
    return best
print("psi(deg)  depth of skin_shell inner boundary below the outer skin")
for deg in (-90,-60,-45,-30,-15,0,15,30,45,60,84):
    t=math.radians(deg)
    p=((A-T-0.5)*math.cos(t), (B-T-0.5)*math.sin(t))
    print("  %5.0f  %.3f mm   (skin_point depth T+0.5 = %.3f)" % (deg, dist_to_ellipse(p), T+0.5))
