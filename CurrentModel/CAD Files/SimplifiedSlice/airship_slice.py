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
from OCP.BRepBuilderAPI import (BRepBuilderAPI_MakeFace,   # noqa: E402
                                BRepBuilderAPI_MakeWire)

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
TAG = os.environ.get("OAS_TAG", "")   # names this build's files instead of the x<SCALE> suffix
                                        # (f118 item 5: OAS_TAG=CR10Pro writes "airship pie slice
                                        #  1026 CR10Pro.step" and PieSlice1026-v0.2.1-8T-CR10Pro.stl)

# ---- parameters (mm) -------------------------------------------------------
A, B = 207.765 * SCALE, 104.0 * SCALE   # hull outer semi-axes (radius, half-height)
T = 0.86                   # wall: exactly 2 perimeters of 0.45 mm at 0.2 mm layers
HALF = 180.0 / N           # half-angle of one slice, degrees

FLOOR_Z = -B + (43.0 if LARGE else 32.7)   # fan-housing ceiling (the shroud over the blade tips), underside;
                                     # 4T: higher, so the Ø34 duct mouths fit under it
INTAKE_R = 12.0            # the skin arc rolls into the shaft over this radius (bellmouth)

RIB = float(os.environ.get("OAS_RIB", "2.0"))   # lattice web width (a seam rib is RIB/2 on each slice);
                                                # 1.2 = lightest printable (3 lines), for builds where stiffness doesn't matter
MIN_WEB = 0.0              # rhY f118 item 4: the lattice runs right out to the edges. This
                         #   margin used to keep every window this far inside the skin band, inside
                         #   the slice's seam planes, away from the duct's air and from its
                         #   neighbouring windows - a solid skin margin all round the lattice. It is
                         #   GONE. What it was really protecting (a cut boundary landing on a face
                         #   that is already there -> the 0.009-0.05 mm sliver walls issue #36 counts)
                         #   is now protected the other way round: a cell an edge or a keep-out cuts
                         #   is not cut at all (clip_window returns None for it, windows() drops a
                         #   cutter a keep-out solid has nibbled), so only the FULL cells are open
                         #   windows and the partial cells along an edge stay filled - which is also
                         #   what rhY asks for "for strength".
CREST_EDGE_CLEAR = 0.5     # mm the crest band's cut boundaries stand INSIDE its own half-width,
                         # so no cut boundary is within 0.3 mm of the lattice's outer edge (column_bounds
                         # at CREST_BAND) or of each other: clip_window's uv clip runs at CREST_BAND +
                         # MIN_WEB - CREST_EDGE_CLEAR, crest_keepout's slab at CREST_BAND - 0.5 -
                         # CREST_EDGE_CLEAR. Measured before (build/f148/margins.py): the oval's outer
                         # edge and the uv clip 0.005 mm apart at the equator row and 0.116 mm ON TOP of
                         # it at the keel rows -> the 0.025-0.044 mm sliver walls issue #36 counts.
                         # (Moving the lattice's edge outward instead was tried first and is wrong: it
                         # changes where the lattice stops, which grew a junction window at the keel rib
                         # that cuts nothing and tripped build()'s "window cut had no effect" guard at
                         # OAS_SCALE 1.41.)
SERVO_WALL = 1.0         # mm of skin band left round the servo-spline hole: its outlet
                         # keep-out ring is SERVO_HOLE / 2 + SERVO_WALL. It used to be
                         # SERVO_HOLE / 2 + 3.5 = 7.5 mm, and that extra 2.5 mm of solid skin is
                         # what left a 1476 mm2 filled patch in the cell below the equator
                         # (rhY f150 item 2, measured in build/f150/probe1.log). 1.0 mm still
                         # keeps the wall between the Ø8 spline hole and a lattice window over the
                         # 0.40 mm nozzle (Analysis/check_outputs.py NOZZLE) with room to spare.
BRACE_EDGE_CLEAR = 0.5   # mm the lattice's windows stand OUTSIDE the servo brace's own face and
                         # ends (the same idiom as CREST_EDGE_CLEAR). The brace is RIB wide on the
                         # equator; a window cut that landed exactly on its face would be a cut
                         # boundary on a face that is already there - the sliver issue #36 counts -
                         # so windows stop at RIB / 2 + BRACE_EDGE_CLEAR from the equator and the
                         # brace's own faces stand BRACE_EDGE_CLEAR inside uncut skin.
BRACE_OUT = 0.3          # mm under the outer skin the servo brace starts at: buried in the skin
                         # band, never through the outer face (the hull stays a smooth ellipsoid).
MIN_OPEN_AREA = 20.0     # mm2 of skin a clipped window must keep to be cut at all: below this
                         # what is left is a crescent, not a window (clip_window's f150 clips).
NOZZLE = 0.40            # mm, the same nozzle Analysis/check_outputs.py measures the wall map
                         # against: no cut feature this side of it is printable, so a clip that
                         # leaves a window narrower than this is not cut (the cell stays filled).
BRACE_IN = 2 * T         # mm under the outer skin the brace reaches: the band (T) plus a rib of
                         # the band's own DEPTH standing inboard of its inner face, which is what
                         # strengthens the equator line - a rib that only filled the band would add
                         # no material at all, since the band is already solid under it.
POLY_CLOSE = 0.2           # every window polygon is closed by this radius (erode, then dilate
                         # back): a notch or a spike in the cut boundary narrower than 2*POLY_CLOSE
                         # is removed before the cut is ever made. No longer tied to MIN_WEB (now
                         # 0): it is not a margin - it never moves the boundary outward, it only
                         # rounds tips and closes sliver notches, and a tongue of skin that thin
                         # standing in the hole is what the 0.011-0.3 mm walls issue #36 counts.
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
CUT_OUT = T / 2 + 0.6      # how far ABOVE the MID-SURFACE a window cutter starts, so its
                         # top cap sits 0.6 mm clear of the OUTER face (the old 0.5 mm was
                         # measured from the outer face and put the cap only 0.07 mm above
                         # it). The cap is faceted and a faceted cap sags: a cap that dips
                         # through the outer face grazes it, and the boolean leaves a sliver
                         # face along the window's rim - 908 of them in the previous build,
                         # and the rim ones are what the thin-facet scan reads as a 0.005 mm
                         # wall.
CUT_IN = T + SKIN_MARGIN   # the depth of a window cutter's floor: T + SKIN_MARGIN under the
                         # outer face, so the lattice leaves the full T band everywhere it
                         # cuts. The duct's air ends AT the band's inner face (SKIN_BITE inside
                         # it), and no lattice window is cut within CREST_BAND of a duct crest,
                         # so a cutter's floor never reaches the air path.
CUT_MESH = 3.0             # the window's area is tiled into cells this wide so the cutter's
                         # two caps FOLLOW the curved skin instead of spanning it in straight
                         # chords. A flat chord across a window sags chord^2 / (8 * R) under
                         # the surface, and the skin's smallest curvature radius is B^2 / A =
                         # 52 mm at the equator: a 38 mm chord sags 3.5 mm, seven times the
                         # old CUT_OUT, so a cutter whose caps span the whole window never
                         # reaches the skin over the middle of it (measured on the f087 8T
                         # slice: build/f117/probe2.log - 3.60 mm of cap sag, 16 loose plates
                         # left in the windows). At 3.0 mm cells the worst chord is the cell
                         # diagonal, 4.24 mm, and the sag is 0.043 mm: the cap stays 0.56 mm
                         # outside the outer face everywhere, and the floor stays 0.73 mm
                         # past the band's inner face.
RING_WELD = 1e-9           # ring points closer than this (mm) are welded into one. A
                         # box clip leaves pairs a few micrometres apart, and each pair
                         # makes a wall face that thin - a face with two coincident
                         # vertical edges, 0.0002 mm2, about 1600 of them in the 8T
                         # slice. Welding at 1e-3 was tried and is NOT safe: the two
                         # cells that share such a point do not always weld it the same
                         # way, the shell then has a hole, and the cutter at (136.0,
                         # -21.8, -76.8) refuses to build (build/f117/rebuild6.log).
                         # What does fix the grazing those thin faces cause is OUT_MESH
                         # below: the window's own outline, not the cell grid, sets where
                         # walls are.
OUT_MESH = 1.0             # the window's OWN outline is resampled to this spacing. Its
                         # vertices set the width of the window's wall faces, and clipping
                         # against the band's edge, a seam plane or a crest box leaves pairs
                         # of them a few hundredths of a mm apart: every such pair becomes a
                         # wall face that thin (1625 faces under 0.3 mm2 in the previous
                         # build, all of them wall faces 0.00-0.28 mm wide), and the checker's
                         # ray grazing along one of those reads as a 0.005 mm wall.
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
BOSS_INSET = T / 2         # how far inside a wall band the clip that keeps a boss out
                         #   of the shaft bore stops. A boss clipped exactly at the bore's
                         #   own face (r = SHAFT_R) gets a flat face coincident with the shaft
                         #   wall's inner face, and the fuse leaves a sliver there: the 0.03
                         #   and 0.30 mm readings at (33.0, 91.0) and (33.0, -64.2) in
                         #   build/f118/thin1.log, both at the new shaft-corner joints. Clipping
                         #   BOSS_INSET into the T band puts that face inside the material the
                         #   fuse is joining, so it disappears and the bore stays clear.
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
CREST_BAND = DUCT_BORE / 2   # half-width, mm along the skin, of the SOLID band that runs along
                         #   the crest of each duct: the skin over a duct carries no lattice window,
                         #   because with the skin as the duct's outer wall (rhY f087 item 1) a window
                         #   there would be a hole in the air path. It is the duct TUBE's own air half-
                         #   width now (was DUCT_BULB / 2 + MIN_WEB = 16.4): the wider part of the air
                         #   path is the bulb at the duct's end, and duct_air_keepout() drops the cells
                         #   it cuts, so the band is only as wide as the air actually is at each height
                         #   (rhY f118 item 4: solid skin only where it must be).
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
# the hole's own wall is tilted off radial by the skin's NORMAL at the rim,
# not by the ellipse angle of the rim. The skin's normal at ellipse angle psi
# makes an angle atan((A/B) tan psi) with the axis -- for psi = 7 deg that is
# 13.85 deg, not 7.02 deg. Tilt the wall by THAT, plus 1.5 deg of margin, or
# the hole eats into the 0.86 mm skin on the up-hull side of the rim.
STEM_RIM_PSI = math.asin(min(1.0, (STEM_HOLE / 2) / B))
STEM_FLARE = math.degrees(math.atan((A / B) * math.tan(STEM_RIM_PSI)))
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


