"""Airship pie slice (1 of 8), rev D: the 125 design, rebuilt cleanly.

The hull is an ellipse A x B revolved about Z and cut into 8 identical
45-degree slices. Each slice carries pegs on its +22.5 deg seam and matching
holes on its -22.5 deg seam, so slice k+1 plugs straight into slice k.

Air path: an impeller in the central shaft pulls air down into the plenum
between the floor and the keel, and the plenum feeds the thrust pipes. The
shaft, floor and keel are therefore solid, airtight walls.

The thrust ducts run inside the skin, so the hull's outside is a smooth
ellipsoid. Its only openings are the round stem and servo holes at each
outlet, plus the lightening windows. Everything is built from the parameters
below, laid out like 125: the skin, the central shaft with its rolled top
rim, the floor, the lower and main decks, and the top trough. Each is a
single thin wall. For minimum weight, the skin above the main deck is two
columns of ovals with 2.0 mm ribs and large hollow diamond junctions
(half-diamonds on the seams stop short of a continuous edge strip), with 125's slots below it. The
decks, the trough shelf and its rim wall carry window grids too.

Run: pip install cadquery && python3 airship_slice.py
     -> "airship pie slice 926.step"
     then: freecadcmd make_fcstd.py
     -> "airship pie slice 926.FCStd", and Print Files/PieSlice926clauderevD.stl laid
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
FLOOR_Z = -70.0            # floor, underside
DECK_Z = -40.625           # main deck, underside
DECK2_Z = -55.3125         # lower deck, underside (as in 125)
SHELF_Z = 82.375           # top trough floor, underside
LIP_R = 94.56              # top trough outer lip, inner radius
LIP_TOP = 91.67
RIM_R = 50.18              # top rim: inner wall of the trough, rolled over to the shaft
SKIN_TOP = 92.37           # skin ends where it meets the lip

RIB = 2.0                  # frame rib width (a seam rib is RIB/2 on each slice)
WIN_R = 2.5                # window corner radius
# Skin lattice: two full-width slots between the floor and the main deck, as
# in 125. Above the main deck, UPPER_ROWS rows of two side columns (split by a
# centre rib): the bottom row is a rounded rectangle, the rest are ovals that
# fill their cells. Where four ovals meet, the junction gets its own small
# diamond window. Printed lying on the seam, each oval's top is a small round
# arch (radius ~9 mm), which prints without supports.
UPPER_ROWS = 6
WIDE_FROM_Z = 1e9          # rows above this would be one wide oval per slice (off: two columns all the way up)
OVAL_N = 1.8               # superellipse exponent: 2 = ellipse; lower = bigger junction diamonds
WIDE_OVAL_N = 4.0
DECK_RINGS = {DECK_Z: [72.0, 96.0, 120.0, 144.0, 168.0],   # every 24 mm, as in 125
              DECK2_Z: [72.0, 96.0, 120.0, 144.0], None: []}  # None = shelf
ROOF_ANGLE = None          # pointed window tops (e.g. 55) if bridges sag; None = plain

# Printing (Prusa MK3S+, 0.4 nozzle, 0.2 layers, 0.45 lines): the slice lies
# on its -22.5 deg (hole) seam. UP is the print's +Z in model coordinates.
UP = cq.Vector(math.sin(math.radians(HALF)), math.cos(math.radians(HALF)), 0)

LEDGE_Z = -46.0            # top of the motor-spider ledge inside the shaft
LEDGE_W = 1.975            # ledge width: its bore (90.8 mm) still passes the 88 mm impeller

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
DUCT_Z_IN = -96.0          # skin height at the duct mouth (on the keel)
OUT_Z = -13.0              # stem axis height at the skin
STEM_HOLE = 16.4           # stem is 16 mm
BOSS_LEN = 6.0             # bearing boss behind the stem hole
BOSS_R = 11.0
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


def skin_ribs():
    """Ellipse angles of the skin's ring ribs, bottom to top."""
    psi = lambda z: math.asin(z / B)
    lo, top = psi(DECK_Z + T / 2), psi(SHELF_Z + T / 2)
    return ([psi(FLOOR_Z + T / 2), psi(DECK2_Z + T / 2)]
            + [lo + (top - lo) * i / UPPER_ROWS for i in range(UPPER_ROWS + 1)])


