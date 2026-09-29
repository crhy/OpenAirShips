"""Airship pie slice (1 of 8), rev E: the bench model.

The hull is an ellipse A x B revolved about Z and cut into 8 identical
45-degree slices. Each slice carries pegs on its +22.5 deg seam and matching
holes on its -22.5 deg seam, so slice k+1 plugs straight into slice k.

Air path: an impeller at the bottom of the central shaft pulls air down the
shaft into the fan housing (plenum) above the keel, which feeds the 8 thrust
ducts. The shaft, the housing ceiling, the keel under the housing and the
duct walls are solid, airtight walls; the shaft bore has nothing in it.

The ducts run inside the skin, so the hull's outside is a smooth ellipsoid
that rolls over a bellmouth into the shaft at the top. Its only openings are
the round stem and servo holes at each outlet, plus the lattice. Everything
else is lattice: two columns of ovals laid out on the curved skin, with a
hollow window at every junction, so every web left is 2.0 mm wide (junction
windows on the seams stop short of a continuous edge strip).
There are no decks. See ../../DESIGN-CONSTRAINTS.md.

Run: pip install cadquery && python3 airship_slice.py
     -> "airship pie slice 926.step"
     then: freecadcmd make_fcstd.py
     -> "airship pie slice 926.FCStd", and Print Files/PieSlice926-v0.1-8T.stl laid
        flat for printing (FreeCAD's mesher gives a watertight STL)
"""
import math
import os
import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))

# ---- variant ------------------------------------------------------------------
# OAS_VARIANT=8T (default): 8 thrusters, 8 identical slices, a duct on every seam.
# OAS_VARIANT=4T: 4 thrusters on alternate seams, with ducts, stems and rings
#   sized for twice the flow each (see Analysis/AIRFLOW-4T.md). The slices come
#   in two hands that alternate round the ring: OAS_SIDE=L carries its duct on
#   its +22.5 deg seam, OAS_SIDE=R on its -22.5 deg seam (and the servo).
VARIANT = os.environ.get("OAS_VARIANT", "8T").upper()
SIDE = os.environ.get("OAS_SIDE", "L").upper()
FOUR = VARIANT == "4T"
assert VARIANT in ("8T", "4T") and SIDE in ("L", "R")
# OAS_SCALE: hull size factor (1 = the 415 mm bench model; 1.9 = the largest
# that prints on an Anycubic Kobra Max, 400 x 400 x 450 mm). Only the hull
# outline and its lattice grow; walls, ribs, joints, the fan, ducts,
# thrusters and servos keep their size, so mass grows ~S^2 while volume
# grows S^3.
SCALE = float(os.environ.get("OAS_SCALE", "1"))

# ---- parameters (mm) -------------------------------------------------------
A, B = 207.765 * SCALE, 104.0 * SCALE   # hull outer semi-axes (radius, half-height)
T = 0.86                   # wall: exactly 2 perimeters of 0.45 mm at 0.2 mm layers
N = 8                      # slices in the ring
HALF = 180.0 / N           # half-angle of one slice, degrees

FLOOR_Z = -B + (43.0 if FOUR else 32.7)   # fan-housing ceiling (the shroud over the blade tips), underside;
                                     # 4T: higher, so the Ø34 duct mouths fit under it
INTAKE_R = 12.0            # the skin arc rolls into the shaft over this radius (bellmouth)

RIB = 2.0                  # frame rib width (a seam rib is RIB/2 on each slice)
# Skin lattice: from the fan housing to the intake bellmouth, rows of two side
# columns of ovals (split by a centre rib). Every row is the same length along
# the skin: ROWS_ABOVE_EQ of them fill the top half, and the bottom half gets
# as many of that height as fit. Where four ovals meet, the junction is a
# hollow window that takes all the skin more than RIB from the ovals. Printed lying on the seam, each oval's top is a
# small round arch, which prints without supports.
ROWS_ABOVE_EQ = 6          # skin rows between the equator and the intake bellmouth
OVAL_N = 1.8               # oval shape: superellipse exponent (2 = ellipse)

# Printing (Prusa MK3S+, 0.4 nozzle, 0.2 layers, 0.45 lines): the slice lies
# on its -22.5 deg (hole) seam. UP is the print's +Z in model coordinates.
UP = cq.Vector(math.sin(math.radians(HALF)), math.cos(math.radians(HALF)), 0)

