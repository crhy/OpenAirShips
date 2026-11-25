# CAD review — 8T CR-10 Pro slice (issue #36), report only

Source: `CurrentModel/CAD Files/SimplifiedSlice/airship_slice.py` (3044 lines, not
3483 as the task said), variant `OAS_VARIANT=8T OAS_SCALE=1.41 OAS_TAG=CR10Pro`.
Measured against the STEP `airship pie slice 1026 CR10Pro.step` with
`/home/rhy/.venvs/cadquery/bin/python -I` (OCP/OCCT). Scratch probes:
`CurrentModel/Analysis/build/c01/probe{,2,3,5}.py` (git-ignored). No geometry
changed — gate `git diff --quiet origin/main -- "CurrentModel/CAD Files"
"CurrentModel/Print Files"` holds.

Whole-solid baseline (probe.py): **1 solid, 1 shell, BRepCheck_Analyzer valid=True**,
volume **45 079.576 mm³**, **11 228 faces**, **8 663 faces < 1 mm²**, **300 faces <
0.05 mm²**. So the mesh checks pass (one watertight body) while the slicer sees
D1–D5: they live in the B-rep face layout, which the STL export hides.

Topology crack scan (probe2.py, pairwise face-distance over non-adjacent faces):
**1 797** bbox-close pairs, of which **123 are < 0.05 mm, 94 < 0.02 mm, and 82
exactly coincident (0.0000 mm)**. Coincident pairs cluster in three places: the
servo mount/pad (x≈270–290, y≈−57…−100, z≈−10…14), the keel/housing root
(x≈50–70, z≈−140), and the top bellmouth/rim band (x≈50–130, z≈130–140). This is
issue #36's "0.005–0.05 mm sliver walls / coincident faces" symptom
(CONSTRUCTION-NOTES §8 rows for f085/f148/f151/f154).

## D1 — seam lines / cracks through solid parts
Where: the servo-mount plate with its round hole, and the long keel arm down to the
rectangular pad with a hole.

Functions: `build()` 2959–3019 (the fuse sequence 2986–3007), `servo_brace()` 2366,
`servo_pad()` 2433 (near edge 2463, `outline()` 2465–2488).

Cause in code: the part is assembled by fusing touching solids one tool at a time —
`body.fuse(bosses + sleeves)` (2986), then `brace`, `pad` (2994–2996), then duct
walls `at_seams(walls)` (2999), then `pegs` (3007). Two of these are known to touch
almost on purpose: the docstring at 2989–2993 says **the brace and the pad overlap
by 117 mm³** and that fusing them as one compound *breaks the body* (45 679 mm³ in
2 solids, 307 faces instead of 8 399), so they are fused separately. Every near-touch
is then resolved with a **fuzzy boolean `tol=1e-4`** (window cut 2973, duct fuse
3001) — a fuzzy fuse keeps both faces instead of welding them, leaving the internal /
coincident faces the slicer cracks open. `servo_pad`'s near edge (2463, 2486–2488) is
itself a documented culprit: 2471–2485 records that a straight edge "crossed the
hole's flare cone at a shallow angle … left a 0.028 mm² face of pad at (274.4, −99.8,
−9.5) with 0.034 mm of wall behind it, which is what the wall map fired on."

Measured: the coincident-face cluster sits exactly on the servo pad (x≈270–290,
y≈−57…−100, z≈−10…14) and the keel/housing root (x≈50–70, z≈−140); 82 face pairs at
distance 0.0000 mm and 123 pairs < 0.05 mm overall.

Smallest fix: stop relying on fuzzy booleans for the structural seams. Give the
brace↔pad junction a real margin (separate their tool volumes so they do not overlap
by 117 mm³, then fuse once cleanly), and keep the pad's near edge outside the whole
stem-flare swept volume by the existing `stem_keep_r() + PAD_RING_CLEAR` (2463) rather
than by a shallow-angled straight line — i.e. remove the `tol=1e-4` retry at 3001 by
pre-clearing the seam, so no coincident pair survives to the STEP.