def node(p1, theta, ovals):
    """Diamond window in a junction of ovals, on rib p1 at azimuth theta.

    Its corners point along the two ribs. It is sized so that a full RIB
    width of skin stays between it and every oval around it (`ovals`: the
    outlines nearby, including the neighbouring slice's across a seam).
    """
    x, z = skin_point(p1, T / 2)
    radial = cq.Vector(math.cos(theta), math.sin(theta), 0)
    origin = radial * x + cq.Vector(0, 0, z)
    n = (radial * (B * math.cos(p1)) + cq.Vector(0, 0, A * math.sin(p1))).normalized()
    u = cq.Vector(-math.sin(theta), math.cos(theta), 0)
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
    if min(ry, rz) < 2.0:
        return None
    k = 1.0
    while k > 0.2:                                       # shrink until every edge clears
        corners = [(ry * k, 0), (0, rz * k), (-ry * k, 0), (0, -rz * k)]
        edge = [(c0[0] + (c1[0] - c0[0]) * t / 20, c0[1] + (c1[1] - c0[1]) * t / 20)
                for c0, c1 in zip(corners, corners[1:] + corners[:1]) for t in range(21)]
        if all(clear(py, pz) for py, pz in edge):
            break
        k -= 0.05
    sk = cq.Sketch().polygon(corners + corners[:1]).vertices().fillet(min(1.5, rz * k / 3))
    return (cq.Workplane(cq.Plane(origin=origin, xDir=u, normal=n))
              .placeSketch(sk).extrude(4, both=True).val())


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
    return [(r_shaft, 97.0),                        # shaft top
            (96.3, 88.0),                           # trough lip
            (r_shaft, -37.0),                       # shaft / main deck
            (r_shaft, -66.5),                       # shaft / floor
            skin_point(-math.acos(r_shaft / A), edge)]  # keel, near the axis


# ---- body ------------------------------------------------------------------
def frame():
    top_psi = math.asin(SKIN_TOP / B)
    skin = wedge_edges(arc(A, B, -math.pi / 2, top_psi),
                       arc(A - T, B - T, math.asin(SKIN_TOP / (B - T)), -math.pi / 2))
    lip = wedge([(LIP_R, SHELF_Z), (LIP_R + T, SHELF_Z),
                 (LIP_R + T, SKIN_TOP), (LIP_R, LIP_TOP)])
    rim_top = B * math.sqrt(1 - ((RIM_R + T) / A) ** 2)   # stays inside the hull
    shaft = wedge([(SHAFT_R, FLOOR_Z), (SHAFT_R + T, FLOOR_Z),
                   (SHAFT_R + T, rim_top), (SHAFT_R, rim_top)])
    rim = wedge([(RIM_R, SHELF_Z), (RIM_R + T, SHELF_Z), (RIM_R + T, rim_top),
                 (SHAFT_R, rim_top), (SHAFT_R, rim_top - T), (RIM_R, rim_top - T)])

    def deck(z, r1):
        return wedge([(SHAFT_R, z), (r1, z), (r1, z + T), (SHAFT_R, z + T)])

    inner = lambda z: hull_r(z, A - T / 2, B - T / 2)
    ledge = wedge([(SHAFT_R - LEDGE_W, LEDGE_Z - 2), (SHAFT_R + T / 2, LEDGE_Z - 2),
                   (SHAFT_R + T / 2, LEDGE_Z), (SHAFT_R - LEDGE_W, LEDGE_Z)])
    body = skin.fuse(lip, shaft, rim, ledge, deck(SHELF_Z, LIP_R + T),
                     deck(FLOOR_Z, inner(FLOOR_Z)), deck(DECK2_Z, inner(DECK2_Z)),
                     deck(DECK_Z, inner(DECK_Z)))
    return body.clean()


