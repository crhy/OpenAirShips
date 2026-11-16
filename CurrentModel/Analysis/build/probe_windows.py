"""Scratch probe: replicate junction()'s polygon maths and report, for every
window polygon, how thin it gets and how close it comes to the band / seam /
neighbouring windows. No booleans, so it is fast."""
import math, os, sys, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "..", "..", "CAD Files", "SimplifiedSlice"))
os.environ.setdefault("OAS_VARIANT", "8T")
os.environ.setdefault("OAS_SLICES", "8")
os.environ.setdefault("OAS_SCALE", "1")
import cadquery as cq
import airship_slice as m
from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union

REC = []

def junction_probe(psi, theta, ovals, keep_side=0):
    """Copy of airship_slice.junction() up to the point where it returns,
    recording the raw region polygon and the buffered one."""
    origin, nrm = m.surface(psi, theta)
    u = cq.Vector(-math.sin(theta), math.cos(theta), 0)
    v = nrm.cross(u)
    tang = cq.Vector(-m.A * math.sin(psi) * math.cos(theta), -m.A * math.sin(psi) * math.sin(theta),
                     m.B * math.cos(psi)).normalized()
    sgn = 1.0 if v.dot(tang) > 0 else -1.0
    reach = 60.0 * m.SCALE
    x0 = m.skin_point(psi, m.T / 2)[0]
    to_uv = lambda p: ((p - origin).dot(u), (p - origin).dot(v))
    to_skin = lambda uu, vv: m.surface(psi + sgn * vv / m.ds_dpsi(psi), theta + uu / x0)
    polys = []
    for ring in ovals:
        uv = [to_uv(p) for p, _ in ring]
        if min(math.hypot(a_, b_) for a_, b_ in uv) < reach:
            polys.append(Polygon(uv).buffer(m.RIB))
    region = box(-reach, -reach, reach, reach).difference(unary_union(polys))
    if keep_side:
        cut_line = box(-reach, -reach, reach, reach).intersection(
            box(-reach, m.RIB / 2, reach, reach) if keep_side * sgn > 0 else box(-reach, -reach, reach, -m.RIB / 2))
        region = region.intersection(cut_line)
    parts = getattr(region, "geoms", [region])
    probe = Point(0, keep_side * sgn * (m.RIB / 2 + 0.5))
    near = [g for g in parts if g.area > 0 and g.distance(probe) < 3.0]
    if not near:
        return None
    g0 = min(near, key=lambda g_: g_.distance(probe))
    g = g0.buffer(-0.6).buffer(0.6)
    if g.is_empty or g.area < 6.0:
        return None
    if g.geom_type != "Polygon":
        g = max(g.geoms, key=lambda g_: g_.area)
    REC.append(dict(psi=math.degrees(psi), theta=math.degrees(theta),
                    keep=keep_side, sgn=sgn,
                    raw_area=g0.area, raw_thin=thinness(g0),
                    buf_area=g.area, buf_thin=thinness(g),
                    buf_type=g.geom_type, buf_parts=len(getattr(g, "geoms", [g])),
                    buf_len=g.exterior.length,
                    raw_len=g0.length))
    return [to_skin(p.x, p.y) for p in
            [g.exterior.interpolate(g.exterior.length * i / 80) for i in range(80)]]


def thinness(g):
    """Largest r for which the inward buffer still has area: a proxy for the
    width of the narrowest part of the polygon (2r)."""
    lo, hi = 0.0, 20.0
    for _ in range(14):
        mid = (lo + hi) / 2
        e = g.buffer(-mid)
        if e.is_empty or e.area < 1e-6:
            hi = mid
        else:
            lo = mid
    return round(2 * lo, 3)


def main():
    m.junction = junction_probe
    rows = m.skin_ribs()
    # windows() calls junction() through the module global, so the patch is used
    cut = m.windows()
    print(f"{len(cut)} window cutters built, {len(REC)} junction polygons")
    REC.sort(key=lambda r: r["buf_thin"])
    for r in REC[:14]:
        print("thin {buf_thin:6.3f} raw {raw_thin:6.3f} area {buf_area:8.2f} raw {raw_area:8.2f} "
              "psi {psi:7.2f} th {theta:7.2f} keep {keep:3d} parts {buf_parts} len {buf_len:7.1f}".format(**r))
    print("min buf_thin %.3f  max buf_thin %.3f" % (REC[0]["buf_thin"], REC[-1]["buf_thin"]))
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "probe_windows.json"), "w") as fh:
        json.dump(REC, fh, indent=1)


if __name__ == "__main__":
    main()
