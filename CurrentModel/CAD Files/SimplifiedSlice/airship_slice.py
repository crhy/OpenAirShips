"""Airship pie slice (1 of 8): a clean, lightweight rebuild.

The hull is an ellipse A x B revolved about Z and cut into 8 identical
45-degree slices. Each slice carries pegs on its +22.5 deg seam and matching
holes on its -22.5 deg seam, so slice k+1 plugs straight into slice k.

The two thrust half-ducts are taken unchanged from the original FreeCAD
model (thrust_pipes.brep). Everything else is rebuilt from the parameters
below: skin, central shaft, floor, main deck and top trough, each a single
thin wall, lightened by a regular grid of round-cornered windows.

Run: pip install cadquery && python3 airship_slice.py
     ->  airship_slice.step / .stl / .brep next to this script
"""
import math
import os
import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))

# ---- parameters (mm) -------------------------------------------------------
A, B = 207.765, 104.0      # hull outer semi-axes (radius, half-height)
T = 0.625                  # wall thickness everywhere (spreadsheet: hulthickness)
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
WIN_R = 3.0                # window corner radius
SKIN_ROWS = 4              # window rows between main deck and top trough

PEG_D, HOLE_D = 3.0, 3.2   # spreadsheet: pegdiameter, holediameter
PEG_L, HOLE_L = 3.6, 4.0
BOSS_D, BOSS_L = 6.5, 5.0

PIPES = os.path.join(HERE, "thrust_pipes.brep")          # original ducts, both seams
PIPE_VOID = os.path.join(HERE, "thrust_pipe_void.brep")  # their bore, cleared through the frame


# ---- helpers ---------------------------------------------------------------
def wedge(pts, half=HALF):
    """Revolve a closed (r, z) polygon over the slice's angle."""
    w = cq.Workplane("XZ").polyline(pts).close()
    return (w.revolve(2 * half, (0, 0, 0), (0, 1, 0))
             .rotate((0, 0, 0), (0, 0, 1), -half).val())


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
    """Fillet the four shortest edges: the window corners."""
    edges = sorted(cutter.Edges(), key=lambda e: e.Length())[:4]
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
    """Ellipse angles of the ring ribs: floor, main deck, then even rows."""
    psi = lambda z: math.asin(z / B)
    lo, top = psi(DECK_Z + T / 2), psi(SHELF_Z + T / 2)
    return [psi(FLOOR_Z + T / 2)] + [lo + (top - lo) * i / SKIN_ROWS
                                     for i in range(SKIN_ROWS + 1)]


def joints():
    psi = lambda z: math.asin(z / B)
    edge = BOSS_D / 2 + T - 1.0                     # boss overlaps skin by 1 mm
    bottom_psi = -math.acos(49.1 / A)
    return [(49.1, 97.0),                           # shaft top
            (96.3, 88.0),                           # trough lip
            skin_point(skin_ribs()[-2], edge),      # upper skin, on a ring rib
            skin_point(skin_ribs()[-3], edge),      # skin, above the nozzle
            (49.1, -38.0),                          # shaft / main deck
            (49.1, -67.0),                          # shaft / floor
            skin_point(bottom_psi, edge)]           # keel, near the axis


# ---- body ------------------------------------------------------------------
def frame():
    top_psi = math.asin(SKIN_TOP / B)
    skin = wedge(ellipse(A, B, -math.pi / 2, top_psi)
                 + ellipse(A - T, B - T, math.asin(SKIN_TOP / (B - T)), -math.pi / 2))
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