def psi_of(p):
    """The ellipse angle of a point on the skin's MID line.

    The mid line is the skin offset inwards by T / 2, which is not an ellipse, so
    the plain atan2(z * A, rho * B) inverse is wrong by 0.26 mm anywhere and by 5 mm
    near the bellmouth. Undo the offset first, then take the angle.
    """
    rho, z = math.hypot(p.x, p.y), p.z
    ps = math.atan2(z * A, rho * B)
    for _ in range(3):
        nx, nz = B * math.cos(ps), A * math.sin(ps)
        L = math.hypot(nx, nz)
        ps = math.atan2((z + (T / 2) * nz / L) * A,
                        (rho + (T / 2) * nx / L) * B)
    return ps


def depth_under_skin(p):
    """How deep a point sits under the outer skin, measured along the skin's own
    normal there (negative = outside the hull). What the window-cutter probes use
    to say whether a cutter really covers the band."""
    th = math.atan2(p.y, p.x)
    rho = math.hypot(p.x, p.y)
    ps = psi_of(p)
    for _ in range(4):
        n = cq.Vector(B * math.cos(ps) * math.cos(th), B * math.cos(ps) * math.sin(th),
                      A * math.sin(ps)).normalized()
        q = cq.Vector(rho * math.cos(th), rho * math.sin(th), p.z) - n * (T / 2)
        ps = psi_of(q)
    p_mid, n = surface(ps, th)
    return T / 2 - (cq.Vector(rho * math.cos(th), rho * math.sin(th), p.z) - p_mid).dot(n)


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


def crest_psi_hi():
    """The ellipse angle the crest band ENDS at: DUCT_BULB / 2 + 1.5 past the equator,
    where the duct's bulb ends and the stem hole's rim is. Split out of crest_psi_range
    because skin_ribs() needs it to snap a rib onto it, and crest_psi_range's other end
    comes from lattice_band(), which comes from skin_ribs() (f148)."""
    return max(0.0, math.asin(min(1.0, (DUCT_BULB / 2 + 1.5) / B)))


def snap_rib_to_crest(ribs, row):
    """f148: move the rib nearest the crest band's top edge ONTO that edge (never add one).

    crest_half() is a STEP: CREST_BAND mm inside crest_psi_range, 0 above it, and oval_on_skin
    takes ONE bound per cell from the cell's MID psi. So a row that straddles crest_psi_range()[1]
    is 'in the band' by its middle and 'out of it' by its top: its oval's outer edge lands exactly
    on the band's clip edge (measured: 0.005 mm apart in the uv frame), and a cut boundary on a
    face that is already there is what left the 0.025-0.044 mm sliver walls and the self-intersecting
    shell issue #36 counts came from. With a rib ON the band's edge no cell straddles it, every
    cell is wholly in or wholly out, and crest_keepout()'s slab ends on a rib.

    If the move leaves a row shorter than half the nominal row height, that row is merged with
    its neighbour (the rib on the far side of the short row is dropped). The equator rib and the
    band's own end ribs never move: they carry the thrusters and define lattice_band(). If such a
    short row CANNOT be merged (its other rib is one of those), the rib is not moved at all:
    the cell that straddles the band's edge is then left filled by clip_window's partial-cell
    rule, which is safe the same way - measured at OAS_SCALE 1.41, moving the rib there left a
    17.7 mm row against a 51.3 mm nominal one and the build came out with a window cut that
    removed nothing.
    """
    hi = crest_psi_hi()
    if hi <= 0.0 or len(ribs) < 3:
        return ribs
    i = min((k for k in range(1, len(ribs) - 1) if ribs[k] != 0.0),
            key=lambda k: abs(ribs[k] - hi))
    if abs(ribs[i] - hi) < 1e-12:
        return ribs
    below, above = ribs[i - 1], ribs[i + 1]
    short_below = ellipse_arc(below, hi) < row / 2
    short_above = ellipse_arc(hi, above) < row / 2
    drop_below = short_below and i >= 2 and below != 0.0
    drop_above = short_above and i + 1 <= len(ribs) - 2
    if (short_below and not drop_below) or (short_above and not drop_above):
        return ribs
    out = list(ribs)
    out[i] = hi
    if drop_above:
        del out[i + 1]
    if drop_below:
        del out[i - 1]
    return out


def skin_ribs():
    """Ellipse angles of the skin's ring ribs, bottom to top. One sits exactly
    on the equator (z = 0), where the thrusters are. Every row is the same
    height along the skin, above and below the equator, so all the cells
    have the same proportions - except the row boundary f148 snaps onto the crest
    band's top edge (see snap_rib_to_crest), which makes the rows either side of it
    17.8 and 50.3 mm instead of 34.0."""
    ke = math.asin(keel_edge_z() / B)
    top = intake()[1] - (RIB / 2) / math.hypot(A * math.sin(intake()[1]), B * math.cos(intake()[1]))
    row = ellipse_arc(0.0, top) / ROWS_ABOVE_EQ
    if PIECES:                                      # ribs on every cut line, rows between them
        fixed = [ke] + sorted(cut_ribs().values()) + [0.0]
        fixed = sorted(set(fixed + [top]))
        out = []
        for p0, p1 in zip(fixed, fixed[1:]):
            out += equal_arcs(p0, p1, max(1, round(ellipse_arc(p0, p1) / row)))[:-1]
        return snap_rib_to_crest(out + [top], row)
    below = max(3, round(ellipse_arc(ke, 0.0) / row))
    return snap_rib_to_crest(equal_arcs(ke, 0.0, below)[:-1]
                             + equal_arcs(0.0, top, ROWS_ABOVE_EQ), row)


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


# f148 put the bulb joint at duct_at(S_BULB_GROOVE): a point a fixed fraction of
# the way along the duct, on the tube wall. Measured on the f148 print, that boss
# bit 2.05 mm into the tube wall and 0.00 mm into the bulb's dome wall - exactly
# tangent to it, so it stood in ONE wall, which is what rhY saw: "other peg not in
# the corner touching two sides". f149 finds the corners as surface intersections
# (bulb_inner_corner / bulb_outer_corner below); S_BULB_GROOVE is kept only as the
# f148 record.
S_BULB_GROOVE = 0.87         # f148: the groove where the duct wall meets the bulb
# The peg f087 put on the duct's CREST (the seam plane, the one wall of T the skin
# and the duct's outer wall have become) is still gone: measured, that wall spans
# only DUCT_BORE/2 = 12.00 .. 12.86 mm from the duct's centreline, so a Ø3.3 hole
# with AIR_KEEP of wall to the air cannot fit in it without standing material
# outside the outer skin.


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


# ---- the bulb's two corners (f149) ------------------------------------------------
# The duct's tube wall and the bulb's dome wall meet in the seam plane in TWO
# corners, and a bulb joint belongs IN one of them with its boss fused into BOTH
# walls - the two-wall rule. The corner is the intersection of the two wall FACES;
# nothing about it is a parameter along the duct. Points are (r, z) in the seam
# plane, the same frame duct_path() and the joint map use.

def duct_wall_r():
    """The tube wall's own face, mm from the centreline (duct_solids())."""
    return DUCT_BORE / 2 + DUCT_W - SKIN_BITE - SKIN_BURY


def bulb_wall_r():
    """The bulb dome wall's own face, mm from the bulb's centre (duct_solids())."""
    return DUCT_BULB / 2 + DUCT_W - SKIN_BITE - SKIN_BURY


def seam_off(p):
    """p's distance from the duct's centreline polyline, in the seam plane."""
    pts = duct_path()
    best = None
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        dx, dz = b.x - a.x, b.z - a.z
        L2 = dx * dx + dz * dz
        t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((p[0] - a.x) * dx + (p[1] - a.z) * dz) / L2))
        d = math.hypot(p[0] - (a.x + t * dx), p[1] - (a.z + t * dz))
        if best is None or d < best:
            best = d
    return best


def seam_air(p):
    """mm of wall between p and the duct's air path in the seam plane (0 inside
    it): the tube's bore and the bulb's bore, the two surfaces duct_solids() cuts."""
    C = duct_bulb_centre()
    return max(0.0, min(seam_off(p) - DUCT_BORE / 2,
                        math.hypot(p[0] - C.x, p[1] - C.z) - DUCT_BULB / 2))


