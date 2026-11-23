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

- 0 INDEX: 20-50
- 1 FRAMES: 51-124
- 2 GENERATOR MAP: 125-361
- 3 DESIGN RULES: 362-510
- 4 JOINTS: 511-568
- 5 LATTICE AND KEEP-OUTS: 569-674
- 6 DUCTS, BULB, STEM, SERVO, BRACE: 675-773
- 7 BUILD AND CHECK WORKFLOW: 774-881
- 8 FAILURE MODES AND FIXES: 882-928
- 9 rhY's REVIEW HISTORY: 929-951
- 10 LESSONS LOG: 952-1341

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
- Keep-out standoffs: `CREST_EDGE_CLEAR` 91, `CUT_FACE_CLEAR` 102 (f156), `SERVO_WALL` 129,
  `BRACE_EDGE_CLEAR` 136 (f158: 1.5 -> 2.5), `MOUNT_EDGE_CLEAR` 142 (f162: 0.5, the actual
  mount edge inside the grown ring), `MOUNT_KEEP` 142, `SEAM_JUNCTION_OPEN` 142 (f162: False -> True),
  `BRACE_OUT` 152, `CREST_BAND` 419.
- Servo brace and pad: `BRACE_W` 175, `BRACE_D` 190, `BRACE_IN` 201, `SERVO_BRACKET_L` 206,
  `SERVO_BRACKET_W` 207, `PAD_MARGIN` 209, `PAD_T` 210 (f158: it is now `max(2 * T, BRACE_D)` —
  the mount has ONE depth), `PAD_CORNER` 233, `PAD_EDGE_CLEAR` 234
  (f154), `PAD_RIB_CLEAR` 242 (f154), `PAD_RING_CLEAR` 256 (f158: 0.6 -> 2.5), and the mount's own outline
  constants `MOUNT_RING` 109, `MOUNT_BLEND` 114 (f158: ring, blend, cap - f156's flare, bulb,
  fillet and end constants are gone), `MOUNT_CAP` 124,
  `MOUNT_AIR_MARGIN` 128 (f156 item 2).
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
- `crest_half` 1285 — how far in from the seam plane the solid skin over a duct reaches at psi:
  the duct's own reach under the skin measured where a lattice cutter's floor is (`CUT_IN`), plus
  `AIR_KEEP` off its air and `CUT_FACE_CLEAR` off its wall face — 6.0 mm beside the tube, 7.0 mm
  beside the bulb, 0 above the bulb (f156 item 3; it used to be the constant `CREST_BAND` = 12 mm).
  column_bounds(), oval_on_skin(), clip_window().
- `crest_half_cell` 1323 — the same over a whole cell's psi span (the widest point), so the layout
  and the clip use one bound. oval_on_skin(), clip_window().
- `duct_centre_points` / `duct_air_sdist` / `duct_wall_sdist` 1345 — the duct centreline sampled at
  0.5 deg, and the signed distance to the air surface and to the tube's own outer wall face.
  crest_half(), mount_geom().
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
- `crest_psi_range` 2986 — the psi range the crest band runs over. crest_half(), crest_keepout().
- `crest_keepout` 2998 — the crest band as a solid guard: the duct's two swept envelopes (air grown
  `AIR_KEEP`, wall face grown `CUT_FACE_CLEAR`), each 0.5 mm inside the bound that made it, so it is
  strictly looser than clip_window()'s uv clip. windows().
