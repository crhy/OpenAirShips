# Changelog: 926 buildable bench model

## v0: first buildable model (September 2026)

The first complete, printable version of the 926 tethered bench demo. It includes the hull, the shrouded fan, 8 vectoring air-multiplier thrusters, the electronics, firmware, BOM and airflow analysis.

**Files**
- **Printable STL:**
  - Hull slice (print 8): [`Print Files/PieSlice926clauderevE.stl`](Print%20Files/PieSlice926clauderevE.stl)
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
