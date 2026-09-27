# Changelog: 926 buildable bench model

## v0.1.1: Kobra Max size, lightweight PLA and the float budget (September 2026)

**Kobra Max versions (x1.9, 790 mm across)** of both the 8- and 4-thruster designs.
- Each slice prints on an Anycubic Kobra Max: 372 × 393 × 279 mm on its 400 × 400 × 450 mm volume.
- Only the hull outline and lattice grow. Walls, ribs, joints, fan, ducts, thrusters and servos keep their size, so the hydrogen volume grows 7.5× (16 L → 124 L) while printed mass grows about 2.3×.
- All checks and the 35 fit checks pass for both.
- **Files:**
  - STL: `Print Files/PieSlice926-v0.1-8T-KobraMax.stl`, `…-4T-left-KobraMax.stl`, `…-4T-right-KobraMax.stl`
  - propulsion: `CAD Files/Propulsion/x1.9/` and `4T/x1.9/`
  - renders: `Renders/v0.1-4T-KobraMax-*.png`

**Will it float?** [Analysis/FLOAT.md](Analysis/FLOAT.md) is a new mass, hydrogen-lift and thrust budget for every version and material, generated from the CAD. Numbers are airborne and tethered.

| 4 thrusters | Mass | H₂ volume | H₂ lift | Lift ÷ mass | H₂ + fan − mass |
|---|---|---|---|---|---|
| Bench, lightweight PLA (moderate foam) | 452 g | 16.3 L | 18 g | 4% | −12 g |
| Bench, lightweight PLA (full foam) | 390 g | 16.3 L | 18 g | 5% | **+50 g (hovers with the fan)** |
| Kobra Max, lightweight PLA (moderate foam) | 742 g | 124 L | 139 g | 19% | −185 g |
| Kobra Max, lightweight PLA (full foam) | 624 g | 124 L | 139 g | 22% | −67 g |

- Floating on hydrogen alone needs about x4.1–4.6 size, a 1.7–1.9 m hull. That's a lower bound, with today's thin walls.

**Lightweight (foaming) PLA** is now a BOM option (item 13b), with print settings in the slice README.

**Fixes:** the fan hatch is rebuilt from a keel cap instead of the whole hull ellipsoid, whose degenerate pole made some exports invalid. All hatch exports are now valid and watertight.

## v0.1: two designs, 8 and 4 thrusters, and a narrower intake (September 2026)

- **Narrow intake:** the shaft is now **Ø66 all the way up** (it was Ø95, narrowing at the bottom).
  - The width was only needed to drop the impeller in from the top, and it now comes in through the keel hatch.
  - The cost is about 1% of the fan pressure. The gas cells gain about 0.6 L and the hull loses about 2 g per slice.
- **New 4-thruster design,** alongside the 8-thruster one:
  - 4 thrusters on alternate seams (at 22.5°, 112.5°, 202.5° and 292.5°), still exactly on the equator.
  - Ø34 ducts, Ø34/31 stems, 72 mm rings with a 2.0 mm slot, and 44-tooth gears, sized for twice the flow per thruster ([AIRFLOW-4T.md](Analysis/AIRFLOW-4T.md)).
  - The housing ceiling is 10 mm higher so the bigger duct mouths fit.
  - **4 left + 4 right slices**, alternating. Each pair closes one duct, and the right slice carries the servo.
  - Expected thrust ≈ 422 gf, slightly more than 8 thrusters (408 gf), with 4 fewer servos and thrusters. The hull is 12% lighter.
- **Files:**
  - `Print Files/PieSlice926-v0.1-8T.stl`, `…-4T-left.stl`, `…-4T-right.stl`
  - FreeCAD/STEP in `CAD Files/SimplifiedSlice/` and `CAD Files/Propulsion/` (4 thrusters: `4T/`)
  - renders in `Renders/`
- **Parametric:** `airship_slice.py` and `propulsion.py` build every version from `OAS_VARIANT=8T|4T`, `OAS_SIDE=L|R` and `OAS_SCALE`.
- **Checks:** every slice passes the solid, airtightness and overlap checks, and all 35 fit checks pass for both designs.
- The v0 slice STL is archived as `OldFiles/PrintFiles/PieSlice926-v0-revE.stl`.


## v0: first buildable model (September 2026)

The v0 files are archived in `OldFiles/PrintFiles/PieSlice926-v0-revE.stl`, and in the `v0` release.

The first complete, printable version of the 926 tethered bench demo. It includes the hull, the shrouded fan, 8 vectoring air-multiplier thrusters, the electronics, firmware, BOM and airflow analysis.