# Fan housing = stationary shroud. The shaft narrows smoothly to the impeller
# eye, turns over the blade tips (SHROUD_GAP clearance) and runs out flat as
# the housing ceiling. With no gap left between the impeller tip and the shaft
# wall, housing air can't leak back up the shaft: the fan works as a shrouded
# fan. Nothing but this smooth nozzle is inside the shaft.
EYE_R = 33.0               # impeller eye (blade inlet) radius, from Analysis/AIRFLOW.md
# The intake shaft is the eye's diameter all the way up (Ø66). It was Ø95 only so
# the impeller could drop in from the top; it now comes in through the keel
# hatch. The narrower shaft costs ~1% of the fan pressure and gives the
# ballonet space more room.
SHAFT_R = EYE_R            # central shaft wall, inner radius
SHROUD_RC = 8.0            # turn from axial to radial over the blades
NOZZLE_L = 30.0            # straight run above the shroud turn (a contraction if SHAFT_R > EYE_R)
SHROUD_GAP = 1.5           # blade tip clearance under the shroud
# The keel under the fan is a removable hatch (../Propulsion: fan_hatch) that
# carries the motor and impeller. It locks with a bayonet: each slice has a lug
# at the bottom of a ring wall round the opening, and a stop post.
HATCH_R = 47.0             # opening in the keel (the 88 mm impeller passes through)
HATCH_WALL_TOP = -B + 11.0   # ring wall round the opening
LUG_R = 44.6               # lug inner radius (0.6 mm past the impeller tip)
LUG_Z = (-B + 5.0, -B + 7.0)
LUG_HALF = 6.0             # lug: +-6 deg about the slice centre
POST = (-6.0, -3.0)        # stop post over the lug: the hatch locks turning clockwise (from above)

PEG_D, HOLE_D = 3.0, 3.3   # 0.15 mm clearance per side for FDM
PEG_L, HOLE_L = 3.6, 4.2
CHAMFER = 0.4              # peg tip and hole mouth (also eats elephant foot)
BOSS_D, BOSS_L = 7.0, 5.0

# Thrust ducts: one per seam, split in half by the seam plane, entirely
# inside the skin. Each runs from a mouth on the keel (in the plenum) up the
# side to a closed end at the equator, where the thruster's stem enters
# through a round hole with a bearing boss behind it.
DUCT_BORE = 34.0 if FOUR else 24.0   # bore diameter; 4T: twice the area for twice the flow
DUCT_W = T                 # duct wall
DUCT_MOUTH_R = 60.0        # the duct mouths sit just outside the impeller (tip r 44)
DUCT_Z_IN = -B * math.sqrt(1 - (DUCT_MOUTH_R / A) ** 2)   # skin height at the mouth

# Plenum (fan housing): only as big as the fan and the duct mouths. Flat under
# the floor out past the mouths, then a sloped ceiling down to the keel.
# Everything outside it, keel included, is oval lattice with hollow junctions: the ducts
# carry the air from here and their own walls keep it airtight.
PLENUM_FLAT_R = 66.0
PLENUM_KEEL_R = 80.0
# OUT_Z (stem and servo axis height) is set below skin_ribs(): it sits on a
# ring rib, so the stem and servo holes' collars are part of that rib.
STEM_HOLE = 34.4 if FOUR else 25.4   # stem OD + 0.4: 34/31 (4T) or 25/22 mm (see Analysis/AIRFLOW*.md)
BOSS_LEN = 12.0            # bearing sleeve behind the stem hole (reaches into the duct bulb)
DUCT_BULB = 44.0 if FOUR else 32.0   # the duct's end swells to this bore so the stem's flange fits
BOSS_R = STEM_HOLE / 2 + 1.3      # thin bearing sleeve, not a solid block
SERVO_T = 44.0 if FOUR else 36.0     # servo spline: this far (tangentially) from the seam
                                     # (= the 1:1 gear pitch diameter: 44T or 36T, module 1)
SERVO_HOLE = 8.0


# ---- helpers ---------------------------------------------------------------
def wedge(pts, half=HALF):
    """Revolve a closed (r, z) polygon over the slice's angle."""
    w = cq.Workplane("XZ").polyline(pts).close()
    return (w.revolve(2 * half, (0, 0, 0), (0, 1, 0))
             .rotate((0, 0, 0), (0, 0, 1), -half).val())


def arc(a, b, t0, t1):
    """Exact ellipse arc in the XZ plane, from angle t0 to t1 (radians)."""
    lo, hi = sorted((t0, t1))
    e = cq.Edge.makeEllipse(a, b, cq.Vector(), cq.Vector(0, -1, 0), cq.Vector(1, 0, 0),
                            math.degrees(lo), math.degrees(hi))
    return e if t0 < t1 else cq.Edge(e.wrapped.Reversed())