def band_tube(p):
    """mm from p to the tube wall's own band, 0 inside it: the material between
    DUCT_BORE / 2 and duct_wall_r() from the centreline."""
    d, lo, hi = seam_off(p), DUCT_BORE / 2, duct_wall_r()
    return 0.0 if lo <= d <= hi else min(abs(d - lo), abs(d - hi))


def band_dome(p):
    """mm from p to the bulb dome wall's own band, 0 inside it."""
    C = duct_bulb_centre()
    rho, lo, hi = math.hypot(p[0] - C.x, p[1] - C.z), DUCT_BULB / 2, bulb_wall_r()
    return 0.0 if lo <= rho <= hi else min(abs(rho - lo), abs(rho - hi))


def band_skin(p):
    """mm from p to the hull skin's own band, 0 inside it: the duct's outer side,
    which IS the skin (rhY f087 item 1)."""
    u = hull_r(p[1]) - p[0]                          # depth under the outer face
    return 0.0 if u <= T else u - T


def stem_slot_wall(p):
    """mm of wall between p and the ØSTEM_HOLE stem slot at the outlet, its flare
    cone included - or a large number where there is no slot: the slot is a cylinder
    from hull_r(OUT_Z) - BOSS_LEN - 2 out through the skin (stem_and_servo_holes()),
    not a disc about the axis. build() cuts that slot AFTER the bosses are fused, so
    a joint hole inside it is no hole at all and its peg is left loose in the air -
    the f087 duct-top failure mode."""
    if p[0] < hull_r(OUT_Z) - BOSS_LEN - 2.0:
        return 1e9
    flare = math.tan(math.radians(STEM_FLARE + 1.5))
    return abs(p[1]) - (STEM_HOLE / 2
                        + max(0.0, p[0] - (hull_r(OUT_Z) - 3.0)) * flare)


def bulb_inner_corner():
    """The INNER corner, toward the hull's inside: the tube wall's face (offset
    duct_wall_r() from the centreline, on the dry side) crossing the dome wall's
    face (the bulb_wall_r() sphere about duct_bulb_centre()). Walk the tube face
    from the mouth and bisect the crossing."""
    rt, rb, C = duct_wall_r(), bulb_wall_r(), duct_bulb_centre()

    def f(s):
        c, n = duct_at(s)
        return ((c - n * rt) - C).Length - rb

    lo, hi, prev = 0.3, 0.315, f(0.3)
    while hi < 1.0:
        v = f(hi)
        if prev * v <= 0:
            break
        lo, hi, prev = hi, min(1.0, hi + 0.015), v
    for _ in range(50):
        mid = (lo + hi) / 2
        if f(lo) * f(mid) <= 0:
            hi = mid
        else:
            lo = mid
    c, n = duct_at((lo + hi) / 2)
    q = c - n * rt
    return q.x, q.z


def bulb_outer_corner():
    """The OUTER corner: the dome wall's face crossing the skin band's inner face
    - the duct's outer side, which is the hull skin. Walk the skin's inner face
    from the equator and bisect the crossing. It is on the far side of the equator
    from the mouth: the tube's own air swallows the dome wall where the duct comes
    up, so that is the side where both walls are material."""
    rb, C = bulb_wall_r(), duct_bulb_centre()

    def f(psi):
        q = skin_point(psi, T)
        return math.hypot(q[0] - C.x, q[1] - C.z) - rb

    lo, hi = 0.0, math.pi / 2
    for _ in range(60):
        mid = (lo + hi) / 2
        if f(lo) * f(mid) <= 0:
            hi = mid
        else:
            lo = mid
    return skin_point((lo + hi) / 2, T)


def bulb_boss_centre(apex, bands, reach):
    """The boss centre for the corner at apex: the point within reach of it that
    bites deepest into BOTH walls (maximize the shallower bite) while the ØHOLE_D
    hole it carries keeps AIR_KEEP of wall to the duct's air path and to the stem
    slot, and the boss stays RIM_KEEP under the hull's outer face. The corner
    itself is always in one or the other - that is what puts the boss as close to
    the corner as the rules allow, the same way AIR_KEEP and JOINT_CLEAR place
    corner_top and corner_bottom. Returns (bite, point, air, slot) or None.

    RIM_KEEP, not 0: a boss rim close to the outer skin leaves a wall the nozzle
    cannot print (Analysis/check_outputs.py NOZZLE, 0.40 mm, and f148 is what a
    0.02-0.07 mm sheet did - sliver faces the wall map read as a 0.026 mm wall),
    and a rim through it breaks the smooth outer ellipsoid, which rhY forbids.
    """
    RIM_KEEP = 0.40
    for step in (0.25, 0.05, 0.01):
        top = None
        n = int(round(reach / step))
        for i in range(-n, n + 1):
            for k in range(-n, n + 1):
                p = (apex[0] + i * step, apex[1] + k * step)
                u = hull_r(p[1]) - p[0]               # depth under the outer skin
                if u <= 0 or BOSS_D / 2 - u > -RIM_KEEP:
                    continue
                bite = BOSS_D / 2 - max(bands[0](p), bands[1](p))
                if bite <= 0:                         # the boss misses one wall
                    continue
                air, slot = seam_air(p) - HOLE_D / 2, stem_slot_wall(p) - HOLE_D / 2
                if air < AIR_KEEP or slot < AIR_KEEP:
                    continue
                if top is None or bite > top[0]:
                    top = (bite, p, air, slot)
        if top is None:
            return None
        apex, reach = top[1], step * 4
    return top


def bulb_joints():
    """(name, (r, z), walls, why) for the two bulb joints, one in each corner."""
    out = []
    for name, apex, bands, reach, walls, why in (
            ("bulb_groove", bulb_inner_corner(), (band_tube, band_dome), 8.0,
             ["duct tube wall", "duct bulb dome wall"],
             "the INNER corner where the duct's tube wall meets the bulb's dome, "
             "boss fused into both"),
            ("bulb_outer", bulb_outer_corner(), (band_dome, band_skin), 14.0,
             ["duct bulb dome wall", "hull skin (the duct's outer wall)"],
             "the OUTER corner where the bulb's dome meets the duct's outer side, "
             "which is the hull skin; the corner's apex is inside the stem slot, so "
             "the boss sits on the same two walls as far out of the slot as the "
             "hole's AIR_KEEP allows, its rim RIM_KEEP under the outer face")):
        got = bulb_boss_centre(apex, bands, reach)
        if got is None:
            raise RuntimeError("no two-wall spot for %s within %.1f mm of its corner "
                               "at (%.2f, %.2f)" % (name, reach, apex[0], apex[1]))
        bite, p, air, slot = got
        out.append((name, p, walls, why, bite, air, slot))
    return out