## D2 — gap under the servo-mount plate
Where: the plate does not sit cleanly on the ring/tube below it.

Function: `servo_pad()` 2433–2525; the plate's near edge is placed at
`-SERVO_T + stem_keep_r() + PAD_RING_CLEAR` (2463) and `outline()` 2465–2488 cuts it.

Measured: the pad's planar underside cap (area 37.22 mm², bbox x 264.0–270.3,
y −106.6…−104.0, z 13.1–19.9) has a nearest **non-adjacent** face that is a **sphere**
(the bulb dome, centre (255.7, −100.5, 1.9), area 1 096 mm²) at a distance of
**0.2508 mm**. So the pad stands ~0.25 mm off the dome/tube wall instead of seating on
it — the "does not sit cleanly" gap. It is larger than a hairline but smaller than the
`PAD_RING_CLEAR` = 0.6 mm the code intends, so the intended ring clearance is being
eaten by the bulb dome rather than the stem ring.

Cause in code: the pad is fused *after* the lattice (2988–2996) and is meant to seat on
the uncut band round the stem boss (2445–2450), but the near edge is measured against
the **stem keep-out ring**, not the duct bulb that actually reaches there.

Smallest fix: measure/seat the pad's near edge against the duct bulb wall (the face it
actually meets) so the 0.25 mm gap closes onto a fused face, or pull the near edge
inside the ring so the plate lands on the tube rather than floating 0.25 mm clear.

## D3 — loose pieces: peg/post beside the half-dome; thin strut in air
Where: a small peg stands beside the bulb (half-dome) without joining it; a thin strut
near the cup ends in air.

Functions: `joint_parts()` 2526–2577 (pegs 2557–2561, `peg` 2558),
`bulb_joints()` 933, `corner_joints()` 1044; `build()` fuses pegs at 3007 and bosses at
2986.

Measured: exactly **4 pegs of radius 1.5 mm** (and 4 mating holes r=1.65) exist;
probe5 reports each peg has **no mating hole within 6 mm** — e.g. pegs at
(243.0, 102.4, −13.4), (264.7, 111.4, 16.4), (32.0, 15.0, −105.9), (32.0, 15.0, 132.9).
This is partly by design: pegs are laid on the **+HALF** seam and holes on the
**−HALF** seam, so they mate **across slices**, and inside one slice a peg tip is a
free end (the chamfered tip edge 2559–2561). The slicer therefore sees a "post beside
the dome that doesn't join anything" in the single printed body. There are **6 298
faces < 0.6 mm²**, the tiny free-end caps.

Cause in code: CONSTRUCTION-NOTES §8 (rows found by f117/f149) calls this exact symptom
out: "a peg or boss is a loose body … the joint was placed where there is no wall," and
"the crest wall carries no peg." `joint_parts` already guards duct seams (2539–2549,
2555–2556) but a peg whose hole falls in the *other* slice still prints as a free stub.

Smallest fix: report-only here, but the fix is to drop any joint whose mating wall is
not in the same printable body (extend the `in_duct`/seam guard in `joint_parts`
2539–2556 to skip a peg whose hole seam is not in this piece), matching the §8 rule
"check a wall exists before moving a joint."

## D4 — rectangular slots cut through the curved top rim band
Where: unintended rectangular slots through the curved top rim of the lattice.

Functions: `clip_window()` 1745–1950, `junction()` 1953, `windows()` 2100, with
`lattice_band()` 1735.

Cause in code: every cell is clipped by **axis-aligned shapely boxes** — the band edges
`v_keep = box(...)` (1800), the seam planes `u_keep = box(...)` (1809), the crest band
`bite = box(...)` (1826), the outlet ring `disc` (1857–1860), and the brace corridor
`bite = box(...)` (1912). These boxes are straight in the uv tangent frame; where a
cell sits on the *curved* rim/bellmouth the band's edge is a curve, so a straight box
edge slices a rectangular notch through it. The docstring (1751–1760, 1804–1808) notes
the cells at "the true half-cells at the top and bottom of the lattice" are exactly the
ones the band's END cuts.

