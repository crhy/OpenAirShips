# Airship pie slice 1026 (v0.2.1): 8- and 4-thruster designs, bench, Kobra Max and double-Kobra sizes

One 45° slice of the hull; eight of them plug together into the full ship. The source is one parametric file that builds every version:

| Version | Slices | Print file (in `Print Files/`) | Size | Printer |
|---|---|---|---|---|
| **8 thrusters, bench** | 8 identical | `PieSlice1026-v0.2.1-8T.stl` | 415 mm across | Prusa MK3S+ (or any 210 × 210 mm bed) |
| **4 thrusters, bench** | 4 left + 4 right, alternating | `PieSlice1026-v0.2.1-4T-left.stl`, `…-4T-right.stl` | 415 mm | Prusa MK3S+ |
| **8 thrusters, Kobra Max** | 8 identical | `PieSlice1026-v0.2.1-8T-KobraMax.stl` | 790 mm | Anycubic Kobra Max (400 × 400 × 450 mm) |
| **4 thrusters, Kobra Max** | 4 left + 4 right | `PieSlice1026-v0.2.1-4T-left-KobraMax.stl`, `…-right-KobraMax.stl` | 790 mm | Kobra Max |
| **8 thrusters, CR-10 Pro** | 8 identical | `PieSlice1026-v0.2.1-8T-CR10Pro.stl` | 586 mm | Creality CR-10 Pro (300 × 300 × 400 mm) |

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
  - Past the blade tips the ceiling eases down to meet the ducts' tops at their mouths. The outer wall stands just past the mouths, at r = 60.5, and drops straight to the keel.
  - The keel skin is the housing's floor. Each duct hugs the hull curve from its mouth, so **it runs straight on from the housing, flush top and bottom**, with no step for the air to trip over (since v0.2.1).
  - The housing holds the impeller (r 44) and the duct mouths (r ≈ 57–60). **The keel is solid only under this housing**; from its outer wall outward it's lattice.
- **Fan hatch opening:** the keel under the fan is a Ø94 opening that the impeller and motor come in and out through. A ring wall round it carries this slice's **bayonet lug** and **stop post**. The removable `fan_hatch` (see `../Propulsion`) locks onto the 8 lugs.
- **Ducts:** they run *inside* the skin, at a constant depth along the hull curve, from their mouths in the fan housing up to the equator, where each ends in a bulb behind the stem hole and its bearing sleeve. Each duct is split by a seam plane, so two slices close it. Their own 0.86 mm walls keep them airtight; the lattice runs straight over them.
  - **Solid skin round an outlet only where the hardware needs it:** a ring round each stem hole's bearing sleeve (the wider of the sleeve's Ø28 and the flared hole's own rim, plus 0.6 mm of wall: **14.6 mm**), and a ring round the servo-spline hole (**5.0 mm** = Ø8 + 1 mm). The lattice is *clipped* to those rings, so a cell a ring only grazes is still an open window with the ring bitten out of it instead of going solid. They used to be 15.5 mm and 7.5 mm, and the extra skin they dragged in was three full cells left solid round the outlet on the printed hull (rhY on the CR-10 Pro print).
  - **Servo brace and mounting pad (f150, strengthened by f151):** the equator beam runs from the servo mount to the duct on the far seam, **6.0 mm wide along the hull (`BRACE_W`) x 3.0 mm deep from the outer skin (`BRACE_D`)** - 18 mm2 of section, against the 2.0 x 1.72 mm (3.4 mm2) rib f150 shipped - standing 0.3 mm under the outer face and fused into the skin, into the far duct's outer wall (the uncut solid band round the stem's bearing boss) and into the mounting pad at its near end. It runs from 41.5 mm along the tangent past the servo's seam to the keep-out ring round the far stem hole - **107 mm of arc** at bench size (az −11.1° to +18.5°) and **174 mm** at CR-10 Pro, because the hardware does not scale - and neither does the beam: `servo_mount.stl` is one printed part, so the beam is the same 6.0 × 3.0 mm at every hull size (it only ever grows out of the hull's own rib: `max(RIB, BRACE_W)`).
    Under the bracket's footprint - **42.3 × 24.2 mm + 2 mm, centred on the Ø8 spline hole, long side along the equator** - the skin is solid and **1.5 mm thick counting the band** (`PAD_T`): that is what the 4.3 cm³ bracket is epoxied to, instead of a 0.86 mm skin with a 1477 mm² window in it. The pad's near edge stands **15.2 mm** off the stem hole's axis (`stem_keep_r` + `PAD_RING_CLEAR`), outside the hole's whole swept volume and 0.6 mm outside the ring the lattice's windows are clipped to, so it neither crosses the hole's flare cone at a shallow angle nor lands on a window's wall. Measured before building: beam **3.75 mm** and pad **5.12 mm** to the duct's air (rule: 0.6), pad **1.83 mm** to the stem hole, **19.5 mm** to the nearest joint, 1,297 + 792 mm³ of new material below the band = **2.59 g** a slice at bench size. The cells it crosses are re-flowed around it (windows stand 3.5 mm of arc off the equator there), so no window wall lands on it.
  - **8 thrusters:** Ø24 ducts on every seam, a Ø32 bulb and a Ø25.4 stem hole.
  - **4 thrusters:** Ø34 ducts on every other seam (twice the flow each), a Ø44 bulb and a Ø34.4 stem hole. A **left** slice carries its half-duct on its +22.5° seam; a **right** slice carries it on its −22.5° seam, plus the servo hole. Assemble them alternating, left, right, left, right, so each pair closes one duct.
