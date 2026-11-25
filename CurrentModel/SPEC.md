# SPEC - the OpenAirShip slice, rebuilt clean (a01/a02)

Reconstructed by a02 from the a01 task's source list (the a01 branch carried no SPEC.md).
Every requirement: intent + numbers + source. Sources are file:line in this repo.
`airship_slice.py` = `CurrentModel/CAD Files/SimplifiedSlice/airship_slice.py` (constants block only -
read for numbers, never copied).

## Envelope
R1. Hull outer surface: prolate spheroid of revolution, equatorial semi-axis A = 207.765*S mm, half-height B = 104.0*S mm, axis vertical. (airship_slice.py:70)
R2. The model is a ring of N = 8 slices; one slice is a 45 deg wedge, HALF = 22.5 deg each side of its seam plane. (airship_slice.py:54,72)
R3. Two builds: 8T bench S = 1.0 (415 mm hull) and CR-10 Pro S = 1.41 (586 mm hull), the largest single slice on a 290x290x390 bed with 5 mm margin (271x290x206 mm). (airship_slice.py:59-64; FLOAT.md:14)
R4. Only the hull outline and its lattice scale with S; walls, ribs, joints, fan, ducts, thrusters, servos, brace and pad keep absolute size. (airship_slice.py:59-62; AGENTS.md rule 5)
R5. Thruster ducts lie exactly on the equator plane, OUT_Z = 0. (airship_slice.py:718; AGENTS.md)

## Parts
R6. Skin lattice: a closed band of wall T = 0.86 mm with open windows; webs RIB = 2.0 mm; the lattice runs right out to the slice edges. (airship_slice.py:71,78,80; AGENTS.md rule 4)
R7. Rim: each seam face carries a solid strip so the two halves of a seam rib (RIB/2 per slice) meet flat. (airship_slice.py:78)
R8. Keel: bottom cap closing the wedge below the fan-housing ceiling FLOOR_Z = -B + 32.7, with shaft wall SHAFT_R = 33.0, plenum outer wall PLENUM_FLAT_R = 60.5, and a keel hatch opening HATCH_R = 47.0 for the 88 mm impeller. (airship_slice.py:74,321,328,377)
R9. Ducts: each slice carries two half-ducts in its seam planes, bore DUCT_BORE = 24.0, the hull skin is the duct's outer wall, the far end swells to a bulb DUCT_BULB = 32.0 around a bearing boss BOSS_R = STEM_HOLE/2 + 1.3, BOSS_LEN = 12.0 behind the stem hole STEM_HOLE = 25.4. (airship_slice.py:356,384-388)
R10. Servo mount: a solid pad under the bracket footprint SERVO_BRACKET_L = 42.3 x SERVO_BRACKET_W = 24.2 mm, thickness PAD_T = 1.5 mm counting the band; spline hole SERVO_HOLE = 8.0 leaving SERVO_WALL = 1.0 of band, spline axis SERVO_T = 36.0 mm from the seam, radial. (airship_slice.py:102,169-173,425-427)
R11. Equator brace: BRACE_W = 9.0 mm along the hull x BRACE_D = 2.5 mm inward, fused into the pad at one end and the far duct's bearing boss band at the other. (airship_slice.py:138,153)
R12. Slice joints: pegs PEG_D = 3.0 x PEG_L = 3.6 mm on one rim into holes HOLE_D = 3.3 x HOLE_L = 4.2 mm in bosses BOSS_D = 7.0 x BOSS_L = 5.0 mm on the other rim; two joints per slice. (airship_slice.py:335-338)

