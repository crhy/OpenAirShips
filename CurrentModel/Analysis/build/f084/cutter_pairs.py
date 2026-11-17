import sys, os, math, time
SL="/home/rhy/strata-fleet/repos/OpenAirShips/CurrentModel/CAD Files/SimplifiedSlice"
sys.path.insert(0, SL); os.environ.setdefault("OAS_VARIANT","8T")
import cadquery as cq, airship_slice as G
cut = G.windows()
bb=[w.BoundingBox() for w in cut]
def bn(a,b,t):
    dx=max(a.xmin-b.xmax,b.xmin-a.xmax,0.0); dy=max(a.ymin-b.ymax,b.ymin-a.ymax,0.0); dz=max(a.zmin-b.zmax,b.zmin-a.zmax,0.0)
    return math.sqrt(dx*dx+dy*dy+dz*dz)<=t
pairs=[]
for i in range(len(cut)):
    for j in range(i+1,len(cut)):
        if not bn(bb[i],bb[j],0.5): continue
        d=cut[i].distance(cut[j])
        if 0.0 < d < G.MIN_WEB: pairs.append((d,i,j))
pairs.sort()
print("%d window pairs at 0 < d < MIN_WEB: %s" % (len(pairs), ["#%d<->#%d %.3f mm"%(i,j,d) for d,i,j in pairs]))