- **Lattice:** everything else is structure only.
  - Two columns of large oval cells, with 2.0 mm ribs.
  - **Every row is the same length along the skin:** five rows from the fan housing up to the equator, six above it (about 33 mm at bench size and 73 mm at Kobra Max size). All the cells therefore have the same proportions, top and bottom.
  - A **ring rib on the equator (z = 0)** carries the thruster stem and servo holes. Thrusters stay exactly on the equator, for navigation.
  - **Minimum material:** the ovals are laid out on the real curved skin, so each fills its cell, touching all four rib lines. Every junction where ovals meet is a hollow window that takes *all* the skin more than 2 mm from the ovals, including along the first and last rows. What's left is a web of 2.0 mm ribs everywhere, and nothing thicker.
  - **Seams:** on the seams each slice's junction windows stop at a continuous 1 mm edge strip, so the two slices' strips glue into one full rib.
  - **A cell a keep-out trims is cut clipped, not dropped (f151):** the lattice's own bounds - the two ends of the band, the seam planes, the column edge the crest band sets, and the two rows a junction sits between - *clip* a cell; the outlet keep-outs then bite it, and a cell that keeps **≥ 50 %** of its own area (`MIN_KEEP`) is cut as *the cell minus the keep-outs*. Only the true half-cells at the top and bottom ends of the lattice, and anything under 20 mm², stay solid. Before this, any cell the crest band or a seam plane touched was dropped whole - the band takes 66-70 % of such a cell's raw polygon - which is what left an hourglass of solid skin down each seam: **36 windows a slice at bench size, now 58**, and the seam column is open from the equator to the duct's end and down to the keel rows.