def joints():
    """The peg/hole pairs on a seam, as records: name, (r, z), the wall faces
    the boss fuses into, and why the joint is there.

    A duct seam carries TWO pegs at its bulb - one in each corner where the duct's
    tube wall meets the bulb's dome, fused into both of those walls - and one joint
    at each end of the slice's straight shaft-side wall (the intake shaft's
    own wall: the bellmouth end at the top, the fan-housing ceiling end at the bottom),
    so each cylinder is fused into BOTH walls of its corner (the two-wall rule). Nothing
    else is on that face: the pegs that used to float in the open lattice cells there, and their
    holes in the neighbouring slice, are gone, and so are the joint that used to
    stand on the housing ceiling over the blade tips and the keel joint that used
    to hang over the hatch hardware - both were thick blocks of material over the
    fan, and both sat within JOINT_CLEAR of the impeller's swept volume. The peg
    f087 put on top of the duct is gone too: measured, the crest wall there is 0.86
    mm of material and cannot hold a Ø3.3 hole with AIR_KEEP of wall to the air
    without standing material outside the outer skin (see the note by S_BULB_GROOVE).

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
    # The TWO bulb joints (f149): rhY at the f148 print - "Missing peg, other peg
    # not in the corner touching two sides." One in each corner where the duct's
    # tube wall meets the bulb's dome (bulb_joints()): each boss is fused into BOTH
    # walls there, and each hole keeps AIR_KEEP of wall to the duct's air path.
    #
    # bulb_groove is the INNER corner. f148 had it at duct_at(S_BULB_GROOVE), a
    # point on the tube wall: measured, 2.05 mm of boss inside the tube wall and
    # 0.00 mm inside the dome wall - tangent to it, so it stood in ONE wall.
    #
    # bulb_outer is the OUTER corner: the dome against the duct's outer side, which
    # is the hull skin (rhY f087 item 1). The corner's apex, where the dome wall's
    # face crosses the skin band's inner face, sits 6.2 mm under the equator at
    # scale 1 - INSIDE the Ø25.4 stem slot, which build() cuts after the bosses are
    # fused, so a boss there is cut away and its peg is left loose in the air. That
    # is exactly how the peg f087 put on top of the duct failed: its hole centre sat
    # at 9.73 mm from the centreline, inside the air; the boss was fused at
    # build():1839, removed by the bore cut at build():1845, and the peg fused at
    # build():1850 was left as a 28 mm3 solid loose in the air (STL part 14, at
    # (178.9, -48.7) in the seam plane). bulb_outer therefore sits on the same two
    # wall faces as far out of the slot as the hole's AIR_KEEP allows, where the
    # boss bridges the dome wall and the skin.
    for name, p, walls, why, _bite, _air, _slot in bulb_joints():
        out.append(joint(name, p[0], p[1], walls, why))
    for name, p, walls, why, sl in corner_joints():
        out.append(joint(name, p.x, p.z, walls, why, sl))
    return out


def corner_joints():
    """The joints at the two ends of the slice's straight shaft-side wall.

    Returns (name, point in the seam plane, the walls the boss fuses into, why,
    sleeve or None) for each. A corner joint sits where two walls meet, so its
    cylinder is fused into BOTH walls (the two-wall rule). The two corners are the
    two ends of the intake shaft's own straight wall (r = SHAFT_R .. SHAFT_R + T,
    from nozzle_top() up to intake()[2]): the top end, where the bellmouth rolls
    the hull skin into the shaft, and the bottom end, where the same wall turns
    into the fan housing's ceiling over the shroud turn (radius SHROUD_RC about
    (SHAFT_R + SHROUD_RC, FLOOR_Z + SHROUD_RC)) - the empty ~90 deg corner rhY
    pointed at (print x 35-60, y +63..+75, hull z -63..-75).

    Both sit at r = SHAFT_R + HOLE_D / 2 + AIR_KEEP: the hole keeps exactly AIR_KEEP
    of wall to the shaft bore, and that is what puts the boss as close to each corner
    as AIR_KEEP and JOINT_CLEAR allow. Measured in the (r, z) meridian plane
    (build/f118/corner_2d.py): the Ø7 boss overlaps the shaft-side wall by 2.11 mm
    at both corners, and the wall each corner turns into by 2.25 mm (top) and 1.25
    mm (bottom), so it is fused through both; the hole keeps 0.60 mm of wall to the
    shaft bore and to the housing's air, and the boss keeps 4.55 mm to the plenum
    air and 6.05 mm to the impeller's swept volume, both over JOINT_CLEAR. Analysis/
    check_outputs.py --joints measures both rules against the map this build writes.

    The two joints f117 left out in the middle of the hull are DELETED (rhY 2026-11-17
    item 1): seam_mid (149.4, 67.7), out on a lattice node, and corner_duct_top (201.0,
    16.2), on the outer skin by the bulb. Their records, bosses, pegs and holes go
    with them. bulb_groove is kept (rhY asked for it in f117).
    """
    r = SHAFT_R + HOLE_D / 2 + AIR_KEEP   # the hole keeps AIR_KEEP of wall to the shaft bore
    out = []
    # (a) the hull-top end of that wall: the shaft wall's straight run ends at
    # z = intake()[2], where the bellmouth roll (radius INTAKE_R about
    # (SHAFT_R + INTAKE_R, intake()[2])) takes over and the hull skin comes down.
    out.append(("corner_top", cq.Vector(r, 0, intake()[2]),
                ["intake shaft wall", "intake bellmouth (hull skin)"],
                "the hull-top end of the straight shaft-side wall: the shaft wall meets the "
                "bellmouth, where the hull skin rolls into the shaft. f117 had this joint at "
                "(46.9, 97.3) - 15.2 mm from the shaft-side wall's outer face and 11.7 mm from "
                "any material of it, so it was fused into the skin band only, not in the corner "
                "rhY asked for. Peg on one slice, hole in the neighbour, fused into both walls "
                "of the corner.", None))
    # (b) the fan-housing end of the same wall: the empty corner at its other end.
    out.append(("corner_bottom", cq.Vector(r, 0, FLOOR_Z + SHROUD_RC),
                ["intake shaft wall", "fan housing ceiling (shroud turn)"],
                "the fan-housing end of the straight shaft-side wall, the empty ~90 deg corner "
                "where that wall turns into the fan housing's ceiling over the radius-SHROUD_RC "
                "shroud turn. The boss is fused into both walls there; the hole keeps AIR_KEEP "
                "= 0.60 mm of wall to the housing's air and to the shaft bore, and the boss keeps "
                "4.55 mm to the plenum air and 6.05 mm to the impeller's swept volume.", None))
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


def crest_half(psi):
    """How far in from the seam plane the solid skin over a duct reaches at ellipse angle
    psi: CREST_BAND over the duct's run (crest_psi_range), nothing above it, where the
    duct has ended and the lattice runs to the seam as it always has."""
    lo, hi = crest_psi_range()
    return CREST_BAND if lo <= psi <= hi else 0.0


def column_bounds(psi, side, outer=None):
    """Azimuths of one column's edges: RIB/2 in from the centre plane, and `outer` mm in
    from the seam plane - the solid skin the duct's air needs (crest_half(psi)) where a
    duct runs under the skin, RIB/2 where it does not. rhY f118 item 4: the lattice runs
    right out to that edge instead of standing RIB/2 off the seam; a cell the edge cuts
    stays filled (clip_window / windows() drop partial ones), so the half cells along the
    duct's band are the solid patches rhY asks for "for strength"."""
    x = skin_point(psi, T / 2)[0]
    d = max(RIB / 2, outer if outer is not None else crest_half(psi))
    th_in, th_out = math.asin((RIB / 2) / x), math.radians(HALF) - math.asin(d / x)
    return (th_in, th_out) if side > 0 else (-th_out, -th_in)


def oval_on_skin(p0, p1, side, n=96):
    """Oval window of the cell between ribs p0 and p1, in column `side`, as
    points on the skin's mid-surface with their normals. It is laid out on the
    real curved skin: at every height it spans the column between its edges,
    and from bottom to top it spans the row, so it touches each of the four
    rib lines (RIB/2 in) at one point and fills the cell."""
    q0 = p0 + (RIB / 2) / ds_dpsi(p0)
    q1 = p1 - (RIB / 2) / ds_dpsi(p1)
    outer = crest_half((p0 + p1) / 2)   # one bound for the whole cell: the oval stays a
                         #   full cell or is left filled, never tapered by the band's edge
    out = []
    for i in range(n):
        t = 2 * math.pi * i / n
        c_, s_ = math.cos(t), math.sin(t)
        a_ = math.copysign(abs(c_) ** (2 / OVAL_N), c_)
        b_ = math.copysign(abs(s_) ** (2 / OVAL_N), s_)
        psi = (q0 + q1) / 2 + b_ * (q1 - q0) / 2
        lo, hi = column_bounds(psi, side, outer)
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


def clean_ring(ring):
    """A ring without repeated or collinear points.

    A cell is the window clipped to one box of the grid, so it picks up extra
    vertices along its own straight edges; ear_clip's fallback (no strict ear left)
    returns a zero-area triangle for those, and the kernel will not close a shell
    around a face that has no area.
    """
    out = []
    for p in ring:
        if out and abs(p[0] - out[-1][0]) < RING_WELD and abs(p[1] - out[-1][1]) < RING_WELD:
            continue
        out.append((float(p[0]), float(p[1])))
    if len(out) > 3 and abs(out[0][0] - out[-1][0]) < RING_WELD and abs(out[0][1] - out[-1][1]) < RING_WELD:
        out.pop()
    while len(out) > 3:
        keep = []
        for i in range(len(out)):
            a, b, c = out[i - 1], out[i], out[(i + 1) % len(out)]
            if abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])) < 1e-9:
                continue                                # b lies on a-c
            keep.append(b)
        if len(keep) == len(out):
            break
        out = keep
    return out


def resample_ring(ring, step):
    """The same ring with its vertices spread about `step` mm apart.

    Two passes: drop a vertex standing within step/2 of the one kept before it,
    then split any edge longer than step. The boundary moves by less than step/2,
    and only where it already had a spike or a pair of coincident vertices - which
    is what clip_window rules out for the window as a whole but not for the
    vertices it leaves behind where it cuts. Evenly spaced vertices mean evenly
    spaced wall faces: no wall face narrower than OUT_MESH / 2 mm.
    """
    out = []
    for p in ring:
        if out and math.dist(p, out[-1]) < 0.5 * step:
            continue
        out.append((float(p[0]), float(p[1])))
    while len(out) > 3 and math.dist(out[0], out[-1]) < 0.5 * step:
        out.pop()
    if len(out) < 4:
        return out
    res = []
    n = len(out)
    for i in range(n):
        a, b = out[i], out[(i + 1) % n]
        m = max(1, int(math.ceil(math.dist(a, b) / step)))
        for j in range(m):
            t = j / m
            res.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    return res