def wedge_edges(*parts, half=HALF):
    """Revolve a closed profile of exact edges and (x, z) corner points."""
    wire = cq.Wire.assembleEdges(parts_to_edges(parts))
    solid = cq.Solid.revolve(cq.Face.makeFromWires(wire), 2 * half,
                             cq.Vector(), cq.Vector(0, 0, 1))
    return solid.rotate((0, 0, 0), (0, 0, 1), -half)


def parts_to_edges(parts):
    """Chain edges and points: straight lines join consecutive items."""
    out, prev = [], None
    first = None
    for p in parts:
        if isinstance(p, cq.Edge):
            s, e = p.startPoint(), p.endPoint()
            if prev is not None and (prev - s).Length > 1e-7:
                out.append(cq.Edge.makeLine(prev, s))
            out.append(p); prev = e
            first = s if first is None else first
        else:
            v = cq.Vector(p[0], 0, p[1])
            if prev is not None and (prev - v).Length > 1e-7:
                out.append(cq.Edge.makeLine(prev, v))
            prev = v
            first = v if first is None else first
    if (prev - first).Length > 1e-7:
        out.append(cq.Edge.makeLine(prev, first))
    return out


def ellipse(a, b, t0, t1, n=90):
    pts = [(a * math.cos(t), b * math.sin(t))
           for t in (t0 + (t1 - t0) * i / n for i in range(n + 1))]
    return [(0.0 if abs(x) < 1e-9 else x, z) for x, z in pts]


def hull_r(z, a=A, b=B):
    return a * math.sqrt(max(0.0, 1 - (z / b) ** 2))


def skin_point(psi, depth):
    """Point `depth` inward from the outer skin at ellipse angle psi."""
    nx, nz = B * math.cos(psi), A * math.sin(psi)
    L = math.hypot(nx, nz)
    return (A * math.cos(psi) - depth * nx / L, B * math.sin(psi) - depth * nz / L)


def column(side):
    """Prism between the centre rib and the seam rib; side +1/-1, 0 = both."""
    h, big, th = RIB / 2, 500.0, math.radians(HALF)
    s = h * (1 + math.cos(th)) / math.sin(th)       # offset seam meets y = h
    ix, iy = s * math.cos(th) + h * math.sin(th), h
    far = (ix + big * math.cos(th), iy + big * math.sin(th))
    if side == 0:
        x0 = h / math.sin(th)                       # two offset seams meet
        pts = [(x0, 0), (x0 + big * math.cos(th), big * math.sin(th)),
               (x0 + big * math.cos(th), -big * math.sin(th))]
    else:
        pts = [(ix, side * iy), (far[0], side * iy), (far[0], side * far[1])]
    return (cq.Workplane("XY").polyline(pts).close()
              .extrude(2 * B + 40).translate((0, 0, -B - 20)).val())


def seam_axis(r, z, phi):
    """Point on the seam plane at angle phi and the unit tangent +theta."""
    p = cq.Vector(r * math.cos(phi), r * math.sin(phi), z)
    t = cq.Vector(-math.sin(phi), math.cos(phi), 0)
    return p, t


def keel_edge_z():
    """Skin height of the first ring rib above where the plenum meets the keel."""
    return -B * math.sqrt(1 - (PLENUM_KEEL_R / A) ** 2) + RIB + 1.0


def ellipse_arc(p0, p1, n=200):
    """Length of the outer skin between two ellipse angles."""
    h = (p1 - p0) / n
    return sum(math.hypot(A * math.sin(p0 + (i + .5) * h), B * math.cos(p0 + (i + .5) * h))
               for i in range(n)) * h


def equal_arcs(p0, p1, n):
    """n + 1 ellipse angles from p0 to p1, equally spaced along the skin."""
    L, out, acc, h = ellipse_arc(p0, p1), [p0], 0.0, (p1 - p0) / 4000
    for i in range(4000):
        p = p0 + (i + .5) * h
        acc += math.hypot(A * math.sin(p), B * math.cos(p)) * abs(h)
        if len(out) < n and acc >= L * len(out) / n:
            out.append(p0 + (i + 1) * h)
    return out + [p1]


def skin_ribs():
    """Ellipse angles of the skin's ring ribs, bottom to top. One sits exactly
    on the equator (z = 0), where the thrusters are. Every row is the same
    height along the skin, above and below the equator, so all the cells
    have the same proportions."""
    ke = math.asin(keel_edge_z() / B)
    top = intake()[1] - (RIB / 2) / math.hypot(A * math.sin(intake()[1]), B * math.cos(intake()[1]))
    row = ellipse_arc(0.0, top) / ROWS_ABOVE_EQ
    below = max(3, round(ellipse_arc(ke, 0.0) / row))
    return equal_arcs(ke, 0.0, below)[:-1] + equal_arcs(0.0, top, ROWS_ABOVE_EQ)


