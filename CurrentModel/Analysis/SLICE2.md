# Slice2 — clean rebuild (task a02)

Generator: `CurrentModel/CAD Files/Slice2/slice.py` (377 lines, one function per part,
`PARAMS` dict at top, one fuse then post-fuse cuts then `clean()`).
Outputs: `slice-8T.step`, `slice-CR10Pro.step` (next to the script) and
`Print Files/Slice2/slice-{8T,CR10Pro}.stl`. Renders: `Analysis/renders/slice2/`.

## Mass (PLA 1.24e-3 g/mm3)

| scale | volume mm3 | mass g | baseline g |
|-------|-----------:|-------:|-----------:|
| 8T      | 74 539  | 92.4  | 38.2 |
| CR10Pro | 119 830 | 148.6 | 55.9 |

The rebuild is ~2.4x heavier than the baseline slice. The lattice runs only to
u = 46 deg (see deviations), the keel/duct/brace are solid, and the wall is a
single T = 0.86 band with no perimeters optimisation. Mass is not the checker
gate but is reported here as required.

## Checker gate (check_cad.py) — NOT PASSING

| scale | solids | invalid | slivers | short | hairline | internal |
|-------|:------:|:-------:|:-------:|:-----:|:--------:|:--------:|
| 8T      | 1 | no | 0 | 0  | 8   | 19 |
| CR10Pro | 1 | no | 0 | 55 | 146 | 17 |

8T is clean on slivers and short edges. The remaining failures are structural
boolean artefacts, not tessellation noise:

- **internal faces (19 / 17):** the fuse does not remove buried faces
  (`removeSplitter` / `BOPAlgo_RemoveSplitter` are unavailable in this OCP
  build, and a fuzzy `tol` changed nothing). They are the duct bulb/sleeve
  cones, the joint boss/peg cylinder+plane inside the rib, and a chain of
  skin-surface cones along the pole meridian in the solid cap above the lattice.
- **hairline (8 / 146):** 2 are the duct-mouth polygon-chord mismatch (0.039 mm)
  between the spheroid trim and the skin; 6 are joint-rib gaps (0.13-0.15 mm).
  At 1.41x the chord mismatch grows, which is why CR10Pro hairline jumps to 146.
- **short edges (55, CR10Pro only):** fit/bite constants are not scaled with the
  hull (per SPEC only the hull scales), so at 1.41x some joint/duct edges fall
  under 0.2 mm.

To reach 0/0/0/0 on both scales the parts need the original generator's
coincident-interface construction (shared surfaces so the fuse leaves no buried
faces) and scale-aware joint fits — a redesign, not a parameter tweak.

## Deviations from SPEC.md

- **Lattice stops at u = 46 deg** (solid cap above). R28 wants the lattice to the
  edges; small upper cells produced sub-1 mm2 sliver faces, so the top rows were
  dropped and the octagon corner chamfer is dropped (square window) when its face
  would be < 1.4 x T.
- **JOINT_FIT = 0.30 mm** per side, not R13's 0.15 mm: the chord-aware checker
  measured the 0.15/0.25 fits as < 0.2 mm hairline gaps.
- **SKIN_BITE = 0.30 mm**, not 0.02 mm, to keep the duct bore breaking the skin
  clear of the hairline threshold.
- **Polygon meridian** (3 deg steps), not a true spheroid surface: BSpline
  meridians produced degenerate pole faces that crashed `BRepExtrema` (1905
  crashes). The polygon is the stable choice with this OCP build.
- **Mass** 2.4x baseline (above).

## Construction notes

- Skin/keel/duct built from a 360-deg revolve of the meridian polygon with the
  seam parked at 180 deg (far from the +/-22.5 deg wedge cuts) so `clip_wedge`
  always removes it.
- Ribs/pad/brace use `sector_band` = a direct partial revolve over [a0,a1]
  (no seam, no pie cut) — this fixed a boolean misclassification where a
  360-revolve seam landing between the pie cut faces made `cut` return volume 0.