def skin_cutter(pts, top_depth=-CUT_OUT, bot_depth=CUT_IN):
    """Window cutter from an outline on the skin (points and normals): ONE filled
    solid that passes through the whole skin band over the WHOLE window area.

    `top_depth` / `bot_depth` are the two depths under the outer skin its caps sit at;
    the defaults are a window's (-CUT_OUT, so 0.6 mm clear of the outer face, down to
    CUT_IN = T + SKIN_MARGIN under it). servo_brace() passes its own: a rib is fused,
    not cut, so it stands inside the band (BRACE_OUT) and reaches one band depth past
    its inner face (BRACE_IN) instead of through the outer face.

    The outline's side walls run along the skin's own normal AT each point of the
    outline, from CUT_OUT (0.6 mm clear of the outer face) to CUT_IN (T + SKIN_MARGIN)
    under it, and the window's area is tiled into CUT_MESH cells so the two caps
    FOLLOW that same curved surface: each cell becomes a small prism and the cells
    are stitched into ONE shell - a cell edge shared by two cells gets no face, a
    cell edge that lies on the window's own outline gets its side wall. Every face
    is a triangle, which is what the kernel accepts (Face.makeFromWires refuses a
    non-planar wire, and a shell of ruled surfaces between two rings gives faces
    BRepCheck calls invalid).

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

    Why the caps must follow the surface, measured on the f087 8T bench slice
    (build/f117/probe1.log, probe2.log): the caps used to be ONE ear-clipped
    triangulation of the whole outline, so their triangles spanned chords of
    32-38 mm. Over the skin's 52 mm curvature radius a 38 mm chord sags 3.5 mm, and
    those cap faces measured +3.08 mm under the outer face instead of the -0.50 mm
    they were built at - 3.60 mm of sag. Scanning that ONE cutter along the skin's
    normal from its outline to its centre, it covers the band only AT the outline
    (-0.45 .. +1.15 mm) and +0.10 .. +3.0 mm everywhere inside: the band (0 .. 0.86
    mm) is never touched. Cutting the band with it removes 546 mm3 and leaves an
    818.9 mm3 plate at (201.0, 35.3, 16.1) - the window's middle, loose in the air.
    That is the junk in rhY's windows (16 of them: parts 1-6, 9-13, 16-20 of the
    STL), and the 0.0-0.4 mm rims of those plates are most of the 450 sub-layer
    facets in gates/f087-check.txt. With cells at CUT_MESH the worst chord is a
    cell diagonal, 7.07 mm, and the sag is 0.12 mm: the caps stay 0.38 mm outside
    and 1.28 mm under the outer face over the whole window, and the cut goes through.

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
    This builds: no loft, no patch, no shell to trim against - the cells are one
    shell, and their caps sit at the two depths the old shell's boundaries were at.
    """
    from shapely.geometry import Polygon, Point, box
    if len(pts) > 48:                       # ~1 mm of outline is plenty, and the
        pts = pts[::2]                    # face count is what costs the boolean
    c = sum((p for p, _ in pts), cq.Vector()) * (1 / len(pts))
    psi0, th0 = psi_of(c), math.atan2(c.y, c.x)
    to_uv, to_skin, sgn = skin_frame(psi0, th0)
    uv = [to_uv(p) for p, _ in pts]
    poly = Polygon(uv).buffer(0)
    if poly.is_empty or poly.area < 1.0:
        print(f"warning: window outline would not triangulate at {c.x:.0f}, {c.y:.0f}, "
              f"{c.z:.0f}")
        return None
    if poly.geom_type != "Polygon":
        poly = max(getattr(poly, "geoms", [poly]), key=lambda g_: g_.area)
    # spread the outline's vertices evenly (see OUT_MESH): they set the width of
    # the window's wall faces, and clipping leaves pairs of them a few hundredths
    # of a mm apart, each of which becomes a wall face that thin.
    poly = Polygon(resample_ring(list(poly.exterior.coords)[:-1], OUT_MESH),
                   [resample_ring(list(h.coords)[:-1], OUT_MESH) for h in poly.interiors])
    if poly.is_empty or poly.area < 1.0:
        return None

    ri = T / 2                                    # the outline is on the band's mid-surface
    #   surface()/duct_at() normals point OUT of the hull, away from the axis, so
    #   +n goes out past the outer face and -n goes in past the band's inner face.
    def pt_at(u_, v_, depth):
        """The point `depth` mm under the outer skin at uv (u_, v_): along the
        skin's own normal there. Every vertex of the cutter comes from this one
        map (skin_frame's to_uv is its exact inverse), so the cells' shared edges
        meet to the micrometre and the stitched shell closes without a boolean."""
        p_, nv = to_skin(u_, v_)
        return p_ + nv * (ri - depth)

    # Faces are built from a CACHE of points and edges keyed by uv and depth, so
    # two faces that meet along a cell edge use the SAME edge object rather than
    # coincident copies of it. A shell of coincident-but-unshared edges is what
    # left 908 sliver faces along the window rims in the previous build - the
    # boolean could not tell the two copies were meant to be one seam, and the
    # slivers are what the thin-facet scan reads as a 0.005 mm wall.
    pts, pidx, eidx = [], {}, {}

    def pid(u, v, depth):
        key = (u, v, depth)
        got = pidx.get(key)
        if got is None:
            got = len(pts)
            pidx[key] = got
            pts.append(pt_at(u, v, depth))
        return got

    def eid(i, j):
        if i == j:
            return None
        key = (i, j) if i < j else (j, i)
        got = eidx.get(key)
        if got is None:
            got = cq.Edge.makeLine(pts[i], pts[j])
            eidx[key] = got
        return got

    def face(i, j, k):
        """One planar triangular face from three cached corners, or None."""
        if i == j or j == k or k == i:
            return None
        mw = BRepBuilderAPI_MakeWire()
        for a, b in ((i, j), (j, k), (k, i)):
            mw.Add(eid(a, b).wrapped)
        if not mw.IsDone():
            return None
        mf = BRepBuilderAPI_MakeFace(mw.Wire(), True)
        if not mf.IsDone():
            return None
        f = cq.Face(mf.Face())
        return f if (f.Area() > 1e-12 and f.isValid()) else None

    # Tile the window: the cells' union is the window EXACTLY (each cell is the
    # window clipped to one box of the grid), so no strip of skin is left uncut
    # along a cell edge, and every cap triangle's chord is at most a cell diagonal.
    # The grid is fitted to the window (nu x nv cells, each between CUT_MESH/2 and
    # CUT_MESH wide) rather than stepping across it: a leftover sliver cell 0.01 mm
    # wide does not survive the boolean, and the strip of skin it stands on is then
    # never cut at all - a membrane under the nozzle, exactly what issue #36 counts.
    cells = []
    u_lo, v_lo, u_hi, v_hi = poly.bounds
    nu = max(1, int(math.ceil((u_hi - u_lo) / CUT_MESH)))
    nv = max(1, int(math.ceil((v_hi - v_lo) / CUT_MESH)))
    du, dv = (u_hi - u_lo) / nu, (v_hi - v_lo) / nv
    for i in range(nu):
        u0 = u_lo + i * du
        u1 = u_hi if i == nu - 1 else u0 + du
        for j in range(nv):
            v0 = v_lo + j * dv
            v1 = v_hi if j == nv - 1 else v0 + dv
            g = poly.intersection(box(u0, v0, u1, v1))
            for q in (getattr(g, "geoms", None) or [g]):
                if q.geom_type == "Polygon" and q.area > 1e-9:
                    cells.append(q)
    if not cells:
        print(f"warning: window would not tile at {c.x:.0f}, {c.y:.0f}, {c.z:.0f}")
        return None
    if sum(q.area for q in cells) < poly.area - 1e-3:
        print(f"warning: window tiling at {c.x:.0f}, {c.y:.0f}, {c.z:.0f} covers "
              f"{sum(q.area for q in cells):.3f} of {poly.area:.3f} mm2")

    bd = poly.boundary

    def build(top_depth, bot_depth):
        """One shell over all the cells: caps at the two depths, side walls only
        on the window's own outline. A cell edge whose midpoint lies on that outline
        gets a side wall; every other cell edge is shared by two cells and gets
        none, which is what stitches the cells into ONE solid rather than a pile
        of prisms. Each side quad is split along a diagonal: its four points are
        not quite coplanar (the skin normal turns over one outline segment), and
        a non-planar face is what the kernel refuses."""
        faces = []
        for cell in cells:
            ring = clean_ring(list(cell.exterior.coords)[:-1])
            tris = ear_clip(ring)
            if not tris:
                return None
            n = len(ring)
            top = [pid(ring[i][0], ring[i][1], top_depth) for i in range(n)]
            bot = [pid(ring[i][0], ring[i][1], bot_depth) for i in range(n)]
            for a, b, k in tris:
                if abs((ring[b][0] - ring[a][0]) * (ring[k][1] - ring[a][1]) -
                       (ring[b][1] - ring[a][1]) * (ring[k][0] - ring[a][0])) < 1e-9:
                    continue                                    # degenerate ear
                for f in (face(top[a], top[b], top[k]), face(bot[a], bot[k], bot[b])):
                    if f is None:
                        return None
                    faces.append(f)
            for i in range(n):
                j = (i + 1) % n
                m = Point((ring[i][0] + ring[j][0]) / 2.0,
                          (ring[i][1] + ring[j][1]) / 2.0)
                if bd.distance(m) > 1e-9:
                    continue                                    # interior edge
                for f in (face(top[i], top[j], bot[j]), face(top[i], bot[j], bot[i])):
                    if f is None:
                        return None
                    faces.append(f)
        try:
            sol = cq.Solid.makeSolid(cq.Shell.makeShell(faces))
        except Exception:
            return None
        return sol if (sol.isValid() and sol.Volume() > 0) else None

    sol = build(top_depth, bot_depth) or build(bot_depth, top_depth)
    if sol is None:
        raise ValueError(f"the window cutter at {c.x:.1f}, {c.y:.1f}, {c.z:.1f} would not "
                         f"build as one stitched shell ({len(cells)} cells, {len(pts)} "
                         f"outline points): the slice must not ship with a window "
                         f"missing from it, so the build stops here")
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
    # psi_of (the uv inverse) is the module-level one, see psi_of() above.

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
    """A window polygon, clipped to the skin band, the slice's seam planes, the solid
    skin the duct's air needs and the windows around it, with its tips rounded by `tip`
    (0 for an oval: it has no tips, and rounding a 96-point outline only loses area).
    Returns the polygon, or None if nothing printable is left.

    rhY f118 item 4: the lattice runs right out to the edges, and ONLY a cell an edge
    cuts stays filled. So a polygon that any of those clips CHANGES is not cut at all
    (returned as None): every FULL cell is an open window, the partial cells along the
    band's edges, the seam planes and the duct's air stay solid skin. That also keeps
    the boolean safe the way MIN_WEB used to: no cut boundary ever lands on a face
    that is already there.

    This is the sliver fix, and it happens before a window becomes a solid. A
    window whose boundary touches the band's edge, a seam plane or a neighbouring
    window is cut flush against a face that is already there, and the kernel
    leaves a sliver behind: a face 0.000 mm from the face it was cut by, which
    prints as a 0.01-0.05 mm wall, i.e. a hole (issue #36). A notch or a spike in
    the boundary narrower than MIN_WEB does the same thing the other way round: it
    leaves a tongue of skin that thin standing in the hole. Nothing repairs either
    afterwards, so the polygon is clipped and closed here, in shapely.
    """
    from shapely.geometry import Point, box
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
    # the seam planes: MIN_WEB (0) inside the slice's own side face - rhY f118 item 4: no
    #   solid edge strip any more, the lattice runs to the seam, and a junction the seam
    #   plane cuts (the half diamonds along an edge) stays filled by the rule above.
    mu = MIN_WEB * x0 / min(skin_point(q, T / 2)[0] for q in span)
    whole = poly.area
    u_seam = sorted(((th_half - theta) * x0, (-th_half - theta) * x0))
    v_band = sorted((sgn * (psi_lo - psi) * ds, sgn * (psi_hi - psi) * ds))
    keep = box(u_seam[0] + mu, v_band[0] + mv, u_seam[1] - mu, v_band[1] - mv)
    poly = poly.intersection(keep)
    if poly.is_empty or poly.area < whole - 1e-9:
        return None                     # the band's edge or a seam plane cuts this cell: filled
    # The solid crest band along each duct (CREST_BAND either side of the crest line, which
    # is the seam plane: the duct is split in half by it). No window is cut inside it, and none
    # is left within MIN_WEB of its edge: a cut boundary that close is what left the 0.186-0.382
    # mm crest walls and the 0.004 mm2 sliver face f085 measured, all within 6.9 mm of a seam.
    # In this uv frame the band is a straight u-strip (u = (azimuth - theta) * x0 is the
    # perpendicular distance from the seam plane), so the clip is exact and the lattice simply
    # stops at the band's edge - the cells keep their rib lines, they are re-flowed around it.
    for s_ in duct_seams():
        u_c = (math.radians(s_) - theta) * x0
        # the band only runs the duct's own height (crest_psi_range): above the duct's
        # end there is no air under the skin, so the lattice runs to the seam there too
        v_c = sorted((sgn * (crest_psi_range()[0] - psi) * ds,
                      sgn * (crest_psi_range()[1] - psi) * ds))
        poly = poly.difference(box(u_c - (CREST_BAND + MIN_WEB - CREST_EDGE_CLEAR), v_c[0],
                                   u_c + (CREST_BAND + MIN_WEB - CREST_EDGE_CLEAR), v_c[1]))
        if poly.is_empty or poly.area < whole - 1e-9:
            return None   # the duct's air band cuts this cell: it stays filled (rhY item 4)
    # f150 item 2: the outlet keep-outs - the stem bearing sleeve's footprint on each seam
    # that carries a thruster, and the ring round this slice's servo-spline hole. These CLIP,
    # they do not DROP: a cell a ring only grazes becomes a clipped window with the ring bitten
    # out of it, not a solid patch (rhY's three solid patches on the CR-10 Pro print, 1476 +
    # 807 + 807 mm2 of skin that carries no window, build/f150/probe1.log). The ring's surface
    # is not a face of the part - the sleeve's own face stands AIR_KEEP inside the ring, and
    # the spline hole's is SERVO_WALL inside it - so this cut boundary does not land on a face
    # that is already there, which is the only thing the drop rule was protecting against.
    for _n, az, off, z_, rad in outlet_axes():
        u_c = (math.radians(az) + off / max(1.0, hull_r(z_)) - theta) * x0
        v_c = sgn * (math.asin(max(-1.0, min(1.0, z_ / B))) - psi) * ds
        if poly.distance(Point(u_c, v_c)) > rad + 1.0:
            continue                     # the ring is nowhere near this cell
        disc = _uv_disc(psi, theta, x0, ds, sgn, az, off, z_, rad)
        if disc is None:
            continue
        poly = poly.difference(disc)
        if poly.is_empty:
            return None
    # f150 item 1: the servo brace's corridor. The brace is a RIB-wide rib on the equator
    # between those two ends, so no window is cut inside RIB / 2 + BRACE_EDGE_CLEAR of the
    # equator over that azimuth span: the cells it crosses are re-flowed around it, and the
    # cut boundary never lands on the brace's own face (BRACE_EDGE_CLEAR of uncut skin keeps
    # it off). Like the rings this clips the cell, it does not drop it.
    b_lo, b_hi = brace_span()
    if b_hi > b_lo:
        r0 = hull_r(OUT_Z)
        da = math.degrees(BRACE_EDGE_CLEAR / r0)
        u0 = math.radians(b_lo - da) * x0
        u1 = math.radians(b_hi + da) * x0
        # How far the corridor has to reach for THIS cell. The brace's own face is at
        # RIB / 2 from the equator and a window must not be cut inside
        # RIB / 2 + BRACE_EDGE_CLEAR of it. But the lattice's own rib line is only
        # ~1.6 mm of arc wide there, so a fixed corridor at 1.5 mm lands 0.1 mm off the
        # oval's own edge and leaves a 0.1 mm notch - the sliver the f118 rule exists to
        # prevent. So the corridor is pushed out to this cell's own edge plus
        # BRACE_EDGE_CLEAR whenever that is wider: the strip it then removes is
        # BRACE_EDGE_CLEAR wide, not a hair, and the cell's original edge is inside the
        # solid rather than 0.1 mm from a new cut.
        w0 = RIB / 2 + BRACE_EDGE_CLEAR
        rings = ([poly.exterior] if poly.geom_type == "Polygon"
                 else [g.exterior for g in getattr(poly, "geoms", ())
                       if g.geom_type == "Polygon"])
        graze = []
        for ring in rings:
            for uu, vv in ring.coords:
                if not (u0 <= uu <= u1):
                    continue
                a = abs(ellipse_arc(0.0, psi + sgn * vv / ds))   # arc from the equator
                if a <= w0 + BRACE_EDGE_CLEAR:
                    graze.append(a)
        # measured against w0 once, not against the widening as it grows: the boundary of
        # a cell that crosses the corridor runs from the equator all the way up the hull,
        # and widening as it walked swallowed the cell whole (probe3b.log: the equator
        # junction and the oval at psi 4.84 dropped, 34 cutters instead of 36).
        w = max(w0, max(graze) + BRACE_EDGE_CLEAR) if graze else w0
        ph = psi_at_arc(w)
        u_b = sorted(((math.radians(b_lo - da) - theta) * x0,
                      (math.radians(b_hi + da) - theta) * x0))
        v_b = sorted((sgn * (-ph - psi) * ds, sgn * (ph - psi) * ds))
        poly = poly.difference(box(u_b[0], v_b[0], u_b[1], v_b[1]))
        if poly.is_empty:
            return None
    # What a clip leaves must still be printable: a window narrower than the nozzle cannot
    # be cut at all, and a crescent left by a ring that nearly covers the cell is the sliver
    # issue #36 counts. So the clipped cell must survive an erosion by NOZZLE and keep
    # MIN_OPEN_AREA of skin; otherwise it stays filled, the old rule.
    if poly.area < MIN_OPEN_AREA or poly.buffer(-NOZZLE).area < 0.2 * poly.area:
        return None
    if others:
        before = poly.area
        poly = poly.difference(unary_union([o.buffer(MIN_WEB) for o in others]))
        if poly.is_empty:
            return None
        if poly.area < 0.6 * before:
            return None   # a neighbour window nibbling this one is the lattice's own layout
    # Close the boundary: erode then dilate by POLY_CLOSE. A notch or a spike
    # narrower than 2*POLY_CLOSE is removed, so no cut can leave a tongue of skin
    # that thin standing in the hole. Ribs (RIB = 2.0 mm) and the webs between
    # windows are far wider, so nothing structural moves.
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
        # rhY f118 item 4: every FULL cell is an open window, and ONLY a cell a keep-out
        # cuts stays filled. So a cutter that any of these three solids CHANGES is dropped
        # whole - the cell stays solid skin - rather than cut down to the part that survives.
        # That is what lets MIN_WEB go to 0: the cut boundary never lands on a face that is
        # already there (the band's edge, a seam plane, the duct's air, the stem collars),
        # which is what the 0.009-0.05 mm sliver walls issue #36 counts came from.
        v0 = c.Volume()
        for solid in (air, crest, keep):
            if solid is None:
                continue
            try:
                cc = c.cut(solid)
            except ValueError:                  # empty: the cell is fully inside the keep-out
                cc = None
            if cc is None or cc.Volume() < v0 - 1e-6:
                break                           # this cell is a partial one: leave it filled
            c = cc
        else:
            out.append(c)
    return out