def intake():
    """The bellmouth where the skin rolls into the shaft: (centre (r, z),
    ellipse angle where it leaves the skin, z where it meets the shaft)."""
    lo, hi = 0.3, math.pi / 2
    for _ in range(80):                              # skin_point(p, R).r == SHAFT_R + R
        mid = (lo + hi) / 2
        if skin_point(mid, INTAKE_R)[0] > SHAFT_R + INTAKE_R:
            lo = mid
        else:
            hi = mid
    c = skin_point(lo, INTAKE_R)
    return c, lo, c[1]


# The thrusters must sit exactly on the equator (z = 0), for navigation.
OUT_Z = 0.0
OUT_THRUST_RIB = skin_ribs().index(0.0)


def joints():
    """(r, z) of each peg/hole pair on the seam plane.

    Holes keep >= 0.6 mm of wall between them and the shaft, floor and keel,
    so the fan duct and plenum stay airtight.
    """
    edge = T + HOLE_D / 2 + 1.0                     # hole centre depth under skin
    r_shaft = SHAFT_R + T + HOLE_D / 2 + 0.6        # boss on the outside of the shaft
    ribs = skin_ribs()
    return [(r_shaft, intake()[2] - 4.0),           # shaft top, under the bellmouth
            skin_point(ribs[-3], edge),             # upper skin, on a ring rib
            (r_shaft, nozzle_top() + 4.0),          # shaft, above the contraction
            (55.0, FLOOR_Z + T + BOSS_D / 2 - 0.5),  # on the housing ceiling
            skin_point(-math.acos(53.0 / A), edge)]  # keel, outside the hatch ring


# ---- body ------------------------------------------------------------------
def frame():
    # skin and shaft are one wall: the skin arc rolls over a bellmouth into the shaft
    (cr, cz), p_top, _ = intake()
    o_top = skin_point(p_top, 0.0)
    def roll(r):                                    # bellmouth arc at radius r
        a0 = math.atan2(o_top[1] - cz, o_top[0] - cr)
        pts = [cq.Vector(cr + r * math.cos(a0 + (math.pi - a0) * t), 0,
                         cz + r * math.sin(a0 + (math.pi - a0) * t)) for t in (0, .5, 1)]
        return cq.Edge.makeThreePointArc(*pts)
    ri = INTAKE_R - T
    q = roll(ri).startPoint()
    p_in = math.atan2(q.z / (B - T), q.x / (A - T))  # the inner skin, where it meets the inner roll
    wall = wedge_edges(arc(A, B, -math.pi / 2, p_top), roll(INTAKE_R),
                       (SHAFT_R, nozzle_top() - 1), (SHAFT_R + T, nozzle_top() - 1),
                       cq.Edge(roll(ri).wrapped.Reversed()),
                       arc(A - T, B - T, p_in, -math.pi / 2))
    body = wall.fuse(plenum_ceiling(), hatch_ring())
    return body.clean()


def nozzle_top():
    return FLOOR_Z + SHROUD_RC + NOZZLE_L


def shroud_curve(n=24):
    """Air-side surface of the housing, (r, z) from the shaft wall down the
    contraction, round the shroud turn and out along the ceiling to the keel."""
    z_eye = FLOOR_Z + SHROUD_RC
    pts = [(SHAFT_R, nozzle_top() + 1.0)]
    for i in range(n + 1):                          # cosine contraction: tangent at both ends
        t = i / n
        pts.append((EYE_R + (SHAFT_R - EYE_R) * (1 + math.cos(math.pi * t)) / 2,
                    nozzle_top() - NOZZLE_L * t))
    for i in range(1, n + 1):                       # turn from axial to radial
        ph = math.pi / 2 * i / n
        pts.append((EYE_R + SHROUD_RC - SHROUD_RC * math.cos(ph), z_eye - SHROUD_RC * math.sin(ph)))
    pts.append((PLENUM_FLAT_R, FLOOR_Z))
    zk = -(B - T) * math.sqrt(1 - (PLENUM_KEEL_R / (A - T)) ** 2)
    d = (PLENUM_KEEL_R - PLENUM_FLAT_R, zk - FLOOR_Z)
    L = math.hypot(*d)
    pts.append((PLENUM_KEEL_R + d[0] / L * 1.5, zk + d[1] / L * 1.5))   # into the skin
    return pts


