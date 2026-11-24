# AirShip construction manual

One place for everything learned building the pie-slice hull, so a later edit starts from the
answer instead of re-deriving it. Tasks f072-f151 spent ~2,500 lines of notes and several full
sessions re-reading `CurrentModel/CAD Files/SimplifiedSlice/airship_slice.py`; f147 and f148 lost
their whole budget to re-discovery. Read section 0 first, then only the sections it points to for
your kind of edit.

Keeping this alive is part of every task (AGENTS.md says so): after a change, update the sections
it affects, add one line to section 10 for your task id, and run
`CurrentModel/Analysis/check_construction_notes.py` — it fails if this file cites a generator
name, a constant, a file path or a section line range that no longer holds.

Line numbers are given so you can jump straight to a function; they drift, so trust the name.
The checker prints a warning when a cited line is more than 40 lines off, and fails when a cited
name or path is gone.

Everything below is measured unless it says otherwise, and the task that measured it is named.

## 0 INDEX

- 0 INDEX: 20-51
- 1 FRAMES: 52-125
- 2 GENERATOR MAP: 126-333
- 3 DESIGN RULES: 334-438
- 4 JOINTS: 439-496
- 5 LATTICE AND KEEP-OUTS: 497-574
- 6 DUCTS, BULB, STEM, SERVO, BRACE: 575-647
- 7 BUILD AND CHECK WORKFLOW: 648-755
- 8 FAILURE MODES AND FIXES: 756-788
- 9 rhY's REVIEW HISTORY: 789-809
- 10 LESSONS LOG: 810-981
- 11 CHECKS — CAD, not STL: 982-1020

Read first, by kind of edit:

- **joints / pegs / holes** — 4, then 3 (AIR_KEEP, JOINT_CLEAR, boss sizes), then 8 (floating
  boss, floating peg, hole that cannot fit in a wall).
- **lattice / windows / ribs** — 5, then 3 (MIN_WEB, MIN_KEEP, the >= 50 % rule), then 8
  (plates left in windows, whole cells solid, sliver walls).
- **ducts and the bulb** — 6, then 5 (crest keep-out, duct air keep-out), then 4 (the two bulb
  corners).