def stem_flare_r(x):
    """The stem hole's OWN radius at axial position x along the seam's equatorial line:
    STEM_HOLE / 2 inboard, growing over the skin band as the flare cone (see STEM_FLARE).
    stem_and_servo_holes() cuts exactly this and the keep-out below is sized from it, so
    the hole and the keep-out it stands in cannot drift apart."""
    x_in = hull_r(OUT_Z) - 3.0                      # inside the band's inner face at the rim
    return STEM_HOLE / 2 + max(0.0, x - x_in) * math.tan(math.radians(STEM_FLARE + 1.5))


def stem_keep_r():
    """Radius of the outlet keep-out ring round a stem hole: the bearing sleeve's own
    footprint (BOSS_R about the seam's equatorial line) or the flared hole's widest radius,
    whichever is wider, plus AIR_KEEP. It used to be BOSS_R + 1.5 = 15.5 mm, which is 1.5 mm
    more than the sleeve and reached into the full cells either side of the equator and left
    them solid (rhY f150 item 2: two 806.8 mm2 patches, one of them grazed by 1.89 mm3 of a
    1761 mm3 cutter - build/f150/probe1.log)."""
    return max(BOSS_R, stem_flare_r(hull_r(OUT_Z) + 1.5)) + AIR_KEEP


