"""Airship pie slice (1 of 8): a clean, lightweight rebuild.

The hull is an ellipse A x B revolved about Z and cut into 8 identical
45-degree slices. Each slice carries pegs on its +22.5 deg seam and matching
holes on its -22.5 deg seam, so slice k+1 plugs straight into slice k.

Air path: an impeller in the central shaft pulls air down into the plenum
between the floor and the keel, and the plenum feeds the thrust pipes. The
shaft, floor and keel are therefore solid, airtight walls.

The two thrust half-ducts are taken unchanged from the original FreeCAD
model (thrust_pipes.brep). Everything else is rebuilt from the parameters
below: skin, central shaft, floor, main deck and top trough, each a single
thin wall. The outer skin, main deck and top trough are lightened by
round-cornered, pointed-top windows.

Run: pip install cadquery && python3 airship_slice.py
     -> "airship pie slice 926.step"
     then: freecadcmd make_fcstd.py
     -> "airship pie slice 926.FCStd", and Print Files/PieSlice926.stl laid
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
SHELF_Z = 82.375           # top trough floor, underside
LIP_R = 94.56              # top trough outer lip, inner radius
LIP_TOP = 91.67
SKIN_TOP = 92.37           # skin ends where it meets the lip

RIB = 4.0                  # frame rib width (a seam rib is RIB/2 on each slice)
WIN_R = 2.5                # window corner radius
ROW_PITCH = 34.0           # target spacing of the skin's ring ribs
ROOF_ANGLE = 55.0          # window roof pitch, in the wall plane

# Printing (Prusa MK3S+, 0.4 nozzle, 0.2 layers, 0.45 lines): the slice lies
# on its -22.5 deg (hole) seam. UP is the print's +Z in model coordinates.
UP = cq.Vector(math.sin(math.radians(HALF)), math.cos(math.radians(HALF)), 0)

PEG_D, HOLE_D = 3.0, 3.3   # 0.15 mm clearance per side for FDM
PEG_L, HOLE_L = 3.6, 4.2
CHAMFER = 0.4              # peg tip and hole mouth (also eats elephant foot)
BOSS_D, BOSS_L = 7.0, 5.0

PIPES = os.path.join(HERE, "thrust_pipes.brep")          # original ducts, both seams
PIPE_VOID = os.path.join(HERE, "thrust_pipe_void.brep")  # their bore, cleared through the frame


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


def wedge_edges(*parts):
    """Revolve a closed profile of exact edges and (x, z) corner points."""
    wire = cq.Wire.assembleEdges(parts_to_edges(parts))
    solid = cq.Solid.revolve(cq.Face.makeFromWires(wire), 2 * HALF,
                             cq.Vector(), cq.Vector(0, 0, 1))
    return solid.rotate((0, 0, 0), (0, 0, 1), -HALF)


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
        return cutter.fillet(WIN_R, edges)
    except Exception:
        return cutter


def seam_axis(r, z, phi):
    """Point on the seam plane at angle phi and the unit tangent +theta."""
    p = cq.Vector(r * math.cos(phi), r * math.sin(phi), z)
    t = cq.Vector(-math.sin(phi), math.cos(phi), 0)
    return p, t


def skin_ribs():
    """Ellipse angles of the ring ribs: floor, main deck, top trough, and
    evenly spaced rings between them about ROW_PITCH apart along the skin."""
    psi = lambda z: math.asin(z / B)
    fixed = [psi(FLOOR_Z + T / 2), psi(DECK_Z + T / 2), psi(SHELF_Z + T / 2)]
    out = [fixed[0]]
    for p0, p1 in zip(fixed, fixed[1:]):
        k = max(1, round(ellipse_arc(p0, p1) / ROW_PITCH))
        out += [p0 + (p1 - p0) * i / k for i in range(1, k + 1)]
    return out


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
            skin_point(ribs[-2], edge),             # upper skin, on a ring rib
            skin_point(ribs[-3], edge),             # skin, above the nozzle
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
    shaft_top = B * math.sqrt(1 - (SHAFT_R / A) ** 2)
    shaft = wedge([(SHAFT_R, FLOOR_Z), (SHAFT_R + T, FLOOR_Z),
                   (SHAFT_R + T, shaft_top), (SHAFT_R, shaft_top)])

    def deck(z, r1):
        return wedge([(SHAFT_R, z), (r1, z), (r1, z + T), (SHAFT_R, z + T)])

    inner = lambda z: hull_r(z, A - T / 2, B - T / 2)
    body = skin.fuse(lip, shaft, deck(SHELF_Z, LIP_R + T),
                     deck(FLOOR_Z, inner(FLOOR_Z)), deck(DECK_Z, inner(DECK_Z)))
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
    """Round-cornered windows with pointed tops, one column per slice.

    Only the outer skin above the floor, the main deck and the top trough are
    lightened. The central shaft, the floor and the keel below it stay solid:
    together they are the fan duct and plenum, where the impeller pulls air
    down the shaft and pushes it out through the thrust pipes.
    """
    whole = column(0)
    cut = []
    th_top = math.radians(HALF) * 0.8                # roof frame near the top seam

    def radial(th):
        return cq.Vector(math.cos(th), math.sin(th), 0)

    # skin: bands whose edges are normal to the skin, RIB/2 in from each rib
    def band(p0, p1):
        (a0, a1), (b0, b1) = [
            (skin_point(p, 6), skin_point(p, -4)) for p in
            (p0 + (RIB / 2) / math.hypot(A * math.sin(p0), B * math.cos(p0)),
             p1 - (RIB / 2) / math.hypot(A * math.sin(p1), B * math.cos(p1)))]
        return wedge([a0, a1, b1, b0])

    rows = skin_ribs()
    for p0, p1 in zip(rows, rows[1:]):
        pm = (p0 + p1) / 2
        x, z = skin_point(pm, T / 2)
        o = radial(th_top) * x + cq.Vector(0, 0, z)
        nrm = radial(th_top) * (B * math.cos(pm)) + cq.Vector(0, 0, A * math.sin(pm))
        cut.append(roofed(band(p0, p1).intersect(whole), o, nrm))

    # decks: ring bands; their top edge is the +seam at 45 deg, no roof needed
    for z, radii in ((DECK_Z, [SHAFT_R + T, 96.0, 144.0, hull_r(DECK_Z) - 1.5]),
                     (SHELF_Z, [SHAFT_R + T, LIP_R])):
        for r0, r1 in zip(radii, radii[1:]):
            r = wedge([(r0 + RIB / 2, z - 1), (r1 - RIB / 2, z - 1),
                       (r1 - RIB / 2, z + T + 1), (r0 + RIB / 2, z + T + 1)])
            cut.append(r.intersect(whole))
    return [rounded(c) for c in cut]


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


def build():
    envelope = wedge_edges(arc(A, B, -math.pi / 2, math.pi / 2)).cut(
        wedge([(0, -B), (SHAFT_R, -B), (SHAFT_R, B), (0, B)]))  # keep the shaft bore clear
    pipes = cq.Shape.importBrep(PIPES)
    void = cq.Shape.importBrep(PIPE_VOID)
    bosses, holes, pegs = joint_parts()

    body = frame()
    for w in windows():                     # one at a time: a compound cut
        body = body.cut(w)                  # silently drops overlapping tools
    body = body.fuse(cq.Compound.makeCompound(bosses).intersect(envelope))
    body = body.cut(void).fuse(pipes)
    body = body.cut(cq.Compound.makeCompound(holes))
    body = body.fuse(cq.Compound.makeCompound(pegs)).clean()
    return body


if __name__ == "__main__":
    s = build()
    print(f"volume {s.Volume() / 1000:.2f} cm3, faces {len(s.Faces())}, "
          f"solids {len(s.Solids())}, valid {s.isValid()}")
    name = "airship pie slice 926"
    cq.exporters.export(s, os.path.join(HERE, name + ".step"))