def windows():
    halves, whole = [column(+1), column(-1)], [column(0)]
    cut = []

    # skin: bands whose edges are normal to the skin, RIB/2 in from each rib
    def band(p0, p1):
        (a0, a1), (b0, b1) = [
            (skin_point(p, 6), skin_point(p, -4)) for p in
            (p0 + (RIB / 2) / math.hypot(A * math.sin(p0), B * math.cos(p0)),
             p1 - (RIB / 2) / math.hypot(A * math.sin(p1), B * math.cos(p1)))]
        return wedge([a0, a1, b1, b0])

    rows = skin_ribs()
    for p0, p1 in zip(rows, rows[1:]):
        b = band(p0, p1)
        cut += [b.intersect(c) for c in halves]

    # central shaft: one window per storey, full slice width
    zs = [FLOOR_Z + T, DECK_Z, 0.0, 42.0, SHELF_Z]
    for z0, z1 in zip(zs, zs[1:]):
        r = wedge([(SHAFT_R - 2, z0 + RIB / 2), (SHAFT_R + 2, z0 + RIB / 2),
                   (SHAFT_R + 2, z1 - RIB / 2), (SHAFT_R - 2, z1 - RIB / 2)])
        cut += [r.intersect(c) for c in whole]

    # decks: ring bands between radial ribs
    for z, radii in ((FLOOR_Z, [SHAFT_R + T, 100.0, hull_r(FLOOR_Z) - 1]),
                     (DECK_Z, [SHAFT_R + T, 96.0, 144.0, hull_r(DECK_Z) - 1]),
                     (SHELF_Z, [SHAFT_R + T, LIP_R])):
        for r0, r1 in zip(radii, radii[1:]):
            r = wedge([(r0 + RIB / 2, z - 1), (r1 - RIB / 2, z - 1),
                       (r1 - RIB / 2, z + T + 1), (r0 + RIB / 2, z + T + 1)])
            cut += [r.intersect(c) for c in halves]
    return [rounded(c) for c in cut]


def joint_parts():
    """Bosses (added), holes (cut) and pegs (added) on both seams."""
    ph, pp = math.radians(-HALF), math.radians(HALF)
    bosses, holes, pegs = [], [], []
    for r, z in joints():
        p, t = seam_axis(r, z, ph)                  # hole seam, inward = +t
        bosses.append(cq.Solid.makeCylinder(BOSS_D / 2, BOSS_L, p, t))
        holes.append(cq.Solid.makeCylinder(HOLE_D / 2, HOLE_L, p - t * 0.01, t))
        p, t = seam_axis(r, z, pp)                  # peg seam, inward = -t
        bosses.append(cq.Solid.makeCylinder(BOSS_D / 2, BOSS_L, p, -t))
        peg = cq.Solid.makeCylinder(PEG_D / 2, PEG_L + 0.5, p - t * 0.5, t)
        tip = [e for e in peg.Edges()
               if e.geomType() == "CIRCLE" and (e.Center() - p).dot(t) > PEG_L - 0.1]
        pegs.append(peg.chamfer(0.4, None, tip))
    return bosses, holes, pegs


def build():
    envelope = wedge(ellipse(A, B, -math.pi / 2, math.pi / 2))
    pipes = cq.Shape.importBrep(PIPES)
    void = cq.Shape.importBrep(PIPE_VOID)
    bosses, holes, pegs = joint_parts()

    body = frame().cut(cq.Compound.makeCompound(windows()))
    body = body.fuse(cq.Compound.makeCompound(bosses).intersect(envelope))
    body = body.cut(void).fuse(pipes)
    body = body.cut(cq.Compound.makeCompound(holes))
    body = body.fuse(cq.Compound.makeCompound(pegs)).clean()
    return body


if __name__ == "__main__":
    s = build()
    print(f"volume {s.Volume() / 1000:.2f} cm3, faces {len(s.Faces())}, "
          f"solids {len(s.Solids())}, valid {s.isValid()}")
    s.exportBrep(os.path.join(HERE, "airship_slice.brep"))
    cq.exporters.export(s, os.path.join(HERE, "airship_slice.step"))
    cq.exporters.export(s, os.path.join(HERE, "airship_slice.stl"), tolerance=0.05, angularTolerance=0.2)