def plenum_ceiling():
    """The housing wall: the shroud curve, T thick on its dry side."""
    pts = shroud_curve()
    off = []
    for i, (r, z) in enumerate(pts):
        a_, b_ = pts[max(i - 1, 0)], pts[min(i + 1, len(pts) - 1)]
        dr, dz = b_[0] - a_[0], b_[1] - a_[1]
        L = math.hypot(dr, dz)
        off.append((r - dz / L * T, z + dr / L * T))   # dry side: left of the flow direction
    return wedge(pts + off[::-1]).intersect(wedge_edges(arc(A, B, -math.pi / 2, math.pi / 2)))


def hatch_ring():
    """Ring wall round the hatch opening, with this slice's bayonet lug and stop post."""
    ring = wedge([(HATCH_R, -B - 1), (HATCH_R + T, -B - 1),
                  (HATCH_R + T, HATCH_WALL_TOP), (HATCH_R, HATCH_WALL_TOP)])
    lug = wedge([(LUG_R, LUG_Z[0]), (HATCH_R + 0.5, LUG_Z[0]),
                 (HATCH_R + 0.5, LUG_Z[1]), (LUG_R, LUG_Z[1])], half=LUG_HALF)
    post = wedge([(LUG_R, LUG_Z[1] - 0.5), (HATCH_R + 0.5, LUG_Z[1] - 0.5),
                  (HATCH_R + 0.5, HATCH_WALL_TOP), (LUG_R, HATCH_WALL_TOP)],
                 half=(POST[1] - POST[0]) / 2).rotate((0, 0, 0), (0, 0, 1), (POST[0] + POST[1]) / 2)
    return ring.fuse(lug, post).intersect(wedge_edges(arc(A - T / 2, B - T / 2, -math.pi / 2, math.pi / 2)))


def hatch_hole():
    """The keel skin inside the ring wall (below the lugs)."""
    return cq.Solid.makeCylinder(HATCH_R, LUG_Z[0] - 0.4 + B + 1, cq.Vector(0, 0, -B - 1))


def surface(psi, theta, depth=T / 2):
    """Point `depth` under the outer skin at (psi, theta), and the outward normal."""
    r, z = skin_point(psi, depth)
    n = cq.Vector(B * math.cos(psi) * math.cos(theta), B * math.cos(psi) * math.sin(theta),
                  A * math.sin(psi)).normalized()
    return cq.Vector(r * math.cos(theta), r * math.sin(theta), z), n


def ds_dpsi(psi):
    return math.hypot(A * math.sin(psi), B * math.cos(psi))


def column_bounds(psi, side):
    """Azimuths of one column's edges at ellipse angle psi: RIB/2 in from the
    centre plane and from the seam plane (measured straight, like column())."""
    x = skin_point(psi, T / 2)[0]
    th_in, th_out = math.asin((RIB / 2) / x), math.radians(HALF) - math.asin((RIB / 2) / x)
    return (th_in, th_out) if side > 0 else (-th_out, -th_in)


def oval_on_skin(p0, p1, side, n=96):
    """Oval window of the cell between ribs p0 and p1, in column `side`, as
    points on the skin's mid-surface with their normals. It is laid out on the
    real curved skin: at every height it spans the column between its edges,
    and from bottom to top it spans the row, so it touches each of the four
    rib lines (RIB/2 in) at one point and fills the cell."""
    q0 = p0 + (RIB / 2) / ds_dpsi(p0)
    q1 = p1 - (RIB / 2) / ds_dpsi(p1)
    out = []
    for i in range(n):
        t = 2 * math.pi * i / n
        c_, s_ = math.cos(t), math.sin(t)
        a_ = math.copysign(abs(c_) ** (2 / OVAL_N), c_)
        b_ = math.copysign(abs(s_) ** (2 / OVAL_N), s_)
        psi = (q0 + q1) / 2 + b_ * (q1 - q0) / 2
        lo, hi = column_bounds(psi, side)
        out.append(surface(psi, (lo + hi) / 2 + a_ * (hi - lo) / 2))
    return out


_SHELL = None


def skin_shell():
    """A thin shell round the skin (0.5 mm beyond both faces): window cutters
    are trimmed to it, so they cut the skin and nothing inside it."""
    global _SHELL
    if _SHELL is None:
        top = math.pi / 2 - 0.02
        _SHELL = wedge_edges(arc(A + 0.5, B + 0.5, -math.pi / 2, top),
                             arc(A - T - 0.5, B - T - 0.5, top, -math.pi / 2), half=HALF + 3)
    return _SHELL