- **stem hole, servo hole, outlet** — 6, then 5 (outlet keep-out rings), then 8 (thin wall at a
  hole's rim).
- **servo brace and mounting pad** — 6 (servo_brace, servo_pad), 3 (rule 11: they do not
  scale, and they are now sized by `Analysis/brace_sizing.py` against
  `Analysis/STRUCTURE-ESTIMATES.md`, not guessed), 10 (f150, f151, f152).
- **scale, printer fit, mass** — 1 (what OAS_SCALE does and does not scale), 3 (printer limits),
  7 (how to bisect a scale), 10 (f118, f148).
- **the checker says FAIL / PROBLEM** — 7 (how to read its lines), 8 (symptom -> cause -> fix).

## 1 FRAMES

### 1.1 The model frame

- The hull is the ellipse `A` x `B` revolved about Z, cut into `N` slices of `2 * HALF` degrees.
  **`A` = 207.765 * `SCALE` is the RADIUS semi-axis and `B` = 104.0 * `SCALE` is the half-height.**
  Getting these the other way round makes every depth you print nonsense (f087 hit exactly that).
- z is the ship's vertical axis. The **equator is z = 0** and is a real ring rib: `OUT_Z` = 0.0,
  and `OUT_THRUST_RIB` = `skin_ribs()`.index(0.0) asserts a rib sits there. Thrusters never move
  off the equator (navigation: DESIGN-CONSTRAINTS).
- A point on the skin is (psi, theta): **psi** is the ellipse (meridian) angle, **theta** the
  azimuth. `surface(psi, theta, depth)` gives the point `depth` under the outer face and its
  outward normal; `skin_point(psi, depth)` is the meridian version; `hull_r(z)` is the skin radius.
- `psi_of(p)` is the ellipse angle of a point on the skin's **mid** line: it undoes the T/2 offset
  before taking the angle (3 fixed-point iterations). The plain `atan2(z * A, rho * B)` inverse is
  wrong by 0.26 mm anywhere and by 5 mm near the bellmouth, because the mid line is an *offset*
  curve, not an ellipse (f085). Any "which psi is this point at" code must use `psi_of`.
- `depth_under_skin(p)` measures depth along the skin's own normal. Do not measure it radially.
- The skin's **normal** at psi is tilted off the radial line by `atan((A / B) * tan(psi))`, not by
  psi. At the stem hole's rim that is 13.85 deg, not 7.02 deg. `STEM_RIM_PSI` / `STEM_FLARE`
  encode this; ignoring it is why the stem hole ate the skin on its up-hull side (f117 item 4.1).
- Curvature: the skin's smallest radius of curvature is `B * B / A` = 52 mm at the equator. Any
  straight chord of length c sags `c*c / (8 * 52)`: a 38 mm chord sags 3.5 mm. That single number
  caused the 16 loose plates in the windows (f117) and is why `CUT_MESH` is 3.0 mm.

### 1.2 Seams and the slice's own faces

- One slice spans azimuth -HALF .. +HALF (`HALF` = 180 / `N`; 22.5 deg at N = 8).
- **Pegs are on the +HALF seam, matching holes on the -HALF seam**, so slice k+1 plugs into slice k.
  A joint record is one (r, z) on the seam plane and means "peg here, hole at the same place on
  the neighbour".
- `column(side)` is the prism between the centre rib and the seam rib (side +1 / -1, 0 = both);
  `inset_wedge(inset, r)` is the slice's wedge with both seam planes pushed `inset` inside it, and
  is how a junction window is kept off the seam face (windows() uses `inset_wedge(RIB / 2 + MIN_WEB, ...)`).
- A duct is split in half by a seam plane, so two slices close one duct: `duct_seams()` names the
  seams that carry one. The duct's **crest line is the seam plane itself**, which is why the crest
  band is a plain u-strip in the unrolled-skin frame.

### 1.3 The print STL's orientation (this one is worth getting right once)

`print_pose()` and `make_fcstd.py` both do: rotate +HALF about Z, then 90 deg about X. Result:

- the **-22.5 deg (hole) seam lies flat on the bed**, so the skin never overhangs more than 45 deg
  and every oval's top prints as a small round arch without supports;
- **print x = hull r**, **print y = -hull z**, **print z = across the slice** (height off the bed).

So a seam-view picture is read with x = radius and y = -z, and a joint at (r 177.6, z -12.5)
draws at print (177.6, +12.5). To take a print-frame mesh point back to the model frame:
rotate -90 about X, then -HALF about Z (f117's probes call this to_model()).

### 1.4 Scale: what grows and what does not

`OAS_SCALE` multiplies `A` and `B` (and anything written as `-B + k`, e.g. `FLOOR_Z`,
`HATCH_WALL_TOP`, `LUG_Z`, `DUCT_Z_IN`, `BAND_Z`, `CUT_R`). Everything else keeps its size:

- **grows:** the hull outline, the lattice cells and their row heights, the bellmouth, the seam
  geometry, the keel arc.
- **does not grow:** wall `T` (0.86), rib `RIB`, every joint (peg, hole, boss), the fan housing,
  the shaft, the plenum, the ducts and bulb, the stem and servo holes, the thruster hardware, the
  servo brace `BRACE_W` x `BRACE_D` and the mounting pad (the bracket is one printed part), the
  crest band, the outlet keep-out rings.
- Consequence, and the reason the float budget works: hydrogen volume grows as size^3 while
  printed mass grows about size^1.3 to size^2. **Never scale a printed STL uniformly** — that
  thickens every wall and the ratio never improves.
- Two scale traps measured the hard way:
  - `crest_psi_hi()` = asin((`DUCT_BULB` / 2 + 1.5) / `B`) **shrinks** as the hull grows (0.1691 rad
    at scale 1, 0.1196 at 1.41) while the rib angles do not, so the rib nearest the crest band's
    edge is a different rib at each size. `snap_rib_to_crest()` has a guard for exactly this (f148).
  - Fixed-size hardware against a growing hull moves features into each other: the servo pad's
    far edge stands at az -6.18 deg at scale 1.0 and az -10.93 at 1.41 (the bracket and `SERVO_T`
    do not grow, `hull_r` does) while the lattice's walls keep their azimuths. f151 read that as
    the edge landing beside a rib line; f154 measured it as the pad's own degenerate cap facet
    exposed at one size and buried in the band at the other - see 8 and 10.

## 2 GENERATOR MAP

`CurrentModel/CAD Files/SimplifiedSlice/airship_slice.py`, 2832 lines at f151. Line numbers are
from that file at this commit. Variant switches are environment variables, read once at import:
`OAS_VARIANT` (8T/4T), `OAS_SIDE` (L/R/P), `OAS_SLICES` (8, or 12 for the double-Kobra build),
`OAS_THRUSTER` (L/S), `OAS_PIECES`, `OAS_SCALE`, `OAS_TAG`, `OAS_RIB`.

### 2.1 Constant groups (what each group is for)

- Variant and size: `VARIANT` 51, `SIDE` 52, `FOUR` 53, `N` 54, `LARGE` 55, `PIECES` 56,
  `SCALE` 64, `TAG` 65, `A`/`B` 70, `HALF` 72, `UP` 244.
- Wall and lattice widths: `T` 71, `RIB` 78, `MIN_WEB` 80 (now 0.0), `POLY_CLOSE` 169,
  `MIN_OPEN_AREA` 117, `MIN_KEEP` 119, `CELL_CLOSE` 129, `NOZZLE` 135, `OVAL_N` 240,
  `ROWS_ABOVE_EQ` 239.
- Cutter geometry: `SKIN_MARGIN` 178, `CUT_OUT` 186, `CUT_IN` 194, `CUT_MESH` 199, `RING_WELD` 211,
  `OUT_MESH` 222, `TILE_EDGE` 244 (f154).
- Keep-out standoffs: `CREST_EDGE_CLEAR` 91, `SERVO_WALL` 102, `BRACE_EDGE_CLEAR` 109,
  `BRACE_OUT` 115, `CREST_BAND` 324.
- Servo brace and pad: `BRACE_W` 138, `BRACE_D` 145, `BRACE_IN` 148, `SERVO_BRACKET_L` 153,
  `SERVO_BRACKET_W` 154, `PAD_MARGIN` 156, `PAD_T` 157, `PAD_CORNER` 159, `PAD_EDGE_CLEAR` 160
  (f154), `PAD_RIB_CLEAR` 168 (f154), `PAD_RING_CLEAR` 175.
- Fan housing and shaft: `FLOOR_Z` 74, `INTAKE_R` 76, `EYE_R` 251, `IMP_TIP_R` 252, `SHAFT_R` 257,
  `SHROUD_RC` 258, `NOZZLE_L` 259, `SHROUD_GAP` 260, `HATCH_R` 264, `HATCH_WALL_TOP` 265,
  `LUG_R` 266, `LUG_Z` 267, `LUG_HALF` 268, `POST` 269.
- Joints: `PEG_D`/`HOLE_D` 273, `PEG_L`/`HOLE_L` 274, `CHAMFER` 274, `BOSS_D`/`BOSS_L` 274,
  `BOSS_INSET` 275, `AIR_KEEP` 283, `JOINT_CLEAR` 285, `S_BULB_GROOVE` 673 (kept only as a record
  of what f149 measured; the corners are computed, not parameterised).
- Ducts, outlets: `DUCT_BORE` 292, `DUCT_W` 293, `SKIN_BITE` 297, `SKIN_BURY` 301,
  `DUCT_MOUTH_R` 304, `DUCT_Z_IN` 305, `PLENUM_FLAT_R` 313, `PLENUM_KEEL_R` 314, `PLENUM_RC` 315,
  `PLENUM_RAMP` 316, `DUCT_FLUSH` 317, `STEM_HOLE` 320, `BOSS_LEN` 321, `DUCT_BULB` 322,
  `BOSS_R` 323, `STEM_RIM_PSI` 347, `STEM_FLARE` 348, `SERVO_T` 361, `SERVO_HOLE` 363, `OUT_Z` 652,
  `OUT_THRUST_RIB` 653.
- Pieces (the double-Kobra build): `PRINT_BED` 622, `BAND_Z` 623, `CUT_R` 624, `STUB_L` 625,
  `SOCK` 626.
- `EXCEPTIONS` 371: the only places allowed to be thicker than `T`. The checker measures the thick
  percentage and the biggest thick blobs; every blob must belong to one of these entries. Adding a
  feature that is thicker than T means adding an entry, and rhY has to agree.
- Module caches: `_BAND` 1224, `_CREST` 2469.

### 2.2 Functions: what each builds and who calls it

Geometry plumbing:

- `wedge` 406 — revolve a closed (r, z) polygon over the slice's angle. build(), pieces().
- `arc` 413 — exact ellipse arc in XZ. frame(), duct_solids(), housing profiles.
- `wedge_edges` 421 / `parts_to_edges` 429 — revolve a profile of exact edges. frame(),
  duct_solids(), crest_keepout(), outlet_keepout().
- `ellipse` 451, `hull_r` 457, `skin_point` 461, `psi_of` 468, `depth_under_skin` 485 — the skin
  and its inverse maps. Everything.
- `column` 501, `seam_axis` 517, `inset_wedge` 1912, `min_radius` 1923 — the slice's own prisms.
  windows(), clip_window().
- `keel_edge_z` 524, `ellipse_arc` 530, `equal_arcs` 537 — row layout. skin_ribs(), oval_on_skin().
- `surface` 1169, `ds_dpsi` 1177 — the (psi, theta) surface and its metric. skin_frame(),
  skin_cutter(), _uv_disc().

Skin ribs and the lattice band:

- `crest_psi_hi` 548 — the ellipse angle the crest band ends at. skin_ribs(), crest_psi_range().
- `snap_rib_to_crest` 556 — f148: move the rib nearest the band's top edge onto that edge (never
  add one; merge a row the move makes too short; refuse the move if the only mergeable neighbour
  is the equator rib). skin_ribs().
- `skin_ribs` 599 — the ring ribs' psi values, bottom to top; one sits exactly at 0.0 (the equator).
  windows(), lattice_band(), OUT_THRUST_RIB.
- `cut_ribs` 629 — the ribs the pieces are cut along (OAS_PIECES). pieces().
- `lattice_band` 1641 — where the lattice-bearing skin actually is (first ring rib outside the
  housing wall to the bellmouth). clip_window(), crest_psi_range().
- `crest_half` 1181 — how far in from the seam plane the solid skin over a duct reaches at psi
  (a step: `CREST_BAND` inside `crest_psi_range()`, 0 above). column_bounds().
- `column_bounds` 1189 — one column's edge azimuths. windows(), oval_on_skin().
- `oval_on_skin` 1202 — the oval of a cell, laid out on the curved skin so it touches all four rib
  lines. windows().
- `junction` 1859 — the hollow window where four ovals meet, clipped to the two rows it sits in
  (`rows=` argument, f151). windows().
- `clip_window` 1651 — the one place a window polygon is decided: band ends, seam planes, column
  edge, the cell's two rows, the crest band, the outlet rings and the brace corridor, then the
  printability gates (`MIN_OPEN_AREA`, the `NOZZLE` erosion). Returns None when nothing printable
  is left. windows().
- `windows` 1930 — the whole lattice: builds every oval and junction, turns each into a solid
  cutter, then applies the 3D keep-out guards. build().

Cutters (the boolean that makes the windows):

- `ear_clip` 1227 — triangulate a simple polygon (index triples). skin_cutter()'s caps.
- `clean_ring` 1287 — drop repeated/collinear ring points (a box clip leaves them; ear_clip's
  fallback then returns a zero-area triangle and the shell will not close). skin_cutter().
- `resample_ring` 1315 — spread a ring's vertices to `OUT_MESH` steps. skin_cutter().
- `skin_cutter` 1377 — ONE filled solid from an outline on the skin: the window's area is tiled
  into `CUT_MESH` cells, each a small prism along the skin's normal at that point, stitched into a
  single shell with shared edges. This is what fixed the plates left in windows (f117) and it also
  builds the servo brace. Its interior tile grid lines are nudged off the outline's own vertices by
  `TILE_EDGE` (f154) so no cell ring starts with a 0.04 mm edge. windows(), servo_brace(),
  servo_pad().
- `lattice_outlines` 1986 — every window outline `windows()` laid out, as skin points, from the
  `_WIN_OUTLINES` cache.
- `outline_rib_clear` 1998 — f154's rule: the smallest distance between a fused feature's own
  outline and a lattice window wall running parallel to it (a wall the outline crosses at a steep
  angle is not a violation). servo_pad() places its far edge with it.
- `skin_frame` 1586 — the uv <-> skin map for one window: `to_uv` is the exact analytic inverse of
  `to_skin`. clip_window(), junction(), _uv_disc().

Fan housing, shaft, keel:

- `intake` 637 — the bellmouth (centre, radius) where the skin rolls into the shaft.
  frame(), corner_joints().
- `frame` 1030 — the slice's solid before the lattice: the hull wedge minus the shaft bore, plus
  the housing, keel, hatch ring, lugs and post. build().
- `tube_top` 1053, `socket` 1057, `tube_segments` 1067, `nozzle_top` 1085 — the OAS_PIECES intake
  tubes and their sockets. pieces().
- `shroud_curve` 1089 — the housing's air-side surface, (r, z). housing_space(), plenum_ceiling(),
  the joint-map profiles.
- `housing_space` 1115, `housing_outline` 1129, `plenum_ceiling` 1140 — the plenum air, its
  footprint, its wall. frame(), outlet checks.
- `hatch_ring` 1152, `hatch_hole` 1164 — the bayonet ring, lug and stop post; the keel opening.
  frame(), build().

Ducts, outlets, brace:

- `duct_at` 681 — point s along the duct centreline and its outward normal. joints() history,
  duct_path() consumers.
- `duct_path` 2368 — the centreline in the seam plane, mouth to end. duct_solids(),
  duct_envelope(), duct_bore_profile().
- `duct_bulb_centre` 2382 — the bulb's centre (it lies IN the seam plane). bulb corners, keep-outs.
- `circle_profile` 2390 — a closed (r, z) circle polygon. duct_solids(), keep-outs.
- `duct_envelope` 2397 — the duct's swept envelope at `off` from the centreline, bulb included.
  duct_air_keepout(), crest guards. One construction, several offsets.
- `duct_solids` 2421 — (walls, bore) of one full duct in the outlet frame; the walls are trimmed
  `SKIN_TRIM` (0.3) under the outer skin because the skin IS the duct's outer wall. build(),
  crest_keepout().
- `crest_psi_range` 2472 — the psi range the crest band runs over. crest_half(), crest_keepout().
- `crest_keepout` 2484 — the crest band as a solid guard, strictly looser than clip_window()'s uv
  clip. windows().
- `duct_air_keepout` 2525 — the duct's air path grown `MIN_WEB`. windows().
- `stem_flare_r` 2023 — the stem hole's own radius along its axis (the flare cone). stem_keep_r(),
  stem_and_servo_holes() — so the hole and the ring that guards it cannot drift apart.
- `stem_keep_r` 2032, `servo_keep_r` 2042, `outlet_axes` 2046, `_axis_line` 2059 — the outlet
  keep-out rings, sized to the hardware (stem 14.6 mm, servo 5.0 mm at bench).
  clip_window(), outlet_keepout(), servo_brace(), servo_pad().
- `outlet_keepout` 2067 — those rings as solids, each 0.5 mm + a tilt term looser than the uv disc.
  windows().
- `_uv_disc` 2110 — an outlet ring traced into the unrolled-skin uv frame (64 rays, bisecting the
  exact 3D distance to the axis). clip_window().
- `psi_at_arc` 2155 — the psi whose arc distance from the equator is w mm. brace_span().
- `brace_span` 2167 — the azimuths the servo brace runs between. servo_brace().
- `servo_brace` 2192 — the equator beam, `BRACE_W` x `BRACE_D`, from the servo end to the far
  stem keep-out ring. build().
- `servo_pad` 2259 — the solid pad under the bracket's footprint, `PAD_T` counting the band. build().
- `stem_and_servo_holes` 2536 — the flared stem hole and the servo spline hole, in the OUTLET frame
  (stem on +x, servo at y = `SERVO_T`): comparing them to slice-frame shapes without rotating is a
  probe bug f150 hit. build().
- `at_seams` 2624 — an outlet-frame shape placed on this slice's duct seams and clipped to the
  slice. build(), crest_keepout(), outlet_keepout().
- `duct_seams` 2555, `slice_sides` 2562, `has_servo` 2571 — which seams carry a duct, which slice
  type sits where, whether this slice carries the servo.

Joints:

- `joint` 656 — one peg/hole record: (r, z), the wall faces its boss fuses into, why.
  joints(), bulb_joints(), corner_joints(), joint_map().
- `duct_wall_r` 711, `bulb_wall_r` 716 — the tube wall's own face and the dome wall's own face
  (the two surfaces a bulb corner is made of). bulb corners, joint_parts().
- `seam_off` 721, `seam_air` 736 — distance to the duct centreline / wall to the duct's air in the
  seam plane. bulb_boss_centre().
- `band_tube` 744, `band_dome` 751, `band_skin` 758 — signed distance to each of the three wall
  bands a bulb boss may bite. bulb_boss_centre().
- `stem_slot_wall` 765 — wall to the flared stem slot (and only where the slot exists: it starts at
  `hull_r(OUT_Z) - BOSS_LEN - 2`, it is not a disc about the axis). bulb_boss_centre().
- `bulb_inner_corner` 779 — the tube wall's face crossing the dome wall's face (walk + bisect).
  bulb_joints().
- `bulb_outer_corner` 807 — the dome wall's face crossing the skin band's inner face. bulb_joints().
- `bulb_boss_centre` 829 — the point near an apex that bites deepest into BOTH walls subject to
  `AIR_KEEP`, the stem slot and `RIM_KEEP` (0.40 mm under the outer face). bulb_joints().
- `bulb_joints` 867 — the two bulb joints. joints().
- `joints` 890 — the peg/hole pairs on a seam (the two bulb ones plus the two shaft ones).
  joint_parts(), joint_map().
- `corner_joints` 978 — the two ends of the straight shaft-side wall. joints().
- `joint_parts` 2314 — bosses (fused), holes (cut), pegs (fused) on both seams, plus any sleeve.
  build().
- `cut_joints` 2575 — a peg across each piece cut. build() (OAS_PIECES), pieces().
- `joint_map` 2700 — the .joints.json the checker's `--joints` measures, with the keep-clear
  profiles built from the same code as the part: `housing_wall_profile` 2644,
  `plenum_air_profile` 2658, `impeller_sweep_profile` 2666, `duct_bore_profile` 2679.

Pieces, pose, output:

- `pieces` 2589 — cut a slice into printable pieces along `cut_ribs()`. __main__.
- `print_pose` 2619 — lay a slice or piece on its -HALF seam. pieces(), make_fcstd.py.
- `slice_name` 2636 — the file name for this variant/scale/TAG. __main__, make_fcstd.py.
- `build` 2747 — the whole order of operations (see 2.3). __main__.

### 2.3 build()'s order, which is not arbitrary

1. `envelope` = the hull wedge minus the shaft bore (kept clear by `BOSS_INSET`).
2. `frame()` — the solid slice: hull, shaft wall, housing, keel, hatch ring, lugs.
3. `windows()` — every lattice cutter, cut **one at a time** (a compound of overlapping cutters
   lets the kernel cut one against another and leave slivers). A cut that moves the body by less
   than 0.5 mm3 is retried as a fuzzy boolean (`tol=1e-4`) and only then raises: a clipped
   window's own faces can sit on a tangent the plain boolean will not resolve (f151 at scale 1.41:
   plain -0.006 mm3, fuzzy 629.1 mm3, which is the whole band under it).