**Files**
- **Printable STL:**
  - Hull slice (print 8): [`OldFiles/PrintFiles/PieSlice926-v0-revE.stl`](../OldFiles/PrintFiles/PieSlice926-v0-revE.stl) (archived)
  - Propulsion parts: [`CAD Files/Propulsion/print/`](CAD%20Files/Propulsion/print)
- **CAD (FreeCAD):**
  - [`airship pie slice 926.FCStd`](CAD%20Files/SimplifiedSlice/airship%20pie%20slice%20926.FCStd)
  - [`propulsion 926.FCStd`](CAD%20Files/Propulsion/propulsion%20926.FCStd)
  - STEP files and parametric CadQuery sources sit next to them.
- **BOM:** [`Electronics/BOM.md`](Electronics/BOM.md). Core parts cost about $230–320.
- **Build notes:**
  - [slice](CAD%20Files/SimplifiedSlice/README.md)
  - [propulsion](CAD%20Files/Propulsion/README.md)
  - [electronics](Electronics/README.md)
  - [airflow analysis](Analysis/AIRFLOW.md)
  - [design constraints](DESIGN-CONSTRAINTS.md)

### Hull (slice rev E)
- **Simplified from the 125 design into 8 identical 45° slices** that plug together, with pegs on one seam and holes on the other.
- **Smooth outside:** the 207.765 × 104 mm ellipsoid. The thrust ducts run inside the skin, and only the thruster stems and servo hubs pass through it.
- **One continuous arc from keel to intake.** The top trough, shelf and lip are gone; the skin rolls into the intake shaft over a 12 mm bellmouth.
- **No decks.** Both interior floors are removed for the bench model.
- **Lattice everywhere except the air path:**
  - two columns of large oval cells with 2.0 mm ribs
  - hollow diamonds at every junction, and hollow half-diamonds on the seams
  - a continuous 1 mm edge strip along each seam
- **Smooth intake shaft:** the motor ledge and spider are gone, and nothing sits in the shaft bore.
- **Shrouded fan housing:**
  - The shaft narrows smoothly to the Ø66 impeller eye, then the housing wall turns over the blade tips with 1.5 mm clearance. This closes the 3.4 mm leak path back up the shaft.
  - The housing is only as big as the fan and the duct mouths (it meets the keel at r = 80 mm).
- **Removable fan hatch:** the keel under the fan is a bayonet hatch that carries the motor and impeller. It locks with an 11.5° clockwise turn, and the motor's torque keeps it locked.
- **Thrusters exactly on the equator (z = 0)**, for navigation.
- **0.86 mm walls** (2 perimeters, the airtight minimum on a 0.4 mm nozzle).
- **Weight:**
  - about 32 cm³ (≈ 40 g of PLA) per slice, down from 48 g in rev D, so ≈ 320 g for the hull
  - about 16 L of free interior space
- **Print setup:** each slice prints on its seam on a Prusa MK3S+, 207 × 201 × 146 mm, with supports only inside the duct arch on the bed.

### Propulsion
- **Motor:** 2207 1750 KV on 4S (≈ 32 g, ≈ 25 A peak), chosen by the airflow analysis. It replaces the A2212.
- **Impeller:** 88 mm backward-curved, printed in PETG (≈ 8 g).
  - eye Ø66, exit width 12.5 mm, blade tops following the shroud curve
  - a cup over the motor bell, clamped by the prop nut
- **8 air-multiplier thrusters:**
  - a Coanda ring with a 1.6 mm slot on a Ø25/22 stem
  - each swivels ±90° on a radial axis, driven by an MG90S servo through a 1:1 36-tooth gear pair
- **Expected thrust:** about 4.0 N (≈ 410 gf) at 15,650 rpm and 62 L/s, with a range of 306–564 gf until the bench measurements are in. A shrouded fan efficiency of 0.42 is assumed.
- **Fit checks:** `check_fit.py` runs 35 clash and clearance checks against the assembled hull, and they all pass.

### Electronics and firmware
- **Controller:** ESP32 + PCA9685, with a Wi-Fi slider control page, ESC arming and a link-loss failsafe. The mixer unit tests pass on a PC; it hasn't yet run on real hardware.
- **Power:** a 4S LiPo or a 15 V 350 W supply feeding a 45 A ESC, with a 5 V UBEC for the servos.

### Known limits
- Bench-test only: hover needs about 8.6 N, and hydrogen in the free volume lifts only about 18 g.
- The fan efficiency, air-multiplier gain and swivel leakage are estimates. Measure them on the bench and rerun `Analysis/airflow.py`.

### Earlier revisions
- **Rev A–D slices** and the older 125/1224 models are archived in [`OldFiles/`](../OldFiles) at the repository root.
- **RevB and revC have a duct leak.** Don't print them.