def skin_cutter(pts):
    """Window cutter from an outline on the skin (points and normals): the
    outline projected onto the plane at its centre, pushed straight through
    the skin along that plane's normal, and trimmed to the skin shell."""
    c = sum((p for p, _ in pts), cq.Vector()) * (1 / len(pts))
    nrm = sum((nv for _, nv in pts), cq.Vector()).normalized()
    xd = (pts[0][0] - c)
    xd = (xd - nrm * xd.dot(nrm)).normalized()
    yd = nrm.cross(xd)
    uv = [((p - c).dot(xd), (p - c).dot(yd)) for p, _ in pts]
    # reach: the outline's own spread plus the skin's bulge between its edges
    # (up to about span^2 / 8R), so the middle of a big window is cut too
    span = max((p - q).Length for p, _ in pts[::4] for q, _ in pts[::4])
    dev = max(abs((p - c).dot(nrm)) for p, _ in pts) + 0.25 * span + T + 3.0
    prism = (cq.Workplane(cq.Plane(origin=c, xDir=xd, normal=nrm)).polyline(uv).close()
             .extrude(dev, both=True).val())
    return prism.intersect(skin_shell())


def junction(psi, theta, ovals, keep_side=0):
    """Hollow junction where ovals meet on the rib at psi, azimuth theta: all
    the skin that is more than RIB from every oval around it (`ovals`: skin
    points, including the neighbouring slice's across a seam). keep_side
    +1/-1 keeps only the side of the rib above/below, RIB/2 off it (for the
    first and last ribs). Returns skin points of its outline, or None."""
    from shapely.geometry import Point, Polygon, box
    from shapely.ops import unary_union
    origin, nrm = surface(psi, theta)
    u = cq.Vector(-math.sin(theta), math.cos(theta), 0)
    v = nrm.cross(u)
    tang = cq.Vector(-A * math.sin(psi) * math.cos(theta), -A * math.sin(psi) * math.sin(theta),
                     B * math.cos(psi)).normalized()                 # up the skin
    sgn = 1.0 if v.dot(tang) > 0 else -1.0
    reach = 60.0 * SCALE
    polys = []
    for ring in ovals:
        uv = [((p - origin).dot(u), (p - origin).dot(v)) for p, _ in ring]
        if min(math.hypot(a_, b_) for a_, b_ in uv) < reach:
            polys.append(Polygon(uv).buffer(RIB))
    region = box(-reach, -reach, reach, reach).difference(unary_union(polys))
    if keep_side:
        cut_line = box(-reach, -reach, reach, reach).intersection(
            box(-reach, RIB / 2, reach, reach) if keep_side * sgn > 0 else box(-reach, -reach, reach, -RIB / 2))
        region = region.intersection(cut_line)
    parts = getattr(region, "geoms", [region])
    probe = Point(0, keep_side * sgn * (RIB / 2 + 0.5))
    near = [g for g in parts if g.area > 0 and g.distance(probe) < 3.0]
    if not near:
        return None
    g = min(near, key=lambda g_: g_.distance(probe)).buffer(-0.6).buffer(0.6)   # round the tips
    if g.is_empty or g.area < 6.0:
        return None
    if g.geom_type != "Polygon":
        g = max(g.geoms, key=lambda g_: g_.area)
    ring = list(g.exterior.coords)[:-1]
    per = g.exterior.length
    pts = [g.exterior.interpolate(per * i / 80) for i in range(80)]    # even spacing
    x0 = skin_point(psi, T / 2)[0]
    out = []
    for p in pts:
        out.append(surface(psi + sgn * p.y / ds_dpsi(psi), theta + p.x / x0))
    return out