- **Joints:** 4 per slice, each a Ø7 x 5 mm boss carrying a Ø3 x 3.6 mm peg on its +22.5° seam and a Ø3.3 x 4.2 mm hole on its -22.5° seam, both with 0.4 mm chamfers. Each one sits where two walls actually meet and is fused into BOTH of them; `airship pie slice 1026.joints.json` lists them by name with their (r, z) and what they are fused to (bench size, and in brackets the CR-10 Pro x1.41 size):
  - `corner_top` (r 35.25, z 89.46 / 132.86): the intake shaft's wall and the bellmouth where it rolls into the hull skin.
  - `corner_bottom` (r 35.25, z -63.30 / -105.94): the intake shaft's wall and the fan housing's ceiling.
  - `bulb_groove` (r 177.58, z -12.46 / 263.72, -13.40): the **inner** corner of the duct's bulb, where the tube wall's own face crosses the bulb's dome wall's face, on the dry side of the duct. The Ø7 boss bites 2.04 mm into each of the two walls; its hole keeps 0.61 mm of wall to the air path.
  - `bulb_outer` (r 201.49, z 15.70 / 287.21, 16.40): the **outer** corner of the bulb, where the dome wall meets the duct's outer side - which is the hull skin itself. Its apex, where the dome wall's face crosses the skin band's inner face, is 6.2 mm under the equator and inside the Ø25.4 stem slot, which is cut after the bosses are fused, so the boss sits on those same two wall faces as far out of the slot as the hole's 0.6 mm of wall allows: 0.46 mm of bite into each wall, 1.27 mm to the air, 1.35 mm to the slot, rim 0.4 mm under the outer skin.
  Both bulb corners are found as the intersection of the two wall faces (`bulb_inner_corner()`, `bulb_outer_corner()`), never as a point a fixed fraction of the way along the duct. The old `bulb_groove` at `duct_at(0.87)` was: measured, it bit 2.05 mm into the tube wall and **0.00 mm** into the dome wall at bench size (tangent to it, so one wall), and at CR-10 Pro size the same arc fraction put it **11.8 mm clear** of the dome wall.
  There is no joint on the duct's centreline any more: the wall there is the T = 0.86 mm skin band, so a Ø3.3 hole with 0.6 mm of wall to the air cannot exist in it, and the sleeve that would make it thick would have to stand outside the outer skin.

## Kobra Max size (x1.9)
- **What grows:** only the hull outline and its lattice cells grow 1.9×, to 790 mm across.
- **What stays the same size:** walls (0.86 mm), ribs (2 mm), joints, the fan, the ducts, the thrusters and the servos.
- **Why not just scale the STL:** printed mass grows about as size^1.3 while the hydrogen volume grows as size³ (124 L instead of 16 L). Scaling the STL uniformly would thicken every wall too, and the ratio would never improve.
- **Print volume:** each slice lies on its seam, 372 × 393 × 279 mm. That fits the Kobra Max's 400 × 400 × 450 mm with about 3 mm to spare each side, so **use a skirt, not a brim**, or rotate the part a few degrees on the bed.

## v0.2 double-Kobra build (x3.8, 1.58 m, 12 slices in pieces)
The self-contained build that floats on hydrogen alone. See [FLOAT.md](../../Analysis/FLOAT.md) for its weight, lift and flight time.

![double-Kobra build](../../Renders/v0.2-double-Kobra-ship.png)

- **12 slices of 30°, 4 thrusters.**
  - **Left** and **right** slices each carry half a thrust duct; **plain** slices have none.
  - Go round the ship **left, right, plain**, four times.
  - Print 4 of each type.
- **Pieces:** each slice is cut into 5 pieces that fit a Kobra Max (400 × 400 × 450 mm):

  | Piece | Where | Print size (mm) |
  |---|---|---|
  | `middle` | the band z = ±150 mm round the equator, with the thruster stem hole | 187 × 307 × 395 (left), 158 × 307 × 395 |
  | `top-outer`, `bottom-outer` | the top/bottom band outside r = 415 mm | 371 × 186 × 365 |
  | `top-inner` | the top band inside r = 415, up to the bellmouth | 386 × 65 × 208 |
  | `bottom-inner` | the bottom band inside r = 415: fan housing, keel and hatch ring | 386 × 86 × 208 |

- **Joints:**
  - Every cut has a rib on it, so each piece ends in a full edge strip.
  - One Ø3 peg crosses each cut. Each seam has joints mid-way up each piece, plus the housing and keel ones.
  - Glue with CA on the lattice. Use epoxy on the housing, the keel round the hatch, the ducts and the tube sockets, which must be airtight.
- **Intake tubes:** the shaft is two printed tubes (Ø66 bore, 0.86 mm wall, 358 and 343 mm tall) instead of a wall on each slice.
  - Tube 1 sits in the socket on top of the fan housing; tube 2 goes on top of it and into the socket under the bellmouth.
  - Epoxy the sockets, since the tube is part of the air path.
- **Lattice:** 1.2 mm webs (`OAS_RIB=1.2`). The equator rib is two-sided, carrying the servo collars.
- **Thrusters:** the 8-thruster size (Ø24 ducts, Ø32 bulbs, 64 mm rings) on the 4 left/right seams.
- **Print files:** `Print Files/v0.2.1 double Kobra/`, 15 pieces (5 each for left, right and plain) plus 2 tubes, all watertight.
  - Each slice piece lies on its seam, and the tubes stand upright.
  - Print them in full-foam lightweight PLA, with the settings below.