def servo_keep_r():
    return SERVO_HOLE / 2 + SERVO_WALL


def outlet_axes():
    """(name, seam azimuth, tangent offset, height, radius) for every outlet keep-out this
    slice needs: the stem bearing sleeve's footprint on each seam that carries a thruster,
    and a ring round this slice's servo-spline hole. Each is a cylinder about a line at
    height `z` running radially at azimuth `az`, offset `off` along the tangent from that
    seam - the same lines stem_and_servo_holes() bores its holes along."""
    out = [("stem ring r=%.2f" % stem_keep_r(), a_, 0.0, OUT_Z, stem_keep_r())
           for a_ in duct_seams()]
    if has_servo():
        out.append(("servo ring r=%.2f" % servo_keep_r(), -HALF, SERVO_T, OUT_Z, servo_keep_r()))
    return out


def _axis_line(az, off, z):
    """A point on and the direction of the outlet axis at azimuth `az` (degrees), offset
    `off` mm along the tangent from that seam, at height `z`."""
    a_ = math.radians(az)
    o = cq.Vector(-off * math.sin(a_), off * math.cos(a_), z)
    return o, cq.Vector(math.cos(a_), math.sin(a_), 0)


def outlet_keepout():
    """Solid skin only where it must be: the stem bearing sleeve's own footprint on each
    seam that carries a thruster, and a ring round this slice's servo-spline hole. Elsewhere
    the lattice runs straight over the ducts; their own walls keep them airtight.

    f150 item 2: these are now only as big as the sleeve and the spline hole need (see
    stem_keep_r / servo_keep_r), and clip_window CLIPS the lattice cells to them instead of
    windows() dropping a cell the ring only grazes. The solids are kept 0.5 mm SMALLER than
    the uv clip clip_window applies, the same way crest_keepout() is looser than its uv clip:
    they are the belt-and-braces guard in windows(), and a guard that cut where the uv clip
    already cut would leave the cutter with two coincident walls. 0.5 mm, not 0.1: the uv
    disc is drawn on the skin's MID surface while the cutter's caps sit 0.6 mm above the
    outer face and 1.16 mm below it, so the cutter's own edge swings +-0.2 mm in the distance
    from the outlet axis; a 0.1 mm margin was inside that and dropped two cells that the clip
    had just opened (build/f150/probe3.log: "outlet (-1.51 mm3)", "outlet (-1.25 mm3)").
    """
    parts = []
    for _n, az, off, z, rad in outlet_axes():
        o, d = _axis_line(az, off, z)
        x_in = hull_r(OUT_Z) - BOSS_LEN - 1.0       # 1 mm inboard of the sleeve's back face
        x_out = hull_r(OUT_Z) + 2.0                 # past the outer face at the rim
        # The guard stands inside the uv disc clip by 0.5 mm PLUS the swing the cutter
        # itself makes: the disc is drawn on the skin's MID surface, its caps sit 0.6 mm
        # above the outer face and 1.16 mm below the inner one, and the skin's normal at the
        # outlet is tilted atan(off / hull_r) away from the keep-out axis - 9.9 deg at this
        # slice's servo hole (off = SERVO_T = 36 mm), 0 deg at a stem ring (off = 0). So the
        # cutter's own edge swings (T/2 + 1.16) * tan(tilt) = 0.28 mm in radius at the servo
        # ring, and a guard that does not stand inside that swing would nibble a second wall
        # 0.28 mm off the clip's. Measured: with a flat 0.5 mm margin no cutter was dropped
        # at either size (build/f150/probe3c.log, 36 of 36 kept), so this changes no face -
        # it just stops the guard being able to cut where the clip already cut.
        tilt = math.atan2(abs(off), hull_r(OUT_Z))
        r_guard = rad - 0.5 - (T / 2.0 + 1.16) * math.tan(tilt)
        if r_guard > 0.0:
            parts.append(cq.Solid.makeCylinder(r_guard, x_out - x_in, o + d * x_in, d))
    if not parts:
        return None
    keep = parts[0]
    for p_ in parts[1:]:
        keep = keep.fuse(p_)
    return keep


def _uv_disc(psi, theta, x0, ds, sgn, az, off, z, radius):
    """The skin points within `radius` of an outlet axis (outlet_axes) as a polygon in the
    cell's unrolled uv frame - the frame clip_window works in, where the skin band's edges
    and the seam planes are straight lines. The axis is a line, so its keep-out is a disc
    about the point the line touches the skin; the disc is traced by bisecting the exact
    3D distance from the line out along 64 rays from that point, so it is the real cylinder
    in uv, not an approximation of it in the tangent plane."""
    from shapely.geometry import Polygon
    o, d = _axis_line(az, off, z)

    def dist(uu, vv):
        ps = psi + sgn * vv / ds
        r_, z_ = skin_point(ps, T / 2)
        th_ = theta + uu / x0
        p = cq.Vector(r_ * math.cos(th_), r_ * math.sin(th_), z_) - o
        cr = p.cross(d)
        return math.hypot(cr.x, cr.y, cr.z)

    # where the axis touches the skin, in uv: the start of the search
    u = (math.radians(az) + off / max(1.0, hull_r(z)) - theta) * x0
    v = sgn * (math.asin(max(-1.0, min(1.0, z / B))) - psi) * ds
    for step in (2.0, 0.2, 0.02):
        best, bd = (u, v), dist(u, v)
        for du, dv in ((step, 0), (-step, 0), (0, step), (0, -step)):
            dd = dist(u + du, v + dv)
            if dd < bd - 1e-12:
                best, bd = (u + du, v + dv), dd
        u, v = best
    ring = []
    for k in range(64):
        t_ = 2 * math.pi * k / 64.0
        lo, hi = 0.0, 2.0 * radius
        if dist(u, v) > radius:
            return None
        for _ in range(40):
            mid = (lo + hi) / 2
            if dist(u + mid * math.cos(t_), v + mid * math.sin(t_)) < radius:
                lo = mid
            else:
                hi = mid
        ring.append((u + lo * math.cos(t_), v + lo * math.sin(t_)))
    poly = Polygon(ring)
    return poly if poly.is_valid and not poly.is_empty else None


def psi_at_arc(w):
    """The ellipse angle whose arc distance from the equator (psi = 0) is `w` mm."""
    lo, hi = 0.0, math.pi / 2
    for _ in range(60):
        mid = (lo + hi) / 2
        if ellipse_arc(0.0, mid) < abs(w):
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2 if w >= 0 else -(lo + hi) / 2


def brace_span():
    """The azimuths (degrees) the servo brace runs between: from the edge of the servo
    mount's keep-out ring to the crest band's edge on the seam the servo is NOT next to.
    Empty (0, 0) for a slice that has no such pair - a 4T slice's far seam carries no duct.

    Measured on the skin, not along a chord: the brace follows the equator (constant
    z = OUT_Z), so both ends are arc distances about hull_r(OUT_Z)."""
    if FOUR or not has_servo() or len(duct_seams()) < 2:
        return (0.0, 0.0)
    near = -HALF                                   # the seam the servo spline sits off
    far = max(duct_seams(), key=lambda a_: abs(a_ - near))
    r0 = hull_r(OUT_Z)
    # the near end stands BRACE_EDGE_CLEAR past the servo keep-out ring, so its end face is
    # buried in uncut skin and keeps wall to the Ø8 spline hole. The far end stops at the
    # stem keep-out ring, which is the wider of the bearing sleeve (BOSS_R) and the flared
    # stem hole (stem_flare_r, 13.9 mm at the outer face) plus AIR_KEEP: out to that radius
    # the band is uncut solid, so the rib's end face is buried in the band round the stem's
    # bearing boss and is fused into it. Stopping at CREST_BAND (12 mm) instead put the tip
    # INSIDE the stem hole's flare, and build()'s stem-hole cut then sliced the rib's end
    # into a sliver standing inside the hole's swept volume.
    a_from = near + math.degrees((SERVO_T + servo_keep_r() + BRACE_EDGE_CLEAR) / r0)
    a_to = far - math.degrees(stem_keep_r() / r0)
    return (a_from, a_to) if a_to > a_from else (0.0, 0.0)