def windows():
    """The lattice: two columns of ovals with hollow junction windows.

    It covers the whole skin from just outside the fan housing up to the
    intake bellmouth. Everything is laid out on the curved skin, and every web
    left between windows is RIB wide: nothing heavier than needed. The shaft,
    the housing ceiling and the keel under it stay solid: they are the intake
    and the plenum.
    """
    whole = column(0)
    rows = skin_ribs()
    nrows = len(rows) - 1
    ovals = {k: [oval_on_skin(rows[k], rows[k + 1], sd) for sd in (-1, 1)] for k in range(nrows)}

    def turn(rings, deg):
        c, s_ = math.cos(math.radians(deg)), math.sin(math.radians(deg))
        rot = lambda p: cq.Vector(p.x * c - p.y * s_, p.x * s_ + p.y * c, p.z)
        return [[(rot(p), rot(nv)) for p, nv in r] for r in rings]

    cut = [skin_cutter(o) for k in ovals for o in ovals[k]]
    for j, psi in enumerate(rows):                  # junctions on every rib
        near = ovals.get(j - 1, []) + ovals.get(j, [])
        keep = 0 if 0 < j < nrows else (1 if j == 0 else -1)
        spots = [(0.0, near), (-HALF, near + turn(near, -2 * HALF)), (HALF, near + turn(near, 2 * HALF))]
        for th, around in spots:
            pts = junction(psi, math.radians(th), around, keep)
            if pts is None:
                continue
            c_ = skin_cutter(pts)
            # seam junctions stop RIB/2 short of the seam: the side edge stays continuous
            cut.append(c_ if th == 0.0 else c_.intersect(whole))
    keep = outlet_keepout()
    out = []
    for c in cut:
        try:
            clipped = c.cut(keep)
            if clipped.Volume() > 0.35 * c.Volume():   # drop slivers next to the collars
                out.append(clipped)
        except ValueError:                  # empty: fully inside the keep-out
            pass
    return out


def outlet_keepout():
    """Solid skin only where it must be: a collar round each stem hole (both
    seams) and round this slice's servo-hub hole. Elsewhere the lattice runs
    straight over the ducts; their own walls keep them airtight."""
    ax = cq.Vector(1, 0, 0)
    stem = cq.Solid.makeCylinder(BOSS_R + 1.5, 60, cq.Vector(A - 37.765, 0, OUT_Z), ax)
    servo = cq.Solid.makeCylinder(SERVO_HOLE / 2 + 3.5, 60, cq.Vector(A - 37.765, SERVO_T, OUT_Z), ax)
    keep = stem.rotate((0, 0, 0), (0, 0, 1), duct_seams()[0])
    for a_ in duct_seams()[1:]:
        keep = keep.fuse(stem.rotate((0, 0, 0), (0, 0, 1), a_))
    return keep.fuse(servo.rotate((0, 0, 0), (0, 0, 1), -HALF)) if has_servo() else keep


def joint_parts():
    """Bosses (added), holes (cut) and pegs (added) on both seams."""
    ph, pp = math.radians(-HALF), math.radians(HALF)
    bosses, holes, pegs = [], [], []
    for r, z in joints():
        p, t = seam_axis(r, z, ph)                  # hole seam, inward = +t
        bosses.append(cq.Solid.makeCylinder(BOSS_D / 2, BOSS_L, p, t))
        hole = cq.Solid.makeCylinder(HOLE_D / 2, HOLE_L, p - t * 0.01, t)
        mouth = cq.Solid.makeCone(HOLE_D / 2 + CHAMFER + 0.01, HOLE_D / 2, CHAMFER + 0.01,
                                  p - t * 0.01, t)
        holes.append(hole.fuse(mouth))
        p, t = seam_axis(r, z, pp)                  # peg seam, inward = -t
        bosses.append(cq.Solid.makeCylinder(BOSS_D / 2, BOSS_L, p, -t))
        peg = cq.Solid.makeCylinder(PEG_D / 2, PEG_L + 0.5, p - t * 0.5, t)
        tip = [e for e in peg.Edges()
               if e.geomType() == "CIRCLE" and (e.Center() - p).dot(t) > PEG_L - 0.1]
        pegs.append(peg.chamfer(CHAMFER, None, tip))
    return bosses, holes, pegs


def duct_path():
    """Duct centreline in the seam plane (x = radius, y = 0), mouth to end."""
    depth = T + DUCT_BORE / 2 + DUCT_W - 0.4         # duct wall merges into the skin
    p0 = math.asin(DUCT_Z_IN / B)
    p1 = math.asin(OUT_Z / B)
    pts = [skin_point(p0 + (p1 - p0) * i / 16, depth) for i in range(17)]
    return [cq.Vector(x, 0, z) for x, z in pts]