- **CAD:**
  - `pieces/airship pie slice 1026 v0.2.1 {left,right,plain} (pieces).FCStd`, plus STEP files per piece in `pieces/<slice>/`.
  - The whole slices are in `airship pie slice 1026 4T {left,right,plain} 12s small x3.8.step`.

To regenerate:
```
export OAS_VARIANT=4T OAS_SLICES=12 OAS_THRUSTER=S OAS_PIECES=1 OAS_SCALE=3.8 OAS_RIB=1.2
for s in L R P; do OAS_SIDE=$s python3 airship_slice.py; done
freecadcmd make_pieces.py
```

To rebuild only the three `pieces/*.FCStd` documents from the piece STEP files
already on disk, and leave the print files alone:
```
OAS_FCSTD_ONLY=1 OAS_VARIANT=4T OAS_SLICES=12 OAS_THRUSTER=S OAS_PIECES=1 \
    OAS_SCALE=3.8 OAS_RIB=1.2 freecadcmd make_pieces.py
```

## Checked (every version)
- Each part is a single valid solid, and only the 5 pegs stick out of the hull.
- **Wall map** (`Analysis/check_outputs.py`): the bench slice passes - nothing under the 0.20 mm layer, no self-intersections, thinnest reading **0.386 mm** (2 facets of 118,874 under the 0.40 mm nozzle, none under the layer). The CR-10 Pro slice does **not** pass yet: one 0.027 mm2 facet at the servo pad's far edge (az −10.93°, r 292, z +9.4) reads 0.033 mm, because at 1.41 the pad's edge lands 1.6 mm inside the lattice column's outer rib instead of clear of it (notes f151, `Analysis/build/f151/thin-cr10.log`). The map fires one ray per mesh facet along that facet's normal; a hit whose face meets the ray at less than `GRAZE_DEG` = 10° is skipped and counted ("grazing hits skipped N"), because every surface of revolution in the slice is parallel to the seam face's own rays and a facet on the seam face within a fraction of a mm of where the duct bulb's dome, the duct tube or the shroud turn crosses it reads 0.005-0.3 mm where the BREP wall is 0.80-0.86 mm. Without that rule the same STEP reads 0.194 mm at `LinearDeflection` 0.03 and 0.433 mm at 0.05, and at 15 000 or 40 000 samples every deflection finds one - the 6 000-facet stride was deciding the gate, not the model (`Analysis/build/f151/meshprobe2.log`, and `grazeprobe.py`, which shows a real 0.15 mm wall is still reported with the rule on).
- Neighbouring slices overlap by 0 mm³ (for 4 thrusters: left against right, on both seams).
- **Airtight:** the keel round the hatch, the housing/shroud wall and the shaft wall are complete; their only openings are where the ducts leave the housing. The duct walls' only openings are the stem holes.
- No material sits inside the shaft or the impeller eye.
- The STLs are watertight.
- `../Propulsion/check_fit.py` passes all 35 checks for all four versions.

## Weight and volume
Weights and lift for every version and material are in [Analysis/FLOAT.md](../../Analysis/FLOAT.md).

| Version | Printed hull | PLA | Moderate-foam lightweight PLA | Full-foam lightweight PLA | Hydrogen volume |
|---|---|---|---|---|---|
| 8 thrusters, bench (8 slices) | 214 cm³ | 265 g | 171 g | 128 g | 16.5 L |
| 4 thrusters, bench (8 slices) | 184 cm³ | 228 g | 147 g | 110 g | 16.5 L |
| 8 thrusters, Kobra Max (8 slices) | 415 cm³ | 514 g | 332 g | 249 g | 124 L |
| 4 thrusters, Kobra Max (8 slices) | 349 cm³ | 432 g | 279 g | 209 g | 124 L |
| double Kobra, 12 slices (v0.2 build) | 474 cm³ | 588 g | 379 g | 284 g | 1022 L |