- `duct_air_keepout` 3051 — the duct's air path grown `AIR_KEEP` (was `MIN_WEB`, which is 0: a guard
  that could only catch a cutter already in the air). windows().
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
- `brace_span` 2503 — the azimuths the servo beam runs between, along the equator. Still what
  `Analysis/brace_sizing.py` measures its span with (conservative: the waisted mount supports the
  beam's first half). f156 item 2: clip_window no longer uses it — the keep-out is the outline.
- `mount_geom` 2554 / `mount_half_w` 2627 / `mount_ring_pts` 2642 / `servo_mount_outline` 2669 —
  the mount's one outline in the uv frame centred on the spline hole: elliptical nose, the ring
  under the bracket, ONE cosine blend, the strip on the equator to its buried end face. Its far end
  is bisected against the duct's air (`AIR_KEEP` + `MOUNT_AIR_MARGIN`).
  servo_brace(), clip_window(), servo_mount_area().
- `servo_mount_area` 2706 — the bonded area (the bracket's footprint where the ring covers it) and
  the load's footprint, for `Analysis/brace_sizing.py --check`.
- `_mount_tool` 2727 / `servo_brace` 2753 — the whole mount as ONE `skin_cutter` tool over ONE
  outline at ONE depth, `max(2 * T, BRACE_D)`: ring, blend and `BRACE_W` x `BRACE_D` strip. build().
- `servo_pad` 2807 — since f158 a no-op that returns None: the pad is the RING end of the same one
  tool, and a second tool over the same outline at a second depth is what made the sliver (see 8).
  build() still fuses the two names one after the other.
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
5. Fuse `servo_brace()` (the whole mount: one tool, one outline, one depth) and then
   `servo_pad()`, which returns None. f156 fused the pad and the beam **one after the other**
   because they overlapped by 117 mm3 and fusing them as one compound broke the body (45,679 mm3 in
   2 solids, 307 faces instead of 8,399 — f151's fuse probe); f158 has nothing left to fuse, which
   is the point.
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
3. **Solid crest band along each duct's crest, half-width `crest_half(psi)`** — the duct's own
   reach under the skin plus `AIR_KEEP` and `CUT_FACE_CLEAR`: 6.0 mm beside the tube, 7.0 mm beside
   the bulb at bench, over the duct's run (`crest_psi_range()`). It was `CREST_BAND` =
   `DUCT_BORE` / 2 = 12 mm at every psi until f156 item 3 (rhY at the print, crop 9: "Too much
   material on the outer hull near the duct. There should only be duct and lattice, no extra
   material"): 12 mm is the air's half-width at the centreline, and the centreline sits 12.84 mm
   under the outer face, so a cutter whose floor is 1.16 mm down only meets the tube 5.3 mm from the
   seam plane — the other 6 mm each side was solid skin with nothing under it but the duct's own
   wall. It is still the normal T wall with no windows, so it adds no material. rhY approved the
   band 2026-11-17 (f086) after f085 measured that no cut floor inside the band, at the wall's face,
   or below it measures printable (0.108-0.314, 0.049, 0.061 mm).
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
   **f158 R1 asked to narrow it for cells by the ducts** — rhY 2026-11-19 (crop 12): "The half
   diamonds by the ducts need to be emptied for weight. Clip them by the ducts and the other
   clearance and open them up, instead of filling them all", reversing f156 item 1 of the same
   review ("Diamond on the central band is half filled. Let's fill it all the way"). The clip is
   implemented — `clip_window` clips the junction by the band a `RIB` further out than a cell's,
   and what is left outside crest_half(psi) becomes a clipped window — and since f162 it is
   **shipped open**: `SEAM_JUNCTION_OPEN` is True. What held it closed at f158 (at 1.41 the opened
   window beside the mount's plate left a chain of 0.3-1.5 mm2 faces at r 289-291, az -19.7..-21,
   z 14-21, a 0.0248 mm face pair and four self-intersecting facet pairs at every mesh deflection,
   `build/f158/facesf158.py`, `selfint-cr10.log`) turned out to be a strip of seam skin claimed
   TWICE — the junction of the rib above and the junction of the rib below each cut the same
   492.89 mm2 region (`build/f159/layout.py`: junc r6 & r7 az -22 at 1.41; junc r5 & r6 az -22 at
    1.0). Each strip is now claimed exactly once: a seam junction keeps only the cell ABOVE its own
    rib, and every claim stands `RIB / 2` off the rib line that ends it — the web between two seam
    junctions is exactly `RIB` and the two cuts never meet. Standing the two halves to MEET along
    the rib line instead (no setback at all) was tried and failed at BOTH scales: each junction
    draws that rib v-line in its own uv frame as its own chord polyline, and the two polylines are
    0.010-0.041 mm apart (`build/f162/facesfault-r2.log`: face chains f8211-f8214 vs f8306-f8311
    at r 198.7, z -29.5, az -17..-20), leaving 0.010 mm walls at 1.0 and 0.005 mm walls plus eight
    open edges (not watertight) at 1.41 — even resampling both junctions' shared ends onto ONE
    global azimuth grid (step 0.004 rad) did not close them (`build/f162/rebuild-r2/r3/r4.log`). The
    setback margin itself costs 0.35 cm3 (48.85 vs 48.50 cm3, `rebuild-r1` vs `rebuild-r2`);
    the REAL cost of claiming once is the spill: f159's junction windows straddled the rib line
    and opened skin in the strip beyond it (+3.5 cm3, 44.98 -> 48.50), and none of it can be
    claimed a second time - every two-cut variant came back with 0.005-0.010 mm sliver walls
    and open edges. The CR-10 Pro floor with claim-once and every wall clean is 60.6 g - see
    10's f162 row and `build/f162/rebuild-r5/r7.log`.
9. **A cell a keep-out trims is cut clipped, not dropped** (f151, rhY 2026-11-18: the middle of the
   slice was "an hourglass of solid skin"). The lattice's own bounds clip a cell; the keep-outs bite
   it; a cell that keeps >= `MIN_KEEP` (0.50; f158 tried 0.47 for the last 0.2 g and the
   self-intersections came back at 1.41 - every clipped cell it opened near the mount was another
   wall grazing the plate) of **its own area inside
   those bounds** is cut as
   cell-minus-keep-outs with corners rounded to `CELL_CLOSE`; below that it stays solid, and
   anything under `MIN_OPEN_AREA` (20 mm2) is a crescent, not a window. Bench slice: 36 windows
   before, 58 after; f156's fills took it back to 40 and f158 opens them again (57 at bench, 62 at
   1.41), with the servo mount's own keep-out running by the `MOUNT_KEEP` (0.6) variant of the same
   rule — see 5.
   **A cell a solid feature covers WHOLLY is still cut** (f158): the feature's own plate closes
   the window, the lattice's wall stands `BRACE_EDGE_CLEAR` off the plate's face, and not cutting
   it is solid skin the feature could not use — which is what f156's +2.5 cm3 of skin at bench
   bought.
10. **No cut boundary may land on a face the part already has.** This is the single most important
    printing rule and it is what every standoff constant exists for: `CREST_EDGE_CLEAR` 0.5,
    `BRACE_EDGE_CLEAR` 2.5 (f156 raised it 0.5 -> 1.5 when a 0.005 mm sliver of skin between two cut walls showed at five places within 1.5 mm of the mount; f158's clipped windows beside the strip wanted 2.5, and it left 0.024-0.08 mm face chains at 1.5 - `build/f158/faces-seam.log`), `PAD_RING_CLEAR` 2.5 (f154 set 0.6, and at 1.41 that 0.6 mm corridor between the stem ring's clipped window wall and the mount's nose face filled with the same chain), `SERVO_WALL` 1.0, `BOSS_INSET` T/2, the guard
    solids being strictly looser than the uv clip that made them, `SKIN_TRIM` 0.3 instead of T,
    `OUT_MESH` 1.0, `CUT_OUT` 0.6 clear of the outer face, and since f156 `CUT_FACE_CLEAR` 0.3 -
    the lattice's floor standing off the duct tube's own outer wall face where the lattice now runs
    up beside a duct. Coincident or near-coincident faces give
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
  `clip_window()`'s uv clip at `crest_half(psi)` + `MIN_WEB` - `CREST_EDGE_CLEAR`, `crest_keepout()`
  at 0.5 mm inside each of the two envelopes the band is made of. The lattice's outer edge is
  `column_bounds` at the same `crest_half` - the widest point of the cell's own psi span
  (`crest_half_cell`), so the layout and the clip can never disagree (f156 item 3; before that
  both used the constant `CREST_BAND` = 12 mm). Moving the lattice edge outward instead was
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
- **The servo mount's keep-out** (f150/f151 corridor, waisted by f156 item 2, re-flowed by f158):
  windows stand `BRACE_EDGE_CLEAR` (2.5 mm since f158; f156 shipped 1.5) outside the mount's own outline, which is one curve
  (`servo_mount_outline`) rather than the box `max(RIB, BRACE_W) / 2 + BRACE_EDGE_CLEAR` of arc off
  the equator over `brace_span()`. The box fitted a straight beam; with a ring and a strip a box
  would leave the ring's corners standing over a cut wall by whatever the lattice happened to do.
  The keep-out is mapped into each cell's own uv frame through that cell's `to_uv`, so it is
  measured on the skin, not in the mount's frame. Three cases (`clip_window`): **a cell the grown
  outline covers WHOLLY is cut as an ordinary window** — the mount's own plate closes it and its
  side faces stay `BRACE_EDGE_CLEAR` from every cut wall; **a cell the outline CROSSes is a clipped
   window**; a cell is filled only when the mount takes >= `MOUNT_KEEP` (0.6) of its own area,
   because what is left then is a crescent, not a window — and since f162 not when it lies wholly
   under the grown ring (the fill never fired: r1 vs r5 measured the SAME 48,849 mm3).
   f162 added the in-between: **a cell wholly
  inside the GROWN ring but crossed by the mount's OWN outline is clipped too, `MOUNT_EDGE_CLEAR`
  (0.5 mm) off the actual edge** — cut as an ordinary window its raw lattice edge landed coplanar
  with the mount's side face, 0.0041-0.010 mm wall at r 205.7-206.2, z 4-7, az -2..+1 on the bench
  slice (`build/f162/facesfault-8t.log`, the 0.005/0.009 mm FAILs in `build/f159/bench-r5.log`).
  f156's two rules — fill any cell the outline bites by more than 5 %, fill any cell that merely
  came within 2 mm of it — are **gone**: they were chasing the coincident-face sliver, they did not
  remove it (f156's own fixes 5 and 6 "changed nothing measurable"), and they cost a column of
  solid skin along the equator and the mass rhY R3 marks. The sliver's real cause was one outline
  built at two depths, not the clipped windows (see 8): f158 builds the mount as ONE tool at ONE
  depth, and the clipped windows then measure 1.45 mm of skin off the mount's face at bench, which
  is what `BRACE_EDGE_CLEAR` asks for.
  What the fills were protecting against is real: two cells clipped by the SAME curve leave their
  walls ON that curve, and the boolean resolves the zero-thickness rib between them at 0.01-0.03 mm
  (`build/f156/faces.py`: f110/f120/f142/f143/f145 against f703/f704/f1066/f1067/f1074/f1075 at
  az 16-17 deg, z +-8-9 mm). Hence clipping to the outline GROWN by `BRACE_EDGE_CLEAR`, so the two
  walls of one clip are 3 mm apart and never 0, and `POLY_CLOSE`'s erode-dilate being undone by the
  bite again (`build/f156/clearprobe.py`: the mount's own outline stands 0.436 mm off the nearest
  parallel wall at bench with the bite re-applied, 0.005 mm without it).

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
- **Servo mount** (`servo_mount_outline`, `mount_geom`, `mount_half_w`, `mount_ring_pts`,
  `servo_brace`, `_mount_tool`): one solid rib on the inside of the skin, in the uv frame centred
  on the Ø8 spline hole — an elliptical nose (`MOUNT_CAP` 9.0 x `MOUNT_RING` 13.0), the wide RING
  under the bracket's footprint (its straight side stops 21.65 mm along the equator =
  `SERVO_BRACKET_L / 2 + PAD_EDGE_CLEAR`, so it covers the bracket's whole 42.3 x 24.2 mm foot),
  ONE cosine blend (`MOUNT_BLEND` 26) down to the strip's own width `BRACE_W` / 2, and a straight
  strip of that width on to `u_far`, where its end face is buried in the uncut skin. 2129 mm2 of
  footprint at bench (`build/f158/mountshape.py`), least radius over the visible outline 6.23 mm.
  It is ONE tool (`_mount_tool`) at ONE depth, `max(2 * T, BRACE_D)` = 2.5 mm under the outer face
  from `BRACE_OUT` 0.3: the whole mount is one parallel surface of the hull, so there is no step
  and no ridge on the inside (f158, rhY: "no straight segment, no step, no ridge"), and the pad's
  plate is 2.5 mm, not `PAD_T` 1.5.

  f156 item 2 (rhY at the CR-10 Pro print: "Brace around the servo looks stupid and isn't flush
  with the outer hull ellipse", and his sketch of a ring round the hole flowing into the beam on
  one side and the duct bulb on the other, "fillet radius >= 5 mm, no corners") built a waisted pad
  with a bulb flare and a rounded cap; f158 (rhY, crops 13/14: "a weird vestigial equatorial brace
  that sticks out inside and does not perfectly conform to the AirShip's outer hull ellipse", "The
  servo mount is a compact ring round the spline hole blended into that strip, not a big waisted
  pad") took the flare, the bulb and the cap out again: they stood 2 mm past the skin's inner face
  on a step, and their flare crossed the lattice diagonally. Flushness was never the fault —
  `check_flush.py` measures the outer surface against the hull's own ellipse and gets +0.000 mm
  maximum deviation over 11,562 points for either shape, because `skin_cutter` builds every tool
  from the skin's own surface. What was wrong was the silhouette and the mass.
- **The mount's far end is set by the duct's air, not by the seam** — except that f158 R3 caps it:
  the end face now stands `stem_keep_r` + `PAD_RING_CLEAR` inside the far seam, the same limit the
  near nose uses, which is 6.6 mm shorter and 0.37 g lighter at 1.41. `mount_geom` bisects `u_far`
  out to the largest value whose end face, at `BRACE_D` deep, still keeps `AIR_KEEP` +
  `MOUNT_AIR_MARGIN` of wall to the duct's air: 116.67 mm along the tangent at bench, 10.51 mm
  inside the far seam's plane, 1.12 mm to the air. **f158 R3 tried shortening it** to `stem_keep_r`
  + `PAD_RING_CLEAR` inside the seam — 6.6 mm of strip, 0.37 g — and it put the self-intersections
  back: 17.1 mm inside the seam the end face is OUTSIDE the ring's 14.60 mm disc, so instead of
  being buried in uncut skin it stands against a clipped window's wall. The end face only belongs
  *inside* that disc. Its end face stands inside the far stem
  keep-out ring's disc (10.51 of 14.60 mm), so it is buried in uncut skin. f150/f151's warning
  stands: ending the beam at `CREST_BAND` (12 mm of arc) put its tip inside the stem hole's flare
  (13.93 mm at the outer face) and build()'s stem-hole cut sliced the tip into a sliver standing
  inside the hole's swept volume. f156's bulb flare put two of its corners OUTSIDE that disc, on
  skin its own keep-out left uncut — one more reason the flare is gone.
- **Beam section unchanged, and still the sizing that sets it** (`Analysis/brace_sizing.py`, rule
  11, `Analysis/STRUCTURE-ESTIMATES.md`): `BRACE_W` 9.0 mm along the hull x `BRACE_D` 2.5 mm deep
  from the outer skin = 22.5 mm2, starting `BRACE_OUT` 0.3 mm under the outer face. The load that
  matters is the servo's stall torque (SG90 1.8 / MG90S 2.2 kg-cm [datasheet]) taken as a
  single-failure bound — the bracket's epoxy bond lets go and the brace alone holds the servo at
  full stall — and that torque is about the **radial** axis (the spline is radial), so the section
  carries it with `Z = BRACE_D * BRACE_W^2 / 6`: 33.8 mm3 and SF 3.13 at 9.0 x 2.5, against 18.0
  mm3 and SF 1.67 at f151's 6.0 x 3.0. `brace_sizing.py --check` now reads the mount's own
  footprint out of the generator instead of a hardcoded rectangle, and reports the whole mount:
  beam SF 3.13, pad plate SF 9.02 (`PAD_T` = `max(2 * T, BRACE_D)` 2.5 against a 1.44 mm requirement
  for the MG90S; f156 read 3.25 with the pad at 1.5), bond
  shear SF 314 against the PLA, peel SF 916, over a bonded area of 977 mm2 — the bracket's 1024
  mm2 footprint where the ring actually covers it (95.4%; the two near corners stand over
  the nose's ellipse, which is what rhY's sketch asks for). f154's `outline_rib_clear()` size
  search is gone: the outline is fixed now and the keep-out is grown from it, so the clearance is
  `BRACE_EDGE_CLEAR` by construction (measured 1.45 mm at bench — the cells beside the strip are
  clipped, not dropped, and the strip's own end corner is the one point that comes closer than the
  grown boundary).
- **Its near edge is still a straight limit, not an arc about the stem axis** — cut to an arc it
  crossed the hole's flare cone at a shallow angle and left a 0.034 mm facet, and cut to the
  keep-out ring itself it sat at distance 0.0000 mm from three window cutters and the fuse produced
  a solid whose shell is closed and whose faces are all valid while the solid itself is not
  (`isValid` False, build/f151/gen-8T.log). The nose's tip stands at `stem_keep_r() +
  PAD_RING_CLEAR` off the near stem axis; the rest of the ellipse falls away from the
  ring faster than the ring does.
- A note for whoever re-shapes it: `skin_cutter()` offsets its rings along the surface **normal**,
  which fans out over psi — harmless for a window, wrong for a rib 1.42 mm deep and 2 mm wide,
  whose end face came out a 45 deg twisted surface (f150). An annular sector (constant z, r and
  azimuth faces) is geometrically cleaner and gave a better bench wall min, but the CR-10 Pro then
  failed on the pre-existing bulb-dome graze facet; the sector is kept as a comment in the function.

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
| a flat facet or step on the duct's crest | a lattice cutter reached inside the duct's outer wall and nibbled the crest | the crest band: no window within `crest_half` of a duct crest, enforced in uv and by a solid guard | f086, f087 |
| solid skin beside a duct, wider than the duct: 6 mm of it each side with nothing under it | `CREST_BAND` = `DUCT_BORE` / 2 is the air's half-width at the centreline, not the duct's reach under the skin | `crest_half()` measures the duct's own reach at the cutter's floor (AIR_KEEP off the air, CUT_FACE_CLEAR off the wall face) | f156 |
| wavy streaks on the INSIDE of the duct tube in the slicer | tessellation, not the model: the bore's BSpline sweep is exact to 0.006 mm of a true R 12 tube (`ductgeom.py`), but the mesher covers it with 1.25 mm facets sitting 0.0154 mm inside that tube - the chord sag of 1.25 mm on R 12 | tighten `make_fcstd.py`'s deflection; at 0.010 mm / 0.03 rad the facets are 0.63 mm and 0.0043 mm, but that mesh self-intersects elsewhere, so the ladder takes the finest that is watertight AND self-intersection-free (0.015 mm / 0.05 rad) | f156 |
| the mesh is watertight, the volume matches the STEP, and the checker still fails the STL | the mesher folds facets over each other on a fine setting: `selfint True` at 0.010 mm / 0.03 rad with 427,286 facets and an otherwise clean report | `make_fcstd.py`'s ladder tests hasSelfIntersections() as well as isSolid() and steps up | f156 |
| thin reading 0.19-0.38 mm all round the stem hole's rim, and adding material does not change it | the hole is bored along the radial line but the skin's normal at the rim is tilted atan((A/B) tan psi) = 13.85 deg, so the ray meets the hole's wall at a graze | flare the hole by `STEM_FLARE` + 1.5 deg so its wall is parallel to the skin normal; a chamfer makes it worse | f086, f117 |
| thin reading 0.005-0.3 mm where the bulb's dome, the duct tube, the shroud turn or the shaft crosses the seam face; the minimum moves with the mesh deflection and the sample count | the wall map fires one ray per facet along that facet's normal, and every surface of revolution is parallel to the seam face's rays: a facet d from the crossing circle reads d/2 (a corner distance, not a wall) | `GRAZE_DEG` = 10 deg: skip and count a hit whose face meets the ray at less than 10 deg; f151's grazeprobe.py shows a real 0.15 mm wall is still reported | f148, f150, f151 |
| one facet reads 0.01-0.03 mm and has area 0.000 mm2 | degenerate mesh facets from the mesher, whose normal is noise; the 6000-facet stride decides whether one lands in the sample | `MIN_FACET_AREA` 1e-4 mm2: skip them as ray sources and targets; and `make_fcstd.py`'s ladder, which used to stop at 0.03 mm, now takes the finest deflection that is watertight and free of self-intersections | f149, f148, f156 |
| a real 0.027-0.034 mm2 planar face in the STEP at the servo pad's edge, read as 0.033 mm, only at 1.41 | NOT a rib line: `servo_pad()`'s own tool, alone with no lattice and no fuse, carries those faces at BOTH scales - degenerate cap triangles off the tile grid (see 5). What changes with scale is which of them ends over a window opening, where the wall map can see it, instead of buried in the band | `TILE_EDGE` in `skin_cutter()`'s tile grid, plus trimming the pad's far edge to `SERVO_BRACKET_L` / 2 + `PAD_EDGE_CLEAR` and placing the outline with `outline_rib_clear()`. Do not cut the pad to an arc about the stem axis (invalid solid) | f151 found it, f154 fixed it |
| one sampled facet 0.027-0.055 mm2 whose ray reads 0.03 mm to a face sharing two of its vertices | a degenerate triangle: three near-collinear points, so its normal is noise and the ray leaves it sideways. All three vertices sit at one cap depth, so it is a cap triangle, not a wall | do not let the tiling make one: `TILE_EDGE` keeps `skin_cutter()`'s interior grid lines off the outline's own vertices. `MIN_FACET_AREA` only skips facets under 1e-4 mm2, so a 0.027 mm2 one is a real FAIL | f154 |
| a fused rib's own face sits 0.005 mm off a lattice window's wall: one pair of self-intersecting facets at any deflection, and a handful of 0.005-0.02 mm wall readings, all at one spot | `clip_window()`'s last act is an erode-dilate by `POLY_CLOSE`, and that closes the boundary back OUT across a keep-out edge it had been clipped to | re-subtract the keep-out polygons after the closing (`bitten`), then take the largest part | f156 |
| the generator prints "lattice-wall clearance 0.00 mm" for the servo mount and a rebuild is spent on it | `outline_rib_clear` was handed the outline grown by `BRACE_EDGE_CLEAR`: the lattice's walls lie on that boundary by construction, so it reads 0.00 mm always | measure the feature's OWN outline against the walls (`mo[0]`, not `mo[1]`); the real number is 0.436 mm at bench | f156 |
| the pad and the beam of one feature fuse to a SHELL (volume 0.0 mm3, isValid False) when probed alone, and in the real part leave a swarm of 0.02-1.9 mm2 faces along one edge, one self-intersecting facet pair at every deflection, and 0.005 mm wall readings | two `skin_cutter` tools over the SAME outline at DIFFERENT depths: their rings are offset along the skin's normal, which fans over psi, so their side faces are coplanar to 0.0002-0.0075 mm rather than coincident, and the boolean cannot close them | **one tool over one outline at one depth** (`_mount_tool(max(2 * T, BRACE_D))`, f158). f156's answer - inset the deeper tool 0.8 mm inside the outline where they overlap - only MOVED the sliver (it followed the pad tool's own inner face, r 206.23-206.39 mm, wherever that was), and the step between the two depths is itself a feature rhY marked ("no step, no ridge"). Probe a feature's tools alone before building: `build/f156/toolprobe.py` | f156, fixed f158 |
| the wall map fails the STL with 0.005-0.05 mm readings in a band under the mount, and six rebuilds of standoffs, clips and fills move it without removing it | the mount was ONE outline built as TWO tools at TWO depths (above); the fills then tried to hide it by removing the clipped windows beside it | take the real cause out: one tool, one depth. Then put the fills back: f158 deleted "fill a cell the outline bites by > 5 %" and "fill a cell within 2 mm of it", cut any cell the mount covers wholly, and the wall map passes at 0.357 mm (1 facet of 5550 under the nozzle) where f156 read 0.007 mm at 8 facets | f156, fixed f158 |
| a rebuild is spent because a filled cell is wanted "for strength" and the print comes back heavier than the task before it | a keep-out that FILLS instead of CLIPPING removes lattice windows, and a lattice window is where the mass already is: f156's fills cost +2.5 cm3 of skin at bench, +7 cm3 at CR-10 Pro | a keep-out may only ever REMOVE area from a window (clip it), never add skin; when a solid feature needs a wall under it, build the wall as the feature and let the lattice cut under it | f156 (rhY: "the weight is too much"), f158 |
| 0.01 mm wall readings and a chain of 0.05-2 mm2 Plane faces 0.024-0.08 mm apart, at 1.41 only, along the mount's nose and along its strip (r 289-291, az -19..-21, z -13..-21) | a corridor the cut walls share: 0.6 mm between the stem ring's clipped window wall and the mount's own nose face (`PAD_RING_CLEAR`), and 1.5 mm between a clipped window's wall and the mount's side face (`BRACE_EDGE_CLEAR`) - at the bigger print a cutter's cap tile lands in that corridor and the boolean resolves it into slivers | widen the corridor: `PAD_RING_CLEAR` 0.6 -> 2.5 and `BRACE_EDGE_CLEAR` 1.5 -> 2.5 (measured at 1.41: the mesh stopped self-intersecting at every deflection, `build/f158/cr10-r6.log`). The bench print never showed it, which is why the standoffs were raised only after a 1.41 rebuild (`build/f158/faces-seam.log`) |
| a clipped window's wall 0.013 mm off the mount's own side face, mid-strip (r 290, z 4, az -6: the blend where the ring narrows into the strip) | the lattice keep-out clip maps the mount's grown ring through each cell's own uv map and resamples it as a polyline, so the clip boundary wanders ~0.01 mm off the curve `BRACE_EDGE_CLEAR` is meant to measure | NOT FIXED, and growing the clip is the wrong lever: `poly.buffer(BRACE_EDGE_CLEAR + 0.1, ...)` in `servo_mount_outline`, then `+ 0.03`, put the self-intersections back at every deflection (`build/f158/cr10-r7.log`, `cr10-r8.log`). Teach the probe to ignore a hit on the same face, or stop the blend touching the strip side line | f158 |
| opening the seam junctions (f158 R1) makes a self-intersecting mesh at EVERY mesh deflection at 1.41, plus a swarm of 0.0001-1.5 mm2 faces around r 290, az -19..-22, z 14-21 and a 0.30 mm wall at the seam | the junction and the two ovals beside it are clipped by the SAME crest-band bite box, so their inner walls are one and the same face: a rib of zero width, which the boolean closes into a knife edge | a junction's bite stands `RIB` further out of the band than a cell's (`if others: half += RIB` in the band loop of `clip_window`) - the same distance a junction keeps from its ovals everywhere else. It only showed at 1.41: the bench cells happened to land clear of the tangent. R1 still ships closed (`SEAM_JUNCTION_OPEN` False): with the margin in, the opened window left the same face chain beside the mount's plate | f158 |
| 0.01 mm wall readings mid-strip at 1.41 (r 290, z 4-7, az -6..-8) with nothing wrong on the bench | `clip_window` maps the mount's outline through EACH cell's uv map; the strip runs the whole width of the lattice, so a cell 60-100 mm along the equator maps the strip's far end far outside itself, where that map folds | intersect the mapped bite with a box ONE CELL WIDTH around the cell before using it (a fixed 4.5 mm margin swallows it for long thin cells and the window census drops 57 -> 8) | f158 |
| 0.005/0.009 mm walls on the bench slice at r 205, z 4-7, az -2..+1 (f159's `build/f159/bench-r5.log`) after the mount-blend facet was gone | a cell wholly inside the mount's GROWN ring but crossed by its OWN outline was cut as an ordinary window, so the cell's raw lattice edge landed ON the mount's side face - coplanar to 0.0041-0.010 mm (`build/f162/facesfault-8t.log`: window walls f156/f157/f451 against mount faces f544-f548 at X 205.06-206.71) | clip it by the ACTUAL outline (`mo[0]`), standing `MOUNT_EDGE_CLEAR` 0.5 off its face; only a cell wholly inside that grown edge is cut as an ordinary window | f159 found it, f162 fixed it |
| opening the seam junctions leaves one strip of seam skin cut TWICE - the junctions of the rib above and below share a 492.89 mm2 region (`build/f159/layout.py`: junc r6 & r7 az -22 at 1.41, junc r5 & r6 at 1.0) - and at 1.41 that is where the mesh self-intersects | both seam junctions claimed the same cell between their ribs | a seam junction keeps ONLY the cell above its own rib (an end rib already keeps its one-sided cell), and every claim stands `RIB / 2` off the rib line that ends it: the web between two seam junctions is exactly RIB and the cuts never meet | standing the two halves to MEET on the rib line instead (no setback) leaves 0.010 mm walls at 1.0 and 0.005 mm + eight open edges at 1.41 - each frame chords the rib v-line its own way, 0.010-0.041 mm apart, and one shared azimuth grid (step 0.004 rad) did not fix it (`build/f162/rebuild-r2/r3/r4.log`, `facesfault-r2.log`); the mass cost of claiming once is the SPILL f159's straddling windows opened across the rib line (+3.5 cm3, 44.98 -> 48.50), and no legal variant wins it back (see 10's f162 row) | f159 found it, f162 fixed it |
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
| 2026-11-19 | the f154 print, four crops | "Diamond on the central band is half filled. Let's fill it all the way."; "Brace around the servo looks stupid and isn't flush with the outer hull ellipse" with a sketch of a waisted ring round the hole flowing into the beam and into the duct bulb, fillet radius >= 5 mm, no corners; "Too much material on the outer hull near the duct. There should only be duct and lattice, no extra material"; wavy streaks on the INSIDE of the duct tube | seam junctions the duct band bites are filled whole; one waisted mount outline (`servo_mount_outline`); `crest_half()` measures the band beside each duct instead of `CREST_BAND`; the mesh deflection tightened to the finest clean mesh | f156 |
| 2026-11-19 | the f156 print, outside and inside, four more crops | "The half diamonds by the ducts need to be emptied for weight. Clip them by the ducts and the other clearance and open them up, instead of filling them all." (R1, reversing item 1 of the same review); "The equator is all wrong, with filled ovoids, diamonds, and a weird vestigial equatorial brace that sticks out inside and does not perfectly conform to the AirShip's outer hull ellipse. Make it look like this" + "NO filled ovoid cells and NO filled diamonds" + "only as big as SF 3 needs", "no straight segment, no step, no ridge", "The servo mount is a compact ring round the spline hole blended into that strip, not a big waisted pad" (R2); "the weight is now too much: we will need to shave it down 10 grams" (R3, a hard 60 g gate on the CR-10 Pro slice); and A: "The coincident or near-coincident faces that leave sliver walls and break the solid under the servo mount - find the two faces within 0.3 mm of each other there and remove the cause per section 8" | the mount is ONE `skin_cutter` tool at ONE depth (`_mount_tool`, `PAD_T` = `max(2 * T, BRACE_D)`), so there is no second side wall to leave coplanar to the first: bench wall min 0.007 -> 0.357 mm and the gate passes; the outline is ring + one blend + a `BRACE_W` strip (2129 mm2, not 2370, no bulb flare, no cap); seam junctions the crest band bites are clipped and opened again; a cell the mount covers wholly is cut, and the "bite > 5 %" / "within 2 mm" fills are deleted (`MOUNT_KEEP` 0.6 takes their place) | f158 |

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
- **f156 rhY review: diamonds, servo mount, duct band, duct inside — OK.** Four crops, four
  different kinds of fix, and three of them were "the rule was right, the number behind it was
  measured at the wrong place". (1) A seam junction the duct band bites was cut as an outer piece
  with the band's clip running through it, so the diamond was half filled: `clip_window()` now
  fills such a junction whole. (2) The servo mount was a rounded rectangle plus a
  square-ended beam: one waisted outline now (`servo_mount_outline`), least radius 6.00 mm, and
  `check_flush.py` proves the flushness was never the problem — the old mount's outer surface was
  already on the hull ellipse to +0.000 mm over 11,562 points, because `skin_cutter` builds every
  tool from the skin. What rhY was objecting to was the silhouette, not the surface. (3) The band
  beside each duct was `CREST_BAND` = `DUCT_BORE` / 2 = 12 mm at every psi: that is the air's
  half-width *at the centreline*, while the centreline sits 12.84 mm under the outer face, so a
  cutter whose floor is 1.16 mm down meets the tube 5.3 mm from the seam plane and the other 6 mm
  each side was solid skin over nothing. `crest_half()` now measures the duct's reach where the
  cutter actually is (6.0 mm beside the tube, 7.0 beside the bulb), and the layout and the clip
  both take the widest value over the cell (`crest_half_cell`) so they cannot disagree. (4) The
  streaks inside the duct: measured the surface exactly first (`ductgeom.py`,
  `BRepAdaptor_Surface.Value`, no tessellation) — the BSpline sweep is within 0.006 mm of a true
  R 12 tube, so it is the mesh: 1.25 mm facets sitting 0.0154 mm inside the tube, which is the
  chord sag of 1.25 mm on R 12. Tightening to 0.010 mm / 0.03 rad gives 0.63 mm and 0.0043 mm but
  the mesher then folds facets over each other and the checker fails the STL for
  self-intersections, so `make_fcstd.py`'s ladder now rejects a mesh that is not both watertight
  and self-intersection-free and lands on 0.015 mm / 0.05 rad. Worked: measuring before changing,
  and writing the probe as the thing that states the rule (`mountshape.py`, `ductband.py`,
  `boreshape.py`); `brace_sizing.py --check` reading the mount's footprint out of the generator so
  the sizing cannot drift from the shape. Differently: hasSelfIntersections() returns a bool in
  FreeCAD 1.1, not a list — len() on it is a probe bug, not a part bug; and the Standard
  mesher's facet size on a BSpline sweep does follow LinearDeflection (1.25 -> 0.63 mm), which I
  first mis-measured with a filter that selected facets by the very deviation it was reporting.

  NOT FINISHED, and this is the part to read before touching the mount again: the waisted mount
  does not pass `check_outputs.py` yet. Six rebuilds, and every one ends with 1-2 sampled facets
  reading 0.005-0.035 mm somewhere within 1.5 mm of the mount's edge - never the same place twice
  (the beam's edge at u 62, the bulb flare at az 16-17, the taper at az -1 z +-7). Each narrower
  rule only moved it: clip the cell (fix 1), re-apply the bite after `POLY_CLOSE` (fix 2), butt
  the beam's two pieces instead of overlapping them (fix 4), drop a cell the outline bites by 5 %
  (fix 3), drop a cell that merely comes within 2 mm of it (fix 5), `BRACE_EDGE_CLEAR` 0.5 -> 1.5
  (fix 6) - and fix 5 and fix 6 changed nothing measurable, which is the tell: the last pair is
  the pad tool's own inner face (r 206.23-206.39 = `PAD_T` 1.5 under the outer face) against a face
  at r 205.93-205.99, 1.78-1.84 mm down, which is no depth the generator asks for. It is a fragment
  of the boolean, at the taper, where the outline's concave waist makes the tool's 1 mm side facets
  twist along the depth. Next step, in order of cost: probe the pad tool ALONE at the taper
  (`toolprobe.py` already does the fuse) and see whether the fragment is there before the lattice
  is cut; if it is, the mount's tools need a coarser/curvature-aware outline spacing than
  `OUT_MESH` 1.0 mm, or the waist's least radius (6.00 mm) needs raising past 5 mm;
  if it is not, the fragment comes from a lattice cutter and the keep-out rule is still wrong.
  Fix 7 already answered half of that: making the whole mount ONE depth (`max(2 * T, BRACE_D)`
  under the pad instead of `PAD_T`) did not remove the sliver, it MOVED it - the thin blob went
  from r 206 to r 205, i.e. it follows the pad tool's inner face wherever that is - and cost
  1.5 cm3. So the pair is a DOUBLED CAP on the pad tool itself, not a pad/beam interaction: look at
  how `skin_cutter` closes the tool's inner end when the outline has a concave waist, not at the
  keep-out. Fix 7 is reverted.
  Items 1, 3 and 4 of f156 are measured and clean on their own.
  **f156's last paragraph was wrong, and fix 7 was right the first time.** The doubled cap was not
  in `skin_cutter`: it was the second `skin_cutter` over the same outline at a second depth, and
  "fix 7 reverted" put the pair back. f158 built the mount as one tool at one depth and the thin
  blobs at r 204-206 went with it - bench wall min 0.007 -> 0.357 mm, `--thin-report` now lists one
  blob, 0 mm2, at r 33 z -64 az -22 (the keel sleeve, not the mount). See f158 below.
- **f158 mount sliver, weight, duct band — OK.** A: the two faces within 0.3 mm of each other under
  the mount are the two side walls of ONE outline built as TWO `skin_cutter` tools at TWO depths
  (0.0003-0.008 mm apart, chains at r 205.9-206.4); the cause is gone by making the mount one tool
  at one depth (`_mount_tool(max(2 * T, BRACE_D))`), not by another standoff. R2: the mount is a
  compact ring (`MOUNT_RING` 13 under the bracket's whole foot) blended into a `BRACE_W` strip on
  the equator - no flare, no bulb, no cap, no step - 2129 mm2 instead of 2370, least visible radius
  6.23 mm, and its outline's two long edges now run along the lattice's own equator rib instead of
  faults f158 found and fixed at 1.41 only, and the bench print never saw them: (i) a clipped
  seam junction clipped by the crest band's own box left a rib of zero width beside its ovals -
  self-intersecting mesh at every deflection; a junction's bite now stands `RIB` further out;
  (ii) the 0.6 mm corridor between the stem ring's clipped window wall and the mount's nose face
  (`PAD_RING_CLEAR`) and the 1.5 mm corridor between a clipped window and the mount's side face
  (`BRACE_EDGE_CLEAR`) filled with chains of 0.05-2 mm2 faces 0.024-0.08 mm apart - both raised to
  2.5 mm, and the mesh stopped self-intersecting (`build/f158/faces-seam.log`, `cr10-r6.log`);
  (iii) growing the lattice clip by 0.1 mm, then 0.03 mm, to chase a 0.013 mm wall read at the
  blend's tangent join put the self-intersections straight back - the clip must stay exactly
  `BRACE_EDGE_CLEAR` (`cr10-r7.log`, `cr10-r8.log`). R1: seam junctions the crest band bites are clipped and opened
  again (f156 item 1 reversed); `crest_half()` is 5.93 mm beside the tube and 6.82 beside the bulb
  at bench, 0 above it, measured against the cutter's floor 1.16 mm under the skin. B: the fills
  that chased the sliver are deleted - a cell the mount covers wholly is cut, a cell it crosses is
  clipped, `MOUNT_KEEP` 0.6 fills only what would be a crescent - and the mount's mass is one depth
  instead of two.

  Worked: `build/f158/mountshape.py` (the outline's area, least radius, bond coverage and the
  window census, no CAD built, 2 minutes) before any rebuild; `build/f158/regionmass.py` (freecadcmd
  box-booleans on the STEP: grams by region - equator, by-duct, rest - which is how the 10 g was
  aimed at the right regions instead of guessed away); keeping f156's STLs and STEP in the scratch
  folder so before/after is a measurement, not a recollection; the bench rebuild as the cheap test
  (4 min) before the CR-10 Pro one.
  Two faults the cheap census could not see, because both are only at 1.41 (rule: **run the bigger
  print, the bench can pass while the scale that rhY prints on fails**) -
  (i) opening the seam junctions clipped them with the crest band's bite box, the SAME box the two
  ovals beside them are clipped with, so the rib between a junction and its neighbours had zero
  width: a swarm of 0.0001-1.5 mm2 faces at r 290, az -19..-22, z 14-21, a self-intersecting mesh
  at every deflection, a 0.30 mm wall at the seam. A junction's bite now stands `RIB` further out
  of the band than a cell's, which is the distance a junction keeps from its ovals everywhere else.
  (ii) `clip_window` maps the mount's outline through each cell's own uv map, and the strip runs the
  whole width of the lattice: a cell 60-100 mm along the equator maps the strip's far end far
  outside itself, where that map folds, and the bite's edge wanders 0.01 mm off a wall (r 290,
  z 4-7, az -6..-8). The mapped bite is now intersected with a box one CELL WIDTH around the cell -
  and the margin has to be a length, not a constant: a fixed 4.5 mm swallowed the bite for the long
  thin cells and the window census fell 57 -> 8, which is the tell to read immediately.
  Differently: the fill rules were never a fix - f156's own log says fixes 5 and 6 "changed nothing
  measurable", and they cost 7 cm3 at CR-10 Pro; a task that ends with "NOT FINISHED, six rebuilds"
  should have ended by probing the one tool that owns the face. And `freecadcmd` takes every
  command-line argument as a file to RUN, so a probe that wants paths must read them from the
  environment (`STEPS=`), or it dies as "Unknown extension".

## Summary: f156 before / after

| | before (main 8c3224c, f154) | after (f156) |
|---|---|---|
| bench 8T slice | 30.76 cm3 = 38.1 g PLA | 33.76 cm3 = 41.9 g PLA |
| CR-10 Pro slice (scale 1.41) | 45.08 cm3 = 55.9 g PLA | 58.38 cm3 = 72.4 g PLA |
| lattice windows, bench | 36 | 40 (item 3 opens cells the 12 mm band used to close; item 2's keep-out closes others) |
| solid skin beside a duct seam | 12.00 mm each side (`CREST_BAND`) | 6.0-7.0 mm (`crest_half`), 0 above the bulb |
| seam junctions the band bites | half solid, half slit | filled whole |
| servo mount | 42.4 x 28.2 mm rounded rectangle + a separate 9.0 x 2.5 beam, 1190 mm2 | one waisted outline, 2370 mm2, least radius 6.00 mm, bracket footprint 95.4 % covered, bonded area 977 mm2 |
| worst SF of the mount | beam 3.13, pad plate 3.25 | beam 3.13, pad plate 3.25, bond 314, peel 916 (`brace_sizing.py --check` PASS) |
| outer-surface flushness over the mount | +0.000 mm proud of the hull ellipse (11,562 points) | +0.000 mm proud |
| duct bore in the print STL | facets 1.25 mm on a side, 0.0154 mm inside the true R 12 tube | facets ~0.7 mm, ~0.005 mm inside |
| mesh | 0.03 mm / 0.1 rad, 115,658 facets, 9.7 MB | 0.015 mm / 0.05 rad, ~205,000 facets, 17.5 MB (cap 90 MB) |
| wall minimum, bench / CR-10 Pro | 0.42 mm / 0.44 mm | 0.005 mm at 2 facets by the mount's taper - NOT YET PASSING, see section 10 f156 |

## Summary: f158 before / after

| | before (f156, parked) | after (f158) |
|---|---|---|
| bench 8T slice | 33.76 cm3 = 41.9 g PLA | 30.97 cm3 = 38.4 g PLA |
| CR-10 Pro slice (scale 1.41) | 58.38 cm3 = 72.4 g PLA | 48.58 cm3 = 60.2 g PLA — 12.2 g off, the 60.0 g gate is 0.2 g away |
| wall minimum, bench / CR-10 Pro | 0.007 mm (8 facets) / 0.005 mm — FAILS | 0.341 mm — bench **PASS** / 0.013 mm at 1 facet, 0 mm2 — CR-10 Pro, the blend's tangent join, still FAIL |
| checker verdict, bench / CR-10 Pro | FAIL / FAIL | **PASS** (`Analysis/build/f158/gate.txt`) / FAIL by one 0 mm2 facet and 0.2 g |
| self-intersecting mesh at 1.41 | no | no (the standoffs `PAD_RING_CLEAR` 2.5 / `BRACE_EDGE_CLEAR` 2.5 removed it: `build/f158/cr10-r6.log`) |
| lattice windows cut, bench | 40 | 40 — but the cells the mount crosses are now CLIPPED, not filled, and the mount carries one depth instead of two |
| servo mount | one waisted outline, 2370 mm2, two depths (pad 1.5 / beam 2.5), bulb flare + rounded cap | ring + one blend + `BRACE_W` strip, 2129 mm2, ONE depth 2.5, no flare / bulb / cap |
| mass by region, bench (equator / by-duct / rest) | 4.72 / 11.20 / 16.87 cm3 | 5.18 / 10.22 / 14.49 cm3 |
| seam junctions the band bites | filled whole | clip machinery in (`clip_window`, a `RIB` further out of the band), shipped closed: `SEAM_JUNCTION_OPEN` False |
| worst SF of the mount | beam 3.13, pad plate 3.25, bond 314, peel 916 | beam 3.13, pad plate 9.02, bond 314, peel 916 (`brace_sizing.py --check` PASS) |
| outer-surface flushness over the mount | +0.000 mm | +0.000 mm (unchanged) |

Two faults f158 leaves open, measured not guessed:

- **one wall reading, 0.013 mm at one facet** (r 290, z 4, az -6), where the ring's cosine blend
  meets the strip's side face. The join is tangent (C1) by construction, so a ray through a facet
  there hits the same continuous surface 0.013 mm away — the checker's grazing filter skipped 9
  such hits and kept this one. It is 0 mm2 of material, not a wall: the fix is either a graze rule
  that ignores a hit on the *same* face, or an outline whose blend does not touch the strip's
  side line. Growing the lattice clip instead (+0.1, then +0.03) is the wrong fix: it put the
  self-intersections back at every mesh deflection (`build/f158/cr10-r7.log`, `cr10-r8.log`).
- **0.2 g over the 60 g gate**: 48.58 cm3 = 60.2 g at 1.41 (the gate wants 48.39 cm3). The slice
  went 72.4 -> 60.2 g, so rhY's "shave it down 10 grams" is met and then some, but the gate is
  absolute. The next step measured here is not to shave the mount (it is at SF 3.13 with a 9.0 mm
  strip) but one more clipped cell, or `PAD_RING_CLEAR` back toward 2.0 mm.

- **f159 open the half-diamonds, the blend facet, 0.2 g — see below.** R1 shipped
  `SEAM_JUNCTION_OPEN` True; the CR-10 Pro went 60.2 -> 56.9 g, and the 0.013 mm facet at the
  mount's blend is gone (wall min 0.471 mm, no facet under the 0.40 mm nozzle).

## Summary: f159 before / after

| | before (f158, parked) | after (f159) |
|---|---|---|
| CR-10 Pro slice (scale 1.41) | 48.58 cm3 = 60.2 g, 0.2 g over the 60.0 g gate | 45.92 cm3 = 56.9 g (`build/f159/cr10-r2.log`) |
| wall minimum, CR-10 Pro | 0.013 mm at 1 facet, 0 mm2, by the ring blend | 0.471 mm, no facet under the nozzle, 0 under the layer |
| thin blobs, CR-10 Pro | 0.013 mm at r 290 z 4 az -6 | none under 0.40 mm |
| self-intersecting mesh at 1.41 | no | yes, at the far seam (r 290.7, az 21.5, z 17.5) where an opened half-diamond necks - see below |
| seam junctions the band bites | shipped closed, `SEAM_JUNCTION_OPEN` False | open: `SEAM_JUNCTION_OPEN` True, closed at half a rib in `clip_window` |
| lattice windows cut, 1.41 | 62 | 76 (the 14 seam junctions the duct bands bite) |
| open skin area, 1.41 | 107072 mm2 | 113397 mm2 (`build/f159/layout.py`) |

What worked:

- **The 0.013 mm facet at the mount's ring blend was never a blend fault.** `windows()` and
  `junction()` re-interpolated each clipped window's ring at 96 (oval) / 80 (junction) evenly
  spaced points, so two cells sharing ONE curved keep-out boundary - and the grown servo-mount
  clip is the only curved boundary a cell meets, at the blend - carried two different chord
  polylines on that one curve. The boolean then leaves whatever the chords differ by: 0.008-0.013
  mm. `resample_ring(ring, OUT_MESH)` keeps the polygon's own vertices and spreads them, so both
  cells carry the same polyline, the two walls are one surface, and the facet is gone: CR-10 Pro
  wall min 0.008 -> 0.471 mm and no facet under the 0.40 mm nozzle, bench unchanged at PASS.
  The probes that found it: `build/f159/mountonly.py` (the mount's tool ALONE, no lattice:
  0.0024 mm face pairs at the blend, so it is not a lattice interaction), `build/f159/layout.py`
  (the lattice layout in one global skin frame: no pair of cut boundaries within 0.05 mm, so it
  is not the layout), `build/f159/outlineprobe.py` (the blend's own outline is clean: no vertex
  pair within 0.5 mm). Three negatives and a change of the discretization.
- **R1's grams**: 14 seam junctions open, 6325 mm2 more skin windowed, 1.76 mm deep = 11.1 cm3,
  60.2 -> 56.9 g. Item 3 is met with 3 g of margin, so `MIN_KEEP` and the strip-end lever that
  f158 measured stay as they were.
- **R1's leftover fault is a NECK, not a coincident face.** `build/f159/selfint.log` (run of
  `build/f158/selfint.py`) put the self-intersection at r 290.7, az 21.5, z 17.5 - the far seam -
  and `build/f159/facesseam.log` shows a chain of 0.000-0.038 mm2 Plane faces there: an opened
  half-diamond pinched to a point by two of its own keep-outs (the crest band's box and the
  outlet's stem ring). The fix is to ask the opened diamond to be rib-wide ALREADY: erode then
  dilate it by `RIB / 2` and compare, and leave the junction FILLED when that closing would change
  the region. Closing it and keeping the result is the wrong fix - it moves a boundary the other
  clearances were measured against, and at the bench it put an opened junction's wall 0.007 mm off
  the servo strip's own side face (`build/f159/bench-r4.log`): section 8's rule that a cut boundary
  may never land on a face the part already has.

- **f162 the double claim, the junction setback, the spill skin — see below.** f159's R1
  shipped the junctions open but its claim was double: the strip of seam skin between two ribs was
  cut TWICE, shared as a 492.89 mm2 region by the junctions of the rib above and the rib below
  (`build/f159/layout.py`), and that is where the 1.41 mesh self-intersected. f162 claimed each
  strip once - a seam junction keeps only the cell above its own rib - and first tried meeting the
  two halves ON the rib line, with no setback. That failed on walls at both scales: 0.010 mm at 1.0
  (3 of 5477 sampled facets, blobs r 199 z -30 az -20/-18) and 0.005 mm at 12 facets plus eight
  open edges, not watertight, at 1.41 (`build/f162/rebuild-r2.log`): each junction chords the rib
  v-line in its own uv frame, and the two polylines sit 0.010-0.041 mm apart
  (`build/f162/facesfault-r2.log`: f8211-f8214 vs f8306-f8311 at r 198.7, z -29.5, az -17..-20).
  Resampling both junctions' shared ends onto ONE global azimuth grid (step 0.004 rad) failed the
  same way (`build/f162/rebuild-r3/r4.log`) - two uv maps of one coordinate line are not one
  polyline, however you grid them; the rib end must STAND CLEAR (`RIB / 2`, the web between two
  seam junctions exactly RIB), not meet. What cost the grams was NOT the setback (meet vs
  setback: 0.35 cm3) and NOT any fill - the `MOUNT_KEEP` fill never fired under the plate
  (r1 vs r5: the SAME 48,849 mm3). It is the SPILL: f159's junction windows straddled the rib
  line, so each strip opened ~2.6 cm3 of skin beyond it, into the next strip - and claiming
  that skin twice is what cut the same opening twice and self-intersected. Claim-once killed
  the spill: +3.5 cm3, 44.98 -> 48.50 (double vs meet, `rebuild-r2.log`). Dead ends, measured:
  a MOUNT_GRAZE test to reopen the mount's crossed cells found ZERO cells that may open at
  1.41 (`build/f162/layout-f159mount.log` probe) and put the coplanar 0.005 mm facet back at
  1.0 (`build/f162/rebuild-r6.log`: r 205.1 z 4.5 az 0.1); `PAD_RING_CLEAR` 2.5 -> 2.0 (f159's
  named lever) gained no mass (48,875 mm3) and brought the 0.008 mm face chain back at BOTH
  scales - f158's reason for 2.5 stands. The legal floor: 48.85 cm3 = 60.6 g, 8T PASS wall min
  0.357 mm, CR-10 Pro PASS wall min 0.696 mm, no selfint (`build/f162/rebuild-r5.log`, r7
  reproduces) - 0.6 g over the 60.0 g gate, which was measured on the double-claimed spill.

## Summary: f162 before / after

| | before (f159, merged) | after (f162) |
|---|---|---|
| CR-10 Pro slice (scale 1.41) | 44.98 cm3 = 55.8 g (`build/f159/cr10-r4.log`) but the seam strip was double-claimed - its spill skin opened twice - and the 1.41 mesh self-intersected (`build/f159/selfint.log`) | 48.85 cm3 = 60.6 g, PASS wall min 0.696 mm, no selfint, watertight - 0.6 g over the 60.0 g gate (`build/f162/rebuild-r5.log`) |
| 8T slice (scale 1.0) | FAIL: 0.005/0.009 mm walls at r 205, z 4-7, az -2..+1 (`build/f159/bench-r5.log`) - the mount's grown edge | PASS: clip the crossed cell `MOUNT_EDGE_CLEAR` 0.5 off the actual edge (rebuild-r5 wall min 0.357 mm) |
| seam strip between two ribs | claimed twice, a 492.89 mm2 region cut by both junctions, plus ~2.6 cm3 of spill skin across the rib line | claimed once, the web between two seam junctions exactly `RIB` |
| mass levers tried | - | fill-skip under the plate: neutral; graze-reopen: zero legal candidates (probe), coplanar wall back at 1.0 (r6); `PAD_RING_CLEAR` 2.0: no gain, 0.008 mm chain (r6) |


## Summary: f167 before / after (ship the seam CLOSED, under 60 g)

| | before (f162, parked, seam open) | after (f167, seam CLOSED) |
|---|---|---|
| CR-10 Pro slice, 1.41 | 48.85 cm3 = 60.6 g (open), parked | 49.74 cm3 = 61.6 g, 1.6 g over the 60.0 g gate |
| seam junctions | open, `SEAM_JUNCTION_OPEN` True | closed, `SEAM_JUNCTION_OPEN` False, filled whole |
| wall min, CR-10 Pro | (open) blend facet gone | 0.005 / 0.011 mm at r 290.1, z +/-7, az -8 (ring-blend tangent, closed config) |
| 8T slice | f159 FAIL at r 205 | PASS, wall min 0.484 mm, no selfint |

f167 resumed f159 (kept `resample_ring`), kept f162's `MOUNT_EDGE_CLEAR` mount clip, and shipped the
seam CLOSED as issue #36 asks. It did NOT pass the gate, and the reason is the model, not a bug:
closing the seam restores the duct-junction skin (22.0 g of the 61.6 g, `regionmass.py`), and
`resample_ring` costs ~+1.1 cm3 at 1.41 over f158's closed 60.2 g, so the closed model is 61.6 g.
The r 290.1 blend facet is the pair `resample_ring` only clears in the open config, and it is present
with and without the mount clip. The levers that remain each break a rule (open the seam -> self-int
at 1.41; narrow `PAD_RING_CLEAR`/`BRACE_EDGE_CLEAR` -> f158's 0.01 mm slivers; shave the brace ->
SF 3.13). 8T ships clean. `build/f167/{rebuild-r1,rebuild-cr10-committed,diag-nomountclip}.sh`,
`build/f167/{check-8t,check-cr10,diag,regionmass}.log`.
