# Airship pie slice 926 (simplified, print-ready)

One 45° slice of the hull. Eight identical copies plug together into the full ship.
It is derived from `../airship pie slice 125.FCStd`.

![slice](slice.png)
![8 slices assembled](assembly.png)

## Air path
The impeller in the central shaft pulls air down into the plenum between the floor (z = −70) and the keel, and the plenum feeds the 8 thrust pipes. For that reason the **shaft, floor and keel are solid, airtight walls**. Only the outer skin above the floor, the main deck and the top trough have lightening windows. Every peg hole keeps at least 0.6 mm of wall between it and the air path. The script checks that the shaft wall, floor and keel have no openings other than the thrust-pipe bores.

## What changed from 125
- Kept: the hull ellipse (207.765 × 104 mm), the top trough, the central shaft, the floor and main deck, and the solid keel.
- New for the propulsion system:
  - a 2 mm ledge inside the shaft at z = −46, which carries the motor spider (see `../Propulsion`)
  - solid skin under each thruster outlet hood, so air can't leak into the hull
- Kept: both thrust half-ducts, copied unchanged (`thrust_pipes.brep`). Two neighbouring slices close them into one full duct.
- Removed: the third deck (z = −55), the doubled inner wall of the top trough, and the hand-drawn window sketches.
- The skin is exact ellipse surfaces (234 faces in total), not a faceted spline.
- Windows are one column per slice with pointed ("gothic") tops at a 55° pitch, so none of them has a flat ceiling in the print orientation.
- Joints: 7 bosses along each seam, all at the same (r, z) positions. The +22.5° seam has Ø3 × 3.6 mm pegs and the −22.5° seam has Ø3.3 × 4.2 mm holes, both with 0.4 mm chamfers. The fit has 0.15 mm clearance per side.

Checked: the part is a single valid solid, a slice rotated 45° overlaps its neighbour by 0 mm³, and the STL is watertight.

## Printing (Prusa MK3S+, PrusaSlicer, PLA)
- **File:** `Print Files/PieSlice926.stl`. It is already laid flat on the −22.5° (hole) seam.
  - Footprint: 207 × 205 mm. It fits the 250 × 210 bed; orient it with the long side along X.
  - Height: 146 mm.
- **Walls:** 0.86 mm, which is exactly 2 perimeters of 0.45 mm at 0.2 mm layers (0.4 mm nozzle).
  - Use the 0.20 mm QUALITY profile with 2 perimeters. Don't let "detect thin walls" change them.
- **Overhangs:** in this orientation the skin never overhangs more than 45°, and the window tops rise at about 35–40°.
  - Nearly everything that overhangs past 55° is the thrust-duct arch (about 2,300 of 2,400 mm²).
  - Use supports **on build plate only**, and paint them only inside the duct lying on the bed. Nothing else needs support.
- **Bed contact:** about 800 mm², all thin seam edges. Add a 3 mm brim; the Y axis has room for it (205 + 2 × 3 < 210).
- **Weight:** 45.5 cm³, about 56 g of PLA per slice and 450 g for the ship.
  - The original 125 was 27 cm³ at 0.625 mm walls, which is below two perimeters and too thin to print reliably; at 0.86 mm walls it would weigh about 37 cm³.
  - The rest of the difference comes from the airtight shaft, floor and keel, and from the stronger joint bosses.

## Files
- `airship pie slice 926.FCStd`: FreeCAD document. It contains the part as a `Part::Feature` used as the base feature of a PartDesign Body, so you can keep modelling on top of it. It also has a parameter spreadsheet.
- `airship pie slice 926.step`: the same part as STEP, for other CAD tools.
- `airship_slice.py`: the parametric source (CadQuery). All sizes are at the top of the file.
- `make_fcstd.py`: builds the FCStd and the print STL from the STEP.
- `thrust_pipes.brep`, `thrust_pipe_void.brep`: the original duct walls and bores that the script uses.

To regenerate everything:
```
pip install cadquery && python3 airship_slice.py && freecadcmd make_fcstd.py
```