4. Fuse the joint bosses and sleeves, intersected with the envelope.
5. Fuse `servo_brace()` then `servo_pad()`, **one after the other**: they overlap by 117 mm3 and
   fusing them as one compound breaks the body (45,679 mm3 in 2 solids, 307 faces instead of
   8,399 — f151's fuse probe).
6. Fuse the duct walls, then cut the bore, then cut the stem hole (so the brace's tip ends buried
   in the solid band round the bearing boss), then the servo hole.
7. Cut the holes, fuse the pegs, cut the hatch hole, then clean().
8. Keep only solids with volume > 1e-3 mm3 (a boolean can leave a degenerate zero-volume shell in
   the compound, and it inflates every number read off the shape).

## 3 DESIGN RULES

Each rule says what, why, and who set it. rhY's words are quoted with the date. These are not
preferences: DESIGN-CONSTRAINTS.md says not to trade any of them away for weight or print time
without asking.

1. **One wall, `T` = 0.86 mm, everywhere.** Exactly 2 perimeters of 0.45 mm lines at 0.2 mm
   layers — the thinnest that prints airtight. Nothing structural is thinner. Skin, duct, shaft,
   floor, keel, hatch ring, housing and rib faces are all `T`.
   rhY 2026-11-16 (f082): "I'm noticing extra weight on the lower side of the duct. It should be
   one uniform thickness across the entire design."
   Only what `EXCEPTIONS` names may be thicker: peg/hole bosses and their sleeve, the stem bearing
   sleeve, the rib width `RIB`, the hatch bayonet lug and post, the solid crest band, and the servo
   pad plus brace. The old entry "two T walls lie on each other" (DUCT_FUSE) was deleted by f087.
2. **The duct uses the hull skin as its outer wall.** One shared wall of thickness `T`, not a duct
   wall stacked on the skin: the bore's outer surface sits `SKIN_BITE` (0.02) inside the band and
   the walls' own outer boundary is buried `SKIN_BURY` (0.04) under the outer face, so the fuse
   adds nothing on the duct's outer side. Measured 0.84-0.96 mm at five points along the duct on
   both seams (f117). rhY 2026-11-17 (f087 item 1): the double wall was one of four marked problems.
   Consequence: **no lattice window may be cut over a duct** — a window there is a hole in the air
   path. That is the crest band.
3. **Solid crest band along each duct's crest, half-width `CREST_BAND` = `DUCT_BORE` / 2** (12 mm
   at bench), over the duct's run (`crest_psi_range()`). It is the normal T wall with no windows,
   so it adds no material. rhY approved it 2026-11-17 (f086) after f085 measured that no cut floor
   inside the band, at the wall's face, or below it measures printable (0.108-0.314, 0.049,
   0.061 mm).
4. **Air paths stay airtight.** The shaft is solid, smooth and empty over its whole height; the
   plenum and the ducts are airtight; the keel is solid only round the fan housing. Every hole
   keeps `AIR_KEEP` = 0.6 mm of wall toward any air side. rhY set it 2026-11-16 (f082 item e).
   `Analysis/check_outputs.py` `--joints` measures it.
5. **Every joint keeps `JOINT_CLEAR` = 1.0 mm from the fan's space** — the plenum air and the
   impeller's swept volume (not the housing wall itself: a boss fused into that wall stands
   3.5 - T = 2.64 mm past its air-side face by geometry, so the "fan housing wall" keep-clear
   entry was removed with the reason recorded in `joint_map()`). rhY 2026-11-16 (f082 item c):
   "that peg will interfere with the fan housing."
6. **A joint sits where two walls actually meet and is fused into BOTH of them.** rhY 2026-11-16
   (f082 items c, d): "the peg above it should be moved to connect to two walls of the geometry";
   "The upper boss should also be in the corner connected to the top and internal duct one".
   A boss standing over an open window prints as a loose peg; a hole that has no wall to sit in
   cannot exist at all (f117 deleted the duct-top joint for that reason — see 4).
7. **Peg and hole sizes are fixed:** peg Ø3.0 x 3.6, hole Ø3.3 x 4.2 (0.15 mm clearance per side
   for FDM), 0.4 mm chamfer on the peg tip and hole mouth (it also eats elephant foot), boss Ø7 x 5.
   Change them only with a reason: they are what the two slices register on.
8. **The lattice runs right out to the edges; only the partial cells an edge cuts stay filled.**
   rhY 2026-11-17 (f118 item 4): "lattice windows must run right out to the edges; ONLY the
   partial cells the edge cuts (the half diamonds along an edge) stay filled, for strength. Every
   full cell is an open window." That is why `MIN_WEB` is 0.0. Solid skin stays only where it must:
   the duct's air walls, the crest band, the outlet rings sized to the hardware, the joint bosses,
   the stem bearing.
9. **A cell a keep-out trims is cut clipped, not dropped** (f151, rhY 2026-11-18: the middle of the
   slice was "an hourglass of solid skin"). The lattice's own bounds clip a cell; the keep-outs bite
   it; a cell that keeps >= `MIN_KEEP` (0.50) of **its own area inside those bounds** is cut as
   cell-minus-keep-outs with corners rounded to `CELL_CLOSE`; below that it stays solid, and
   anything under `MIN_OPEN_AREA` (20 mm2) is a crescent, not a window. Bench slice: 36 windows
   before, 58 after.
10. **No cut boundary may land on a face the part already has.** This is the single most important
    printing rule and it is what every standoff constant exists for: `CREST_EDGE_CLEAR` 0.5,
    `BRACE_EDGE_CLEAR` 0.5, `PAD_RING_CLEAR` 0.6, `SERVO_WALL` 1.0, `BOSS_INSET` T/2, the guard
    solids being strictly looser than the uv clip that made them, `SKIN_TRIM` 0.3 instead of T,
    `OUT_MESH` 1.0, `CUT_OUT` 0.6 clear of the outer face. Coincident or near-coincident faces give
    0.005-0.05 mm sliver walls, self-intersecting meshes, and invalid solids. f147's rule for the
    whole generator: **no new cut boundary within 0.05 mm of an existing face.**
11. **Weight versus strength is a trade rhY makes explicitly.** 2026-11-18 (f152): "Lighter is
    better but we need it to be structurally solid. These are competing requests, and we will have
    to make trade offs. Until one is built for actual physical testing and flight, we are going to
    have to do some educated guesses." f151's brace and pad sizes were a sturdy first guess;
    **f152 replaced them with an estimate**: every load is listed with its source tagged
    [measured] / [datasheet] / [guess] in `CurrentModel/Analysis/STRUCTURE-ESTIMATES.md`, the
    arithmetic is `CurrentModel/Analysis/brace_sizing.py`, and `SAFETY_FACTOR` = 3 [guess] now
    sits in the generator next to `BRACE_W`, `BRACE_D` and `PAD_T` so nobody re-sizes them
    without meeting the factor that sized them. Until a part is tested, quote the low end of
    any material property (PLA across the layers: 20 MPa, not the 35-50 along them) and say
    which numbers are guesses. What the estimate found: the brace had its material in the
    wrong direction - the servo's stall torque is about the RADIAL axis, so it is `BRACE_W`
    squared that carries it - and the pad's limit is the PLA under the bond, not the bond
    (SF ~ 400 in shear).
12. **Printers.** Bench: Prusa MK3S+ (0.4 mm nozzle, 0.2 mm layers, 0.45 lines) — the numbers
    `T` and `RIB` are derived from these. Anycubic Kobra Max 400 x 400 x 450 (`PRINT_BED` is that
    less a margin). Creality CR-10 Smart Pro 300 x 300 x 400, and rhY's fit rule from 2026-11-16
    (f080) and again in f118 item 5: **leave 5 mm on every side, so the part must fit
    290 x 290 x 390.** `BEDS` in `CurrentModel/Analysis/check_outputs.py` carries all three and
    the checker prints which beds the part fits.
13. **Do not re-read the generator to find out how it works.** This file is the index; the generator
    is 2,832 lines and re-reading it cost f147 and f148 their entire budgets. Read section 0, then
    the sections it points at, then open only the named functions at the named lines.
14. **Nothing in the model may break the outer ellipsoid** except the window holes, the round stem
    and servo holes, and the four joint pegs (which stick out into the neighbouring slice). Boss
    rims stay under the outer face (`RIM_KEEP` 0.40 mm), the brace starts `BRACE_OUT` 0.3 mm under
    it, the duct walls are buried `SKIN_BURY` under it.
15. **The float problem is decided by the envelope, not by how thin the lattice is.** f155 sized
    three concepts up to the size where each floats with +150 g and +250 g of margin on rhY's
    CR-10 Pro bed - today's lattice skin re-pieced for that bed, a semi-rigid frame (meridian
    battens + latitude rings) with a film envelope, and a pressure envelope with no printed skin
    at all - in `CurrentModel/Analysis/FLOAT-DESIGN-STUDY.md`, arithmetic in
    `CurrentModel/Analysis/float_design_study.py`. The lattice needs 1.67 m of hull and 256
    printed pieces for +250 g; the batten frame needs 2.21 m and ~426 print hours, because
    battens deep enough not to Euler-buckle under the film's Laplace load come to 1.7 kg; the
    pressure envelope needs 1.63 m, 47 parts and ~89 h. So do not answer "it is too heavy" by
    thinning the lattice: the skin is exactly the part that never stops paying (lift ~ a^3,
    printed skin ~ a^0.8-1.0 measured, FLOAT.md). If a later task goes the film route, what is
    left printed is the keel tube, the fan housing, the thruster ducts (tapered: 2T at the root,
    because a duct is a 0.7 m cantilever - an `EXCEPTIONS` entry with this reason) and one duct
    support ring, and the load path runs through a bonded film-to-keel band that no wall-map
    checker can see. Rule 1 still holds for every printed member.

## 4 JOINTS

Four per slice at f151, each a Ø7 x 5 boss carrying a Ø3 x 3.6 peg on the +HALF seam and a
Ø3.3 x 4.2 hole on the -HALF seam. `joints()` returns the records; `joint_parts()` builds them;
`joint_map()` writes them to `CurrentModel/CAD Files/SimplifiedSlice/airship pie slice 1026.joints.json`
for the checker. Bench (r, z) and in brackets the CR-10 Pro x1.41 value:

- `corner_top` (35.25, 89.46 / 132.86) — the intake shaft's wall and the bellmouth where it rolls
  into the hull skin. r is `SHAFT_R + HOLE_D / 2 + AIR_KEEP`: the hole keeps exactly `AIR_KEEP` to
  the shaft bore, which is what puts the boss as close to the corner as the rules allow.