def duct_solids():
    """(walls, bore) of one full duct, seam plane = XZ, in the outlet frame."""
    pts = duct_path()
    path = cq.Wire.assembleEdges([cq.Edge.makeSpline(pts)])
    t0 = (pts[1] - pts[0]).normalized()

    def tube(r, extra=0.0):
        start = pts[0] - t0 * extra
        prof = cq.Wire.makeCircle(r, start, t0)
        body = cq.Solid.sweep(prof, [], path if not extra else cq.Wire.assembleEdges(
            [cq.Edge.makeLine(start, pts[0]), cq.Edge.makeSpline(pts)]), True, False)
        return body.fuse(cq.Solid.makeSphere(r, pts[-1], angleDegrees1=-90, angleDegrees2=90))

    # the end swells into a bulb (bore DUCT_BULB) so the wide stem and its
    # flange fit; the bulb's centre moves inward so it stays inside the skin
    p1 = math.asin(OUT_Z / B)
    n_end = cq.Vector(B * math.cos(p1), 0, A * math.sin(p1)).normalized()
    centre = pts[-1] - n_end * (DUCT_BULB / 2 - DUCT_BORE / 2)
    # (the tube's rounded end sits inside the bulb, so a plain sphere joins them)
    inside = wedge_edges(arc(A, B, -math.pi / 2, math.pi / 2), half=90)
    outer = tube(DUCT_BORE / 2 + DUCT_W).fuse(
        cq.Solid.makeSphere(DUCT_BULB / 2 + DUCT_W, centre, angleDegrees1=-90, angleDegrees2=90))
    bore = tube(DUCT_BORE / 2, extra=3.0).fuse(
        cq.Solid.makeSphere(DUCT_BULB / 2, centre, angleDegrees1=-90, angleDegrees2=90))
    # stem bearing boss behind the hole, filled up to the skin
    x_s = hull_r(OUT_Z)
    boss = cq.Solid.makeCylinder(BOSS_R, BOSS_LEN + 6, cq.Vector(x_s - BOSS_LEN, 0, OUT_Z),
                                 cq.Vector(1, 0, 0))
    walls = outer.fuse(boss.intersect(inside))
    return walls, bore


def stem_and_servo_holes():
    """Stem hole on the seam; servo spline hole SERVO_T along +tangent (outlet frame)."""
    ax = cq.Vector(1, 0, 0)
    x0 = hull_r(OUT_Z) - BOSS_LEN - 2.0             # stop inside the bore: don't pierce its back wall
    stem = cq.Solid.makeCylinder(STEM_HOLE / 2, 30, cq.Vector(x0, 0, OUT_Z), ax)
    servo = cq.Solid.makeCylinder(SERVO_HOLE / 2, 30, cq.Vector(A - 17.765, SERVO_T, OUT_Z), ax)
    return stem, servo


def duct_seams():
    """Angles of the seams that carry a duct and thruster on this slice."""
    if not FOUR:
        return (HALF, -HALF)
    return (HALF,) if SIDE == "L" else (-HALF,)


def has_servo():
    return not FOUR or SIDE == "R"


def at_seams(shape):
    """An outlet-frame shape on this slice's duct seams, clipped to the slice."""
    wedge_all = wedge_edges(arc(A + 50, B + 50, -math.pi / 2, math.pi / 2))
    seams = duct_seams()
    out = shape.rotate((0, 0, 0), (0, 0, 1), seams[0])
    for a_ in seams[1:]:
        out = out.fuse(shape.rotate((0, 0, 0), (0, 0, 1), a_))
    return out.intersect(wedge_all)


def slice_name():
    return ("airship pie slice 926" + ("" if not FOUR else " 4T " + ("left" if SIDE == "L" else "right"))
            + ("" if SCALE == 1 else f" x{SCALE:g}"))


def build():
    envelope = wedge_edges(arc(A, B, -math.pi / 2, math.pi / 2)).cut(
        wedge([(0, -B), (SHAFT_R, -B), (SHAFT_R, B), (0, B)]))  # keep the shaft bore clear
    walls, bore = duct_solids()
    stem_hole, servo_hole = stem_and_servo_holes()
    bosses, holes, pegs = joint_parts()

    body = frame()
    for w in windows():                     # one at a time: a compound cut
        body = body.cut(w)                  # silently drops overlapping tools
    body = body.fuse(cq.Compound.makeCompound(bosses).intersect(envelope))
    body = body.fuse(at_seams(walls)).cut(at_seams(bore))
    body = body.cut(at_seams(stem_hole))
    if has_servo():
        body = body.cut(servo_hole.rotate((0, 0, 0), (0, 0, 1), -HALF))  # this slice's servo
    body = body.cut(cq.Compound.makeCompound(holes))
    body = body.fuse(cq.Compound.makeCompound(pegs))
    body = body.cut(hatch_hole()).clean()
    return body


if __name__ == "__main__":
    s = build()
    print(f"volume {s.Volume() / 1000:.2f} cm3, faces {len(s.Faces())}, "
          f"solids {len(s.Solids())}, valid {s.isValid()}")
    cq.exporters.export(s, os.path.join(HERE, slice_name() + ".step"))
