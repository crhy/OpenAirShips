# Simplified pie slice (from `airship pie slice 125.FCStd`)

One 45° slice of the hull. Eight identical copies plug together into the full ship.

![slice](slice.png)
![8 slices assembled](assembly.png)

| | Original 125 | Simplified |
|---|---|---|
| Volume per slice | 27.2 cm³ | 21.4 cm³ |
| PLA per slice (1.24 g/cm³) | ~34 g | ~27 g |
| Full ship, 8 slices | ~270 g | ~212 g |

## What changed
- Kept: the hull ellipse (207.765 × 104 mm), the 0.625 mm wall, the top trough, the central shaft, the floor (z = −70) and main deck (z = −40), and the solid keel below the floor.
- Kept: both thrust half-ducts, copied unchanged from the original model (`thrust_pipes.brep`). Two neighbouring slices close them into one full duct.
- Removed: the third deck (z = −55), the doubled inner wall of the top trough, and the hand-drawn window sketches.
- New: one regular frame of 4 mm ribs, with round-cornered windows in the skin, shaft and decks. A seam rib is 2 mm on each slice, so two slices together make a 4 mm rib.
- New joints: 7 bosses along each seam, all at the same (r, z) positions. The +22.5° seam has Ø3 × 3.6 mm pegs and the −22.5° seam has Ø3.2 × 4 mm holes, so slice k+1 plugs into slice k.

Checked: the part is a single valid solid, and a slice rotated 45° overlaps its neighbour by 0 mm³.

## Files
- `airship_slice.step`: the part, which opens in FreeCAD, Fusion, etc.
- `../../Print Files/PieSlice125-simplified.stl`: the part for printing.
- `airship_slice.py`: the parametric source (CadQuery). All sizes are at the top of the file. Run `pip install cadquery && python3 airship_slice.py` to regenerate the STEP and STL.
- `thrust_pipes.brep`, `thrust_pipe_void.brep`: the original duct walls and bores that the script uses.