- `corner_bottom` (35.25, -63.30 / -105.94) — the shaft's wall and the fan housing's ceiling, at
  `FLOOR_Z + SHROUD_RC`, the smooth ~90 deg corner. Boss 4.5 mm from the plenum air, 6.0 mm from
  the impeller's swept volume.
- `bulb_groove` (177.58, -12.46 / 263.72, -13.40) — the INNER corner of the bulb: the tube wall's
  own face (`duct_wall_r`) crossing the dome wall's own face (`bulb_wall_r`). Bites 2.04 mm into
  each wall at both scales; hole 0.61 mm from the air.
- `bulb_outer` (201.49, 15.70 / 287.21, 16.40) — the OUTER corner: the dome wall against the duct's
  outer side, which is the hull skin itself. 0.46 mm of bite into each wall, 1.27 mm to the air,
  1.35 mm to the stem slot, rim 0.4 mm under the outer face.

How a bulb joint is placed (this is the part to copy for any new corner):

1. Find the corner as the **intersection of the two wall faces** (`bulb_inner_corner()`,
   `bulb_outer_corner()`), never as a fraction of the way along the duct. A corner is a property of
   two surfaces; an arc fraction is not, and the bulb does not grow with the hull. f149 measured
   the old `duct_at(S_BULB_GROOVE)` point: it bit 2.05 mm into the tube wall and **0.00 mm** into
   the dome wall at bench size, and sat **11.8 mm clear** of the dome wall at 1.41.
2. `bulb_boss_centre()` then picks the point near the apex that bites deepest into **both** walls,
   subject to: `AIR_KEEP` 0.6 mm of wall from the hole to the duct's air (`seam_air`), 0.6 mm to the
   flared stem slot (`stem_slot_wall`, and only where the slot exists), and the boss rim
   `RIM_KEEP` 0.40 mm under the outer skin.
3. Two facts about the outer corner that cost a whole attempt (f149): the dome's outer wall **does
   not exist below the equator** (the tube's end sphere is internally tangent to the bulb's bore, so
   the 16-16.8 mm shell is inside the air there), and the corner's apex is **inside the Ø25.4 stem
   slot**, which `build()` cuts after the bosses are fused — so a boss standing at the apex is cut
   away and its peg is left loose in the air. Stand on the same two wall faces, out of the slot.

What went wrong before, so it is not repeated:

- f082: pegs floated in the lattice; the housing-ceiling peg sat over the impeller blade tips
  (0.36 mm from the plenum air); the "central" peg was a quarter of the way along, not midway.
- f087: both duct pegs were on the duct's interior wall 12.86 mm from the crest, and the sleeve
  grew through the duct's outer wall 2.2 mm into the Ø24 bore — a bump on the air side, while the
  hole it protected sat in a wall only 0.86 mm thick and punched clean through it.
- f117: seam_mid was the midpoint of the straight chord between two skin points, i.e. 61.6 mm
  inside the hull in open lattice, so both bosses floated; corner_bulb_root stood at a corner
  whose material was inside the bulb's air, so only its peg survived, loose.
- f117 deleted the **duct-top joint** outright: a Ø3.3 hole with 0.6 mm of wall cannot exist in the
  shared 0.86 mm crest wall, and the sleeve that would make it thick would have to stand outside
  the outer skin, which rhY forbids. If a joint seems impossible, check whether a wall exists there
  at all before moving it.
- f118: rhY removed seam_mid and corner_duct_top ("out in the middle of the hull") and asked
  for `corner_bottom`; that made exactly 3 joints. f149 added `bulb_outer` back at the other bulb
  corner: "Missing peg, other peg not in the corner touching two sides." — 4 joints today.
- f118 also found that a boss clipped exactly at the shaft bore's face gets a flat face coincident
  with the shaft wall's inner face, and the fuse leaves a sliver there: hence `BOSS_INSET` = T/2,
  which stops the clip half a wall inside the band so that face lands in material.

## 5 LATTICE AND KEEP-OUTS

Layout: two columns of ovals per row, split by a centre rib, rows from the first ring rib outside
the housing wall to the bellmouth (`lattice_band()`). Every row is the same length along the skin
(`equal_arcs`), so all cells have the same proportions top and bottom. `ROWS_ABOVE_EQ` = 6 rows
above the equator. The ovals are laid out on the real curved skin (`oval_on_skin`) so each fills
its cell, touching all four rib lines; every junction where ovals meet is a hollow window
(`junction`) that takes all the skin more than `RIB` from the ovals. What is left is a web of
`RIB`-wide ribs and nothing thicker.

- **A rib snapped to the crest band's edge (f148).** `snap_rib_to_crest()` moves the rib nearest
  `crest_psi_hi()` onto it. Without it a row straddles the band's step: `oval_on_skin()` takes one
  bound per cell from the cell's MID psi, so such a cell is "in the band" by its middle and out by
  its top rib, and its outer edge lands 0.005 mm from the crest clip (0.116 mm *inside* it at the
  keel rows) — coincident cut boundaries, 0.025-0.044 mm sliver walls and a self-intersecting mesh.
  Rules: never add a rib; merge a row the move makes shorter than half the nominal row height; and
  **do not move the rib at all** if the only mergeable neighbour is the equator rib, which carries
  the thrusters. At 1.41 the band's edge is closer to the equator rib than to the next one, so the
  snap does not happen there and the straddling cell stays filled as a partial cell.
- **The band's cut boundaries stand inside their own half-width** (`CREST_EDGE_CLEAR` 0.5):
  `clip_window()`'s uv clip at `CREST_BAND + MIN_WEB - CREST_EDGE_CLEAR`, `crest_keepout()`'s slab
  at `CREST_BAND - 0.5 - CREST_EDGE_CLEAR`. The lattice's outer edge stays where f117 put it
  (`column_bounds` at `crest_half` = `CREST_BAND`). Moving the lattice edge outward instead was
  tried first and is wrong: it changed where the lattice stops, grew a junction window at the keel
  rib that cuts nothing in the body, and tripped build()'s "window cut had no effect" guard at 1.41.
- **Guard solids are always strictly looser than the uv clip that made the tool** — `crest_keepout`,
  `duct_air_keepout`, `outlet_keepout`. Two coincident cutter walls left 0.002-0.04 mm plates (f085).
  `outlet_keepout()`'s margin is `0.5 + (T/2 + 1.16) * tan(atan(off / hull_r))`: 0.5 mm at a stem
  ring (off = 0) and 0.78 mm at the servo ring, because the ring is drawn on the skin's MID surface
  while a cutter's caps sit 0.6 mm above the outer face and 1.16 mm below the inner one, and the
  skin's normal at the servo hole is tilted atan(36 / 207.765) = 9.9 deg off the ring's axis, so the
  cutter's edge swings 0.28 mm in radius. A flat 0.5 mm margin is inside that (f150).
- **Outlet keep-outs are the size of the hardware, and they CLIP** (f150): the stem ring is
  `stem_keep_r()` = max(`BOSS_R`, the flare's own radius at the outer face) + `AIR_KEEP` = 14.6 mm
  (was 15.5), the servo ring `SERVO_HOLE / 2 + SERVO_WALL` = 5.0 mm (was 7.5), and each is only as
  long as the sleeve's own footprint, not 60 mm. A cell a ring grazes is a clipped window, not a
  solid patch: the three full cells those rings used to leave solid are what rhY marked on the
  CR-10 Pro print.
- **The >= 50 % rule (f151)** — see rule 9 in section 3. The denominator is the cell's own area
  inside the lattice's bounds, never the raw polygon: the crest band takes 66-70 % of the raw
  polygon of a seam junction, so no test against the raw polygon could ever have opened them, and
  against their own area they keep 84-100 %.
- **A junction's polygon is not its cell.** Along a seam the skin more than `RIB` from the ovals
  runs the whole height of the hull, so a junction on a seam rib reaches into the rows above and
  below (the equator one spanned psi -33..+33 deg, 10,207 mm2 raw). `junction(..., rows)` clips
  every junction to the two rows it sits in; without it opening the seam cells would have cut the
  horizontal ribs out.
- **Chord sag and cutter caps (f117).** A cutter's caps must follow the skin: `CUT_MESH` 3.0 tiles
  the window's area into cells so the worst chord is the cell diagonal 4.24 mm (sag 0.043 mm).
  One `ear_clip` triangulation of a whole 48-point outline spans 32-38 mm chords and sags 3.6 mm,
  so the cut never reaches the middle of its own window: 16 loose curved plates in the windows and
  most of the sub-layer facets. `CUT_OUT` = T/2 + 0.6 puts the top cap 0.6 mm clear of the outer
  face (measuring 0.5 from the outer face left it 0.07 mm clear and the faceted cap sagged through).
  `CUT_IN` = T + `SKIN_MARGIN` (0.30) is the floor: at `SKIN_MARGIN` 0.02 the floor sat 0.02 mm off
  the band's inner face and the boolean left 0.005-0.1 mm membranes behind it.
- **The tile grid must not clip a cell ring at an outline vertex (f154).** `skin_cutter()`'s caps
  are ear-clipped from each tile cell's ring, and a grid line passing within a hair of one of the
  outline's own vertices leaves a cell ring whose first edge is 0.04-0.16 mm long. The cap triangle
  on it is degenerate - 0.027-0.055 mm2 with all three vertices at one cap depth - and its normal is
  the noise of three near-collinear points, so the checker's ray along it reads 0.033 mm to the wall
  beside it. `TILE_EDGE` 0.5 keeps the interior grid lines off the outline's vertices; the cells
  still tile the outline exactly, so the cut does not move. Measured on the servo pad's own tool at
  both print sizes before the fix: 12 cell edges under 0.16 mm (`build/f154/tileprobe.py`).
- **The outline, not the cell grid, sets where walls are** (`OUT_MESH` 1.0): a box clip leaves pairs
  of outline vertices a few hundredths of a mm apart and each pair becomes a wall face that thin
  (~1,600 of them), which the checker's ray reads as a 0.005 mm wall. `RING_WELD` 1e-3 was tried
  and is NOT safe: the two cells sharing such a point do not always weld it the same way, the shell
  then has a hole, and a cutter refuses to build.
- **The uv frame must be one map** (f085): `skin_frame()`'s `to_uv` is the exact analytic inverse of
  `to_skin`. Laying a polygon out on the tangent plane and putting it back with the unrolled map
  disagreed by up to a millimetre at the seams, keel and bellmouth, so parts of one cut boundary
  arrived at the same place in 3D: 553 face pairs 0.002-0.4 mm apart.
- **The brace corridor** (f150/f151, sized by f152): windows stand `max(RIB, BRACE_W) / 2 + BRACE_EDGE_CLEAR`
  = 5.0 mm of arc off the equator over the brace's span (3.5 mm at f151's 6.0 mm brace), and the corridor is pushed out to the
  cell's own edge when that edge falls within `BRACE_EDGE_CLEAR` of it — a fixed 1.5 mm corridor
  landed 0.1 mm off an oval's own edge and left a 0.1 mm notch, the exact thing the partial-cell
  rule exists to prevent.

## 6 DUCTS, BULB, STEM, SERVO, BRACE