Measured: the crack cluster at the **top bellmouth / rim band** (x≈50–130, z≈130–140)
lines up with these box clips; the coincident/hairline pairs there are the straight
box edge lying on the curved band face.

Smallest fix: clip the rim cells against the curved band boundary
(`lattice_band()`/`crest_psi_range()` arc sampled in uv) instead of an axis-aligned
`box`, or inset the box edge by `CELL_CLOSE`/`CREST_EDGE_CLEAR` so it never lands on the
curved band face.

## D5 — lattice ovals overlap each other and the rim unevenly
Where: ovals overlap each other and the rim; some struts only graze neighbours.

Functions: `oval_on_skin()` 1268, `windows()` 2100, `junction()` 1953; the neighbour
clip in `clip_window()` 1935–1941; rule 4 (`MIN_WEB` = 0).

Cause in code: `MIN_WEB` = 0 runs the lattice "right out to the edges" (AGENTS rule 4),
so neighbouring cells share a rib line and their ovals meet at a hairline. Where two
ovals meet, `clip_window` does `poly.difference(others.buffer(MIN_WEB))` (1937) — with
`MIN_WEB` = 0 that buffer is zero, so the boundary between two windows lands exactly on
the shared rib and two oval walls touch (graze) rather than being separated by a real
web. Near the rim the oval layout (`junction`/`column_bounds`) is uneven because the
band's END cuts half-cells (1803) while inner cells stay full.

Measured: consistent with the 123 sub-0.05 mm / 82 coincident pairs — the graze pairs
are the sub-0.05 mm neighbours; the 8 663 faces < 1 mm² are the thin webs between
grazing ovals.

Smallest fix: stand every neighbour window apart by a real rib: change the neighbour
`others.buffer(MIN_WEB)` (1937) to a positive web width, and lay the ovals short of the
rim (give `column_bounds`/`junction` a non-zero rim inset) so the grazed struts meet
with a full web instead of touching.

## Script health
- Actual size: **3044 lines** (the task's "3483" overstates it — be honest, the file is
  3 044). **606 comment lines (~20 %)**; **130 lines reference a task id** from **11
  patch generations** (`f085, f086, f087, f117, f118, f148, f149, f150, f151, f152,
  f154`); **32 lines cite a `build/...` probe/log** as their evidence; **2 fuzzy-boolean
  `tol=1e-4` retries**; **4 `raise ValueError` build guards**.
- Most of the non-obvious logic is a *keep-clear constant* added to dodge one earlier
  failure: `CREST_EDGE_CLEAR`, `BRACE_EDGE_CLEAR`, `PAD_RING_CLEAR`, `BOSS_INSET`,
  `SKIN_TRIM`, `TILE_EDGE`, `RIM_KEEP`, `AIR_KEEP`, `JOINT_CLEAR`, `GRAZE_DEG`,
  `MIN_FACET_AREA`, `CELL_CLOSE`, `POLY_CLOSE`, `MIN_KEEP`. Each is a real physical
  guard, but the per-task edge offsets and the fuzzy-boolean retries are accretion over
  11 generations — the same problem (coincident clip faces → sliver walls) is patched
  separately in the uv clip, the duct fuse, the pad edge, and the checker.
- Would a clean rebuild from a written spec be smaller? Honestly, **probably yes but
  not dramatically.** The irreducible physics is small (T = 0.86, one wall, the duct
  using the skin as its wall, AIR_KEEP, joints only where two walls meet — AGENTS rules
  1–5). A spec-first rebuild would likely land well under 3 000 lines because it could
  keep clip boundaries apart by construction (one boolean pass with a global minimum
  separation) instead of layering 13 keep-clear constants and a fuzzy-boolean retry to
  undo the slivers the axis-box clips and shallow pad edges keep re-introducing. I
  cannot claim a firm number without building it, so: the *geometry intent* is ~5 rules,
  the *3 044 lines* are roughly those rules plus ~11 generations of "the cut landed on a
  face, nudge it by this constant" patches.
