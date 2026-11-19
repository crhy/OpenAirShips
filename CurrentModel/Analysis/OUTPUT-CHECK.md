# OUTPUT-CHECK: what is actually wrong with the CAD and print files

Audit of every `.FCStd`, `.step` and `.stl` under `CurrentModel/CAD Files` and
`CurrentModel/Print Files` — 14 + 66 + 23 = **103 files**.
Checker: `CurrentModel/Analysis/check_outputs.py`. Raw logs:
`/home/rhy/strata-fleet/tasks/logs-f072/final.txt`, `final.json`, `stl.json`,
`prusaslicer-info.txt`, `prusaslicer-info-propulsion.txt`.

**Result: 33 of 103 files fail. 0 STEP files fail.**

Re-measured after f073 fixed the FCStd writer (`Analysis/check_outputs.py --only
cad`): **all 14 `.FCStd` and all 66 `.step` files pass**. The 19 thin-walled STLs
still fail — that is f074's fix, not this one.

## The three real defects, ranked by how badly they break the thing

### 1. The CAD files cannot be regenerated — the generator's dependency is missing

`CurrentModel/CAD Files/SimplifiedSlice/airship_slice.py:563-564` imports
`shapely.geometry` and `shapely.ops`. `shapely` is **not installed** in the
cadquery venv (`/home/rhy/.venvs/cadquery/bin/python -c "import shapely"` →
`ModuleNotFoundError`), and the repo declares no requirements file at all.

Running the documented regeneration command dies inside the first window cut:

```
$ OAS_VARIANT=8T python3 airship_slice.py
  File "airship_slice.py", line 863, in build
  File "airship_slice.py", line 646, in windows
  File "airship_slice.py", line 563, in junction
ModuleNotFoundError: No module named 'shapely'
```

So nobody can rebuild a `.step`, and the `.FCStd` / `.stl` files drift from the
source silently. This is the root cause of #2 and #3.

### 2. Every `.FCStd` file is the *previous* release's document, renamed

(fixed by f073 — see “What f073 changed” near the end of this file; the numbers
below are what the audit measured, kept as the evidence)

All 14 store a document label from the 926 / v0.2 run while the file names say
1026 / v0.2.1:

| file | stored label |
|---|---|
| `airship pie slice 1026.FCStd` | `airship pie slice 926` |
| `airship pie slice 1026 v0.2.1 left (pieces).FCStd` | `airship pie slice 926 v0.2 left (pieces)` |
| `propulsion 1026 4T.FCStd` | `propulsion 926 4T` |
| … (all 14 follow this pattern) | |

They were written by **FreeCAD 1.0R39319**, not the 1.1.4 the README tells you
to use. FreeCAD 1.1.4 relabels a document from the file name when it opens it,
which is why the mismatch is invisible in the tree and why nobody noticed.

What that costs when you open one:

* every shape triggers `Recomputation required … geo element version change in
  <doc>#<obj>.Shape: 0.4 → 15.70200.5` — the element map is rebuilt on open;
* none of them contains a `GuiDocument.xml`, so there is no saved camera, no
  object visibility flags and no per-object colour: the viewer shows the model
  from the default view with default shading;
* the same 13 MB brep is stored **3-4 times** (36-42 MB uncompressed, 10-12 MB
  on disk), so the viewer loads three identical solids that sit exactly on
  each other and z-fight.

The geometry inside them is current — each slice `.FCStd` matches its `.step`
volume to the last digit — so this is a stale-container problem, not a
wrong-model problem.

### 3. Nineteen print files have walls thinner than the layer they are printed at

Measured per facet, inward thickness, on the shipped STLs:

| file | thinnest wall | facets under 0.40 mm nozzle | under 0.20 mm layer |
|---|---|---|---|
| `…plain-top-outer.stl` | **0.012 mm** | 394 / 8997 | 98 |
| `…right-top-outer.stl` | **0.012 mm** | 394 / 8997 | 98 |
| `…left-top-outer.stl` | **0.012 mm** | 394 / 8997 | 98 |
| `…plain-bottom-outer.stl` | **0.009 mm** | 405 / 9096 | 113 |
| `…plain-middle.stl` | 0.017 mm | 23 / 5345 | 18 |
| `…left-middle.stl` | 0.043 mm | 11 / 5926 | 3 |
| `…right-middle.stl` | 0.049 mm | 9 / 6095 | 3 |
| `…left-bottom-outer.stl` | 0.023 mm | 30 / 6174 | 7 |
| `…right-bottom-outer.stl` | 0.018 mm | 28 / 6118 | 8 |
| `…left-top-inner.stl` / `…right-top-inner.stl` / `…plain-top-inner.stl` | 0.038 mm | 6-7 | 1-2 |
| `…plain-bottom-inner.stl` | 0.028 mm | 2 | 1 |
| `PieSlice1026-v0.2.1-4T-left.stl` | 0.017 mm | 14 | 2 |
| `PieSlice1026-v0.2.1-4T-right.stl` | 0.125 mm | 6 | 1 |
| `PieSlice1026-v0.2.1-8T.stl` | 0.090 mm | 9 | 4 |
| `PieSlice1026-v0.2.1-8T-KobraMax.stl` | 0.023 mm | 11 | 6 |
| `PieSlice1026-v0.2.1-4T-left-KobraMax.stl` | 0.023 mm | 19 | 9 |
| `PieSlice1026-v0.2.1-4T-right-KobraMax.stl` | 0.042 mm | 14 | 6 |

A 0.012 mm wall at a 0.20 mm layer height is not a thin wall, it is a **hole**:
the slicer cannot lay a 1/17th-of-a-layer shell, so those facets become gaps in
the printed skin. That is what makes the prints trash, and it is invisible to
the slicer — PrusaSlicer reports all 59 print files as `manifold = yes`,
`number_of_parts = 1`, `exit = 0`, bed-fitting.

Where the thinness is, measured on the BREP rather than the mesh
(`pieces/airship pie slice 1026 4T plain 12s small x3.8/top_outer.step`):

* the hull wall is real: outer skin ↔ inner skin = **0.811 mm** minimum
  (nominal `T = 0.86` at `airship_slice.py:63`) — 2.15 nozzle widths, so every
  printed shell is 2 layers thick;
* `top_outer.step` has **6 faces with area < 1 mm²**; the smallest (0.216 mm²)
  sits at distance **0.00000 mm** from the skin surface it was cut by — a
  zero-thickness sliver left behind by a boolean, which is exactly the 0.009-0.012
  mm walls the mesh shows;
* the slivers cluster on the outer skin band (r ≈ 729 mm, z ≈ 151.5 mm, φ ≈ 0°
  at the x3.8 scale), i.e. where the window lattice meets the skin.

The code that produces them: `junction()` / `windows()` build each window as an
80-point polygon run through `.buffer(-0.6).buffer(0.6)` to round the tips
(`airship_slice.py:605`); where a window boundary grazes the skin that buffer
leaves a sliver, and `build()` (`airship_slice.py:854-873`) cuts windows one at
a time and *retries* any cut that had no effect, printing
`warning: window cut had no effect at …` — a known silent-degradation path.

## What is *not* broken (so the fix is aimed at the right thing)

* **Every STL is watertight and manifold.** FreeCAD: 0 open edges, 0 non-manifold
  edges, 0 self-intersections, correct orientation, positive volume, for all 23.
  PrusaSlicer agrees for all 59 print files.
* **Every STEP is a single valid closed solid.** 66/66: `isValid`, 1 solid, 1
  closed shell, 4,436-4,794 faces for the bench slices.
* **The print files match the CAD.** All 23 STLs match their source STEP within
  0.2 % volume; all 6 slice `.FCStd` files match their STEP exactly.
* **The pieces do not overlap.** The neighbouring slice solids share exactly
  0.000 mm³ of volume (measured with `common()` on the 12s small x3.8 pieces) —
  so the joints are butt joints on a `RIB/2 = 0.6 mm` edge strip
  (`airship_slice.py:70`, and the `RIB / 2` in the seam cutter box), 1.5 nozzle
  widths, with no tongue, no groove and no registration.
* **The STEP files load, but slowly:** 1.5-11.5 s for the bench-size slices
  (`airship pie slice 1026.step` = 32 MB, 4,436 faces, 11.5 s).
* **The meshing ladder is load-bearing.** `make_pieces.py:25` and
  `make_fcstd.py:59` mesh at 0.02 and then retry 0.015, 0.03, 0.01, 0.05 until
  the mesh is watertight. The three bench-size slice STEPs
  (`airship pie slice 1026.step`, `…4T left.step`, `…4T right.step`) mesh with
  **4 open edges at the first deflection of 0.02** and only close at the 0.015
  retry. `make_pieces.py:29-30` goes further: if *no* deflection gives a solid
  mesh it falls back to 0.02 plus `removeDuplicatedPoints()` to "close the few
  tessellation gaps" — a hand-closed mesh, not a watertight one.