- **Duct:** one per duct seam, split in half by the seam plane, running at constant depth inside
  the skin from its mouth in the plenum (`DUCT_MOUTH_R` 60, just outside the impeller tips) to a
  closed end at the equator. Bore Ø24 (Ø34 on 4T), wall `DUCT_W` = T on the **inner** side only,
  bulb Ø32 (Ø44 on 4T) so the stem's flange fits. The centreline depth is
  `T + DUCT_BORE / 2 - SKIN_BITE`, so the bore's outer surface is 0.84 mm under the outer skin
  everywhere and the skin is the duct's outer wall. The ducts never get smaller; only their walls
  are thinned, to the printable minimum.
- **Duct walls are trimmed `SKIN_TRIM` = 0.3 mm under the outer skin** (f148). Ending them
  `SKIN_BURY` 0.04 mm under the skin left their outer boundary parallel to the skin for the duct's
  whole run and the fuse left 0.01-0.33 mm2 sliver faces 0.002-0.07 mm under the keel skin.
  Trimming to the skin's inner face (= T) instead puts the new face exactly ON a surface that is
  already there and gives 0.005-0.009 mm walls: the trim must land inside the skin's own material.
- **Bulb:** the duct's end swells; its centre lies in the seam plane, so its two spheres (air
  `DUCT_BULB` / 2, wall face + `DUCT_W`) are concentric about a point on the seam face. That is
  where the checker's grazing readings come from (section 8).
- **Stem hole:** Ø25.4 (Ø34.4 on 4T) bored along the equatorial radial line on the seam, flared by
  `STEM_FLARE` + 1.5 deg over the skin band so the hole's wall is parallel to the skin's normal at
  the rim; the narrowest point is still `STEM_HOLE`, so the stem and its bearing sleeve fit
  unchanged. Behind it, the bearing sleeve `BOSS_R` (= `STEM_HOLE` / 2 + 1.3) x `BOSS_LEN` 12 is an
  EXCEPTION and is hollow down its axis.
- **Servo:** the MG90S hangs on a separate glued mount, `servo_mount.stl` (42.3 x 24.2 x 16 mm,
  4.3 cm3) epoxied to the INSIDE of the skin centred on the Ø8 spline hole, which sits `SERVO_T`
  (36 mm bench, 44 mm large) along the tangent from the seam, on the equator. There is no servo
  boss in the slice: the only material there is the pad.
- **Servo brace** (`servo_brace`, `brace_span`): the equator beam from the servo end to the **far
  stem keep-out ring**, `BRACE_W` 9.0 mm along the hull x `BRACE_D` 2.5 mm deep from the outer
  skin = 22.5 mm2 of section, starting `BRACE_OUT` 0.3 mm under the outer face. 107 mm of arc at
  bench, 174 mm at CR-10 Pro, because the hardware does not scale. **f152 sized it** (rule 11,
  `Analysis/STRUCTURE-ESTIMATES.md`, `Analysis/brace_sizing.py`): the load that matters is the
  servo's stall torque (SG90 1.8 / MG90S 2.2 kg-cm [datasheet]) taken as a single-failure bound -
  the bracket's epoxy bond lets go and the brace alone holds the servo at full stall - and that
  torque is about the **radial** axis (the spline is radial), so the section carries it with
  `Z = BRACE_D * BRACE_W^2 / 6`: 33.8 mm3 and SF 3.13 at 9.0 x 2.5, against 18.0 mm3 and SF 1.67
  at f151's 6.0 x 3.0. It is the same amount of material turned the way the load wants it:
  +0.43 g a slice measured at bench (+0.53 g estimated), +1.0 g at CR-10 Pro. `BRACE_D` sits at its floor, not at its load -
  2.5 mm is the band plus ~4 extruded lines, and f150's 1.72 mm rib (band + 2 lines) is what rhY
  rejected - and the equator's buckling margin goes 9.1 -> 26.6 with the brace against a crash
  load 20x under the critical stress. It must end buried in the uncut solid
  band: ending it at `CREST_BAND` (12 mm of arc) put its tip inside the stem hole's flare (13.93 mm
  at the outer face) and build()'s stem-hole cut sliced the tip into a sliver standing inside the
  hole's swept volume. Clearances measured before building: 3.75 mm to the duct's air (rule 0.6),
  19.5 mm to the nearest joint.
  A note for whoever re-shapes it: `skin_cutter()` offsets its rings along the surface **normal**,
  which fans out over psi — harmless for a window, wrong for a rib 1.42 mm deep and 2 mm wide,
  whose end face came out a 45 deg twisted surface (f150). An annular sector (constant z, r and
  azimuth faces) is geometrically cleaner and gave a better bench wall min, but the CR-10 Pro then
  failed on the pre-existing bulb-dome graze facet; the sector is kept as a comment in the function.
- **Servo pad** (`servo_pad`): solid skin under the bracket's footprint, corners rounded
  `PAD_CORNER` 4.0, wall `PAD_T` 1.5 mm **counting the band** - f152's estimate needs 1.34 mm
  (MG90S) of plate under the bracket's 42.3 mm foot and the epoxy bond itself is at SF ~ 400 in
  shear, so 1.5 is the requirement rounded up, not a guess (rule 11). Fused after the lattice is
  cut (so it closes the windows under the footprint into one 1.5 mm wall) and before the stem and
  servo holes are bored (so both are bored through it). Its near edge stands at
  `stem_keep_r() + PAD_RING_CLEAR` = 15.2 mm off the stem axis, as a **straight** edge: cut to an
  arc about the stem axis it crossed the hole's flare cone at a shallow angle and left a 0.034 mm
  facet, and cut to the keep-out ring itself it sat at distance 0.0000 mm from three window cutters
  and the fuse produced a solid whose shell is closed and whose faces are all valid while the solid
  itself is not (valid False). f154: the pad is 42.4 x 28.2 mm, not 46.3 x 28.2 - the far edge
  stands at `SERVO_BRACKET_L / 2 + PAD_EDGE_CLEAR` = 21.65 mm along the tangent from the servo axis
  instead of at `PAD_MARGIN`, and `outline_rib_clear()` measures the outline against the lattice's
  own window walls at the scale being built and picks the size whose edges stand >= `PAD_RIB_CLEAR`
  (0.3 mm) off any wall they run beside while still covering the bracket - and among those, the
  shape closest to bracket + margin: round 2 of f154 grew the pad to 29.2 mm to win the clearance and
  the CR-10 Pro came back with 1 facet under the 0.40 mm nozzle. A wall the outline **crosses** is not
  a wall it runs beside - the wall segment's endpoints lie on opposite sides of the edge's line - and
  an outline that crossed nothing could not close. The bracket does not
  scale and the hull does, so the pad's edges sit at different azimuths at each size (far edge az
  -6.18 at scale 1, -10.93 at 1.41) and that check has to be made at every size.
- **Keel and hatch:** the keel is solid only round the fan housing; the fan (motor + 88 mm impeller)
  comes out through the bayonet hatch, whose lug and stop post are an EXCEPTION.

## 7 BUILD AND CHECK WORKFLOW

Environment: generator and probes run with `/home/rhy/.venvs/cadquery/bin/python` (cadquery 2.8.0,
shapely 2.2.0, trimesh, scipy, matplotlib). FreeCAD 1.1.4 runs headless as
`flatpak run --command=freecadcmd org.freecad.FreeCAD <script>`. Scratch goes in the git-ignored
`CurrentModel/Analysis/build/<taskid>/` — never under `CurrentModel/CAD Files` or
`CurrentModel/Print Files`, because the checker walks those trees and has no hidden-dir skip, and
never in /tmp (it is RAM).

**Hard rule about time, learned by three tasks dying:** every foreground command must finish in
under 3 minutes — prefix it with `timeout 170`. Anything slower (generator, make_fcstd, checker,
solid probes) goes to the background and you poll its log:

    nohup <command> > CurrentModel/Analysis/build/<taskid>/run1.log 2>&1 &
    sleep 120; tail -5 CurrentModel/Analysis/build/<taskid>/run1.log

A foreground command that runs 15 minutes kills the task. Check nothing of yours is already
running first: `pgrep -af venvs/cadquery`.

### 7.1 Rebuild one slice (bench 8T, scale 1)

    OAS_VARIANT=8T OAS_SCALE=1 /home/rhy/.venvs/cadquery/bin/python \
        "CurrentModel/CAD Files/SimplifiedSlice/airship_slice.py"
    OAS_VARIANT=8T OAS_SCALE=1 flatpak run --command=freecadcmd org.freecad.FreeCAD \
        "CurrentModel/CAD Files/SimplifiedSlice/make_fcstd.py"

The first writes the .step and the .joints.json, the second the .FCStd and the print STL. Add
`OAS_TAG=CR10Pro` to both to name the CR-10 Pro files, `OAS_SCALE=1.41` for its size,
`OAS_VARIANT=4T OAS_SIDE=L|R` for the 4-thruster hands, and
`OAS_VARIANT=4T OAS_SLICES=12 OAS_THRUSTER=S OAS_PIECES=1 OAS_SCALE=3.8 OAS_RIB=1.2` plus
`make_pieces.py` for the double-Kobra pieces. `OAS_FCSTD_ONLY=1` on make_fcstd.py or
make_pieces.py rewrites only the .FCStd from the .step on disk and touches no print file.

Timings here (bench 8T): generator 4-8 min, make_fcstd 1-2 min, print checker 1-2 min per file,
`--joints` under a minute, full checker over all 103 CAD+print files ~12 min, `--only cad` ~7 min,
`--filter .stl` ~3 min. A scale-1.41 build is a little slower than bench.

Earlier tasks left a wrapper, `CurrentModel/Analysis/build/f149/rebuild.sh <scale> <tag>` (and
`build/f118/rebuild.sh <scale>`, which stops after make_fcstd unless given the STL, PNG name and
joints.json as arguments 2-5). It is scratch and may not exist in a fresh checkout — the two
commands above are the whole thing, so write your own wrapper in your own build folder.

### 7.2 Check

    nice -n 10 flatpak run --command=freecadcmd org.freecad.FreeCAD \
        CurrentModel/Analysis/check_outputs.py --pass "--only print --filter 8T.stl"

`freecadcmd` swallows anything that looks like an option unless it follows `--pass`, and it tries
to open every other bare argument as a file, so **all of the checker's own arguments go in one
quoted string after `--pass`**. A path with a space inside that string needs inner quotes (the
script re-splits it with shlex). Flags: `--only cad|print`, `--filter <substring>`,
`--thin-report` (list every facet under the nozzle, grouped into 2 mm clusters, with the BREP faces
near each), `--samples N` (default 6000 facets), `--joints <joints.json>` (measure JOINT_CLEAR and
AIR_KEEP), `--json <out>`, `--no-thin`, `--no-tess`, `--cad-root`, `--stl-root`.

Reading the lines:

- `PASS <file> [STL] facets N open 0 nonmani 0 selfint False orientOK True parts 1 vol ... mm3
  bbox ... bed <printers it fits> wall min <x> mm <nozzle n <layer n thick p% (area, blobs)
  vs STEP same` — one line per file.
- A **FAIL** on an STL is raised only by `wall min` < `LAYER` (0.20 mm), a non-manifold or open
  mesh, a self-intersection, more than one part, or a volume that does not match its STEP. Facets
  under the 0.40 mm nozzle are a warning, not a FAIL — but rhY's rule is none of them.
