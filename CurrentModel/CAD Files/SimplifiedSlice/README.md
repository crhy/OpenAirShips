# Airship pie slice 926, rev D: the 125 design, cleaned up, with an oval upper lattice

One 45° slice of the hull. Eight identical copies plug together into the full ship.
It follows `../airship pie slice 125.FCStd` closely, rebuilt as clean parametric geometry.

![slice, outside](slice_front.png)
![slice](slice.png)
![slice, inside](slice_inside.png)
![8 slices assembled](assembly.png)

## Kept from 125
- **Hull:** the ellipse (207.765 × 104 mm), and the top trough with its outer lip and **rolled double-wall rim** around the top opening.
- **Central shaft and three decks:** the floor at z = −70, the lower deck at −55 and the main deck at −40, with the solid keel below the floor.
- **Lower skin:** two full-width slots between the floor and the main deck, as in 125.
- **Deck windows:** two columns, with ring ribs every 24 mm as in 125. The trough shelf has 2 × 2 windows.

## Changed
- **Upper lattice (rev D):** above the main deck there are 6 rows of **two side columns of large ovals** either side of a centre rib. The bottom row is a rounded rectangle.
  - Every junction where four ovals meet is **hollow**, with its own small diamond window and a full 4 mm rib all round.
  - Printed lying on the seam, each oval's top is a small round arch (about 9 mm radius), which prints without supports.
- **Smooth outside:**
  - The 125 thrust pipes bulged out through the hull. They're now Ø24 mm ducts that run entirely inside the skin, along the same route: a mouth on the keel in the plenum, up the side, to the equator. Each duct is split by the seam, so two slices close it.
  - The only openings besides the windows are the stem hole on each seam (Ø16.4 mm, with a bearing boss behind it) and an Ø8 mm hole for the servo gear hub.
  - The lattice runs straight over the ducts: their own walls keep them airtight. Solid skin is kept only as small collars around the stem and servo holes.
  - Nothing sticks out except the joint pegs, which plug into the neighbouring slice.
- **Airtight air path:** the shaft, floor, keel and duct walls are solid. The check covers the duct walls too: their only openings are the stem holes. (Rev D also fixes a leak in revB/C, where the stem hole was drilled through the back wall of the duct.)
- **Motor ledge:** a 2 mm ledge inside the shaft at z = −46 carries the motor spider (see `../Propulsion`).
- **Walls:** 0.86 mm (2 perimeters). 125's 0.625 mm is too thin for two perimeters.
- **Joints:** 7 bosses along each seam, all at the same (r, z) positions.
  - The +22.5° seam has Ø3 × 3.6 mm pegs; the −22.5° seam has Ø3.3 × 4.2 mm holes.
  - Both have 0.4 mm chamfers, giving 0.15 mm clearance per side.

Checked:
- The part is a single valid solid.
- A slice rotated 45° overlaps its neighbour by 0 mm³.
- The keel skin has no openings.
- The STL is watertight.
- `../Propulsion/check_fit.py` passes.

## Printing (Prusa MK3S+, PrusaSlicer, PLA)
- **File:** `Print Files/PieSlice926clauderevD.stl`. It is already laid flat on the −22.5° (hole) seam.
  - Footprint: 208 × 205 mm; long side along X.
  - Height: 147 mm.
  - Revs A–C are kept alongside it for comparison. RevB and revC have the duct leak described above, so don't print them.
- **Walls:** 0.20 mm QUALITY profile with 2 perimeters. Don't let "detect thin walls" change them.
- **Overhangs:**
  - The skin never overhangs more than 45°.
  - The ovals' tops are small round arches. The two lower rows of slots, and the row of rounded rectangles above the main deck, bridge about 17–25 mm.
- **Supports:** use supports **on build plate only**, and paint them inside the duct arch lying on the bed. Nothing else needs support.
- **Brim:** add a 3 mm brim.
- **Weight:** 48.7 cm³, about 60 g of PLA per slice and 485 g for the ship.

## Files
- `airship pie slice 926.FCStd`: FreeCAD document. It contains the part as the base feature of a PartDesign Body, plus a parameter spreadsheet.
- `airship pie slice 926.step`: the same part as STEP.
- `airship_slice.py`: the parametric source (CadQuery). The lattice, decks, ducts and joints are all set at the top of the file.
- `make_fcstd.py`: builds the FCStd and the print STL.

To regenerate: `pip install cadquery && python3 airship_slice.py && freecadcmd make_fcstd.py`
