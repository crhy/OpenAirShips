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
else is lattice: two columns of ovals with 2.0 mm ribs and hollow diamond
junctions (half-diamonds on the seams stop short of a continuous edge strip).
There are no decks. See ../../DESIGN-CONSTRAINTS.md.

Run: pip install cadquery && python3 airship_slice.py
     -> "airship pie slice 926.step"
     then: freecadcmd make_fcstd.py
     -> "airship pie slice 926.FCStd", and Print Files/PieSlice926clauderevE.stl laid
        flat for printing (FreeCAD's mesher gives a watertight STL)
"""
import math
import os
import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))

# ---- parameters (mm) -------------------------------------------------------
A, B = 207.765, 104.0      # hull outer semi-axes (radius, half-height)
T = 0.86                   # wall: exactly 2 perimeters of 0.45 mm at 0.2 mm layers
N = 8                      # slices in the ring
HALF = 180.0 / N           # half-angle of one slice, degrees

SHAFT_R = 47.375           # central shaft wall, inner radius
FLOOR_Z = -71.3            # fan-housing ceiling (the shroud over the blade tips), underside
DECK2_Z = -55.3125         # 125's lower deck height: now just a skin ring rib (no decks on the bench model)
INTAKE_R = 12.0            # the skin arc rolls into the shaft over this radius (bellmouth)

RIB = 2.0                  # frame rib width (a seam rib is RIB/2 on each slice)
WIN_R = 2.5                # window corner radius
# Skin lattice: from the fan housing to the intake bellmouth, KEEL_ROWS +
# ROWS_BELOW_EQ + ROWS_ABOVE_EQ rows of two side columns of ovals (split by a
# centre rib). Where four ovals meet, the junction is a hollow diamond window.
# Printed lying on the seam, each oval's top is a small round arch, which
# prints without supports.
ROWS_BELOW_EQ = 3          # skin rows between the DECK2_Z rib and the equator
ROWS_ABOVE_EQ = 6          # ... and between the equator and the intake bellmouth (equal arc lengths)
WIDE_FROM_Z = 1e9          # rows above this would be one wide oval per slice (off: two columns all the way up)
OVAL_N = 1.8               # superellipse exponent: 2 = ellipse; lower = bigger junction diamonds
WIDE_OVAL_N = 4.0
ROOF_ANGLE = None          # pointed window tops (e.g. 55) if bridges sag; None = plain

# Printing (Prusa MK3S+, 0.4 nozzle, 0.2 layers, 0.45 lines): the slice lies
# on its -22.5 deg (hole) seam. UP is the print's +Z in model coordinates.
UP = cq.Vector(math.sin(math.radians(HALF)), math.cos(math.radians(HALF)), 0)

# Fan housing = stationary shroud. The shaft narrows smoothly to the impeller
# eye, turns over the blade tips (SHROUD_GAP clearance) and runs out flat as
# the housing ceiling. With no gap left between the impeller tip and the shaft
# wall, housing air can't leak back up the shaft: the fan works as a shrouded
# fan. Nothing but this smooth nozzle is inside the shaft.
EYE_R = 33.0               # impeller eye (blade inlet) radius, from Analysis/AIRFLOW.md
SHROUD_RC = 8.0            # turn from axial to radial over the blades
NOZZLE_L = 30.0            # length of the contraction from the shaft to the eye
SHROUD_GAP = 1.5           # blade tip clearance under the shroud
# The keel under the fan is a removable hatch (../Propulsion: fan_hatch) that
# carries the motor and impeller. It locks with a bayonet: each slice has a lug
# at the bottom of a ring wall round the opening, and a stop post.
HATCH_R = 47.0             # opening in the keel (the 88 mm impeller passes through)
HATCH_WALL_TOP = -93.0     # ring wall round the opening
LUG_R = 44.6               # lug inner radius (0.6 mm past the impeller tip)
LUG_Z = (-99.0, -97.0)
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
DUCT_BORE = 24.0           # bore diameter (452 mm2; the thruster slot is ~110 mm2)
DUCT_W = T                 # duct wall
DUCT_MOUTH_R = 60.0        # the duct mouths sit just outside the impeller (tip r 44)
DUCT_Z_IN = -B * math.sqrt(1 - (DUCT_MOUTH_R / A) ** 2)   # skin height at the mouth

# Plenum (fan housing): only as big as the fan and the duct mouths. Flat under
# the floor out past the mouths, then a sloped ceiling down to the keel.
# Everything outside it, keel included, is oval/diamond lattice: the ducts
# carry the air from here and their own walls keep it airtight.
PLENUM_FLAT_R = 66.0
PLENUM_KEEL_R = 80.0
KEEL_ROWS = 3              # skin rows between the fan housing and the DECK2_Z rib
# OUT_Z (stem and servo axis height) is set below skin_ribs(): it sits on a
# ring rib, so the stem and servo holes' collars are part of that rib.
STEM_HOLE = 25.4           # stem is 25 mm OD / 22 mm bore (see Analysis/AIRFLOW.md)
BOSS_LEN = 12.0            # bearing sleeve behind the stem hole (reaches into the duct bulb)
DUCT_BULB = 32.0           # the duct's end swells to this bore so the stem's flange fits
BOSS_R = STEM_HOLE / 2 + 1.3      # thin bearing sleeve, not a solid block
SERVO_T = 36.0             # servo spline: this far (tangentially) from the seam
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


def rounded(cutter):
    """Fillet the window corners: the short straight edges through the wall."""
    edges = [e for e in cutter.Edges() if e.geomType() == "LINE" and e.Length() < 12.5]
    try:
        r = cutter.fillet(WIN_R, edges)
        if r.isValid() and abs(r.Volume() - cutter.Volume()) < 0.2 * cutter.Volume():
            return r
    except Exception:
        pass
    return cutter


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


def skin_ribs():
    """Ellipse angles of the skin's ring ribs, bottom to top. One sits exactly
    on the equator (z = 0), where the thrusters are."""
    psi = lambda z: math.asin(z / B)
    ke, lo = psi(keel_edge_z()), psi(DECK2_Z + T / 2)
    top = intake()[1] - (RIB / 2) / math.hypot(A * math.sin(intake()[1]), B * math.cos(intake()[1]))
    L = ellipse_arc(0.0, top)
    up, acc, h = [0.0], 0.0, top / 2000
    for i in range(2000):                            # equal arc lengths above the equator
        p = (i + .5) * h
        acc += math.hypot(A * math.sin(p), B * math.cos(p)) * h
        if acc >= L * len(up) / ROWS_ABOVE_EQ and len(up) < ROWS_ABOVE_EQ:
            up.append((i + 1) * h)
    return ([ke + (lo - ke) * i / KEEL_ROWS for i in range(KEEL_ROWS)]
            + [lo - lo * i / ROWS_BELOW_EQ for i in range(ROWS_BELOW_EQ)]
            + up + [top])


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


def node(p1, theta, ovals):
    """Diamond window in a junction of skin ovals, on ring rib p1 at azimuth theta."""
    x, z = skin_point(p1, T / 2)
    radial = cq.Vector(math.cos(theta), math.sin(theta), 0)
    origin = radial * x + cq.Vector(0, 0, z)
    n = (radial * (B * math.cos(p1)) + cq.Vector(0, 0, A * math.sin(p1))).normalized()
    u = cq.Vector(-math.sin(theta), math.cos(theta), 0)
    return diamond(origin, n, u, ovals, depth=4)


def diamond(origin, n, u, ovals, depth):
    """Diamond window at a junction of ovals (skin or deck).

    Its corners point along the two ribs. It is sized so that a full RIB
    width stays between it and every oval around it (`ovals`: the outlines
    nearby, including the neighbouring slice's across a seam).
    """
    v = n.cross(u)
    pts = []
    for ring in ovals:                                   # oval outlines (3D points on the skin)
        for i, p in enumerate(ring):
            p2 = ring[(i + 1) % len(ring)]
            for t in (0.0, 0.25, 0.5, 0.75):
                q = p + (p2 - p) * t - origin
                if q.Length < 80:
                    pts.append((q.dot(u), q.dot(v)))

    def clear(py, pz):
        return all(math.hypot(py - a_, pz - b_) >= RIB for a_, b_ in pts)

    def reach(dy, dz):
        s_ = 0.0
        while clear(dy * (s_ + 0.25), dz * (s_ + 0.25)) and s_ < 60:
            s_ += 0.25
        return s_

    ry, rz = min(reach(1, 0), reach(-1, 0)), min(reach(0, 1), reach(0, -1))
    if min(ry, rz) < 1.0:                                # every junction big enough is hollow
        return None
    k = 1.0
    while k > 0.2:                                       # shrink until every edge clears
        corners = [(ry * k, 0), (0, rz * k), (-ry * k, 0), (0, -rz * k)]
        edge = [(c0[0] + (c1[0] - c0[0]) * t / 20, c0[1] + (c1[1] - c0[1]) * t / 20)
                for c0, c1 in zip(corners, corners[1:] + corners[:1]) for t in range(21)]
        if all(clear(py, pz) for py, pz in edge):
            break
        k -= 0.05
    sk = cq.Sketch().polygon(corners + corners[:1]).vertices().fillet(min(1.5, min(ry, rz) * k / 3))
    return (cq.Workplane(cq.Plane(origin=origin, xDir=u, normal=n))
              .placeSketch(sk).extrude(depth, both=True).val())


def lens(p0, p1, side, grow=0.0):
    """The window solid for oval_outline()."""
    ring, n = oval_outline(p0, p1, side, grow)
    depth = 10 if grow else 4
    edge = cq.Edge.makeSpline([p - n * depth for p in ring], periodic=True)
    face = cq.Face.makeFromWires(cq.Wire.assembleEdges([edge]))
    return cq.Solid.extrudeLinear(face, n * (2 * depth))


def oval_outline(p0, p1, side, grow=0.0):
    """Oval (elliptical) window between ribs p0 and p1: side -1/+1 is one side
    column, side 0 one wide oval spanning the slice seam to seam.

    It is drawn in the skin's tangent plane at the cell centre and cut
    through the wall along the normal. Its width spans the column (RIB/2 in
    from the centre rib and the seam rib) and its height spans the row (RIB/2
    in from each ring rib).
    """
    pm = (p0 + p1) / 2
    d0 = (RIB / 2) / math.hypot(A * math.sin(p0), B * math.cos(p0))
    d1 = (RIB / 2) / math.hypot(A * math.sin(p1), B * math.cos(p1))
    x, z = skin_point(pm, T / 2)
    # column bounds at this radius: centre rib edge and seam rib edge
    th_out = math.radians(HALF) - math.asin((RIB / 2) / x)
    th_in = -th_out if side == 0 else math.asin((RIB / 2) / x)
    thc = side * (th_in + th_out) / 2
    width = x * (th_out - th_in)
    radial = cq.Vector(math.cos(thc), math.sin(thc), 0)
    origin = radial * x + cq.Vector(0, 0, z)
    n = (radial * (B * math.cos(pm)) + cq.Vector(0, 0, A * math.sin(pm))).normalized()
    u = cq.Vector(-math.sin(thc), math.cos(thc), 0)           # along the ring
    pts = [skin_point(p, T / 2) for p in (p0 + d0, p1 - d1)]
    v = n.cross(u)
    vs = [((radial * px + cq.Vector(0, 0, pz)) - origin).dot(v) for px, pz in pts]
    height, vc = abs(vs[1] - vs[0]), (vs[0] + vs[1]) / 2
    ex = WIDE_OVAL_N if side == 0 else OVAL_N
    a_, b_ = width / 2 + grow, height / 2 + grow
    ring = []
    for i in range(72):
        t = 2 * math.pi * i / 72
        c_, s_ = math.cos(t), math.sin(t)
        pu = a_ * math.copysign(abs(c_) ** (2 / ex), c_)
        pv = vc + b_ * math.copysign(abs(s_) ** (2 / ex), s_)
        ring.append(origin + u * pu + v * pv)
    return ring, n


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


def roofed(cell, origin, normal):
    """Cut a pointed roof into a window so that no edge is a flat ceiling.

    Print "up" is UP. In the wall's tangent plane at `origin` the roof edges
    rise at ROOF_ANGLE, and the roof sits under every point of the cell's
    upper boundary. That keeps every downward-facing edge of the window at
    least ~40 deg above horizontal.
    """
    if ROOF_ANGLE is None:
        return cell
    n = normal.normalized()
    v = (UP - n * UP.dot(n)).normalized()           # steepest up, in the wall
    h = n.cross(v)
    pts = [e.positionAt(t) for e in cell.Edges() for t in (0, .25, .5, .75, 1)]
    q = [((p - origin).dot(h), (p - origin).dot(v)) for p in pts]
    h0 = (min(a for a, _ in q) + max(a for a, _ in q)) / 2
    vmid = (min(b for _, b in q) + max(b for _, b in q)) / 2
    k = math.tan(math.radians(ROOF_ANGLE))
    top = min(b + k * abs(a - h0) for a, b in q if b > vmid)
    big = 400.0
    roof = [(h0, top), (h0 + big, top - k * big), (h0 - big, top - k * big)]
    w = [origin + h * a + v * b - n * 20 for a, b in roof]
    face = cq.Face.makeFromWires(cq.Wire.makePolygon(w, close=True))
    return cell.intersect(cq.Solid.extrudeLinear(face, n * 40))


def windows():
    """The lattice: two columns of ovals with hollow diamond junctions.

    It covers the whole skin from just outside the fan housing up to the
    intake bellmouth. The shaft, the housing ceiling and the keel under it
    stay solid: they are the intake and the plenum.
    """
    halves, whole = [column(-1), column(+1)], column(0)
    cut = []

    def radial(th):
        return cq.Vector(math.cos(th), math.sin(th), 0)

    def band(p0, p1):
        """Skin band whose edges are normal to the skin, RIB/2 in from each rib."""
        (a0, a1), (b0, b1) = [
            (skin_point(p, 6), skin_point(p, -4)) for p in
            (p0 + (RIB / 2) / math.hypot(A * math.sin(p0), B * math.cos(p0)),
             p1 - (RIB / 2) / math.hypot(A * math.sin(p1), B * math.cos(p1)))]
        return wedge([a0, a1, b1, b0])

    rows = skin_ribs()
    wide = lambda p0, p1: B * math.sin((p0 + p1) / 2) > WIDE_FROM_Z
    sides = {k: ([0] if wide(p0, p1) else [-1, 1])
             for k, (p0, p1) in enumerate(zip(rows, rows[1:]))}
    ovals = {k: [oval_outline(rows[k], rows[k + 1], sd)[0] for sd in sides[k]] for k in sides}

    def turn(rings, deg):
        c, s_ = math.cos(math.radians(deg)), math.sin(math.radians(deg))
        return [[cq.Vector(p.x * c - p.y * s_, p.x * s_ + p.y * c, p.z) for p in r] for r in rings]

    for k in sides:
        cut += [lens(rows[k], rows[k + 1], sd) for sd in sides[k]]
        if k + 1 in sides:                           # hollow junctions on the rib above row k
            near = ovals[k] + ovals[k + 1]
            spots = [(-HALF, near + turn(near, -2 * HALF)), (HALF, near + turn(near, 2 * HALF))]
            if len(sides[k]) == 2:                   # the centre rib ends at this rib
                spots.append((0.0, near))
            for th, around in spots:
                d = node(rows[k + 1], math.radians(th), around)
                if d is not None:
                    # seam diamonds stop RIB/2 short of the seam: the side edge stays continuous
                    cut.append(d if th == 0.0 else d.intersect(whole))
    keep = outlet_keepout()
    out = []
    for c in cut:
        try:
            clipped = c.cut(keep)
            if clipped.Volume() > 0.35 * c.Volume():   # drop slivers; round what stays
                out.append(rounded(clipped) if clipped.Volume() < c.Volume() - 1 else
                           (c if c.Faces()[0].geomType() != "PLANE" or len(c.Faces()) < 7
                            else rounded(c)))
        except ValueError:                  # empty: fully inside the keep-out
            pass
    return out


def outlet_keepout():
    """Solid skin only where it must be: a collar round each stem hole (both
    seams) and round this slice's servo-hub hole. Elsewhere the lattice runs
    straight over the ducts; their own walls keep them airtight."""
    ax = cq.Vector(1, 0, 0)
    stem = cq.Solid.makeCylinder(BOSS_R + 1.5, 60, cq.Vector(170, 0, OUT_Z), ax)
    servo = cq.Solid.makeCylinder(SERVO_HOLE / 2 + 3.5, 60, cq.Vector(170, SERVO_T, OUT_Z), ax)
    return (stem.rotate((0, 0, 0), (0, 0, 1), HALF)
            .fuse(stem.rotate((0, 0, 0), (0, 0, 1), -HALF))
            .fuse(servo.rotate((0, 0, 0), (0, 0, 1), -HALF)))


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
    servo = cq.Solid.makeCylinder(SERVO_HOLE / 2, 30, cq.Vector(190, SERVO_T, OUT_Z), ax)
    return stem, servo


def at_seams(shape):
    """An outlet-frame shape on both seams of this slice, clipped to the slice."""
    wedge_all = wedge_edges(arc(A + 50, B + 50, -math.pi / 2, math.pi / 2))
    both = shape.rotate((0, 0, 0), (0, 0, 1), HALF).fuse(
        shape.rotate((0, 0, 0), (0, 0, 1), -HALF))
    return both.intersect(wedge_all)


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
    body = body.cut(servo_hole.rotate((0, 0, 0), (0, 0, 1), -HALF))  # this slice's servo
    body = body.cut(cq.Compound.makeCompound(holes))
    body = body.fuse(cq.Compound.makeCompound(pegs))
    body = body.cut(hatch_hole()).clean()
    return body


if __name__ == "__main__":
    s = build()
    print(f"volume {s.Volume() / 1000:.2f} cm3, faces {len(s.Faces())}, "
          f"solids {len(s.Solids())}, valid {s.isValid()}")
    name = "airship pie slice 926"
    cq.exporters.export(s, os.path.join(HERE, name + ".step"))