- `PROBLEM ...` lines say which rule failed, in words ("walls thinner than the 0.20 mm layer:
  0.026 mm at 2 of 5566 sampled facets", "self-intersecting mesh").
- `thin blob <area> <wall> mm at r=.. z=.. az=..` lines come from `--thin-report` and are the
  starting point for any thin-wall hunt: they are in the model frame, so undo the print pose to
  compare with a mesh.
- `thick p%` and the thick blobs are notes, not failures, as long as every blob belongs to an
  `EXCEPTIONS` entry.
- `grazing hits skipped N` and `sliver facets skipped N` are the checker's two measurement guards
  (`GRAZE_DEG` = 10 deg, `MIN_FACET_AREA` = 1e-4 mm2). They do not weaken the thin-wall rule; they stop
  the gate being decided by the tessellation. If a wall minimum moves a lot when you change the
  mesh deflection or the sample count, read section 8's graze rows before believing it.
- The last line is `N files checked, P pass, F fail` and the exit code is non-zero on any fail.

### 7.3 Looking at the part without a GUI

The probes are matplotlib/trimesh scripts in the scratch folders (copy one, change the path):

- seam view (`build/f118/seamview.py`): top view of a print STL, facets within 0.05 mm of the bed
  coloured by print height, every joint from its joints.json marked with its Ø7 boss and Ø3.3 hole.
  This is the picture that matches rhY's slicer screenshots.
- bulb zoom (`build/f149/bulbview.py`): the seam face near the bulb with both corner apexes, the
  bosses and holes, and the stem slot's rim — the rim is why `bulb_outer` cannot stand at its apex.
- outside view (`build/f150/outsideview.py --az <azimuth> --brace lo,hi`): the slice seen from
  outside along a radius, shaded by depth, the brace's span drawn as a band.
- shaded hull (`build/f151/hullview.py`): the STL's triangles as a lit 3D surface
  (Poly3DCollection), from outside down the stem hole's axis or from inside at the servo.
- solid map (`build/f151/solidascii.py`): '#' solid skin, '.' open window, 'P' pad, 'B' brace
  corridor, across the whole lattice band at 3 mm per character. The fastest way to see what the
  lattice rules are actually doing, and it needs no renderer.
- cell table (`build/f151/cells.py`): every cell with its raw area, its area inside the lattice's
  bounds, what each keep-out leaves, its kept %, and whether it is cut or solid.
- parts split (`build/f117/parts.py`): trimesh split of a print STL — part count, per part volume,
  2*vol/area, bbox, nearest main-body vertex. The test for "one clean piece".
- cut replay (`build/f151/cutprobe.py`): build()'s cut loop against the bare frame, naming the
  cutter and what each cut removed.

### 7.4 Finding the largest scale that fits a bed

Bisect on `OAS_SCALE` to 2 decimals, printing the print-pose bbox each time (the print pose is
fixed: seam face on the bed). The CR-10 Pro answer is **1.41**: 271 x 290 x 206 mm, inside
290 x 290 x 390. 1.42 gives 291.8 and does not fit. Rotating about the bed normal cannot help,
because the long print dimension is the hull's full height (202.76 * S plus ~3.9 mm of fixed-size
fan housing), not its length. Add the bed to `BEDS` in `CurrentModel/Analysis/check_outputs.py`
and map the STL to its STEP in `STEP_FOR_STL` so the volume cross-check runs.

## 8 FAILURE MODES AND FIXES

Symptom as the checker or the generator reports it | cause | fix | task that found it.

| Symptom | Cause | Fix | Found by |
|---|---|---|---|
| wall min 0.005-0.05 mm, clusters of tiny Plane faces 0.0003-1 mm2 at depth 0.01-0.4 mm under the skin | two cut boundaries coincident or within a hair of each other, or a cut floor landing on a face the part already has | separate them: no new cut boundary within 0.05 mm of an existing face; guard solids strictly looser than the uv clip; `CREST_EDGE_CLEAR`, `BRACE_EDGE_CLEAR`, `PAD_RING_CLEAR`, `SKIN_TRIM` 0.3 not T | f085, f148, f151 |
| wall min 0.005-0.1 mm, ~1,600 wall faces 0.00-0.28 mm wide, each spanning the whole band | the window outline's own shortest segments: a box clip leaves vertex pairs a few hundredths apart and each pair becomes a wall face that thin | resample the outline to `OUT_MESH` 1.0 (not the cell grid); `RING_WELD` at 1e-3 is NOT safe | f117 |
| self-intersecting mesh (`selfint True`), sometimes with the right volume | coincident clip planes, or a fused pair of overlapping tools, or sliver faces touching | make the two clips differ by a real margin; fuse overlapping tools one after the other, never as one compound; remove the sliver at its source | f148, f151 |
| 16-21 separate bodies in the print STL; curved plates 0.0-0.65 mm thick sitting in the window holes | chord sag: the cutter's caps spanned 32-38 mm chords of a curved outline and saged 3.6 mm, so the cut never reached the middle of its own window | tile the window into `CUT_MESH` 3.0 cells and stitch one shell whose caps follow the skin; `CUT_OUT` 0.6 clear of the outer face | f117 |
| a peg or boss is a loose body 30-60 mm from the part | the joint was placed where there is no wall: a chord midpoint instead of an arc midpoint, a corner whose material is inside the bulb's air, or an apex inside the stem slot which is cut later | place joints on real wall faces (`bulb_inner_corner`, `bulb_outer_corner`, `corner_joints`), and check a wall exists before moving a joint | f117, f149 |
| a hole cannot be placed at all | the wall there is the T = 0.86 mm skin band: a Ø3.3 hole with 0.6 mm of wall to the air cannot exist in it, and the sleeve that would make it thick would stand outside the outer skin | delete the joint and say why; the crest wall carries no peg | f117 |
| boss rim reads a thin wall, or breaks the outer ellipsoid | the boss was pushed until its rim sat at or through the outer face | keep the rim `RIM_KEEP` 0.40 mm under the outer face; a deeper bite is rhY's choice between a 0.4 mm wall and a flat patch | f149 |
| a boss clipped at a bore's face leaves 0.03-0.30 mm readings at that face | the clip face is coincident with the wall's inner face, and the fuse leaves a sliver | `BOSS_INSET` = T/2: stop the clip half a wall inside the band so that face lands in material | f118 |
| the cutter "does nothing": `window cut had no effect at x, y, z mm`, or the build returns `valid False` | the plain boolean cannot resolve a tool whose faces sit on a tangent; also happens when a lattice edge is moved so a window grows that cuts nothing | build() retries the dead cut as a fuzzy boolean (tol 1e-4) before raising; do not "fix" it by moving the lattice edge | f148, f151 |
| inside-out cutter: the cut removes nothing and the guard fires | the surface normals point OUT of the hull, so `p - n * d` goes inward; the outer ring was offset inward and the inner ring outward | swap the rings; verify a cutter spans depth -0.5 .. +0.88 mm under the outer face with a sphere probe | f087 |
| whole lattice cells left solid where a keep-out passes (an "hourglass of solid skin" down a seam) | the f118 rule dropped any cell a clip changed, and the crest band takes 66-70 % of a seam junction's raw polygon; a junction's polygon also reached into the rows above and below | the lattice's own bounds clip, keep-outs bite, and a cell keeping >= `MIN_KEEP` of its own area is cut clipped; `junction(..., rows)` | f151 |
| a whole column of cells solid and the slice 50 % heavier | MIN_WEB set to 0 without running the lattice's columns out to the band's edge, so every cell touching the crest strip became a partial cell | re-flow the columns (`column_bounds` / `crest_half`) so those cells are full cells again | f118 |
| a visibly thick double wall along the duct's outer side, thick % ~10 % | a duct wall stacked on the skin (the old DUCT_FUSE) | the skin IS the duct's outer wall: `SKIN_BITE` / `SKIN_BURY`, and delete the EXCEPTIONS entry | f087 |
| a flat facet or step on the duct's crest | a lattice cutter reached inside the duct's outer wall and nibbled the crest | the crest band: no window within `CREST_BAND` of a duct crest, enforced in uv and by a solid guard | f086, f087 |
| thin reading 0.19-0.38 mm all round the stem hole's rim, and adding material does not change it | the hole is bored along the radial line but the skin's normal at the rim is tilted atan((A/B) tan psi) = 13.85 deg, so the ray meets the hole's wall at a graze | flare the hole by `STEM_FLARE` + 1.5 deg so its wall is parallel to the skin normal; a chamfer makes it worse | f086, f117 |
| thin reading 0.005-0.3 mm where the bulb's dome, the duct tube, the shroud turn or the shaft crosses the seam face; the minimum moves with the mesh deflection and the sample count | the wall map fires one ray per facet along that facet's normal, and every surface of revolution is parallel to the seam face's rays: a facet d from the crossing circle reads d/2 (a corner distance, not a wall) | `GRAZE_DEG` = 10 deg: skip and count a hit whose face meets the ray at less than 10 deg; f151's grazeprobe.py shows a real 0.15 mm wall is still reported | f148, f150, f151 |
| one facet reads 0.01-0.03 mm and has area 0.000 mm2 | degenerate mesh facets from the mesher, whose normal is noise; the 6000-facet stride decides whether one lands in the sample | `MIN_FACET_AREA` 1e-4 mm2: skip them as ray sources and targets; and mesh at 0.03 mm first in make_fcstd.py | f149, f148 |
| a real 0.027-0.034 mm2 planar face in the STEP at the servo pad's edge, read as 0.033 mm, only at 1.41 | NOT a rib line: `servo_pad()`'s own tool, alone with no lattice and no fuse, carries those faces at BOTH scales - degenerate cap triangles off the tile grid (see 5). What changes with scale is which of them ends over a window opening, where the wall map can see it, instead of buried in the band | `TILE_EDGE` in `skin_cutter()`'s tile grid, plus trimming the pad's far edge to `SERVO_BRACKET_L` / 2 + `PAD_EDGE_CLEAR` and placing the outline with `outline_rib_clear()`. Do not cut the pad to an arc about the stem axis (invalid solid) | f151 found it, f154 fixed it |
| one sampled facet 0.027-0.055 mm2 whose ray reads 0.03 mm to a face sharing two of its vertices | a degenerate triangle: three near-collinear points, so its normal is noise and the ray leaves it sideways. All three vertices sit at one cap depth, so it is a cap triangle, not a wall | do not let the tiling make one: `TILE_EDGE` keeps `skin_cutter()`'s interior grid lines off the outline's own vertices. `MIN_FACET_AREA` only skips facets under 1e-4 mm2, so a 0.027 mm2 one is a real FAIL | f154 |
| the fused body comes out in 2 solids and loses the lattice (307 faces instead of 8,399) | two tools that overlap were fused as one compound | fuse them one after the other, or pre-fused | f151 |
| the slice reports more solids or a wrong volume | a boolean left a degenerate zero-volume shell in the compound | build() keeps only solids over 1e-3 mm3 and prints how many were dropped | f151 |
| the .FCStd opens on an empty 3D view, or shows three identical z-fighting solids | the writer stored a PartDesign Body plus base feature (the same brep 3-4 times), no GuiDocument.xml, and the previous release's document label | `CurrentModel/CAD Files/fcstd_doc.py`: one Part::Feature per part, label = file name, hand-written GuiDocument.xml (freecadcmd has no GUI and never writes it) | f073 |
| the generator dies with `ModuleNotFoundError: No module named 'shapely'` | the venv lacked shapely and the repo declared no requirements | shapely 2.2.0 is in the cadquery venv now; there is still no requirements.txt in the repo | f072, f073 |
| a task ends having read everything and changed nothing; or ends with "next session, resume with" | re-reading the generator and probing for an hour burn the budget; in this harness a reply with no tool call ends the task | read this manual instead of the source; make the first edit inside 30 minutes; keep going until the gate passes or the timeout | f118, f147, f148 |
| a foreground command runs 15 minutes and the task is killed | generator, checker and solid probes are all minutes-long | `timeout 170` on anything in the foreground; everything slower goes to nohup with a log you poll | f149 onwards |
| the wall minimum jumps between rebuilds with no model change | the wall map samples every n-th facet, so which facets are sampled depends on the facet count and the deflection | judge with `--samples 20000` and the graze/facet guards on; never chase a single facet without first checking its area and its angle | f149, f151 |

