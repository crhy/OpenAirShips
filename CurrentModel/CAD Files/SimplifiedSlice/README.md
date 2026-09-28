# Airship pie slice 926, v0.1: 8- and 4-thruster designs, bench and Kobra Max sizes

One 45° slice of the hull; eight of them plug together into the full ship. The source is one parametric file that builds every version:

| Version | Slices | Print file (in `Print Files/`) | Size | Printer |
|---|---|---|---|---|
| **8 thrusters, bench** | 8 identical | `PieSlice926-v0.1-8T.stl` | 415 mm across | Prusa MK3S+ (or any 210 × 210 mm bed) |
| **4 thrusters, bench** | 4 left + 4 right, alternating | `PieSlice926-v0.1-4T-left.stl`, `…-4T-right.stl` | 415 mm | Prusa MK3S+ |
| **8 thrusters, Kobra Max** | 8 identical | `PieSlice926-v0.1-8T-KobraMax.stl` | 790 mm | Anycubic Kobra Max (400 × 400 × 450 mm) |
| **4 thrusters, Kobra Max** | 4 left + 4 right | `PieSlice926-v0.1-4T-left-KobraMax.stl`, `…-right-KobraMax.stl` | 790 mm | Kobra Max |

It keeps the outline of `OldFiles/CAD/airship pie slice 125.FCStd` (archived at the repository root): the 207.765 × 104 mm ellipse, rebuilt as clean parametric geometry. See [../../DESIGN-CONSTRAINTS.md](../../DESIGN-CONSTRAINTS.md) for the fixed rules and [../../Analysis/FLOAT.md](../../Analysis/FLOAT.md) for weights, hydrogen volume and lift.

![8 thrusters: section through a seam](../../Renders/v0.1-8T-section.png)
![4 thrusters, Kobra Max size](../../Renders/v0.1-4T-KobraMax-ship.png)
![slice, outside](slice_front.png)
![slice, inside](slice_inside.png)
![slice from below](slice_below.png)

## What's in a slice
- **Skin:** a smooth ellipsoid outside. The skin runs in one arc from the keel up over the top and **rolls into the intake shaft over a 12 mm bellmouth**.
- **Intake shaft:** a plain 0.86 mm tube, **Ø66 all the way from the bellmouth down to the impeller eye.** Nothing is inside it: no ledge, no spider, no windows. It must stay solid and smooth for the craft's Coanda intake flow.
  - Up to v0 the shaft was Ø95 and narrowed at the bottom. That width was only needed to drop the impeller in from the top, and it now comes in through the keel hatch.
  - The narrower shaft costs about 1% of the fan pressure and gives the gas cells about 0.6 L more room.
- **Shrouded fan housing:** the housing *is* the fan's shroud.
  - At the bottom of the shaft the wall turns from axial to radial over the blade tips, with 1.5 mm clearance, and runs out flat as the housing ceiling. That's z = −71.3 for 8 thrusters, or 10 mm higher for 4 thrusters so the bigger duct mouths fit.
  - At r = 66 the ceiling slopes down to meet the keel at r = 80.
  - The housing holds the impeller (r 44) and the duct mouths (r ≈ 58–60). **The keel is solid only around this housing.**
- **Fan hatch opening:** the keel under the fan is a Ø94 opening that the impeller and motor come in and out through. A ring wall round it carries this slice's **bayonet lug** and **stop post**. The removable `fan_hatch` (see `../Propulsion`) locks onto the 8 lugs.
- **Ducts:** they run *inside* the skin from their mouths in the fan housing up to the equator, where each ends in a bulb behind the stem hole and its bearing sleeve. Each duct is split by a seam plane, so two slices close it. Their own 0.86 mm walls keep them airtight; the lattice runs straight over them.
  - **8 thrusters:** Ø24 ducts on every seam, a Ø32 bulb and a Ø25.4 stem hole.
  - **4 thrusters:** Ø34 ducts on every other seam (twice the flow each), a Ø44 bulb and a Ø34.4 stem hole. A **left** slice carries its half-duct on its +22.5° seam; a **right** slice carries it on its −22.5° seam, plus the servo hole. Assemble them alternating, left, right, left, right, so each pair closes one duct.
- **Lattice:** everything else is structure only.
  - Two columns of large oval cells, with 2.0 mm ribs.
  - **Every row is the same length along the skin:** five rows from the fan housing up to the equator, six above it (about 33 mm at bench size and 73 mm at Kobra Max size). All the cells therefore have the same proportions, top and bottom.
  - A **ring rib on the equator (z = 0)** carries the thruster stem and servo holes. Thrusters stay exactly on the equator, for navigation.
  - **Every junction is a hollow diamond.** On the seams each slice has a hollow half-diamond that stops at a continuous 1 mm edge strip.
- **Joints:** 5 bosses along each seam, all at the same (r, z) positions. The +22.5° seam has Ø3 × 3.6 mm pegs and the −22.5° seam has Ø3.3 × 4.2 mm holes, both with 0.4 mm chamfers.