**Not in that table yet:** the outlet keep-outs cut to the hardware, the servo brace and the servo mounting pad (f150/f151) take one 8-thruster bench slice from 32.4 cm³ to **30.45 cm³** (37.8 g of PLA, −2.0 g a slice and −16 g a hull) and the CR-10 Pro slice from 55.5 cm³ to **44.47 cm³** (55.1 g). The 58 open windows a slice (was 36) give back more than the 6.0 × 3.0 mm equator beam and the 46.3 × 28.2 mm pad put in.

## Printing
- **Walls:** 0.20 mm layers, 0.4 mm nozzle, 2 perimeters, with no infill needed (the walls are 2 lines thick). Don't let "detect thin walls" change them.
- **Orientation:** every STL is already laid flat on its −22.5° seam. The skin never overhangs more than 45°. Oval tips and junction points point up, so the ribs are carried by sloping edges rather than bridges.
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
- **FreeCAD documents:** `airship pie slice 1026[ 4T left| 4T right][ x1.9].FCStd`. Each holds the part as one `Part::Feature` solid plus a parameter spreadsheet, and a saved view (`GuiDocument.xml`: the part switched on, in colour, with a camera framed on it) so the parts appear as soon as the file is opened in the FreeCAD GUI. They are written through `../fcstd_doc.py`, which also refuses to store a shape that is not a valid closed solid.
- **STEP:** the same parts, in the matching `.step` files.
- **`airship_slice.py`:** the parametric source (CadQuery). Everything is set at the top of the file. The version is chosen with environment variables:
  - `OAS_VARIANT=8T|4T`
  - `OAS_SIDE=L|R` (4 thrusters only)
  - `OAS_SCALE=1|1.9` (3.8 for v0.2; 1.41 is the largest that lies on its seam inside
    290 × 290 × 390, the CR-10 Pro's bed less a 5 mm margin)
  - `OAS_TAG=CR10Pro` names a build's files instead of the ` x<SCALE>` suffix: it writes
    `airship pie slice 1026 CR10Pro.step/.FCStd/.joints.json` and
    `PieSlice1026-v0.2.1-8T-CR10Pro.stl`
  - v0.2 only: `OAS_SLICES=12`, `OAS_SIDE=P` (plain slice), `OAS_THRUSTER=S` (8-thruster-size ducts on 4 thrusters), `OAS_PIECES=1` (cut into pieces, with intake tubes), `OAS_RIB=1.2` (web width)
- **`make_pieces.py`:** builds the v0.2 piece STLs and FCStd documents.
- **`make_fcstd.py`:** builds the FCStd and the print STL for the same settings.
- **`../fcstd_doc.py`:** the shared document writer (one `Part::Feature` per part, document label = file name, `GuiDocument.xml` with every part visible). `OAS_FCSTD_ONLY=1` on any of these scripts rewrites only the `.FCStd`, from the STEP files on disk.

To regenerate, for example the right-hand 4-thruster Kobra Max slice:
```
pip install cadquery
OAS_VARIANT=4T OAS_SIDE=R OAS_SCALE=1.9 python3 airship_slice.py
OAS_VARIANT=4T OAS_SIDE=R OAS_SCALE=1.9 freecadcmd make_fcstd.py
```

All six whole-slice documents, from the `.step` files already in this folder:
```
freecadcmd make_fcstd.py                                        # 8 thrusters, bench
OAS_SCALE=1.9 freecadcmd make_fcstd.py                           # 8 thrusters, Kobra Max
OAS_SCALE=1.41 OAS_TAG=CR10Pro freecadcmd make_fcstd.py          # 8 thrusters, CR-10 Pro
OAS_VARIANT=4T OAS_SIDE=L freecadcmd make_fcstd.py              # 4 thrusters, left
OAS_VARIANT=4T OAS_SIDE=R freecadcmd make_fcstd.py              # 4 thrusters, right
OAS_VARIANT=4T OAS_SIDE=L OAS_SCALE=1.9 freecadcmd make_fcstd.py # 4 thrusters, left, Kobra Max
OAS_VARIANT=4T OAS_SIDE=R OAS_SCALE=1.9 freecadcmd make_fcstd.py # 4 thrusters, right, Kobra Max
```
Add `OAS_FCSTD_ONLY=1` to any of those lines to rewrite the `.FCStd` only and
leave `Print Files/` untouched.