def ellipse_arc(p0, p1, n=200):
    """Length of the outer skin between two ellipse angles."""
    h = (p1 - p0) / n
    return sum(math.hypot(A * math.sin(p0 + (i + .5) * h), B * math.cos(p0 + (i + .5) * h))
               for i in range(n)) * h


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
    """The 125 lattice, regularised: round-cornered windows, pointed on top.

    The two rows between the floor and the main deck are full-width slots;
    above them each row has two windows either side of a centre rib, as in
    125. The decks and the trough shelf get the same treatment. The shaft,
    floor and keel stay solid: they are the fan duct and plenum.
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

    # one more row of ovals in the skin between the trough shelf and the top edge,
    # leaving a full rib along the edge
    top = math.asin(SKIN_TOP / B)
    rows = skin_ribs() + [top - (RIB / 2) / math.hypot(A * math.sin(top), B * math.cos(top))]
    wide = lambda p0, p1: B * math.sin((p0 + p1) / 2) > WIDE_FROM_Z
    sides = {k: ([0] if wide(p0, p1) else [-1, 1])
             for k, (p0, p1) in enumerate(zip(rows, rows[1:])) if k >= 3}
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
    for k, (p0, p1) in enumerate(zip(rows, rows[1:])):
        if k >= 3:
            continue
        cols = [(whole, 0.4)] if k < 2 else [(halves[0], -0.5), (halves[1], 0.5)]
        pm = (p0 + p1) / 2
        x, z = skin_point(pm, T / 2)
        for col, frac in cols:
            th = math.radians(HALF) * (frac + 0.3)       # roof frame in the upper part
            o = radial(th) * x + cq.Vector(0, 0, z)
            nrm = radial(th) * (B * math.cos(pm)) + cq.Vector(0, 0, A * math.sin(pm))
            cut.append(roofed(band(p0, p1).intersect(col), o, nrm))

    # the trough's inner rim wall (not the air shaft): one window per column
    rim_top = B * math.sqrt(1 - ((RIM_R + T) / A) ** 2)
    band_ = wedge([(RIM_R - 1, SHELF_Z + T + RIB / 2), (RIM_R + T + 1, SHELF_Z + T + RIB / 2),
                   (RIM_R + T + 1, rim_top - T - RIB / 2), (RIM_R - 1, rim_top - T - RIB / 2)])
    cut += [band_.intersect(c) for c in halves]

    # decks and the trough shelf: ring bands, two columns
    for z, rings in DECK_RINGS.items():
        z = SHELF_Z if z is None else z
        r_out = LIP_R if z == SHELF_Z else hull_r(z) - 1.5
        radii = [SHAFT_R + T if z != SHELF_Z else RIM_R + T] + rings + [r_out]
        for r0, r1 in zip(radii, radii[1:]):
            ring = wedge([(r0 + RIB / 2, z - 1), (r1 - RIB / 2, z - 1),
                          (r1 - RIB / 2, z + T + 1), (r0 + RIB / 2, z + T + 1)])
            for col, frac in ((halves[0], -0.5), (halves[1], 0.5)):
                th = math.radians(HALF) * (frac + 0.3)
                o = radial(th) * ((r0 + r1) / 2) + cq.Vector(0, 0, z)
                cut.append(roofed(ring.intersect(col), o, cq.Vector(0, 0, 1)))
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

    outer = tube(DUCT_BORE / 2 + DUCT_W)
    bore = tube(DUCT_BORE / 2, extra=3.0)           # open mouth into the plenum
    # stem bearing boss behind the hole, filled up to the skin
    x_s = hull_r(OUT_Z)
    boss = cq.Solid.makeCylinder(BOSS_R, BOSS_LEN + 6, cq.Vector(x_s - BOSS_LEN, 0, OUT_Z),
                                 cq.Vector(1, 0, 0))
    inside = wedge_edges(arc(A, B, -math.pi / 2, math.pi / 2), half=90)
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
    body = body.fuse(cq.Compound.makeCompound(pegs)).clean()
    return body


if __name__ == "__main__":
    s = build()
    print(f"volume {s.Volume() / 1000:.2f} cm3, faces {len(s.Faces())}, "
          f"solids {len(s.Solids())}, valid {s.isValid()}")
    name = "airship pie slice 926"
    cq.exporters.export(s, os.path.join(HERE, name + ".step"))