## Interfaces
R13. Peg-in-hole running fit: 0.15 mm clearance per side (0.3 mm diametral) for PLA on a 0.4 mm nozzle. (airship_slice.py:335)
R14. A joint sits where two walls actually meet and is fused into both; >= JOINT_CLEAR = 1.0 mm from the plenum air and the impeller's swept volume, else the joint does not exist. (airship_slice.py:349; AGENTS.md rule 5)
R15. Every hole toward an air path keeps AIR_KEEP = 0.6 mm of wall. (airship_slice.py:347; AGENTS.md rule 3)
R16. The servo bracket (42.3x24.2x16 mm, Propulsion) epoxies flat onto the pad's inside face; the stem turns in the bearing sleeve at STEM_HOLE. (airship_slice.py:169-170,384)

## Loads
R17. SAFETY_FACTOR = 3 on every part, against across-the-layers PLA (tensile 20 MPa, shear 12 MPa). (STRUCTURE-ESTIMATES.md:15-36; airship_slice.py:187)
R18. Load cases: L1 servo mass 23.4 g, L2 stall 215.8 N.mm (MG90S), L3 gear force 12.0/4.4 N, L4 fan thrust 3.0 N, L5 handling x4, L6 hand on ring 20 N, L7 crash 20 g, L8 plenum 13 N. (STRUCTURE-ESTIMATES.md:66-76)
R19. Pad: plate bending under the bracket needs 1.34 mm -> PAD_T = 1.5 mm. (STRUCTURE-ESTIMATES.md:91-98)
R20. Brace design case C4 (stall torque as end moment at the 174 mm span): 9.0 x 2.5 gives SF 3.13; nothing lighter holds SF 3. (STRUCTURE-ESTIMATES.md:113-143)

## Print rules
R21. 0.4 mm nozzle, 0.2 mm layers; thinnest wall 0.86 mm = 2 perimeters of 0.43-0.45 mm; nothing in the model thinner. (AGENTS.md rule 1; airship_slice.py:71)
R22. Material PLA 1.24 g/cm3 (mass = volume x 1.24e-3 g/mm3). (STRUCTURE-ESTIMATES.md:34)
R23. No cut boundary may land on a face the part already has (nothing within 0.05 mm) - coincident faces make slivers. (AGENTS.md rule 2; CAD-REVIEW.md)

## Mass budget
R24. CR-10 Pro slice: hull 447 g / 8 slices = 55.9 g PLA per slice is the current baseline; the rebuild must not exceed it materially. (FLOAT.md:107)
R25. Bench slice: 38.2 g PLA (30.77 cm3) measured on the f152 rebuild. (STRUCTURE-ESTIMATES.md:181-184)

## Construction rules
R26. Every part is a closed solid that OVERLAPS its neighbours by >= 0.4 mm - never coincident faces. (a01 task step 2; AGENTS.md rule 2)
R27. ONE final fuse of all parts, then `.clean()`; no fuzzy tolerances, no per-task keep-clear constants. (a01 task step 2)
R28. Lattice cells are cut as 2D-offset shapes with minimum web >= 1.2 mm (3 nozzle lines) and no cell touching the rim or keel (>= 1.2 mm land). (a02 task step 1)
R29. No lattice window over a duct: a solid CREST_BAND = DUCT_BORE/2 = 12.0 mm band either side of each duct seam stays filled. (airship_slice.py:388; AGENTS.md rule 3)
R30. The STEP must pass Analysis/check_cad.py: valid, 1 solid, 0 faces < 1.0 mm2, 0 edges < 0.2 mm, 0 hairline gaps < 0.2 mm, 0 internal faces. (check_cad.py; CAD-CHECK.md)

## Dropped
- CREST_EDGE_CLEAR, BRACE_EDGE_CLEAR, PAD_RING_CLEAR, BOSS_INSET, SKIN_BITE - coincident-face patches; R26 overlaps make them dead code.
- MIN_KEEP, MIN_OPEN_AREA, CELL_CLOSE - keep-out clipping rules; R28's fixed webs/lands make cells uniform.
- INTAKE_R bellmouth fillet - cosmetic; the intake is a plain opening under R23.
- MIN_WEB = 0 edge lattice - replaced by R28's 1.2 mm land.
- OAS_PIECES multi-piece split - not needed at these two scales.
