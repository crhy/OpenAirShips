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
     -> "airship pie slice 1026.step"
     then: freecadcmd make_fcstd.py
     -> "airship pie slice 1026.FCStd", and Print Files/PieSlice1026-v0.2.1-8T.stl laid
        flat for printing (FreeCAD's mesher gives a watertight STL)
     and: "airship pie slice 1026.joints.json", the joint map Analysis/check_outputs.py
        --joints measures the fan and air-path clearances against.
"""
import json
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
# OAS_SLICES: slices in the ring (8, or 12 for the double-Kobra build, whose
#   30-degree slices stay under 450 mm tall when printed on the seam). With 4
#   thrusters on 12 slices every third slice is plain: OAS_SIDE=P.
# OAS_THRUSTER=L|S: large (Ø34 duct, Ø34/31 stem) or small (Ø24, Ø25/22)
#   thruster hardware; default large for 4T, small for 8T.
# OAS_PIECES=1: printable pieces for a hull too big for one print (see
#   pieces()): the intake shaft becomes separate tubes, and each slice is cut
#   along ring ribs into 5 pieces with peg joints.
VARIANT = os.environ.get("OAS_VARIANT", "8T").upper()
SIDE = os.environ.get("OAS_SIDE", "L").upper()
FOUR = VARIANT == "4T"
N = int(os.environ.get("OAS_SLICES", "8"))  # slices in the ring
LARGE = os.environ.get("OAS_THRUSTER", "L" if FOUR else "S").upper() == "L"
PIECES = os.environ.get("OAS_PIECES", "0") == "1"
assert VARIANT in ("8T", "4T") and SIDE in ("L", "R", "P")
assert N % (4 if FOUR else 8) == 0 and (FOUR or N == 8)
# OAS_SCALE: hull size factor (1 = the 415 mm bench model; 1.9 = the largest
# that prints on an Anycubic Kobra Max, 400 x 400 x 450 mm). Only the hull
# outline and its lattice grow; walls, ribs, joints, the fan, ducts,
# thrusters and servos keep their size, so mass grows ~S^2 while volume
# grows S^3.
SCALE = float(os.environ.get("OAS_SCALE", "1"))

# ---- parameters (mm) -------------------------------------------------------
A, B = 207.765 * SCALE, 104.0 * SCALE   # hull outer semi-axes (radius, half-height)
T = 0.86                   # wall: exactly 2 perimeters of 0.45 mm at 0.2 mm layers
HALF = 180.0 / N           # half-angle of one slice, degrees

FLOOR_Z = -B + (43.0 if LARGE else 32.7)   # fan-housing ceiling (the shroud over the blade tips), underside;
                                     # 4T: higher, so the Ø34 duct mouths fit under it
INTAKE_R = 12.0            # the skin arc rolls into the shaft over this radius (bellmouth)

RIB = float(os.environ.get("OAS_RIB", "2.0"))   # lattice web width (a seam rib is RIB/2 on each slice);
                                                # 1.2 = lightest printable (3 lines), for builds where stiffness doesn't matter
MIN_WEB = 0.4              # the least skin a window cut must leave itself: it stays this far
                         # inside the skin band, inside the slice's seam planes and away from
                         # its neighbouring windows. Closer than this and the boolean leaves a
                         # sliver face (0.009-0.05 mm walls on the prints, issue #36), not a
                         # thin web: see Analysis/OUTPUT-CHECK.md.
POLY_CLOSE = MIN_WEB / 2   # every window polygon is closed by this radius (erode, then dilate
                         # back): a notch or a spike in the cut boundary narrower than
                         # 2*POLY_CLOSE = MIN_WEB mm is removed before the cut is ever made.
                         # Such a notch leaves a tongue of skin that thin standing in the hole
                         # - the 0.011-0.3 mm walls and the sub-millimetre facets issue #36
                         # counts, on ovals as well as on junctions.
SKIN_MARGIN = 0.30         # how far past the skin band's inner face a window cutter may reach:
                         # the cutter's floor stops T + SKIN_MARGIN under the outer skin, so it
                         # pierces the band (T) and stays clear of a surface behind it. It must
                         # clear the band's own inner face by more than a hair: at 0.02 the floor
                         # sat 0.02 mm off that face and the boolean left 0.005-0.1 mm membranes
                         # behind it (the 8T thin-wall report, 507 facets under the layer). Nothing
                         # but air sits behind the band where the lattice cuts - the duct is kept
                         # out of the lattice by CREST_BAND - so reaching 0.3 mm past is safe.
CUT_OUT = 0.5              # how far outside the outer skin a window cutter starts (the old
                         # skin_shell()'s outer boundary was here too): enough to clear the
                         # skin's own tessellation, not enough to reach anything else.
CUT_IN = T + SKIN_MARGIN   # the depth of a window cutter's floor: T + SKIN_MARGIN under the
                         # outer face, so the lattice leaves the full T band everywhere it
                         # cuts. The duct's air ends AT the band's inner face (SKIN_BITE inside
                         # it), and no lattice window is cut within CREST_BAND of a duct crest,
                         # so a cutter's floor never reaches the air path.
CREST_BAND_SEE_DUCTS = True  # the solid band along each duct's crest is defined with the
                         # ducts below (CREST_BAND), because its width is the duct's own
                         # air path: see the definition next to DUCT_BULB.
                         # cut in it, so it is NOT in EXCEPTIONS.
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
IMP_TIP_R = 44.0           # impeller blade tip radius (88 mm impeller)
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
LUG_HALF = 6.0 * 8 / N     # lug: +-6 deg about the slice centre (8 slices; scaled with the pitch)
POST = (-6.0 * 8 / N, -3.0 * 8 / N)   # stop post over the lug: the hatch locks turning clockwise (from above)

PEG_D, HOLE_D = 3.0, 3.3   # 0.15 mm clearance per side for FDM
PEG_L, HOLE_L = 3.6, 4.2
CHAMFER = 0.4              # peg tip and hole mouth (also eats elephant foot)
BOSS_D, BOSS_L = 7.0, 5.0
AIR_KEEP = 0.6             # mm of wall a hole leaves toward the air path (joints()
                         # docstring; Analysis/check_outputs.py --joints measures it)
JOINT_CLEAR = 1.0          # mm every joint keeps from the fan housing and the
                         # impeller's swept volume (same checker)

# Thrust ducts: one per seam, split in half by the seam plane, entirely
# inside the skin. Each runs from a mouth on the keel (in the plenum) up the
# side to a closed end at the equator, where the thruster's stem enters
# through a round hole with a bearing boss behind it.
DUCT_BORE = 34.0 if LARGE else 24.0   # bore diameter; 4T: twice the area for twice the flow
DUCT_W = T                 # duct wall - and it exists on the duct's INNER side only. rhY f087
                         # item 1: "one uniform thickness across the entire design", so the duct
                         # uses the hull skin AS its outer wall: one shared wall of thickness T,
                         # not a duct wall stacked on the skin.
SKIN_BITE = 0.02           # how far the duct bore bites into the skin band: the bore's outer
                         # surface sits SKIN_BITE inside the band instead of exactly on its inner
                         # face, so the boolean is clean and the wall on the duct's outer side
                         # measures T - SKIN_BITE = 0.84 mm at every point along the duct.
SKIN_BURY = 0.04           # how far under the outer skin the duct walls' own outer boundary
                         # sits: buried in the band (flush with neither face), so the fuse adds
                         # no material on the duct's outer side and leaves no coincident face.
DUCT_MOUTH_R = 60.0        # the duct mouths sit just outside the impeller (tip r 44)
DUCT_Z_IN = -B * math.sqrt(1 - (DUCT_MOUTH_R / A) ** 2)   # skin height at the mouth

# Plenum (fan housing): only as big as the fan and the duct mouths. The keel
# skin is its floor, and the ducts hug the skin from their mouths, so their
# bottoms run straight on from it. The ceiling covers the blade tips, then eases
# down to meet the ducts' tops at the mouths, so they are flush there too; the
# outer wall stands at the mouths. Everything outside it is oval lattice with
# hollow junctions: the ducts carry the air from here in their own airtight walls.
PLENUM_FLAT_R = DUCT_MOUTH_R + 0.5   # the outer wall (air side), just past the duct mouths
PLENUM_KEEL_R = PLENUM_FLAT_R + T    # where its dry side meets the keel
PLENUM_RC = 3.0            # rounded corner where the ceiling meets the outer wall
PLENUM_RAMP = (IMP_TIP_R + 2.0, PLENUM_FLAT_R - PLENUM_RC)   # the ceiling eases down over this radius span
DUCT_FLUSH = 0.3           # the bore's top runs this far past the ceiling at the mouth (no tangent faces)
# OUT_Z (stem and servo axis height) is set below skin_ribs(): it sits on a
# ring rib, so the stem and servo holes' collars are part of that rib.
STEM_HOLE = 34.4 if LARGE else 25.4   # stem OD + 0.4: 34/31 (4T) or 25/22 mm (see Analysis/AIRFLOW*.md)
BOSS_LEN = 12.0            # bearing sleeve behind the stem hole (reaches into the duct bulb)
DUCT_BULB = 44.0 if LARGE else 32.0   # the duct's end swells to this bore so the stem's flange fits
BOSS_R = STEM_HOLE / 2 + 1.3      # thin bearing sleeve, not a solid block
CREST_BAND = DUCT_BULB / 2 + MIN_WEB
                         # half-width, mm along the skin, of the SOLID band that runs along the
                         # crest of each duct: the skin over a duct and its outlet carries NO
                         # lattice window, because with the skin as the duct's outer wall (rhY f087
                         # item 1) a window there would be a hole in the air path. The duct's crest
                         # line IS the seam plane (each duct is split in half by it), so the band is
                         # a strip CREST_BAND either side of every seam that carries a duct, over the
                         # duct's whole run. It must clear the widest part of the air path, which is
                         # the bulb (Ø32 bench, Ø44 on 4T), hence DUCT_BULB / 2 + MIN_WEB = 16.4 mm
                         # on the bench slice (was 7.4 in f086, which only had to keep window floors
                         # off a separate duct wall and left the double wall rhY objected to).
STEM_FLARE = math.degrees(math.asin(min(1.0, (STEM_HOLE / 2) / B)))
                         # the tilt of the skin's own normal at the stem hole's rim. The rim sits
                         # at ellipse angle asin((STEM_HOLE / 2) / B) - 7.0 deg at the bench 8T slice -
                         # and the hole is bored along the radial line, which at that angle is
                         # STEM_FLARE off the skin's normal there. Bore the hole straight and the
                         # wall map's ray (the skin's normal) runs into the hole's own wall at a
                         # 7 deg graze: 0.19-0.38 mm of skin between the outside and the hole's air
                         # at 1.4-6.9 mm either side of the seam - 6 of the 7 facets f085 measured,
                         # and all 7 again after the crest band (see Analysis/OUTPUT-CHECK.md).
                         # Flaring the hole by STEM_FLARE + 1.5 deg over the skin band makes the
                         # hole's wall parallel to that ray, so the ray never crosses it and the
                         # rim keeps its clearance; the hole's narrowest point is still STEM_HOLE,
                         # so the stem (Ø25, Ø34 on 4T) and its bearing sleeve fit unchanged.
SERVO_T = 44.0 if LARGE else 36.0     # servo spline: this far (tangentially) from the seam
                                     # (= the 1:1 gear pitch diameter: 44T or 36T, module 1)
SERVO_HOLE = 8.0

# ---- one wall thickness ----------------------------------------------------
# The design has ONE wall: T. Every skin, duct, shaft, floor, keel, hatch ring,
# housing and rib face is T thick. Analysis/check_outputs.py measures it on the
# print mesh (per facet, inward ray): the % of the sampled surface whose wall
# is over T + 0.25 mm, grouped into blobs with their place. Only what this list
# names may be thicker, and each entry says why:
EXCEPTIONS = [
    ("peg/hole bosses (BOSS_D, BOSS_L) and the sleeve they sit in",
     "joint_parts(): the material a Ø3 peg and a Ø3.3 hole are set in. A Ø3.3 "
     "hole punched straight into the duct's T wall would leave no wall around "
     "itself and nothing to glue to, so the wall there grows into a sleeve "
     "BOSS_D - 2*AIR_KEEP across, from the duct wall's own face to AIR_KEEP + "
     "HOLE_D past the bore: the hole keeps AIR_KEEP of wall to the air path on "
     "both sides, and the boss keeps its Ø7 footprint on duct material."),
    ("stem bearing sleeve (BOSS_R, BOSS_LEN)",
     "duct_solids(): the stem's bearing seat behind the stem hole - 1.3 mm of "
     "wall, 12 mm deep, hollow down its axis; the Ø25.4 (Ø34.4 on 4T) stem needs "
     "it, and the duct's air path stays clear of it."),
    ("lattice rib width (RIB)",
     "windows()/oval_on_skin(): ribs are RIB wide ALONG the skin and T thick "
     "across it. Width is not wall thickness; where two ribs cross the checker "
     "sees a RIB x RIB patch, which is this, not a thick wall."),
    ("keel hatch bayonet lug and stop post (LUG_R, LUG_Z, POST)",
     "hatch_ring(): the tab the fan hatch locks under - 2.9 mm of engagement set "
     "in a T-thick ring wall. The fan comes out through here."),
    ("solid crest band along each duct (CREST_BAND)",
     "clip_window()/crest_keepout(): the skin over a duct carries no lattice window, because "
     "the skin IS the duct's outer wall - a window there would be a hole in the air path. It "
     "is the normal T wall with nothing added, so it is thick only in the sense that it is "
     "solid where the rest of the skin is windowed; the wall map reads T across it."),
]


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
    h, big, th = RIB / 2, 2.5 * A, math.radians(HALF)   # reaches past the rim at any scale
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
    """Skin height of the first ring rib, just outside where the housing wall
    meets the keel (measured along the nearly flat keel, not straight up)."""
    return -B * math.sqrt(1 - ((PLENUM_KEEL_R + T + RIB / 2) / A) ** 2)


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
    if PIECES:                                      # ribs on every cut line, rows between them
        fixed = [ke] + sorted(cut_ribs().values()) + [0.0]
        fixed = sorted(set(fixed + [top]))
        out = []
        for p0, p1 in zip(fixed, fixed[1:]):
            out += equal_arcs(p0, p1, max(1, round(ellipse_arc(p0, p1) / row)))[:-1]
        return out + [top]
    below = max(3, round(ellipse_arc(ke, 0.0) / row))
    return equal_arcs(ke, 0.0, below)[:-1] + equal_arcs(0.0, top, ROWS_ABOVE_EQ)


# ---- printable pieces (OAS_PIECES=1) -----------------------------------------
PRINT_BED = (390.0, 390.0, 440.0)   # Kobra Max 400 x 400 x 450, less a margin
BAND_Z = 150.0 / 3.8        # the middle (thruster) band spans +-BAND_Z*SCALE round the equator
CUT_R = 415.0 / 3.8         # top and bottom bands are cut at this radius (x SCALE)
STUB_L = 20.0               # bellmouth stub above the intake tube
SOCK = 15.0                 # socket depth round each tube end


def cut_ribs():
    """Ellipse angles of the ribs the pieces are cut along: z = -+BAND_Z*SCALE
    (horizontal planes) and r = CUT_R*SCALE (cylinders) in the bottom and top."""
    zc = BAND_Z * SCALE
    pr = math.acos(min(1.0, CUT_R * SCALE / A))
    return {"z_lo": math.asin(-zc / B), "z_hi": math.asin(zc / B), "r_lo": -pr, "r_hi": pr}


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


def joint(name, r, z, walls, why, sleeve=None):
    """One peg/hole pair on the seam plane: where it is, the wall faces its boss
    is fused into, why it is there, and the sleeve its hole stands in (if any), as
    (s, near, far): the point s along the duct, the signed offset from the duct's
    centreline of the air-side face of the material the hole sits in (+ toward the
    skin), and how far past that face the sleeve reaches. joints() returns these;
    joint_parts() builds them, and joint_map() writes them for the checker."""
    return dict(name=name, r=r, z=z, walls=walls, why=why, sleeve=sleeve)


# Where the two duct joints sit along the duct, as an arc fraction (0 = the mouth
# in the fan housing, 1 = the bulb behind the stem hole). The duct-top one is on the
# duct's CREST - the seam plane itself - which since f087 is the one wall of T the
# hull skin and the duct's outer wall have become; the groove one is on the duct's
# interior-side wall where that wall meets the bulb's dome, which is where the
# design owner's "in that little groove there" is. Both holes stand in a sleeve
# joint_parts() grows: a Ø3.3 hole needs AIR_KEEP + HOLE_D/2 of material between
# itself and the bore, and the wall it sits in is only T thick.
S_DUCT_TOP = 0.72            # the ONE peg on top of the duct, on the seam face
S_BULB_GROOVE = 0.87         # the groove where the duct wall meets the bulb: the
                             # point where the tube's wall face crosses the bulb's
                             # dome (duct_bulb_centre, DUCT_BULB/2 + DUCT_W)


def duct_at(s):
    """Point s along the duct's centreline (duct_path), and the outward normal
    in the seam plane. The air's outer boundary is DUCT_BORE / 2 out toward the
    skin, and it ends AT the skin band's inner face - the skin IS the duct's outer
    wall (rhY f087 item 1) - while the duct's own wall on the other side runs from
    DUCT_BORE / 2 out to DUCT_BORE / 2 + DUCT_W."""
    pts = duct_path()
    seg = [(pts[i + 1] - pts[i]).Length for i in range(len(pts) - 1)]
    cum, acc = [0.0], 0.0
    for L in seg:
        acc += L
        cum.append(acc)
    d = max(0.0, min(1.0, s)) * acc
    k = max(i for i in range(len(pts) - 1) if cum[i] <= d)
    t = (d - cum[k]) / (cum[k + 1] - cum[k])
    c = pts[k] + (pts[k + 1] - pts[k]) * t
    tg = (pts[k + 1] - pts[k]).normalized()
    n = cq.Vector(tg.z, 0, -tg.x)                     # 90 deg, in the seam plane
    if n.dot(c) < 0:
        n = n * -1                                     # outward: away from the axis
    return c, n


def joints():
    """The peg/hole pairs on a seam, as records: name, (r, z), the wall faces
    the boss fuses into, and why the joint is there.

    A duct seam carries ONE peg on top of the duct, fused straight into the duct
    wall ("that would be stronger"), ONE more in the groove where the duct wall
    meets the bulb on the other side of the duct, and one in each corner where
    the duct wall meets another wall, so its cylinder is fused into BOTH walls;
    the joint between the two corner ones sits exactly midway between them on
    the same wall. Nothing else is on that face: the pegs that used to float in
    the open lattice cells there, and their holes in the neighbouring slice, are
    gone, and so are the joint that used to stand on the housing ceiling over
    the blade tips and the keel joint that used to hang over the hatch hardware -
    both were thick blocks of material over the fan, and both sat within
    JOINT_CLEAR of the impeller's swept volume.

    Holes keep >= AIR_KEEP of wall between them and the shaft, floor and keel,
    so the fan duct and plenum stay airtight, and every joint keeps >= JOINT_CLEAR
    from the fan housing and the impeller's swept volume. Analysis/check_outputs.py
    --joints measures both rules against the map this build writes.
    """
    if PIECES:                                      # one per piece, mid-way up each band
        edge = BOSS_D / 2 + 0.5                     # boss clear of the skin, not tangent to it
        c = cut_ribs()
        mids = [(c["z_hi"] + c["r_hi"]) / 2,          # top outer piece
                (c["r_hi"] + skin_ribs()[-1]) / 2,    # top inner piece
                (c["z_lo"] + c["r_lo"]) / 2,          # bottom outer piece
                c["z_hi"] * 0.6]                      # middle band, clear of the stem hole
        out = [joint("piece_%d" % (i + 1), skin_point(p, edge)[0], skin_point(p, edge)[1],
                     ["hull skin"], "one joint per printable piece, mid-way up its band")
               for i, p in enumerate(mids)]
        out.append(joint("housing_ceiling", IMP_TIP_R, FLOOR_Z + T + BOSS_D / 2 - 0.5,
                         ["fan housing ceiling"],
                         "pieces build: on the housing ceiling, over the blade tips"))
        out.append(joint("keel", skin_point(-math.acos(53.0 / A), edge)[0],
                         skin_point(-math.acos(53.0 / A), edge)[1], ["keel skin"],
                         "pieces build: on the keel, outside the hatch ring"))
        return out
    if FOUR:
        # a 4-thruster slice's two seams are NOT alike (a left slice carries its
        # half-duct on +HALF and a plain seam on -HALF), so its joints cannot sit
        # on duct walls: it keeps the old skin/shaft/keel layout. Open item - 4T
        # wants per-seam joint lists; the 8T design is the one rebuilt here.
        edge = T + HOLE_D / 2 + 1.0                     # hole centre depth under skin
        r_shaft = SHAFT_R + T + HOLE_D / 2 + 0.6        # boss on the outside of the shaft
        ribs = skin_ribs()
        return [joint("shaft_top", r_shaft, intake()[2] - 4.0, ["intake shaft wall"],
                      "shaft top, under the bellmouth"),
                joint("upper_skin", skin_point(ribs[-3], edge)[0],
                      skin_point(ribs[-3], edge)[1], ["hull skin"], "upper skin, on a ring rib"),
                joint("shaft", r_shaft, nozzle_top() + 4.0, ["intake shaft wall"],
                      "shaft, above the contraction"),
                joint("housing_ceiling", IMP_TIP_R, FLOOR_Z + T + BOSS_D / 2 - 0.5,
                      ["fan housing ceiling"], "on the housing ceiling, over the blade tips"),
                joint("keel", skin_point(-math.acos(53.0 / A), edge)[0],
                      skin_point(-math.acos(53.0 / A), edge)[1], ["keel skin"],
                      "keel, outside the hatch ring")]
    out = []
    # rhY f087 item 3: the duct pegs are ONLY these two, and the duct-top one is ON
    # the duct's crest, not on the duct's interior wall. The duct's crest line IS the
    # seam plane (each duct is split in half by it), so "on top of the duct, at the
    # seam face" is the one wall of T that the hull skin and the duct's outer wall
    # have become (item 1); the hole is set SKIN_BITE inside the band's inner face
    # and keeps AIR_KEEP of wall to the air, in the sleeve joint_parts() grows.
    c, n = duct_at(S_DUCT_TOP)
    p = c + n * (DUCT_BORE / 2 - SKIN_BITE - AIR_KEEP - HOLE_D / 2)
    out.append(joint("duct_top", p.x, p.z,
                     ["hull skin", "duct outer wall (the shared wall)"],
                     "the ONE peg on top of the duct, on the seam face: the duct's crest "
                     "line IS the seam plane, so this is the single wall of T the hull "
                     "skin and the duct's outer wall have become (rhY f087 item 1). It "
                     "replaces the peg that used to stand on the duct's interior wall "
                     "beside the bulb - the one rhY marked with an X - and the two that "
                     "used to float in the open lattice cells there.",
                     (S_DUCT_TOP, DUCT_BORE / 2 - SKIN_BITE, AIR_KEEP + HOLE_D)))
    c, n = duct_at(S_BULB_GROOVE)
    p = c - n * (DUCT_BORE / 2 + AIR_KEEP + HOLE_D / 2)
    out.append(joint("bulb_groove", p.x, p.z,
                     ["duct inner wall", "duct bulb wall"],
                     "one more peg for strength, on the other side of the duct from the "
                     "duct-top peg, seated in the groove where the duct's wall meets the "
                     "bulb's dome: the boss fuses into the duct wall and the bulb's wall, "
                     "and the hole keeps AIR_KEEP of wall to the air path.",
                     (S_BULB_GROOVE, -DUCT_BORE / 2, AIR_KEEP + HOLE_D)))
    for name, p, walls, why, sl in corner_joints():
        out.append(joint(name, p.x, p.z, walls, why, sl))
    return out


def corner_joints():
    """The three corners rhY marked in red, and the midway joint on the seam wall.

    Returns (name, point in the seam plane, the walls the boss fuses into, why,
    sleeve or None) for each. A corner joint sits where two walls meet, so its
    cylinder is fused into BOTH walls (the two-wall rule); the joint between the
    two corner ones on the seam wall's face sits exactly midway between them on
    that same wall. Every one keeps >= JOINT_CLEAR from the fan housing, the
    plenum air and the impeller's swept volume, and >= AIR_KEEP of wall to any
    air side - Analysis/check_outputs.py --joints measures both against the map
    this build writes - and all four are on the seam wall's face, where clip_window
    keeps every lattice window MIN_WEB clear, so the peg and the matching hole
    print as solid pegs rather than a peg standing over an open window.
    """
    e = BOSS_D / 2 + 0.5       # hole/boss centre depth under the outer skin. The boss is
                         #   BOSS_D (7.0) across, so its outer face sits 0.5 mm under the skin's
                         #   own outer face: deep enough that the fuse cannot leave a membrane of
                         #   itself under the skin (at T + HOLE_D/2 + 1.0 = 3.51 that face sat
                         #   0.01 mm under the skin and the 8T slice came out with 0.004-0.05 mm2
                         #   sliver faces at every corner joint, which is what the mesh then
                         #   self-intersected on), and still 0.36 mm into the T band that holds it.
    #   stays 1.0 mm inside the skin, and the boss (BOSS_D across, BOSS_L deep)
    #   is fused into the corner's two walls.
    out = []
    # (a) the TOP-LEFT corner of the slice: the left end of the top edge, where the
    # top wall - the solid skin band the lattice stops under, below the intake
    # bellmouth - meets the left seam and the skin.
    r, z = skin_point(lattice_band()[1], e)
    top = cq.Vector(r, 0, z)
    out.append(("corner_top", top, ["hull skin", "seam edge strip"],
                "the top-left corner of the slice: the top wall (the solid skin under the "
                "intake bellmouth) meets the seam and the skin. Peg on one slice, hole in "
                "the neighbour, fused into both walls of the corner.", None))
    # (b) the TOP-RIGHT corner: the right end of that same wall, where it meets the
    # duct's outer end - the top of the duct's run, where the solid skin over the
    # duct (the crest band) ends and the lattice resumes, on the seam.
    r, z = skin_point(crest_psi_range()[1], e)
    dend = cq.Vector(r, 0, z)
    out.append(("corner_duct_top", dend, ["hull skin", "duct end wall"],
                "the top-right corner of the slice: the top wall meets the duct's outer "
                "end, where the solid skin over the duct ends and the lattice resumes. Peg "
                "on one slice, hole in the neighbour, fused into both walls of the corner.",
                None))
    # (c) the corner just left of the bulb, low on the slice: where the skin meets
    # the bulb's dome / the duct's root. Found as the crossing of the dome's outer
    # face (the sphere DUCT_W thick over the bulb's bore) with the skin band's inner
    # face, on the mouth side of the bulb.
    cb = duct_bulb_centre()
    r_out = DUCT_BULB / 2 + DUCT_W
    lo, hi = -0.6, 0.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if (cq.Vector(*skin_point(mid, T), 0) - cb).Length < r_out:
            hi = mid
        else:
            lo = mid
    r, z = skin_point(lo, e)
    root = cq.Vector(r, 0, z)
    out.append(("corner_bulb_root", root, ["hull skin", "duct bulb wall"],
                "the corner just left of the bulb, low on the slice: the skin meets the "
                "bulb's dome and the duct's root. Peg on one slice, hole in the neighbour, "
                "fused into both walls of the corner; the hole keeps AIR_KEEP of wall to "
                "the bulb's air.", None))
    # (d) the joint between the two corner ones on the same wall - the seam wall's
    # face runs from the top corner to the bulb-root corner - sits exactly midway
    # between them on that wall.
    mid = (top + root) * 0.5
    out.append(("seam_mid", mid, ["hull skin", "seam edge strip"],
                "the joint between the two corner ones, exactly midway between them on "
                "the same wall (the seam wall's face, top corner to bulb-root corner), "
                "as the design owner's rule asks.", None))
    return out



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
    z_low = tube_top() if PIECES else nozzle_top() - 1   # pieces: a stub over the intake tube
    wall = wedge_edges(arc(A, B, -math.pi / 2, p_top), roll(INTAKE_R),
                       (SHAFT_R, z_low), (SHAFT_R + T, z_low),
                       cq.Edge(roll(ri).wrapped.Reversed()),
                       arc(A - T, B - T, p_in, -math.pi / 2))
    body = wall.fuse(plenum_ceiling(), hatch_ring())
    if PIECES:                                      # sockets that the tube ends slide into
        body = body.fuse(socket(tube_top(), -1), socket(nozzle_top() + 1.0, +1))
    return body.clean()


def tube_top():
    return intake()[2] - STUB_L


def socket(z_face, direction):
    """Collar round a tube end: the tube butts on the wall's end face at
    z_face and the collar reaches SOCK past it (direction -1 down, +1 up)."""
    ri, ro = SHAFT_R + T + 0.15, SHAFT_R + 2 * T + 0.15
    z1 = z_face + direction * SOCK
    z0 = z_face - direction * 2.0                   # 2 mm onto the wall it grows from
    pts = [(ri, z_face), (ri, z1), (ro, z1), (ro, z0), (SHAFT_R + T / 2, z0), (SHAFT_R + T / 2, z_face)]
    return wedge(pts)


def tube_segments(max_len=400.0):
    """The intake tube (OAS_PIECES): full-round Ø66 tubes printed upright,
    from the fan housing up into the bellmouth stub. Where two meet, the
    lower one carries a socket for the upper one."""
    z0, z1 = nozzle_top() + 1.0, tube_top()
    n = max(1, math.ceil((z1 - z0) / max_len))
    edges = [z0 + (z1 - z0) * i / n for i in range(n + 1)]
    ri, ro = SHAFT_R + T + 0.15, SHAFT_R + 2 * T + 0.15
    out = []
    for i, (a_, b_) in enumerate(zip(edges, edges[1:])):
        pts = [(SHAFT_R, a_), (SHAFT_R + T, a_), (SHAFT_R + T, b_), (SHAFT_R, b_)]
        if i < n - 1:                               # socket round the next tube's foot
            pts = [(SHAFT_R, a_), (SHAFT_R + T, a_), (SHAFT_R + T, b_ - 2.0), (ro, b_ - 2.0),
                   (ro, b_ + SOCK), (ri, b_ + SOCK), (ri, b_), (SHAFT_R, b_)]
        out.append(wedge(pts, half=180.0).clean())
    return out


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
    zm = duct_path()[0].z + DUCT_BORE / 2 - DUCT_FLUSH   # ceiling at the mouths: the ducts' tops
    r0, r1 = PLENUM_RAMP
    pts.append((r0, FLOOR_Z))
    for i in range(1, n + 1):                       # ease down to the ducts' tops (cosine: no kinks)
        pts.append((r0 + (r1 - r0) * i / n, FLOOR_Z + (zm - FLOOR_Z) * (1 - math.cos(math.pi * i / n)) / 2))
    rc, ro = PLENUM_RC, PLENUM_FLAT_R
    for i in range(1, n // 2 + 1):                  # round into the outer wall
        ph = math.pi / 2 * i / (n // 2)
        pts.append((ro - rc + rc * math.sin(ph), zm - rc + rc * math.cos(ph)))
    zk = -(B - T) * math.sqrt(1 - (ro / (A - T)) ** 2)
    pts.append((ro, zk - 1.5))                      # down the outer wall into the keel skin
    return pts


def housing_space(grow=0.0):
    """The air inside the housing, from the keel up to its ceiling and out to its
    outer wall, grown `grow` into the walls (to trim a duct's start against)."""
    pts = [(r, z) for r, z in shroud_curve()[1:]
           if r >= EYE_R + SHROUD_RC - 1e-9 and z <= FLOOR_Z + 1e-9]
    off = []
    for i, (r, z) in enumerate(pts):                 # same dry-side normal as plenum_ceiling()
        a_, b_ = pts[max(i - 1, 0)], pts[min(i + 1, len(pts) - 1)]
        dr, dz = b_[0] - a_[0], b_[1] - a_[1]
        L = math.hypot(dr, dz)
        off.append((r - dz / L * grow, z + dr / L * grow))
    return wedge([(0, FLOOR_Z + grow)] + off + [(off[-1][0], -B - 1), (0, -B - 1)], half=60)


def housing_outline():
    """(r, z) outline of everything the housing takes up, walls included, from
    the axis out (for gas-volume sums)."""
    ceil = [(r, z) for r, z in shroud_curve()[1:-1]
            if EYE_R + SHROUD_RC - 1e-9 <= r <= PLENUM_FLAT_R - PLENUM_RC + 1e-9 and z <= FLOOR_Z + 1e-9]
    ceil = sorted(set(ceil), key=lambda q: -q[0])   # outside in
    return ([(0, -B - 1), (PLENUM_KEEL_R, -B - 1), (PLENUM_KEEL_R, ceil[0][1] + T)]
            + [(r, z + T) for r, z in ceil]
            + [(SHAFT_R + T, FLOOR_Z + T), (SHAFT_R + T, nozzle_top()), (0, nozzle_top())])


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


_BAND = None


def ear_clip(poly):
    """Triangulate a simple polygon: index triples of `poly` = [(u, v), ...].

    The window cutter is a closed solid whose two caps cannot be flat faces - the
    outline's points lie on a curved skin - so each cap is triangulated and every
    face of the cutter is a triangle (measured: a shell of ruled surfaces between
    the outline's two rings gives faces BRepCheck calls invalid, and Face.makeFromWires
    refuses a non-planar wire outright; an all-triangle shell gives a valid solid).
    Plain O(n^2) ear clipping on a 96-point outline is nothing next to the booleans.
    Repeated points and hair-of-collinearity are what make a strict ear search stall,
    so they are dropped first and the largest convex corner is taken when no strict
    ear exists - the polygon comes out of shapely buffer/clip, so it is simple.
    """
    def area(a, b, c):
        return ((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))

    def inside(p, a, b, c):
        return (area(a, b, p) >= -1e-9 and area(b, c, p) >= -1e-9 and
                area(c, a, p) >= -1e-9)
    clean = []
    for p in poly:
        if clean and abs(p[0] - clean[-1][0]) < 1e-9 and abs(p[1] - clean[-1][1]) < 1e-9:
            continue
        clean.append(p)
    if len(clean) > 2 and abs(clean[0][0] - clean[-1][0]) < 1e-9 \
            and abs(clean[0][1] - clean[-1][1]) < 1e-9:
        clean.pop()
    if len(clean) < 3:
        return []
    idx = list(range(len(clean)))
    if area(clean[idx[0]], clean[idx[1]], clean[idx[2]]) < 0:
        idx.reverse()
    out = []
    while len(idx) > 3:
        best = None
        for k in range(len(idx)):
            a, b, c = idx[k - 1], idx[k], idx[(k + 1) % len(idx)]
            ar = area(clean[a], clean[b], clean[c])
            if ar <= 1e-9:
                continue
            if any(inside(clean[m], clean[a], clean[b], clean[c])
                   for m in idx if m not in (a, b, c)):
                continue
            if best is None or ar > best[1]:
                best = (k, ar, (a, b, c))
        if best is None:                     # no strict ear left: take the widest corner
            for k in range(len(idx)):
                a, b, c = idx[k - 1], idx[k], idx[(k + 1) % len(idx)]
                ar = area(clean[a], clean[b], clean[c])
                if best is None or ar > best[1]:
                    best = (k, ar, (a, b, c))
        if best is None:
            return []
        out.append(best[2])
        idx.pop(best[0])
    if len(idx) == 3:
        out.append((idx[0], idx[1], idx[2]))
    return out


def skin_cutter(pts):
    """Window cutter from an outline on the skin (points and normals): a RADIAL
    prism - the outline's side walls run along the skin's own normal AT each point
    of the outline, from CUT_OUT (0.5 mm) outside the outer face to CUT_IN (T +
    SKIN_MARGIN) under it - closed into a solid by triangulated caps.

    Why radial, measured on the 8T bench slice: the checker fires a ray along each
    facet's normal and reads the distance to the first surface it meets. A wall
    built as a straight prism along the normal at the window's CENTRE is up to 16
    deg off the skin's normal at that wall's own edge (the ellipse's curvature radius
    at the equator is B^2 / A = 52 mm and a cell is 30 mm across), so a ray along
    the skin's normal crosses the wall at a graze and reads d / sin(swing): f086
    measured 40 facets under the 0.40 mm nozzle, 0.042-0.399 mm, every one of them
    a facet within 0.4 * sin(swing) mm of a cut wall - a graze along a near-parallel
    wall, not a thin wall of material. Along the LOCAL normal the swing is the
    normal's turn over one outline segment (0.3 deg for a 96-point outline here),
    so the ray never crosses the wall and the reading is the band itself.

    Kept from the attempts before this one (all measured on the 8T bench slice):
      - a through-cut of the band, floor at T + 1.5 mm below the band's inner face,
        crosses the duct's surfaces at a shallow angle and the fuse leaves 0.061 mm
        fins behind (12 facets under the nozzle, worse than 7);
      - stopping the cutter short of the duct wall's outside face: the floor and that
        face coincide, 0.049 mm plates;
      - an axis-offset shell (0.5 mm past BOTH faces) puts the inner boundary 1.36 mm
        under the skin, past the duct's air and level with the housing wall and the
        keel skin where the lattice meets them - it cuts a face that thin off a
        surface that is already there;
      - lofting the cutter so the floor leans 12 deg off the normal: the kernel returns
        a bad loft, the slice came out as 12 solids and 1,341 facets under the nozzle;
      - lofting the outline along its own normal field: makeLoft returns invalid solids,
        five of the 56 cutters came out 70 litres wide;
      - cutting in 6 mm patches, each a straight prism along the normal at its own part
        of the outline: the patch compounds fragment against the shell (81 solids on
        one oval) and a cut lands with no effect at all.
    The radial prism builds: no loft, no patch, no shell to trim against - the caps
    are at the two depths the old shell's boundaries were at, so nothing inside the
    band's inner face is ever touched.
    """
    if len(pts) > 48:                       # ~1 mm of outline is plenty, and the
        pts = pts[::2]                    # face count is what costs the boolean
    c = sum((p for p, _ in pts), cq.Vector()) * (1 / len(pts))
    nrm = sum((nv for _, nv in pts), cq.Vector()).normalized()
    xd = (pts[0][0] - c)
    xd = (xd - nrm * xd.dot(nrm)).normalized()
    yd = nrm.cross(xd)
    uv = [((p - c).dot(xd), (p - c).dot(yd)) for p, _ in pts]
    tris = ear_clip(uv)
    if not tris:
        print(f"warning: window outline would not triangulate at {c.x:.0f}, {c.y:.0f}, "
              f"{c.z:.0f}")
        return None
    ri = T / 2                                    # the outline is on the band's mid-surface
    #   surface()/duct_at() normals point OUT of the hull, away from the axis, so
    #   +n goes out past the outer face and -n goes in past the band's inner face.
    out_ring = [p + nv * (ri + CUT_OUT) for p, nv in pts]
    in_ring = [p - nv * (CUT_IN - ri) for p, nv in pts]

    def build(ring_a, ring_b):
        """Close the two rings into a solid: every face a triangle. The caps are the
        ear-clipped outline; each side quad is split along a diagonal - the four
        points are not quite coplanar (the skin normal turns 0.3 deg over one
        outline segment), and a non-planar face is what the kernel refuses: measured
        here, Face.makeFromWires raises "wires not planar" and a shell of ruled
        surfaces between the rings gives faces BRepCheck calls invalid, while an
        all-triangle shell gives a valid solid."""
        def tri(a, b, c):
            return cq.Face.makeFromWires(cq.Wire.makePolygon([a, b, c, a]))
        faces = []
        for a, b, k in tris:
            faces.append(tri(ring_a[a], ring_a[b], ring_a[k]))
            faces.append(tri(ring_b[a], ring_b[k], ring_b[b]))
        n = len(ring_a)
        for i in range(n):
            j = (i + 1) % n
            faces.append(tri(ring_a[i], ring_a[j], ring_b[j]))
            faces.append(tri(ring_a[i], ring_b[j], ring_b[i]))
        try:
            sol = cq.Solid.makeSolid(cq.Shell.makeShell(faces))
        except Exception:
            return None
        return sol if (sol.isValid() and sol.Volume() > 0) else None

    sol = build(out_ring, in_ring) or build(in_ring, out_ring)
    if sol is None:
        print(f"warning: radial cutter would not build at {c.x:.0f}, {c.y:.0f}, "
              f"{c.z:.0f}")
        return None
    if sol.Volume() < 1.0:
        print(f"warning: empty window cutter at {c.x:.0f}, {c.y:.0f}, {c.z:.0f}")
    return sol


def skin_frame(psi, theta):
    """uv <-> skin for a window centred on the skin at (psi, theta).

    uv is the flat tangent plane there, except in PIECES builds, where the big
    cells near the axis are laid out on the skin unrolled instead (a flat plane
    distorts them badly). Returns (to_uv, to_skin, sgn): sgn is the way +v runs
    along the skin.
    """
    origin, nrm = surface(psi, theta)
    u = cq.Vector(-math.sin(theta), math.cos(theta), 0)
    v = nrm.cross(u)
    tang = cq.Vector(-A * math.sin(psi) * math.cos(theta), -A * math.sin(psi) * math.sin(theta),
                     B * math.cos(psi)).normalized()                 # up the skin
    sgn = 1.0 if v.dot(tang) > 0 else -1.0
    x0 = skin_point(psi, T / 2)[0]
    # The frame is the skin UNROLLED (azimuth x arc length), not the flat tangent
    # plane at (psi, theta): every window polygon, every clip line and every
    # neighbour buffer is then measured in a frame that is isometric with the
    # skin. The old flat-plane frame mapped the skin twice (once to lay the
    # polygon out, once through to_skin when the cutter was built), and where
    # the skin curves away from that plane - along the seams, at the keel, at
    # the bellmouth - the two mappings disagree by up to a millimetre, and the
    # cut boundary lands on top of itself: 553 pairs of faces 0.002-0.4 mm
    # apart on the bench 8T slice, which is what prints as the 0.007-0.4 mm
    # walls issue #36 counts. (PIECES builds already did this; it is now the
    # only mapping, so the lattice cannot drift between the two.)
    def psi_of(p):
        # the ellipse angle of a point on the skin's MID line. The mid line is the
        # skin offset inwards by T / 2, which is not an ellipse, so the plain
        # atan2(z * A, rho * B) inverse is wrong by 0.26 mm anywhere and by 5 mm
        # near the bellmouth. Undo the offset first, then take the angle.
        rho, z = math.hypot(p.x, p.y), p.z
        ps = math.atan2(z * A, rho * B)
        for _ in range(3):
            nx, nz = B * math.cos(ps), A * math.sin(ps)
            L = math.hypot(nx, nz)
            ps = math.atan2((z + (T / 2) * nz / L) * A,
                            (rho + (T / 2) * nx / L) * B)
        return ps

    # The uv frame is the skin unrolled - azimuth across, ellipse angle up - and
    # to_uv is the exact analytic inverse of to_skin, not a projection of 3D
    # points onto the tangent plane at (psi, theta). A projection is a different
    # map from the one that lays the cutter back down: the two disagree by up to
    # a millimetre wherever the skin curves away from that plane (along the seams,
    # at the keel, at the bellmouth), and the cut boundary then lands on top of
    # itself - 553 pairs of faces 0.002-0.4 mm apart on the bench 8T slice, which
    # is what prints as the 0.007-0.4 mm walls issue #36 counts. With one map,
    # the band's edges and the slice's seam planes are also exact straight uv
    # lines, which is what clip_window already measures them as.
    x0, ds = skin_point(psi, T / 2)[0], ds_dpsi(psi)

    def to_uv(p):
        return ((math.atan2(p.y, p.x) - theta) * x0, sgn * (psi_of(p) - psi) * ds)

    def to_skin(uu, vv):
        ps = psi + sgn * vv / ds
        # the skin ends at the axis: past psi = +-pi/2 the radius goes negative and
        # the azimuth flips, which would fold a window's outline into a spike.
        # The band's own clip keeps windows off the rim, so this only ever bites
        # a polygon's buffer, and it folds that edge onto the rim instead.
        lim = math.pi / 2 - 1e-9
        ps = max(-lim, min(lim, ps))
        return surface(ps, theta + uu / x0)
    return to_uv, to_skin, sgn


def lattice_band():
    """Where the skin the lattice sits on actually is: the ring rib just outside
    the fan housing, the rib under the intake bellmouth, and the slice's half-angle."""
    global _BAND
    if _BAND is None:
        rows = skin_ribs()
        _BAND = (rows[0], rows[-1], math.radians(HALF))
    return _BAND


def clip_window(poly, psi, theta, to_uv, to_skin, sgn, others=(), tip=0.6):
    """A window polygon, kept MIN_WEB inside the skin band, MIN_WEB inside the
    slice's seam planes, MIN_WEB away from the windows around it, with its tips
    rounded by `tip` (0 for an oval: it has no tips, and rounding a 96-point
    outline only loses area). Returns the polygon, or None if nothing printable
    is left.

    This is the sliver fix, and it happens before a window becomes a solid. A
    window whose boundary touches the band's edge, a seam plane or a neighbouring
    window is cut flush against a face that is already there, and the kernel
    leaves a sliver behind: a face 0.000 mm from the face it was cut by, which
    prints as a 0.01-0.05 mm wall, i.e. a hole (issue #36). A notch or a spike in
    the boundary narrower than MIN_WEB does the same thing the other way round: it
    leaves a tongue of skin that thin standing in the hole. Nothing repairs either
    afterwards, so the polygon is clipped and closed here, in shapely.
    """
    from shapely.geometry import box
    from shapely.ops import unary_union
    if poly is None or poly.is_empty:
        return None
    if tip > 0.0:
        poly = poly.buffer(-tip).buffer(tip)          # round the tips first
    if poly.is_empty:
        return None
    psi_lo, psi_hi, th_half = lattice_band()
    x0, ds = skin_point(psi, T / 2)[0], ds_dpsi(psi)
    # The frame maps uv back to the skin as (psi + sgn*v/ds, theta + u/x0), so
    # the band's edges and the slice's seam planes are straight uv lines at a
    # fixed v / a fixed u. They must be measured that way, not by projecting
    # those 3D edges into the tangent plane: near the keel and the bellmouth that
    # plane is nearly horizontal, and they land in the middle of the window.
    u_lo, v_lo, u_hi, v_hi = poly.bounds
    span = [psi + sgn * vv / ds for vv in (v_lo, (v_lo + v_hi) / 2, v_hi)]
    mv = MIN_WEB * max(ds_dpsi(q) for q in span) / ds            # the band's edges
    # the seam planes: a junction on a seam stops inside this slice's own edge strip
    # (RIB / 2 per slice, the two slices' strips glue into one RIB rib), and never closer
    # than MIN_WEB to the slice's side face, so the cut is never flush with it
    mu = max(MIN_WEB, RIB / 2) * x0 / min(skin_point(q, T / 2)[0] for q in span)
    u_seam = sorted(((th_half - theta) * x0, (-th_half - theta) * x0))
    v_band = sorted((sgn * (psi_lo - psi) * ds, sgn * (psi_hi - psi) * ds))
    keep = box(u_seam[0] + mu, v_band[0] + mv, u_seam[1] - mu, v_band[1] - mv)
    poly = poly.intersection(keep)
    # The solid crest band along each duct (CREST_BAND either side of the crest line, which
    # is the seam plane: the duct is split in half by it). No window is cut inside it, and none
    # is left within MIN_WEB of its edge: a cut boundary that close is what left the 0.186-0.382
    # mm crest walls and the 0.004 mm2 sliver face f085 measured, all within 6.9 mm of a seam.
    # In this uv frame the band is a straight u-strip (u = (azimuth - theta) * x0 is the
    # perpendicular distance from the seam plane), so the clip is exact and the lattice simply
    # stops at the band's edge - the cells keep their rib lines, they are re-flowed around it.
    for s_ in duct_seams():
        u_c = (math.radians(s_) - theta) * x0
        before = poly.area
        poly = poly.difference(box(u_c - CREST_BAND - MIN_WEB, v_band[0],
                                   u_c + CREST_BAND + MIN_WEB, v_band[1]))
        if poly.is_empty:
            return None
        if poly.area < 0.6 * before:
            # the crest band cutting a window down to a chip leaves a slot a few tenths of a
            # mm wide, and such a slot severs the web beside it: the 8T skin came off the slice
            # in 16 islands, 1.2-2.8 mm adrift of the rest. A window either survives or is not
            # cut at all.
            return None
    if others:
        before = poly.area
        poly = poly.difference(unary_union([o.buffer(MIN_WEB) for o in others]))
        if poly.is_empty:
            return None
        if poly.area < 0.6 * before:
            return None
    # Close the boundary: erode then dilate by POLY_CLOSE. A notch or a spike
    # narrower than 2*POLY_CLOSE = MIN_WEB mm is removed, so no cut can leave a
    # tongue of skin under MIN_WEB wide behind it. Ribs (RIB = 2.0 mm) and the
    # webs between windows are far wider, so nothing structural moves.
    poly = poly.buffer(-POLY_CLOSE).buffer(POLY_CLOSE)
    parts = [g for g in getattr(poly, "geoms", [poly]) if g.geom_type == "Polygon" and g.area > 6.0]
    if not parts:
        return None
    return max(parts, key=lambda g_: g_.area)


def junction(psi, theta, ovals, keep_side=0):
    """Hollow junction where ovals meet on the rib at psi, azimuth theta: all
    the skin that is more than RIB from every oval around it (`ovals`: skin
    points, including the neighbouring slice's across a seam). keep_side
    +1/-1 keeps only the side of the rib above/below, RIB/2 off it (for the
    first and last ribs). Returns skin points of its outline, or None."""
    from shapely.geometry import Point, Polygon, box
    from shapely.ops import unary_union
    to_uv, to_skin, sgn = skin_frame(psi, theta)
    reach = 60.0 * SCALE
    polys, raw = [], []
    for ring in ovals:
        uv = [to_uv(p) for p, _ in ring]
        if min(math.hypot(a_, b_) for a_, b_ in uv) < reach:
            p0 = Polygon(uv)
            raw.append(p0)
            polys.append(p0.buffer(RIB))
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
    g = clip_window(min(near, key=lambda g_: g_.distance(probe)), psi, theta, to_uv, to_skin, sgn, raw)
    if g is None:
        return None
    ring = list(g.exterior.coords)[:-1]
    per = g.exterior.length
    pts = [g.exterior.interpolate(per * i / 80) for i in range(80)]    # even spacing
    return [to_skin(p.x, p.y) for p in pts]


def inset_wedge(inset, r):
    """The slice's wedge with both seam planes pushed `inset` mm inside it at
    the radius r a window sits at. A window cut that reaches the slice's own
    side face is cut flush with it, and the kernel leaves a sliver there.
    Belt and braces after clip_window: r is the nearest the cutter gets to the
    axis, the worst case along it."""
    d = math.asin(max(-1.0, min(1.0, inset / r)))
    return (column(0).rotate((0, 0, 0), (0, 0, 1), d)
            .intersect(column(0).rotate((0, 0, 0), (0, 0, 1), -d)))


def min_radius(shape):
    """The closest a shape's bounding box comes to the Z axis."""
    bb = shape.BoundingBox()
    return max(1.0, min(math.hypot(x, y) for x in (bb.xmin, bb.xmax)
                        for y in (bb.ymin, bb.ymax)))


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

    def oval_pts(k, ring):
        """An oval window, clipped like every other window: MIN_WEB inside the
        skin band, inside the seam planes and away from its neighbours. It is
        already RIB/2 off the ribs and the seams by construction, so this only
        bites where a cell is laid out too far out on the skin."""
        from shapely.geometry import Polygon
        psi = (rows[k] + rows[k + 1]) / 2
        to_uv, to_skin, sgn = skin_frame(psi, 0.0)
        g = clip_window(Polygon([to_uv(p) for p, _ in ring]), psi, 0.0, to_uv, to_skin, sgn, tip=0.0)
        if g is None:
            return None
        ring = list(g.exterior.coords)[:-1]
        per = g.exterior.length
        pts = [g.exterior.interpolate(per * i / 96) for i in range(96)]   # even spacing, as the oval's own
        return [to_skin(p.x, p.y) for p in pts]

    cut = []
    for k in ovals:                               # the ovals, clipped first, like the junctions
        for o in ovals[k]:
            pts = oval_pts(k, o)
            if pts is not None:
                c_ = skin_cutter(pts)
                if c_ is not None:
                    cut.append(c_)
    for j, psi in enumerate(rows):                  # junctions on every rib
        near = ovals.get(j - 1, []) + ovals.get(j, [])
        keep = 0 if 0 < j < nrows else (1 if j == 0 else -1)
        # cut lines, and (in pieces builds, whose big junctions would otherwise cross
        # it) the equator rib that carries the thruster and servo collars
        on_cut = PIECES and (any(abs(psi - c_) < 1e-9 for c_ in cut_ribs().values()) or psi == 0.0)
        spots = [(0.0, near), (-HALF, near + turn(near, -2 * HALF)), (HALF, near + turn(near, 2 * HALF))]
        for th, around in spots:
            # on a cut line a full rib stays whole: the junction splits either side of it
            for side_ in ((1, -1) if on_cut else (keep,)):
                pts = junction(psi, math.radians(th), around, side_)
                if pts is None:
                    continue
                c_ = skin_cutter(pts)
                if c_ is None:
                    continue
                # a junction on a seam stops MIN_WEB inside this slice, so the cut
                # never lies in the slice's own side face; each slice keeps a
                # continuous edge strip there and the two strips glue into one rib
                cut.append(c_ if th == 0.0 else c_.intersect(
                    inset_wedge(RIB / 2 + MIN_WEB, min_radius(c_))))
    keep = outlet_keepout()
    air = duct_air_keepout()
    crest = crest_keepout()
    out = []
    for c in cut:
        if air is not None:
            # and one that only grazes the air keeps MIN_WEB of the duct wall
            v0 = c.Volume()
            try:
                clear = c.cut(air)
            except ValueError:
                continue
            if clear.Volume() < 0.35 * v0:
                continue
            c = clear
        if crest is not None:
            # no cutter may reach the solid crest band along a duct at all (clip_window
            # already stopped it MIN_WEB clear of the band's edge; this is the looser guard)
            try:
                c = c.cut(crest)
            except ValueError:
                continue
            if c.Volume() < 1.0:
                continue
        if keep is None:
            out.append(c)
            continue
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
    parts = [stem.rotate((0, 0, 0), (0, 0, 1), a_) for a_ in duct_seams()]
    if has_servo():
        parts.append(servo.rotate((0, 0, 0), (0, 0, 1), -HALF))
    if not parts:
        return None
    keep = parts[0]
    for p_ in parts[1:]:
        keep = keep.fuse(p_)
    return keep


def joint_parts():
    """Bosses (added), holes (cut) and pegs (added) on both seams, plus the
    sleeve the bulb-groove hole is set in.

    A joint whose hole sits in a groove, where one wall's face runs past the
    next, gets a sleeve (BOSS_D - 2*AIR_KEEP across) from that wall's face out
    past the hole's far side: the hole then has AIR_KEEP of wall to the air path
    on the air side and HOLE_D/2 of boss around it everywhere else. Without it a
    Ø3.3 hole punched into a groove would open the air path to the seam gap.
    """
    ph, pp = math.radians(-HALF), math.radians(HALF)
    bosses, holes, pegs, sleeves = [], [], [], []
    def in_duct(r, z):
        """Where a seam carries a duct, a joint inside the duct's run would sit
        in its bore; the seam is glued along both duct halves there instead."""
        return PIECES and z < DUCT_BULB / 2 + BOSS_D and r > DUCT_MOUTH_R - 5
    seams = duct_seams()
    for j in joints():
        r, z = j["r"], j["z"]
        p0 = cq.Vector(r * math.cos(ph), r * math.sin(ph), z)   # hole seam
        p1 = cq.Vector(r * math.cos(pp), r * math.sin(pp), z)   # peg seam
        th = cq.Vector(-math.sin(ph), math.cos(ph), 0)
        tp = cq.Vector(-math.sin(pp), math.cos(pp), 0)
        if not (-HALF in seams and in_duct(r, z)):
            bosses.append(cq.Solid.makeCylinder(BOSS_D / 2, BOSS_L, p0, th))
            hole = cq.Solid.makeCylinder(HOLE_D / 2, HOLE_L, p0 - th * 0.01, th)
            mouth = cq.Solid.makeCone(HOLE_D / 2 + CHAMFER + 0.01, HOLE_D / 2, CHAMFER + 0.01,
                                      p0 - th * 0.01, th)
            holes.append(hole.fuse(mouth))
        if HALF in seams and in_duct(r, z):
            continue
        bosses.append(cq.Solid.makeCylinder(BOSS_D / 2, BOSS_L, p1, -tp))
        peg = cq.Solid.makeCylinder(PEG_D / 2, PEG_L + 0.5, p1 - tp * 0.5, tp)
        tip = [e for e in peg.Edges()
               if e.geomType() == "CIRCLE" and (e.Center() - p1).dot(tp) > PEG_L - 0.1]
        pegs.append(peg.chamfer(CHAMFER, None, tip))
        if j["sleeve"]:
            # the sleeve the hole is set in: a rod from the air-side face of the
            # material the hole stands in, out past the hole's far side, so the hole
            # keeps AIR_KEEP of wall to the air path and HOLE_D/2 of material around
            # it. f086 started it at DUCT_BORE / 2 + DUCT_W - the OUTER wall's face -
            # which left the Ø3.3 hole punched clean through the T-thick wall it sat
            # in (the air path open to the seam gap) and stood the rod in the duct's
            # outer wall, 2.2 mm inside the bore: the bump rhY circled on the duct.
            s_at, s_near, s_far = j["sleeve"]
            c, n = duct_at(s_at)
            side = 1.0 if s_near > 0 else -1.0        # which side of the centreline
            sleeve = cq.Solid.makeCylinder(BOSS_D / 2 - 2 * AIR_KEEP, s_far,
                                           c + n * s_near, n * side)
            for a_ in duct_seams():
                sleeves.append(sleeve.rotate((0, 0, 0), (0, 0, 1), a_))
    return bosses, holes, pegs, sleeves


def duct_path():
    """Duct centreline in the seam plane (x = radius, y = 0), mouth to end.

    The centreline sits T + DUCT_BORE / 2 - SKIN_BITE under the outer skin, so the
    bore's outer surface is SKIN_BITE inside the skin band: the skin IS the duct's
    outer wall (rhY f087 item 1), one wall of T, and the duct adds no wall there.
    """
    depth = T + DUCT_BORE / 2 - SKIN_BITE
    p0 = math.asin(DUCT_Z_IN / B)
    p1 = math.asin(OUT_Z / B)
    pts = [skin_point(p0 + (p1 - p0) * i / 16, depth) for i in range(17)]
    return [cq.Vector(x, 0, z) for x, z in pts]


def duct_bulb_centre():
    """The duct bulb's centre, in the seam plane: set in from the tube's end by
    DUCT_BULB/2 - DUCT_BORE/2 so the bulb's dome stays inside the skin."""
    p1 = math.asin(OUT_Z / B)
    n_end = cq.Vector(B * math.cos(p1), 0, A * math.sin(p1)).normalized()
    return duct_path()[-1] - n_end * (DUCT_BULB / 2 - DUCT_BORE / 2)


def circle_profile(c, r, n=48):
    """A closed (r, z) polygon: the circle of radius r about the point c, in the
    seam plane (the bulb's bore is a sphere, and this is its section there)."""
    return [(c.x + r * math.cos(2 * math.pi * i / n),
             c.z + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


def duct_envelope(off, extra=3.0, bulb=None):
    """The duct's swept envelope at `off` mm from its centreline (duct_path),
    plus the bulb's dome at the same offset when `bulb` names it.

    off = DUCT_BORE/2 is the air path itself, DUCT_BORE/2 + DUCT_W the wall's outside
    face; anything larger is a keep-clear volume for the cuts that must not breach the
    air (the lattice). Built one way every time, so a keep-clear cannot drift from the
    part it protects.
    """
    pts = duct_path()
    spline = cq.Edge.makeSpline(pts)
    t0 = (pts[1] - pts[0]).normalized()
    start = pts[0] - t0 * extra
    prof = cq.Wire.makeCircle(off, start, t0)
    spine = ([cq.Edge.makeLine(start, pts[0]), spline] if extra else [spline])
    body = cq.Solid.sweep(prof, [], cq.Wire.assembleEdges(spine), True, False)
    body = body.fuse(cq.Solid.makeSphere(off, pts[-1],
                                         angleDegrees1=-90, angleDegrees2=90))
    if bulb:
        body = body.fuse(cq.Solid.makeSphere(bulb, duct_bulb_centre(),
                                             angleDegrees1=-90, angleDegrees2=90))
    return body


def duct_solids():
    """(walls, bore) of one full duct, seam plane = XZ, in the outlet frame.

    The walls exist only where the air is not already against the skin: the outer
    boundary of the walls solid is DUCT_BORE / 2 + DUCT_W - SKIN_BITE - SKIN_BURY from
    the centreline, i.e. SKIN_BURY under the outer skin, so it is buried in the band
    and adds no material on the duct's outer side - the skin is that wall. The bore
    is DUCT_BORE / 2 from the centreline, which lands SKIN_BITE inside the band, so
    the wall on the duct's outer side measures T - SKIN_BITE = 0.84 mm all along it.
    """
    # the end swells into a bulb (bore DUCT_BULB) so the wide stem and its
    # flange fit; the bulb's centre moves inward so it stays inside the skin
    inside = wedge_edges(arc(A, B, -math.pi / 2, math.pi / 2), half=90)
    outer = duct_envelope(DUCT_BORE / 2 + DUCT_W - SKIN_BITE - SKIN_BURY, extra=8.0,
                          bulb=DUCT_BULB / 2 + DUCT_W - SKIN_BITE - SKIN_BURY)
    bore = duct_envelope(DUCT_BORE / 2, extra=3.0, bulb=DUCT_BULB / 2)
    # stem bearing boss behind the hole, filled up to the skin
    x_s = hull_r(OUT_Z)
    boss = cq.Solid.makeCylinder(BOSS_R, BOSS_LEN + 6, cq.Vector(x_s - BOSS_LEN, 0, OUT_Z),
                                 cq.Vector(1, 0, 0))
    walls = outer.fuse(boss.intersect(inside))
    # nothing of the duct inside the housing: its tilted start would leave a lip
    # under the ceiling at the mouth; the housing's outer wall closes round it.
    # Trim to T + 0.2 so the duct's wall ends inside the housing wall's own T
    # band: the two walls fuse, and neither is left thinner or thicker than T.
    walls = walls.cut(housing_space(T))
    return walls, bore


_CREST = None


def crest_psi_range():
    """The ellipse angles the crest band runs between: from the lattice band's lowest rib
    (the duct's mouth is below it, inside the fan housing) to DUCT_BULB / 2 + 1.5 past the
    equator, where the duct's bulb ends and the stem hole's rim is. The band stops with the
    duct: above it the lattice runs to the bellmouth as before. It has to cover the bulb's
    dome, which is the widest part of the air path and now ends at the skin itself."""
    lo = lattice_band()[0]
    hi = max(0.0, math.asin(min(1.0, (DUCT_BULB / 2 + 1.5) / B)))
    return lo, hi


def crest_keepout():
    """The crest band as a solid: the skin CREST_BAND mm either side of each seam that carries
    a duct, over the duct's whole run (crest_psi_range). A slab about the seam plane, not a
    wedge about the axis - the duct's crest line IS the seam plane, and u = (azimuth - theta) *
    x0, the measure clip_window uses, is the perpendicular distance from that plane.

    windows() cuts every cutter with this as belt and braces after clip_window's uv clip, and
    strictly looser: CREST_BAND here against CREST_BAND + MIN_WEB there. When the two seam
    clips were at the SAME distance (f085) the cutter had two coincident walls and the boolean
    left 0.002-0.04 mm plates behind, so the guard must never bite where the uv clip has
    already done the job."""
    global _CREST
    if _CREST is None:
        lo, hi = crest_psi_range()
        reach = math.hypot(A, B) + 20.0
        # the band in the outlet frame (x radial, y out of the seam plane, z up), then
        # rotated onto every seam that carries a duct, as at_seams() does
        psi_wedge = wedge([(0.0, lo), (reach, lo), (reach, hi), (0.0, hi)], half=HALF + 2)
        slab = cq.Solid.makeBox(reach, 2 * CREST_BAND, 2 * B + 40,
                                cq.Vector(0.0, -CREST_BAND, -B - 20))
        band0 = slab.intersect(psi_wedge)
        out = None
        for a_ in duct_seams():
            b = band0.rotate((0, 0, 0), (0, 0, 1), a_)
            out = b if out is None else out.fuse(b)
        _CREST = out
    return _CREST


def duct_air_keepout():
    """The duct's air path grown MIN_WEB, on every seam that carries a duct.

    No lattice cut may come within MIN_WEB of the air: the duct's own T wall is what
    keeps it airtight (DESIGN-CONSTRAINTS), and a cut that nibbles into that wall leaves
    a fin of it under the nozzle. windows() cuts every cutter with this.
    """
    body = duct_envelope(DUCT_BORE / 2 + MIN_WEB, extra=3.0, bulb=DUCT_BULB / 2 + MIN_WEB)
    return at_seams(body)


def stem_and_servo_holes():
    """Stem hole on the seam; servo spline hole SERVO_T along +tangent (outlet frame).

    The stem hole is a cylinder about the radial line that flares into a cone over the
    skin band - see STEM_FLARE. The flare is what makes the hole's rim printable: bored
    straight, the hole's wall grazes the skin's normal at 7 deg and leaves a 0.19-0.38 mm
    wall between the hole's air and the outside all round the rim.
    """
    ax = cq.Vector(1, 0, 0)
    x0 = hull_r(OUT_Z) - BOSS_LEN - 2.0             # stop inside the bore: don't pierce its back wall
    stem = cq.Solid.makeCylinder(STEM_HOLE / 2, 30, cq.Vector(x0, 0, OUT_Z), ax)
    x_in = hull_r(OUT_Z) - 3.0                      # inside the skin band's inner face at the rim
    x_out = hull_r(OUT_Z) + 1.5                     # past the skin's outer face at the rim
    r_out = STEM_HOLE / 2 + (x_out - x_in) * math.tan(math.radians(STEM_FLARE + 1.5))
    stem = stem.fuse(cq.Solid.makeCone(STEM_HOLE / 2, r_out, x_out - x_in,
                                       cq.Vector(x_in, 0, OUT_Z), ax))
    servo = cq.Solid.makeCylinder(SERVO_HOLE / 2, 30, cq.Vector(A - 17.765, SERVO_T, OUT_Z), ax)
    return stem, servo


def duct_seams():
    """Angles of the seams that carry a duct and thruster on this slice."""
    if not FOUR:
        return (HALF, -HALF)
    return {"L": (HALF,), "R": (-HALF,), "P": ()}[SIDE]


def slice_sides():
    """The slice type at each position round the ring, starting from slice 0:
    a thruster sits on every (N/4)th seam, between an L and an R slice."""
    if not FOUR:
        return ["L"] * N
    per = N // 4
    return (["L", "R"] + ["P"] * (per - 2)) * 4


def has_servo():
    return not FOUR or SIDE == "R"


def cut_joints():
    """(point, axis) of a peg across each cut, on the slice's centre line, in
    a boss under the skin. Axis points from the peg side to the hole side."""
    edge = T + HOLE_D / 2 + 1.0
    out = []
    for key, psi in cut_ribs().items():
        r, z = skin_point(psi, edge)
        if key.startswith("z"):                     # horizontal cut: peg on the middle band
            out.append((key, cq.Vector(r, 0, z), cq.Vector(0, 0, 1 if key == "z_hi" else -1)))
        else:                                       # radial cut: peg on the outer piece, pointing in
            out.append((key, cq.Vector(r, 0, z), cq.Vector(-1, 0, 0)))
    return out


def pieces(body):
    """Cut a slice into printable pieces along its cut ribs: a middle band
    round the equator (the thruster), and the top and bottom bands, each cut
    again at CUT_R into an inner and an outer piece. A peg crosses every cut."""
    c = cut_ribs()
    zl, zh = B * math.sin(c["z_lo"]), B * math.sin(c["z_hi"])
    rc = A * math.cos(c["r_hi"])
    big = 4 * A
    above = lambda z: cq.Solid.makeBox(big, big, big, cq.Vector(-big / 2, -big / 2, z))
    below = lambda z: cq.Solid.makeBox(big, big, big, cq.Vector(-big / 2, -big / 2, z - big))
    inner = cq.Solid.makeCylinder(rc, 2 * big, cq.Vector(0, 0, -big))
    top, bot = body.intersect(above(zh)), body.intersect(below(zl))
    out = {"middle": body.intersect(above(zl)).intersect(below(zh)),
           "top_outer": top.cut(inner), "top_inner": top.intersect(inner),
           "bottom_outer": bot.cut(inner), "bottom_inner": bot.intersect(inner)}
    peg_on = {"z_hi": "middle", "z_lo": "middle", "r_hi": "top_outer", "r_lo": "bottom_outer"}
    hole_in = {"z_hi": "top_outer", "z_lo": "bottom_outer", "r_hi": "top_inner", "r_lo": "bottom_inner"}
    for key, p, ax in cut_joints():
        face = p + ax * 0.0
        if key.startswith("z"):
            face = cq.Vector(p.x, p.y, zh if key == "z_hi" else zl)
        else:
            face = cq.Vector(rc, p.y, p.z)
        peg = cq.Solid.makeCylinder(PEG_D / 2, PEG_L + 0.5, face - ax * 0.5, ax)
        hole = cq.Solid.makeCylinder(HOLE_D / 2, HOLE_L, face - ax * 0.01, ax)
        out[peg_on[key]] = out[peg_on[key]].fuse(peg)
        out[hole_in[key]] = out[hole_in[key]].cut(hole)
    return {k: v.clean() for k, v in out.items()}


def print_pose(shape):
    """Lay a slice (or piece) on its -HALF seam, the way it prints."""
    return shape.rotate((0, 0, 0), (0, 0, 1), HALF).rotate((0, 0, 0), (1, 0, 0), 90)


def at_seams(shape):
    """An outlet-frame shape on this slice's duct seams, clipped to the slice."""
    wedge_all = wedge_edges(arc(A + 50, B + 50, -math.pi / 2, math.pi / 2))
    seams = duct_seams()
    if not seams:
        return None
    out = shape.rotate((0, 0, 0), (0, 0, 1), seams[0])
    for a_ in seams[1:]:
        out = out.fuse(shape.rotate((0, 0, 0), (0, 0, 1), a_))
    return out.intersect(wedge_all)


def slice_name(side=None):
    hand = {"L": "left", "R": "right", "P": "plain"}[side or SIDE]
    return ("airship pie slice 1026" + ("" if not FOUR else f" 4T {hand}")
            + ("" if N == 8 else f" {N}s") + ("" if LARGE == FOUR else (" large" if LARGE else " small"))
            + ("" if SCALE == 1 else f" x{SCALE:g}"))


# ---- the joint map the checker reads -------------------------------------
def housing_wall_profile():
    """(r, z) outline of the housing wall's own band: the shroud curve and the
    same curve offset T to its dry side - plenum_ceiling()'s outline. The housing
    is a body of revolution, so revolving this gives the wall it really builds."""
    pts = shroud_curve()
    off = []
    for i, (r, z) in enumerate(pts):
        a_, b_ = pts[max(i - 1, 0)], pts[min(i + 1, len(pts) - 1)]
        dr, dz = b_[0] - a_[0], b_[1] - a_[1]
        L = math.hypot(dr, dz)
        off.append((r - dz / L * T, z + dr / L * T))
    return pts + off[::-1]


def plenum_air_profile():
    """(r, z) of the air inside the fan housing, from the shaft down the keel -
    housing_space()'s outline."""
    pts = [(r, z) for r, z in shroud_curve()[1:]
           if r >= EYE_R + SHROUD_RC - 1e-9 and z <= FLOOR_Z + 1e-9]
    return [(0, FLOOR_Z)] + pts + [(pts[-1][0], -B - 1), (0, -B - 1)]


def impeller_sweep_profile():
    """(r, z) of the volume the impeller's blades sweep: from the axis out to
    the blade tips (IMP_TIP_R), from the backplate's underside up to SHROUD_GAP
    under the housing's shroud. Blade height 12.5 mm and the 0.8 mm backplate are
    ../Propulsion/propulsion.py:48 and :64; the top follows the shroud, as
    propulsion.py:250-255 makes the blade tops do."""
    BLADE = 12.5 + 0.8
    top = [(r, z - SHROUD_GAP) for r, z in shroud_curve()
           if EYE_R <= r <= IMP_TIP_R + 1e-9 and z <= FLOOR_Z + 1e-9]
    bottom = FLOOR_Z - SHROUD_GAP - BLADE
    return [(0, bottom), (IMP_TIP_R, bottom)] + top[::-1] + [(0, top[0][1])]


def duct_bore_profile(off=DUCT_BORE / 2):
    """(r, z) polygon of the duct's tube at `off` from its centreline, in the
    seam plane: off = DUCT_BORE/2 is the air path, DUCT_BORE/2 + DUCT_W the
    wall's outside face. The duct is NOT a body of revolution, so the checker
    measures this one in the seam plane instead of revolving it - which is the
    plane the joints live in, and it only ever under-states the distance."""
    pts = duct_path()
    nrm = []
    for i in range(len(pts)):
        d0 = pts[i] - pts[i - 1] if i else pts[1] - pts[0]
        d1 = pts[i + 1] - pts[i] if i < len(pts) - 1 else pts[-1] - pts[-2]
        tg = (d0 + d1).normalized()
        n = cq.Vector(tg.z, 0, -tg.x)
        if n.dot(pts[i]) < 0:
            n = n * -1
        nrm.append(n)
    a = [(p + n * off) for p, n in zip(pts, nrm)]
    b = [(p - n * off) for p, n in zip(pts, nrm)]
    return [(p.x, p.z) for p in a] + [(p.x, p.z) for p in reversed(b)]


def joint_map():
    """The joint map this build writes next to the STEP: <slice>.joints.json.

    Analysis/check_outputs.py --joints reads it and measures the two rules the
    design owner set: every boss, peg and hole keeps JOINT_CLEAR from the fan
    housing, the plenum air and the impeller's swept volume, and every hole keeps
    AIR_KEEP of wall between itself and the air path. The keep-clear volumes come
    from the same code that builds the part, so they cannot drift from it.
    """
    return {
        "variant": VARIANT + (" 4T " + SIDE if FOUR else ""),
        "scale": SCALE,
        "nominal_wall": T,
        "joint_clear": JOINT_CLEAR,
        "air_keep": AIR_KEEP,
        "seam_degrees": [-HALF, HALF],
        "joints": [dict(name=j["name"], r=round(j["r"], 3), z=round(j["z"], 3),
                        boss_d=BOSS_D, boss_l=BOSS_L, peg_d=PEG_D, peg_l=PEG_L,
                        hole_d=HOLE_D, hole_l=HOLE_L,
                        fused_to=j["walls"], why=j["why"]) for j in joints()],
        "keep_clear": [
            {"name": "fan housing wall", "kind": "joint",
             "profile": housing_wall_profile()},
            {"name": "plenum air", "kind": "joint",
             "profile": plenum_air_profile()},
            {"name": "impeller swept volume", "kind": "joint",
             "profile": impeller_sweep_profile()},
            {"name": "shaft bore", "kind": "air",
             "profile": [(0, -B - 1), (SHAFT_R, -B - 1), (SHAFT_R, B + 1), (0, B + 1)]},
            {"name": "duct bore", "kind": "air2d",
             "profile": duct_bore_profile()},
            {"name": "bulb bore", "kind": "air2d",
             "profile": circle_profile(duct_bulb_centre(), DUCT_BULB / 2)},
        ],
    }


def build():
    envelope = wedge_edges(arc(A, B, -math.pi / 2, math.pi / 2)).cut(
        wedge([(0, -B), (SHAFT_R, -B), (SHAFT_R, B), (0, B)]))  # keep the shaft bore clear
    walls, bore = duct_solids()
    stem_hole, servo_hole = stem_and_servo_holes()
    bosses, holes, pegs, sleeves = joint_parts()

    body = frame()
    tools = windows()
    for w in tools:                        # one cut at a time: a compound of cutters
        v = body.Volume()                  # whose boxes overlap would let the kernel
        body = body.cut(w)                 # cut one against another and leave slivers
        if v - body.Volume() < 0.5:        # a window cut that does nothing means
            c = w.Center()                # the tool never reached the skin: a lattice
            raise ValueError(f"window cut had no effect at {c.x:.1f}, {c.y:.1f}, "
                             f"{c.z:.1f} mm - the build stops here rather than "
                             f"shipping a slice with a window missing from it")
    if PIECES:                                      # bosses for the pegs across the cuts
        for _, p, ax in cut_joints():
            bosses.append(cq.Solid.makeCylinder(BOSS_D / 2, 2 * BOSS_L, p - ax * BOSS_L, ax))
    body = body.fuse(cq.Compound.makeCompound(bosses + sleeves).intersect(envelope))
    if duct_seams():
        try:
            body = body.fuse(at_seams(walls))
        except ValueError:                  # the kernel can fail on near-touching faces:
            body = body.fuse(at_seams(walls), tol=1e-4)   # retry as a fuzzy boolean
        body = body.cut(at_seams(bore))
        body = body.cut(at_seams(stem_hole))
    if has_servo():
        body = body.cut(servo_hole.rotate((0, 0, 0), (0, 0, 1), -HALF))  # this slice's servo
    body = body.cut(cq.Compound.makeCompound(holes))
    body = body.fuse(cq.Compound.makeCompound(pegs))
    body = body.cut(hatch_hole()).clean()
    # keep only real solids: a boolean can leave a degenerate shell in the
    # compound (volume 0, a few faces), and it inflates every number read off
    # the shape, so a slice must be reported by the solids it actually has
    solids = [so for so in body.Solids() if so.Volume() > 1e-3]
    if not solids:
        raise ValueError(f"the slice came out with no solid in it: {len(body.Faces())} faces, "
                         f"volume {body.Volume():.1f} mm3")
    if len(solids) > 1:
        print(f"note: {len(body.Solids()) - len(solids)} degenerate shell(s) dropped, "
              f"{len(solids)} solids kept")
    body = solids[0] if len(solids) == 1 else cq.Compound.makeCompound(solids)
    return body


if __name__ == "__main__":
    s = build()
    print(f"volume {s.Volume() / 1000:.2f} cm3, faces {len(s.Faces())}, "
          f"solids {len(s.Solids())}, valid {s.isValid()}")
    name = slice_name()
    cq.exporters.export(s, os.path.join(HERE, name + ".step"))
    with open(os.path.join(HERE, name + ".joints.json"), "w") as fh:
        json.dump(joint_map(), fh, indent=1)
    print(f"{name + '.joints.json':52} {len(joint_map()['joints'])} joints, "
          f"{len(joint_map()['keep_clear'])} keep-clear volumes")
    if PIECES:                                      # printable pieces, and the intake tubes
        d = os.path.join(HERE, "pieces", slice_name())
        os.makedirs(d, exist_ok=True)
        for k, v in pieces(s).items():
            bb = print_pose(v).BoundingBox()
            print(f"  {k:13} {v.Volume() / 1000:6.2f} cm3  solids {len(v.Solids())}  valid {v.isValid()}  "
                  f"print {bb.xlen:.0f} x {bb.ylen:.0f} x {bb.zlen:.0f} mm")
            cq.exporters.export(v, os.path.join(d, k + ".step"))
        for i, t_ in enumerate(tube_segments()):
            cq.exporters.export(t_, os.path.join(d, f"intake_tube_{i + 1}.step"))
            bb = t_.BoundingBox()
            print(f"  intake tube {i + 1}  {t_.Volume() / 1000:6.2f} cm3  {bb.zlen:.0f} mm tall")