## Kobra Max size (x1.9)
- **What grows:** only the hull outline and its lattice cells grow 1.9×, to 790 mm across.
- **What stays the same size:** walls (0.86 mm), ribs (2 mm), joints, the fan, the ducts, the thrusters and the servos.
- **Why not just scale the STL:** printed mass grows about as size^1.3 while the hydrogen volume grows as size³ (124 L instead of 16 L). Scaling the STL uniformly would thicken every wall too, and the ratio would never improve.
- **Print volume:** each slice lies on its seam, 372 × 393 × 279 mm. That fits the Kobra Max's 400 × 400 × 450 mm with about 3 mm to spare each side, so **use a skirt, not a brim**, or rotate the part a few degrees on the bed.

## Checked (every version)
- Each part is a single valid solid, and only the 5 pegs stick out of the hull.
- Neighbouring slices overlap by 0 mm³ (for 4 thrusters: left against right, on both seams).
- **Airtight:** the keel round the hatch, the housing/shroud wall and the shaft wall are complete; their only openings are where the ducts leave the housing. The duct walls' only openings are the stem holes.
- No material sits inside the shaft or the impeller eye.
- The STLs are watertight.
- `../Propulsion/check_fit.py` passes all 35 checks for all four versions.

## Weight and volume
Weights and lift for every version and material are in [Analysis/FLOAT.md](../../Analysis/FLOAT.md).

| Version | Printed hull (8 slices) | PLA | Moderate-foam lightweight PLA | Hydrogen volume |
|---|---|---|---|---|
| 8 thrusters, bench | 243 cm³ | 302 g | 195 g | 16.4 L |
| 4 thrusters, bench | 214 cm³ | 265 g | 171 g | 16.3 L |
| 8 thrusters, Kobra Max | 561 cm³ | 695 g | 449 g | 124 L |
| 4 thrusters, Kobra Max | 495 cm³ | 613 g | 396 g | 124 L |

## Printing
- **Walls:** 0.20 mm layers, 0.4 mm nozzle, 2 perimeters, with no infill needed (the walls are 2 lines thick). Don't let "detect thin walls" change them.
- **Orientation:** every STL is already laid flat on its −22.5° seam. The skin never overhangs more than 45°. Oval tips and diamond corners point up, so the ribs are carried by sloping edges rather than bridges.
- **Supports:** on build plate only. Paint them inside the duct arch lying on the bed; nothing else needs support.
- **Airtight seams:** when assembling, epoxy the seams of the shaft, the housing wall, the keel round the hatch ring, and the ducts. Tape the hatch's outside seam.
- **Earlier versions:** v0 (Ø95 shaft) and revs A–D are archived in `OldFiles/PrintFiles`. RevB and revC have a duct leak, so don't print them.

### Lightweight (foaming) PLA
It saves about a third of the hull's weight; see the table above.
- **How it works:** the filament foams as it prints hotter, so you print the same lines with less plastic.
- **Airtight walls:** the shaft, housing and ducts must stay airtight. Use moderate foam (about 0.8 g/cm³) and print a small test piece of a duct first. Blow into it, or put it under water with a little air pressure.
  - If it leaks, lower the temperature and raise the flow, or brush a thin coat of epoxy inside the ducts.
- **Starting settings (MK3S+ or Kobra Max, 0.4 mm nozzle):**
  - Use the filament maker's profile if there is one.
  - Nozzle 230–245 °C for moderate foam (about 250 °C for full foam), bed 55 °C.
  - Flow (extrusion multiplier) 0.60–0.70 for moderate foam (0.45–0.55 for full foam). Calibrate on a single-wall cube to the density you want.
  - Retraction short and slow (about 0.8 mm at 25 mm/s on the MK3S+, a direct drive; 3–4 mm on the Kobra Max's Bowden), plus wipe/coast to fight stringing.
  - Part cooling 50–100%, speed 40–60 mm/s.
- **What to print in it:** the hull slices, thruster rings and servo mounts. Keep the stems, gears and fan hatch in standard PLA (accurate teeth, bearing surfaces and bayonet tabs). Keep the impeller in PETG, and never foam it: its tip runs at 72 m/s, and uneven foam would throw it out of balance.

## Files
- **FreeCAD documents:** `airship pie slice 926[ 4T left| 4T right][ x1.9].FCStd`. Each holds the part as the base feature of a PartDesign Body, plus a parameter spreadsheet.
- **STEP:** the same parts, in the matching `.step` files.
- **`airship_slice.py`:** the parametric source (CadQuery). Everything is set at the top of the file. The version is chosen with environment variables:
  - `OAS_VARIANT=8T|4T`
  - `OAS_SIDE=L|R` (4 thrusters only)
  - `OAS_SCALE=1|1.9`
- **`make_fcstd.py`:** builds the FCStd and the print STL for the same settings.

To regenerate, for example the right-hand 4-thruster Kobra Max slice:
```
pip install cadquery
OAS_VARIANT=4T OAS_SIDE=R OAS_SCALE=1.9 python3 airship_slice.py
OAS_VARIANT=4T OAS_SIDE=R OAS_SCALE=1.9 freecadcmd make_fcstd.py
```
