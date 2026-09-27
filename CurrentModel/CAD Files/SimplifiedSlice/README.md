# Airship pie slice 926, rev C: the 125 design, cleaned up

One 45° slice of the hull. Eight identical copies plug together into the full ship.
It follows `../airship pie slice 125.FCStd` closely, rebuilt as clean parametric geometry.

![slice](slice.png)
![8 slices assembled](assembly.png)

## Kept from 125
- **Hull:** the ellipse (207.765 × 104 mm), and the top trough with its outer lip and **rolled double-wall rim** around the top opening.
- **Central shaft and three decks:** the floor at z = −70, the lower deck at −55 and the main deck at −40, with the solid keel below the floor.
- **Skin lattice, same layout:**
  - two full-width slots between the floor and the main deck
  - above them, two columns of rounded windows either side of a centre rib
  - the middle band, from −40 to +38, has 3 rows as in 125
- **Deck windows:** two columns, with ring ribs every 24 mm as in 125. The trough shelf has 2 × 2 windows.

## Changed
- **Upper lattice:** larger and sparser, with **2 rows** (windows about 33–41 mm tall) where 125 had 4. Below that, windows are about 17–25 mm tall.
- **Smooth outside:**
  - The 125 thrust pipes bulged out through the hull. They're now Ø24 mm ducts that run entirely inside the skin, along the same route: a mouth on the keel in the plenum, up the side, to the equator. Each duct is split by the seam, so two slices close it.
  - The only openings besides the windows are the stem hole on each seam (Ø16.4 mm, with a bearing boss behind it) and an Ø8 mm hole for the servo gear hub.
  - Nothing sticks out except the joint pegs, which plug into the neighbouring slice.
- **Airtight air path:** the shaft, floor and keel are solid. The skin stays solid (no windows) over the ducts and around the servo mount.
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
- **File:** `Print Files/PieSlice926clauderevC.stl`. It is already laid flat on the −22.5° (hole) seam.
  - Footprint: 208 × 202 mm; long side along X.
  - Height: 147 mm.
  - RevA (pipes outside) and revB (smooth, one-column windows) are kept alongside it for comparison.
- **Walls:** 0.20 mm QUALITY profile with 2 perimeters. Don't let "detect thin walls" change them.
- **Overhangs:**
  - The skin never overhangs more than 45°.
  - Window tops are short bridges along the ribs: at most about 25 mm in the middle band and about 41 mm in the upper band.
  - If the upper bridges sag on your printer, set `ROOF_ANGLE = 55` in the script. That gives pointed window tops that don't need bridging.
- **Supports:** use supports **on build plate only**, and paint them inside the duct arch lying on the bed. Nothing else needs support.
- **Brim:** add a 3 mm brim.
- **Weight:** 50.9 cm³, about 63 g of PLA per slice and 505 g for the ship.

## Files
- `airship pie slice 926.FCStd`: FreeCAD document. It contains the part as the base feature of a PartDesign Body, plus a parameter spreadsheet.
- `airship pie slice 926.step`: the same part as STEP.
- `airship_slice.py`: the parametric source (CadQuery). The lattice, decks, ducts and joints are all set at the top of the file.
- `make_fcstd.py`: builds the FCStd and the print STL.

To regenerate: `pip install cadquery && python3 airship_slice.py && freecadcmd make_fcstd.py`