## 9 rhY's REVIEW HISTORY

Every review, what he saw, what he asked, what was done. Read this before changing a joint, the
lattice or the outlet: the current shapes are answers to specific complaints.

| Date | Saw | Asked | Done | Task |
|---|---|---|---|---|
| 2026-11-16 | the shipped CAD and print files | issue #36: "All the new CAD files and 3d print files are trash. Most of them have gaps that would never 3d print, and the CAD files don't even open and display things in FreeCAD." | audit: 33 of 103 files fail; three root causes (missing shapely, stale FCStd containers, 19 STLs with walls under the layer) | f072 |
| 2026-11-16 | the FCStd files | they must open in FreeCAD and show the parts | fcstd_doc.py writer: one Part::Feature per part, GuiDocument.xml, label = file name; 80 CAD files pass | f073 |
| 2026-11-16 | the 8T/4T slice in a slicer | one uniform thickness everywhere ("extra weight on the lower side of the duct"); one peg per seam face on the duct top fused into the duct wall; pegs clear of the fan housing; every corner boss fused into BOTH walls; the central peg exactly midway; one more peg in the groove where the duct meets the bulb | EXCEPTIONS list, JOINT_CLEAR and AIR_KEEP added to the checker, duct-top and groove pegs, corner and midway pegs | f082 |
| 2026-11-16 | his new printer | "make us a printable hull section that maximizes the new cr 10 pro" (CR-10 Smart Pro, 300 x 300 x 400, 5 mm margin) | bed limits recorded; the max-size work carried into f118 | f080 |
| 2026-11-17 | the f085 model, four marks | the duct's outer side is a double wall; a blemish on the duct's top; a peg in the wrong place on the duct; missing peg/hole connectors at three corners | the skin becomes the duct's outer wall; radial window cutters; the duct pegs moved; four corner joints added — but the slice came apart in 21 solids | f087 |
| 2026-11-17 | f085's proposal | approved a solid band along each duct's crest with no lattice windows cut into it | `CREST_BAND` enforced in uv and as a solid guard; `STEM_FLARE` | f086 |
| 2026-11-17 | the f087 print in a slicer | a peg floats in thin air, every window has junk in it, the exterior is a mess (measured: 21 bodies) | chord-sag fix in `skin_cutter`, 16 plates gone, floating joints deleted or moved onto real walls, 4 joints fused into two walls each; 1 part, 0 facets under the nozzle | f117 |
| 2026-11-17 | the f117 model | remove the two pegs "out in the middle of the hull"; "make sure that peg is in the corner more"; add a peg in the empty corner at the other end of the shaft wall; "lattice windows must run right out to the edges; ONLY the partial cells the edge cuts stay filled"; the largest, lightest print for a CR-10 Pro | 3 joints; `MIN_WEB` 0 and the columns run out to the band's edge; the CR-10 Pro size work was left unfinished | f118 |
| 2026-11-18 | the CR-10 Pro print's seam face at the bulb | "Missing peg, other peg not in the corner touching two sides." | both bulb corners computed as wall intersections; `bulb_groove` moved into the inner corner, `bulb_outer` added; 4 joints | f149 |
| 2026-11-18 | the CR-10 Pro print from outside | "a horizontal brace from the farther duct to the servo mount" (purpose: strengthening the equator line); empty the three extra solid cells | `servo_brace`; outlet rings sized to the hardware and clipping instead of dropping; 36 windows, 0 solid cells near the outlet | f150 |
| 2026-11-18 | f150's CR-10 Pro print | "Not quite. Also the equator brace isn't thick enough to support the servo bracket." | the >= 50 % clipped-cell rule (36 -> 58 windows); `BRACE_W` 6.0 x `BRACE_D` 3.0 and the servo pad | f151 |
| 2026-11-18 | the trade-off itself | "Lighter is better but we need it to be structurally solid. These are competing requests... we are going to have to do some educated guesses." | a documented load estimate and SAFETY_FACTOR sizing the pad and beam | f152 |
| 2026-11-18 | the scattered knowledge | "Make sure Strata makes note of all AirShip construction details so that future edits are faster and easier." | this manual, AGENTS.md, and the checker that keeps them honest | f153 |

## 10 LESSONS LOG

One entry per OpenAirShips task. **New tasks append here** (id, result, what worked, what to do
differently). Result OK = its gate passed and the work is in the tree; PARKED = its gate failed and
the branch was parked (its changes may still be inherited by the next task).

- **f072 audit — OK.** Wrote `CurrentModel/Analysis/check_outputs.py` and OUTPUT-CHECK.md; measured
  103 files instead of guessing. Worked: one checker, reused by every task since. Differently: the
  audit's line numbers go stale; cite names, not lines.
- **f073 FCStd open — OK.** Fixed the writer, not the model; found that freecadcmd cannot write
  GuiDocument.xml and hand-wrote it from FreeCAD's own example files. Worked: regenerate from the
  STEP files on disk (`OAS_FCSTD_ONLY=1`) so no print file moved. Differently: the gate line as
  written cannot run — freecadcmd needs `--pass "..."`.
- **f074 STL gaps — PARKED.** First attempt at the slivers (146 lines, introduced MIN_WEB).
  Differently: do not start by adding a margin constant; measure where the thin facets are first.
- **f075 merge CAD and prints — PARKED/local.** Merging half-finished branches produced nothing
  usable. Differently: do not merge a branch whose gate failed without re-running the gate.
- **f076 printed mass budget — OK.** Measured all 59 print STLs with numpy only, reproduced every
  published hull volume and gram column, corrected two recorded numbers. Worked: a --check mode
  that fails when the committed table drifts. Differently: 0.86 mm is the airtight minimum, so
  "print at half the thickness" is not available and had to be reported rather than implemented.
- **f076 no-slivers one variant — PARKED.** Its prerequisite was not on the remote, so it changed
  nothing and said so. Worked: measuring the consequence (wall min 0.09 mm on the committed STL)
  instead of arguing it. Differently: check which refs actually exist before planning a chain.
- **f077 regenerate all v0.2.2 — PARKED.** Correctly refused: rebuilding with an unfixed generator
  would overwrite 14 FCStd, 66 STEP and 59 STLs with output known to fail. Worked: refusing with
  measurements. Differently: none — that was the right call.
- **f080 CR-10 Pro hull section — see f118.** Set the bed and the 5 mm margin rule.
- **f082 uniform wall and duct peg — OK.** One wall T plus the EXCEPTIONS list; JOINT_CLEAR and
  AIR_KEEP became checker rules; the peg rules that still shape the joints. Differently: the
  duct-top peg it added was impossible (no wall thick enough) and f117 deleted it — check that a
  wall can hold a hole before placing a joint on it.
- **f084 slivers hard gate — PARKED.** Added `--thin-report` (the tool every later task used) and
  rewrote skin_shell with parallel curves. Differently: its STL still failed; a tool is worth
  committing even when the fix is not.
- **f085 slivers continue — PARKED.** Found two real root causes: the double uv map (553 face pairs
  0.002-0.4 mm apart) and coincident seam clips; got wall min from 0.009 to 0.186 mm. Worked:
  probing the boolean cut by cut to name the cutter. Differently: it ended on a design decision it
  could not make alone (a solid crest band) — ask early, and rhY approved it the next day.
- **f086 duct crest band — PARKED.** `CREST_BAND` in one place, used as a uv clip and a solid guard;
  `STEM_FLARE`. Cut the thin population from 225 to 110 facets. Differently: adding an outlet collar
  cannot change a measurement that is a graze; three ways of building a normal-field cutter were
  tried and all measured worse — record that in the docstring, which is what f086 did.
- **f087 duct wall and joints review — PARKED.** Landed all four review items (shared duct/skin
  wall, radial cutters, pegs, corner joints) and cut thick material from 10.5 % to 5.4 %, but the
  slice came apart in 21 solids. Worked: writing the cause with file:line before changing code.
  Differently: its own diagnosis of the plates ("a web is removed") was the opposite of the truth;
  measure the body, do not infer it.
- **f117 one clean piece — OK.** The breakthrough: chord sag, not a removed web. `skin_cutter` now
  tiles each window into 3 mm cells stitched into one shell; 21 parts -> 1, 709 sub-nozzle facets
  -> 0, mass 39.93 -> 34.69 cm3. Worked: start from the measured fact given in the task, not the
  previous task's theory. Differently: four separate causes each needed one small fix — do not look
  for one big one.
- **f118 pegs, lattice to the edges, CR-10 Pro — PARKED.** Did the joints and MIN_WEB = 0, and
  stopped itself after 1.5 h of a 5 h budget without editing the last item. Worked: the rule that
  replaced the margins (a cell an edge changes stays filled) is what kept the boolean safe.
  Differently: never stop early; a reply with no tool call ends the task.
- **f147 finish CR-10 Pro — PARKED.** Read everything, explained the coincidence, ended its turn
  without editing. Differently: make the first edit within 30 minutes; probe only what the edit needs.
- **f148 rib snap, CR-10 Pro — OK.** `snap_rib_to_crest` plus `CREST_EDGE_CLEAR` plus trimming the
  duct walls `SKIN_TRIM` 0.3 under the skin: both sizes PASS, 1 part each, CR-10 Pro at scale 1.41
  (271 x 290 x 206, 68.5 g). Worked: fix the layout so no cell straddles a step, instead of adding
  margins. Differently: the mesh deflection ladder (0.03 mm first) matters as much as the geometry;
  and a guard that refuses a bad rib move is what made the bigger scale buildable.
- **f149 bulb corner pegs — OK.** Corners computed as wall intersections, not arc fractions;
  measured the old point's bite as 2.05 / 0.00 mm at bench and 2.05 / -11.80 mm at 1.41. Worked:
  one checker change (`MIN_FACET_AREA`) flagged to rhY as a gate change. Differently: a corner's
  apex may be inside the stem slot or inside the bulb's air — check what material is really there.
- **f150 servo brace and open cells — OK.** `servo_brace`, outlet rings sized to the hardware and
  clipping instead of dropping; 34 -> 36 windows, 3 solid cells near the outlet -> 0, bench slice
  32.38 -> 30.24 cm3. Worked: end the rib in solid band, not at a keep-out's nominal edge.
  Differently: `skin_cutter` is wrong for a narrow deep rib (its end faces twist 45 deg); and a
  guard margin must include the cutter's own edge swing from the skin's tilt.