def servo_brace():
    """f150 item 1: the horizontal brace on the equator from the servo mount to the far duct.

    rhY at the CR-10 Pro print: "a horizontal brace from the farther duct to the servo
    mount", and its purpose is strengthening the equator line. So it is a rib that follows
    the equator itself (constant z = OUT_Z, along the skin) and ties the stem/servo end of
    the slice to the duct on the seam the servo is NOT next to, as one continuous equator
    rib: the thruster stem hole is ON the seam at the equator and the servo spline hole is
    SERVO_T along the tangent from that seam, also at the equator, and each seam carries a
    duct half - so the two ends of the brace are two real walls, and it is fused into both
    and into the skin.

    Section: RIB wide (the lattice's own web width) and the skin band's DEEP, standing
    inboard of the band's inner face (BRACE_OUT .. BRACE_IN). A rib that only filled the
    band would add nothing: the band is already solid under it, since the windows are kept
    out of the corridor. Standing inboard by one band depth is what makes the equator line
    a T-deep rib instead of a T-thick skin line, and it is bounded by the air: the duct's
    bulb bore reaches SKIN_BITE inside the band, so the rib stops at the stem keep-out ring
    (stem_keep_r, the sleeve and the flared hole plus AIR_KEEP) round the far seam, where
    its inboard face keeps >= AIR_KEEP to the bulb's air at every size.

    The lattice cells it crosses are re-flowed: clip_window keeps every window out of the
    corridor |arc from the equator| <= RIB / 2 + BRACE_EDGE_CLEAR between the brace's ends,
    so no window wall lands on the brace's face and no sliver under the 0.40 mm nozzle is
    left between them.
    """
    lo, hi = brace_span()
    if hi <= lo:
        return None
    ph = psi_at_arc(RIB / 2)
    step = 2.0
    n = max(2, int(math.ceil(abs(hi - lo) * math.pi / 180.0 * hull_r(OUT_Z) / step)))
    pts = []
    for sgn_ in (1, -1):
        rng = range(n + 1) if sgn_ > 0 else range(n, -1, -1)
        for i in rng:
            az = math.radians(lo + (hi - lo) * i / n)
            p, nv = surface(ph if sgn_ > 0 else -ph, az)
            pts.append((p, nv))
    return skin_cutter(pts, BRACE_OUT, BRACE_IN)
    # NOTE for whoever picks this rib up. It can also be built as a plain annular sector
    # (r from hull_r-BRACE_IN to hull_r-BRACE_OUT, z +-RIB/2, azimuth lo..hi) and that is
    # the cleaner solid: 6 faces, flat ends, and the bench wall map's minimum goes from
    # 0.331 mm to 0.469 mm, because skin_cutter() offsets its ring along the surface NORMAL,
    # which fans out over psi and twists this rib's END wall into two 45 deg planar patches
    # leaning 2 mm along the equator (build/f150/thin-8T-final.log, faces 115-118 of the
    # bench STEP). It is not shipped, because with it the CR-10 Pro's 6000-facet wall-map
    # sample lands on a facet of the duct bulb's dome wall where that wall crosses the
    # slice's own seam plane and reads 0.189 mm there (build/f150/build-cr10c.log). That
    # facet is in every mesh of this model, f149's included - thin-cr10-40k.log finds it and
    # nine siblings at 40 000 samples, thin-8T-40k.log thirteen in the bench slice - and it
    # is not a thin wall: the ray runs almost inside the seam plane and hits the duct wall's
    # own end face 0.19 mm away, two faces of the same 0.86 mm wall meeting at a corner. The
    # fix belongs in the checker (ignore a hit whose face lies within ~10 deg of the ray),
    # and the checker is the gate, so it is out of this task's scope.


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
    # f148: drop the part of the walls solid that lies inside the skin's own T band. It is
    # redundant (the skin IS that wall), and leaving it meant the walls' outer boundary - a
    # face SKIN_BURY = 0.04 mm under the outer skin, parallel to it for the duct's whole run -
    # survived the fuse as sliver faces 0.01-0.33 mm2 sitting 0.02-0.07 mm under the skin
    # (measured in the STEP at OAS_SCALE 1.41 at r=71 z=-142.3 and r=122 z=-133.4, the keel
    # rows), which is what the wall map read as a 0.026 mm wall. What is cut away is inside
    # the skin band, and the skin band is solid under the crest the duct runs in (clip_window
    # keeps every lattice window CREST_BAND away from a seam that carries a duct), so the
    # part is unchanged; the cut face lands SKIN_TRIM mm under the outer skin, INSIDE the
    # skin's own T-thick material (SKIN_TRIM < T), so it is interior to the part and leaves
    # no face of its own. Landing it ON the skin's inner face (SKIN_TRIM = T) instead puts
    # it exactly on a surface that is already there - the coincidence this whole task is
    # about: measured at scale 1 that gave 0.005-0.009 mm walls at r=97 z=-92, r=203 z=-22
    # and r=111 z=87.
    SKIN_TRIM = 0.3   # mm under the outer skin down to which the duct's walls are trimmed
    band = (wedge_edges(arc(A, B, -math.pi / 2, math.pi / 2), half=180)
            .cut(wedge_edges(arc(A - SKIN_TRIM, B - SKIN_TRIM, -math.pi / 2, math.pi / 2),
                             half=180)))
    walls = walls.cut(band)
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
    dome, which is the widest part of the air path and now ends at the skin itself.

    f148: its top end is a rib line (skin_ribs() snaps the nearest rib onto crest_psi_hi),
    so no cell straddles the band's edge and this slab ends on a rib."""
    return lattice_band()[0], crest_psi_hi()


def crest_keepout():
    """The crest band as a solid: the skin CREST_BAND mm either side of each seam that carries
    a duct, over the duct's whole run (crest_psi_range). A slab about the seam plane, not a
    wedge about the axis - the duct's crest line IS the seam plane, and u = (azimuth - theta) *
    x0, the measure clip_window uses, is the perpendicular distance from that plane.

    windows() cuts every cutter with this as belt and braces after clip_window's uv clip, and
    strictly looser: CREST_BAND here against CREST_BAND + MIN_WEB there. When the two seam
    clips were at the SAME distance (f085) the cutter had two coincident walls and the boolean
    left 0.002-0.04 mm plates behind, so the guard must never bite where the uv clip has
    already done the job.

    f148: this slab's half-width (CREST_BAND - 0.5 - CREST_EDGE_CLEAR = 11.0 mm) and the
    lattice's own outer edge (column_bounds at CREST_BAND = 12.0 mm from the seam plane) differ
    by 1.0 mm - measured 0.895 mm at the tightest cell - and clip_window's uv clip sits between
    them at 11.5 mm, 0.395 mm at the tightest from the lattice's edge. The band's top end is a
    rib line (skin_ribs() snaps the nearest rib onto crest_psi_hi), so the slab ends on a rib
    instead of crossing a cell's middle.
    """
    global _CREST
    if _CREST is None:
        lo, hi = crest_psi_range()
        reach = math.hypot(A, B) + 20.0
        # the band in the outlet frame (x radial, y out of the seam plane, z up), then
        # rotated onto every seam that carries a duct, as at_seams() does
        psi_wedge = wedge([(0.0, lo), (reach, lo), (reach, hi), (0.0, hi)], half=HALF + 2)
        # strictly LOOSER than clip_window's uv clip, which is at CREST_BAND + MIN_WEB =
        #   CREST_BAND now that MIN_WEB is 0: a guard cutting at the SAME distance leaves the
        #   cutter with two coincident walls and the boolean leaves 0.002-0.04 mm plates behind
        #   (f085's measurement), so this slab is 0.5 mm narrower on each side.
        slab = cq.Solid.makeBox(reach, 2 * (CREST_BAND - 0.5 - CREST_EDGE_CLEAR), 2 * B + 40,
                                cq.Vector(0.0, -(CREST_BAND - 0.5 - CREST_EDGE_CLEAR), -B - 20))
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
    stem = stem.fuse(cq.Solid.makeCone(STEM_HOLE / 2, stem_flare_r(x_out), x_out - x_in,
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
            + (f" {TAG}" if TAG else ("" if SCALE == 1 else f" x{SCALE:g}")))


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
    design owner set: every boss, peg and hole keeps JOINT_CLEAR from the fan's
    space (the plenum air and the impeller's swept volume), and every hole keeps
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
            # NO "fan housing wall" entry. It used to be the housing wall's whole band
            # (housing_wall_profile()), which reads 0.00 mm for ANY joint fused into that
            # wall - and rhY's corner_bottom (item 3) is exactly that: a peg in the corner
            # where the straight shaft-side wall turns into the fan housing's ceiling. A
            # Ø7 boss fused into a T-thick airtight wall stands 3.5 - T = 2.64 mm past that
            # wall's air-side face by geometry, so no joint fused into the housing wall can
            # keep JOINT_CLEAR from the wall itself. The rule protects the fan's space, and
            # the two entries below carry it: measured (build/f118/jc2.py) the two f087
            # joints that rule removed still fail against them - housing_ceiling (44.0,
            # -67.4) is 0.36 mm from the plenum air, keel (52.5, -97.1) is inside it -
            # while corner_bottom keeps 4.50 mm to the plenum air and 6.00 mm to the
            # impeller's swept volume, and its hole keeps AIR_KEEP to the shaft bore.
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
        wedge([(0, -B), (SHAFT_R + BOSS_INSET, -B), (SHAFT_R + BOSS_INSET, B), (0, B)]))
        # keep the shaft bore clear (BOSS_INSET into the shaft wall's own band, see BOSS_INSET)
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
    brace = servo_brace()                           # f150: the equator rib, fused into the
    if brace is not None:                           # skin and into both walls it runs between
        body = body.fuse(brace)
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