## What f073 changed: the FCStd files now open and show the parts

The writer, not the model, was the problem. `make_fcstd.py` (both folders) and
`make_pieces.py` now go through one helper, `CAD Files/fcstd_doc.py`, which

* stores one `Part::Feature` per part and refuses to save a shape that is null,
  invalid, has no solid or has an open shell (`add_part()` raises instead of
  writing a document that shows nothing);
* drops the `PartDesign::Body` + base-feature wrapper, which stored the same
  brep three times (`SimplifiedSlice` documents went from 36-42 MB of brep in
  4 shape files to 12-14 MB in 1, and the viewer no longer loads three
  identical solids that z-fight);
* sets the document `Label` to the file name, so the tree matches the file
  (all 14 used to carry a 926 / v0.2 label);
* writes `GuiDocument.xml` itself — `freecadcmd` has no GUI, so FreeCAD never
  writes that file: one ViewProvider per part with `Visibility` on, its own
  colour and shaded display, plus a camera framed on the parts. Without it the
  GUI restores no camera, no per-object visibility and no display mode;
* saves with the running FreeCAD (1.1.4), so the stored element map version
  matches and the `Recomputation required … geo element version change 0.4 ->
  15.70200.5` message on open is gone.

All 14 files under `CurrentModel/CAD Files` were regenerated from the `.step`
files already on disk with `OAS_FCSTD_ONLY=1` (no `.step` or `.stl` touched —
that is f074's job). Command: `CurrentModel/Analysis/build/regen_fcstd.sh` in
the ignored build dir; log `build/regen_fcstd.log`.

Re-check (`build/cad2.log`, `build/cad2.json`): 80 CAD files checked, 80 pass,
0 fail. Every `.FCStd` line now reads `gui True`, and the only notes left on
them are the honest ones: the intake tubes and the `avionics_tray` are printed
parts that are not members of the documents they sit next to.

The checker got three changes with it: `--only cad` (`.FCStd` + `.step` only),
a GuiDocument.xml check (missing file, unparseable file, or a part with no
visible ViewObject is now a FAIL, not a note), and `compare_assembly()` matches
the document's objects to the sibling STEP files **by name** — it used to sum
every STEP under the folder, which for `pieces/` mixed the three slice types
and the intake tubes into one number.

## What f151 changed: three more root causes, all measured

### 1. The solid skin down each seam (issue #36, what rhY saw on the printed hull)

`clip_window()` dropped a cell **whole** whenever any clip changed it. The cells that
straddle a seam - the junctions on the seam rib lines - are exactly the ones the crest
band (`CREST_BAND` = 12 mm each side of a duct seam) changes, so all 26 of them were
dropped, and that is the hourglass of solid skin down each seam. Measured
(`Analysis/build/f151/cells.py`, bench 8T): the band takes **66-70 %** of such a cell's
raw polygon, so no "keep at least half" test measured against the raw polygon could ever
have opened them; the cell's own area - what the lattice's bounds leave, after the band,
the seam planes and the junction's two rows clip it - is the denominator, and against
that they keep 84-100 %.

The other half of the cause: a junction's polygon is not its cell. Along a seam the skin
more than `RIB` from the ovals runs the whole height of the hull, so the junction at the
equator rib spans psi -33..+33 deg, 10,207 mm2 raw, and 70 % of what the crest clip
leaves lies inside other rows' ovals - opening it as it stood would have cut the
horizontal ribs out. `junction(..., rows)` now clips every junction to the two rows it
sits in. With both fixes the bench slice cuts **58 windows where f150 cut 36**, and the
five cells still solid are the half-cells at each end of the lattice (4.5 and 16.6 mm2,
under `MIN_OPEN_AREA`).

### 2. The wall map's minimum moved with the tessellation, not with the model

The map fires one ray per facet along that facet's normal and takes the first face it
hits. Every surface of revolution in the slice - the duct bulb's dome, the duct tube,
the fan housing's shroud turn, the shaft - is **parallel to the seam face's own rays**,
so a facet on the seam face within a fraction of a mm of where one of them crosses it
reads 0.005-0.3 mm where the BREP wall is 0.80-0.86 mm. Measured on one and the same
STEP: min 0.194 mm at `LinearDeflection` 0.03 and 0.433 mm at 0.05, and at 15 000 or
40 000 samples *every* deflection finds such a facet (`Analysis/build/f151/meshprobe2.log`).
The gate's 6 000-facet stride was deciding pass or fail.

`check_outputs.py` now skips a hit whose face meets the ray at less than **`GRAZE_DEG` =
10 deg** and counts them ("grazing hits skipped N" on the summary line). A real thin wall
is hit near-perpendicular, so it is still found: `Analysis/build/f151/grazeprobe.py`
meshes a solid with one 0.86 mm wall and one 0.15 mm wall and the map reports 0.155 mm
with the rule on and off. This is the fix f150's own note asked for ("the fix belongs in
the checker - ignore a hit whose face lies within ~10 deg of the ray").

### 3. A clipped window's cut can silently do nothing

`build()` cuts the lattice one window at a time and stops if a cut removes less than
0.5 mm3. At `OAS_SCALE` 1.41 the bottom-row cutter at (88.7, -12.0, -139.4) did exactly
that: the plain boolean moved the body by **-0.006 mm3**. The tool is not wrong - it
contains the skin band's mid points, and its overlap with the band is 629.0 mm3 - and a
fuzzy cut (`tol=1e-4`) of the same tool removes **629.1 mm3 and leaves 0.000 mm3 inside
it**. Geometry fine, plain boolean unable to resolve it (f148 hit the same guard at the
keel rib at 1.41 and worked around it by moving the lattice's edge instead). `build()`
now retries a dead cut fuzzy before it raises, and `Analysis/build/f151/cutprobe.py` is
the probe that names the cutter and what it cost.

## How to run the checker

```
cd repos/OpenAirShips
flatpak run --command=freecadcmd org.freecad.FreeCAD \
    CurrentModel/Analysis/check_outputs.py \
    --pass "--json /home/rhy/strata-fleet/tasks/logs-f072/final.json"
```

CAD only (`.FCStd` + `.step`, ~7 min):

```
flatpak run --command=freecadcmd org.freecad.FreeCAD \
    CurrentModel/Analysis/check_outputs.py --pass "--only cad"
```

`freecadcmd` swallows anything that looks like an option unless it follows
`--pass`, and it tries to open every other bare argument as a file, so keep
all of this script's own arguments inside one quoted string after `--pass`.
This is not a quirk of this script: `freecadcmd … check_outputs.py --only cad`
fails in FreeCAD's own argument parser (`unrecognised option '--only'`, exit 1)
before the script starts, so the `--pass "…"` form is the only one that runs.
Useful flags: `--filter .stl` (STLs only, ~3 min), `--only cad|print`,
`--cad-root`, `--print-root`, `--no-slicer-compare`, `--thickness-samples N`,
`--no-tess`, `--no-thin`. Full run: ~12 min, 103 files.

## Fix list, in the order that unblocks the rest

1. `pip install shapely` into the cadquery venv and add a
   `CurrentModel/CAD Files/SimplifiedSlice/requirements.txt`
   (`cadquery`, `shapely`) — without this nothing else can be re-verified.
2. Re-run `airship_slice.py` for all 6 variants, then `make_fcstd.py` and
   `make_pieces.py`, so the `.FCStd` documents stop carrying 926 / v0.2 labels
   and stop storing the same brep 3-4 times. **Done by f073** — the documents
   were rebuilt from the STEP files on disk (`OAS_FCSTD_ONLY=1`), and the
   writer now also supplies `GuiDocument.xml`.
3. In `junction()` (`airship_slice.py:557`) / `windows()` (`:616`), drop the
   `.buffer(-0.6).buffer(0.6)` tip rounding (`:605`) or filter its result: reject
   any cut face whose area is < 1 mm² or whose distance to the skin is < 0.2 mm.
   Then re-measure with `check_outputs.py --filter .stl` and require 0 facets
   under the layer height.
4. Raise `T` (`airship_slice.py:63`) from 0.86 to at least 3 nozzle widths
   (1.2 mm) and `RIB` (`airship_slice.py:70`) so the joint strip is >= 2 layers,
   or add an explicit registration feature to the seam instead of relying on
   glue over a 0.6 mm butt joint.
5. Make `make_pieces.py` / `make_fcstd.py` fail loudly when the meshing ladder
   has to retry past the first deflection, instead of quietly accepting a mesh
   that only closes at 0.015.