- **f151 open seam cells and strong brace — PARKED** (bench PASS, CR-10 Pro FAIL on one 0.033 mm
  facet at the pad's far edge; the one-rebuild fix is recorded in section 8). `MIN_KEEP` /
  `CELL_CLOSE` / `junction(rows)` took 36 -> 58 windows; `BRACE_W` 6.0 x `BRACE_D` 3.0 and
  `servo_pad`; `GRAZE_DEG` in the checker. Worked: measure the cell inside the lattice's own bounds;
  retry a dead cut fuzzy. Differently: at a bigger scale fixed-size hardware lands beside lattice
  ribs — check the pad and beam edges at every scale, not just at bench.
- **f152 brace sizing estimate — OK.** Replaced f151's guess with
  `CurrentModel/Analysis/STRUCTURE-ESTIMATES.md` (every load tagged [measured] /
  [datasheet] / [guess], `SAFETY_FACTOR` 3 [guess]) and `CurrentModel/Analysis/brace_sizing.py`
  (the arithmetic; it reads `SAFETY_FACTOR` from the generator, so the factor and the sizes
  cannot drift apart). **`BRACE_W` 6.0 -> 9.0, `BRACE_D` 3.0 -> 2.5, `PAD_T` 1.5 unchanged.**
  The finding: the servo's stall torque (SG90 1.8 / MG90S 2.2 kg-cm [datasheet]) is about the
  **radial** axis, because the spline is radial, so the brace carries it in bending with
  `Z = BRACE_D * BRACE_W^2 / 6` - f151's 6.0 x 3.0 had the same amount of material pointed the
  wrong way (Z 18.0 mm3, SF 1.67 against the MG90S single-failure bound); 9.0 x 2.5 gives
  33.8 mm3 and SF 3.13 for +0.43 g a slice (measured: bench slice 30.42 -> 30.77 cm3, 37.7 ->
  38.2 g PLA). The pad's limit is the PLA under the bond, not the bond (the epoxy is at SF ~
  400 in shear): plate bending under the bracket's 42.3 mm foot needs 1.34 mm, so 1.5 stays.
  `BRACE_D` is at a documented floor (2.5 mm = band + ~4 lines; f150's 1.72 mm rib is what rhY
  rejected), not at its load - the equator's buckling margin goes 9.1 -> 26.6 with the brace.
  Worked: sizing on paper before rebuilding once - one bench and one CR-10 Pro build, both
  first attempts, and the estimate's predicted mass (+0.53 g a slice) landed within 0.1 g of
  the measured +0.43. Differently: the trade-off is a *shape* question before it is a *size*
  question, and nobody had asked it; and a load-sharing fraction is the weakest link in an
  estimate like this - the file says so and lists the five measurements that would replace it
  (push a slice on a scale at the servo pad, strip an epoxied bracket, stall a real servo,
  weigh a slice, note the print orientation).
  **Float budget (f152 step 4):** `float_budget.py` re-run on the current hull, and it now has
  **CR-10 Pro x1.41 rows** (8 and 4 thrusters, PLA and both LW-PLA foams) plus a grams-per-item
  table for the 8T PLA build: hull 447 g, rings 143, servo mounts 42, stems and gears 94, fan
  hatch 12, impeller 8, motor 32, 8 servos 107, wiring 33, screws 3, glue 29, gas cells 11 =
  **961 g**, 49.2 L of H2, **55 g** of lift, lift/mass **6 %**, lift+thrust-mass **-501 g**;
  the 4T at 1.41 is 672 g / 8 % / -196 g and hovers at full foam (+38 g). That lands on rhY's
  2026-11-18 question (Claude's estimate: hull ~441 g, total ~940 g, ~50 L, ~56 g, ~6 %): the
  measured hull is 447 g and the total 961 g, so the estimate was right to within 2 %. Two
  side effects worth knowing: the 8T bench rows moved +26 g because FLOAT.md had not been
  regenerated since v0.2.1 - f152's own share is **+3.4 g a hull**, measured by tessellating
  the previous committed STEP (30.18 -> 30.51 cm3 a slice) - and `hull_volumes.py` grew an
  OAS_PART_DIR environment variable, because the fan, thrusters and servos do not scale with
  the hull and the x1.41 size has no Propulsion folder of its own, so it reads the bench parts. The 4T rows do
  not move at all: `servo_brace()` returns None for FOUR, so a 4T slice has no brace (only the
  right-hand slices get the pad).
- **f153 construction notes — OK.** This manual, `AGENTS.md` and
  `CurrentModel/Analysis/check_construction_notes.py`. No model or geometry change. Worked: the
  manual is written to be read by section, so a task loads the 60-120 lines for its kind of edit
  instead of 2,500 lines of notes. Differently for the next task: append your line here and update
  the sections your change touched — the checker proves the file is stale, not you.
- **f154 servo pad far edge — OK** (both slices pass: bench wall min 0.422 mm, CR-10 Pro 0.536 mm,
  0 facets under the 0.40 mm nozzle at either size, 1 part each, the same 4 joints, 37.7 g and 55.1 g).
  f151's diagnosis was wrong and the probes that showed it are in `build/f154/`: the 0.033 mm facet is
  a **degenerate cap triangle of the pad's own tool** (`padonly.py` builds `servo_pad()` alone, no
  lattice, and finds the same 0.027 mm2 faces at both scales), made because one of `skin_cutter()`'s
  tile grid lines passed within 0.04 mm of an outline vertex (`tileprobe.py`). Fixed with `TILE_EDGE`;
  the pad's far edge was also trimmed to `SERVO_BRACKET_L / 2` + `PAD_EDGE_CLEAR`, and
  `outline_rib_clear()` with `PAD_RIB_CLEAR` is the general 0.3 mm rule, measured against the window
  outlines `windows()` now caches in `_WIN_OUTLINES`. Worked: reproduce the checker's own ray
  (`wallpair.py`) before believing the previous task's theory, and build the suspect tool by itself.
  Differently: a facet that only appears at one scale is not automatically a scale interaction - it
  can be the same bad facet, exposed at one size and buried at the other. And do not tune a feature's
  size to satisfy a clearance rule without re-running the wall map: f154's first scoring grew the pad
  to win 0.3 mm and the CR-10 Pro came back with a facet under the nozzle.
- **f155 float design study - OK.** No model or geometry change: `CurrentModel/Analysis/FLOAT-DESIGN-STUDY.md`
  and `CurrentModel/Analysis/float_design_study.py` (pure Python + numpy; it imports
  `float_budget.py` for NET_LIFT, the densities and the film, and reproduces FLOAT.md's x3.8
  rows to 5 g: 1027 L / 1150 g / +173 g against 1022 / 1145 / +168, so the comparison of shapes
  is a comparison of shapes). Found: (a) the CR-10 Pro bed forces 16 slices and 256 pieces on the
  x3.8 lattice build, and that re-piecing alone is +68 g of glue and joint bosses over FLOAT.md's
  rows; (b) a semi-rigid batten frame is **heavier** than the lattice it replaces - 12 battens and
  3 rings sized to `SAFETY_FACTOR` 3 against the film's Laplace load (axial N = dp x R x w / 2,
  Euler over the ring spacing, dp 100 Pa [guess]) is ~0.9 kg at 1.58 m, and a geodesic strut frame
  is worse again (~850 g of struts before its 42 nodes); (c) the lightest sound ship is a pressure
  envelope - printed core only (keel tube, fan housing, 4 tapered ducts, one support ring, tray)
  plus a metallized-PET film held at 200-300 Pa - which floats with **+250 g at 1.63 m hull,
  1008 g all-up, 1123 L of H2, 47 printed parts, ~89 print hours**, against 1.67 m / 256 parts /
  143 h for today's skin and 2.21 m / 235 parts / 426 h for the frame. Worked: anchoring every
  mass on FLOAT.md's rows and every strength on `CurrentModel/Analysis/STRUCTURE-ESTIMATES.md`'s
  tags, and tagging every new number [measured] / [datasheet] / [guess] the way f152 did. The
  structure came out of the same maths: keel tube in bending SF 30, duct root under the thruster
  reaction x 4 SF 15 (but only SF 0.6 with no support ring and 1.1 with a ring at 0.5 a and a T
  wall - the tapered 2T root is what buys SF 2.3 against a 20 N hand), film in tension SF 6-60.
  Differently: the two numbers that decide whether any of this is real are not in the CAD at all -
  the film's grip on the keel rim (the film's Laplace tension at 100 Pa is only 1.3 x the ship's
  weight, fixed by 200-300 Pa plus a 10 mm bond band) and whether LW-PLA really prints at 0.60
  g/cm3 (at 0.80 the +250 g margin becomes +149 g). And one 0.1 mm pinhole in a seam leaks 20 L/day
  of H2, ~100x the whole film's permeation: seal the seams before believing any datasheet.

- **c02 CAD checker + fixed views — OK.** Wrote `CurrentModel/Analysis/check_cad.py`
  (B-rep checks on the STEP: solids, outer shells, BRepCheck, sliver faces, short
  edges, hairline face gaps, internal faces) and `CurrentModel/Analysis/render_views.py`
  (six fixed views, hidden lines off, 1200 px PNGs, close-up boxes from the
  `SERVO_T` / `DUCT_BULB` constants). The CR10Pro STEP fails: 8663 sliver faces,
  4988 short edges, 6032 hairline gaps, 86 internal faces — see
  `CurrentModel/Analysis/CAD-CHECK.md`. Worked: the bbox-gap sweep (a bbox gap is a
  lower bound on the face distance) plus skipping shared-edge neighbours cut 26k
  candidate pairs; forked chunk workers with a SIG_DFL alarm survive
  `BRepExtrema`'s hangs and segfaults on this model's BSpline soup. Differently:
  the mesh checker (check_outputs.py) says PASS while the B-rep is full of slivers —
  check the CAD before tessellating, every task, section 11.

## 11 CHECKS — CAD, not STL

New rule (rhY 2026-11-23): work on the CAD, not the STL. From now on every
AirShip task edits the CAD script, regenerates the STEP, and gates on
`CurrentModel/Analysis/check_cad.py` plus the renders in
`CurrentModel/Analysis/renders/`; STLs are exported only at the end. The mesh
checkers (section 7.2) stay as the print-time gate, but a B-rep sliver or an
internal face survives the fuse long before a tessellation can see it, so the
CAD check runs first.

The CAD checker:

    /home/rhy/.venvs/cadquery/bin/python -I CurrentModel/Analysis/check_cad.py \
        "CurrentModel/CAD Files/SimplifiedSlice/airship pie slice 1026 CR10Pro.step" \
        --json CurrentModel/Analysis/build/c02/check.json

Exits 1 with one line per failure and prints counts plus the worst 10 locations
per check. It checks the STEP's B-rep for: more than one solid; more than one
outer shell; an invalid shape (BRepCheck_Analyzer); faces under 1.0 mm2 (sliver
walls); edges under 0.2 mm (pinched seams); pairs of faces closer than 0.2 mm
but not touching (hairline gaps and seam cracks, measured with BRepExtrema on
the pairs whose bounding boxes come within 0.2 mm); and faces with material on
both sides (0.05 mm along +/- the surface normal is inside the solid twice — a
face two solids shared before the fuse). The first run on the CR10Pro STEP
(2026-11-23): 8663 sliver faces, 4988 short edges, 6032 hairline gaps, 86
internal faces — the point is to catch these today, see
`CurrentModel/Analysis/CAD-CHECK.md`.

The fixed views:

    /home/rhy/.venvs/cadquery/bin/python -I CurrentModel/Analysis/render_views.py \
        "CurrentModel/CAD Files/SimplifiedSlice/airship pie slice 1026 CR10Pro.step" \
        CurrentModel/Analysis/renders

Six views: iso front, iso back, top, side, and close-ups of the servo mount and
the duct bulb. The close-up boxes come from the `SERVO_T` spline-hole centre and
the `DUCT_BULB` dome centre in `CurrentModel/CAD Files/SimplifiedSlice/airship_slice.py`,
rotated onto the slice's seam; the views are CadQuery SVG exports with hidden
lines off, converted to 1200 px PNGs with rsvg-convert. The CAD is never modified.
