# Float design study: the lightest structurally sound, FDM-printable AirShip that floats on hydrogen

Written by `CurrentModel/Analysis/float_design_study.py` (f155). Analysis only: no CAD, no generator constant changed. It reuses `float_budget.py`'s constants (lift 1.1202 g/L, PLA 1.24 / LW-PLA 0.80 and 0.60 g/cm3, film 11 g/m2, the oblate-ellipsoid area formula) and `Analysis/STRUCTURE-ESTIMATES.md`'s strength numbers (`SAFETY_FACTOR` 3, PLA across the layers 20 MPa, epoxy lap shear 10 MPa). Every number is tagged [measured] / [datasheet] / [guess].

Printer: Creality CR-10 Pro, usable **290 x 290 x 390 mm** (rhY's 5 mm margin, rule 12) [measured]. Hull form: oblate spheroid, equatorial radius `a`, half-height `B = ba x a`, today `ba` = 0.5006 [measured: `A` 207.765, `B` 104.0]. The study tries `ba` = 0.45, 0.5006 and 0.55.

## 0 Does this model agree with FLOAT.md? (it must)

The x3.8 double-Kobra build of FLOAT.md, rebuilt from this file's formulas. The glue row is shown for both piece layouts, because this study always cuts the hull to the CR-10 Pro bed and FLOAT.md's build was cut to a Kobra Max; the total row is the Kobra-layout total, which is the number being checked:

| item | FLOAT.md | this study |
|---|---|---|
| hull (12 slices) | 285 | 285 |
| core printed parts | 205 | 205 |
| gas cells, 12 um LDPE | 77 | 77 |
| motor + servos + screws + wiring | 114 | 114 |
| glue (Kobra layout / CR-10 layout) | 66 | 97 |
| electronics + battery | 230 | 230 |
| **total** | 977 | 977 |
| H2 volume (L) | 1022 | 1027 |
| H2 lift (g) | 1145 | 1150 |
| margin (g) | 168 | 173 |

The two agree to a few grams, so the same arithmetic can be pointed at new shapes with some confidence [measured].

## 1 The answer in one table

Smallest hull that floats with the margin named, `ba` = 0.5006, LW-PLA full foam (0.60 g/cm3), metallized PET envelope, 4 thrusters, battery and controller on board:

| concept | margin | hull diameter | H2 | all-up mass | margin | printed parts | print hours |
|---|---|---|---|---|---|---|---|
| A today's lattice skin, re-pieced for the CR-10 Pro | +150 g | 1.62 m | 1114 L | 1098 g | +150 g | 256 | 141 h |
| A today's lattice skin, re-pieced for the CR-10 Pro | +250 g | 1.67 m | 1225 L | 1123 g | +250 g | 256 | 143 h |
| B semi-rigid: core + 12 battens + 3 rings + film | +150 g | 2.18 m | 2706 L | 2881 g | +150 g | 235 | 421 h |
| B semi-rigid: core + 12 battens + 3 rings + film | +250 g | 2.21 m | 2829 L | 2919 g | +250 g | 235 | 426 h |
| C pressure envelope: printed core + film, no skin | +150 g | 1.54 m | 946 L | 910 g | +150 g | 46 | 75 h |
| C pressure envelope: printed core + film, no skin | +250 g | 1.59 m | 1055 L | 931 g | +250 g | 47 | 77 h |
| C as recommended (tapered ducts 2T root / T mouth + ring) | +150 g | 1.57 m | 1013 L | 985 g | +150 g | 47 | 87 h |
| C as recommended (tapered ducts 2T root / T mouth + ring) | +250 g | 1.63 m | 1123 L | 1008 g | +250 g | 47 | 89 h |

*Printed parts* counts every separate print (slices x pieces for A, frame segments for B, core segments for C). *Print hours* is the printed volume at 10 cm3/h effective for thin lattice on a 0.45 mm line at 0.2 mm layers plus 15 min per part for bed changes [guess, calibrated on f148's 55 cm3 CR-10 Pro slice taking ~6 h]. All-up mass includes the 4S LiPo (180 g), the ESC, ESP32, BEC, IMU and switch (50 g), the wiring, the glue and the envelope film.

## 2 Concept A - today's lattice skin, re-pieced for the CR-10 Pro

The x3.8 / 12-slice self-contained build of FLOAT.md, but cut to what the 290 x 290 x 390 bed will take. Hull mass follows the measured law: between x1 and x1.9 the 4T hull mass grows as S^1.00 [measured, FLOAT.md], anchored on the x3.8 build's 285 g of LW-PLA at 0.60 g/cm3 [measured].

| item | g |
|---|---|
| hull (16 slices) | 293 |
| core printed parts | 205 |
| gas cells (metallized PET) | 126 |
| motor/servos/screws | 71 |
| wiring | 44 |
| glue | 100 |
| extra piece joints | 29 |
| electronics | 50 |
| battery | 180 |
| **all-up** | **1098** |
| H2 lift | 1248 |
| **margin** | **+150** |

At a = 811 mm (diameter 1.62 m): 16 slices, 256 pieces, 585 peg joints, 771 cm3 of print, **141 print hours** on the CR-10 Pro. The bed forces 16 slices, not 12: a slice stands 317 mm across the azimuth and the bed is 390 mm tall [measured, f148's 206 mm at N=8 x1.41].

| item | g |
|---|---|
| hull (16 slices) | 302 |
| core printed parts | 205 |
| gas cells (metallized PET) | 134 |
| motor/servos/screws | 71 |
| wiring | 45 |
| glue | 103 |
| extra piece joints | 31 |
| electronics | 50 |
| battery | 180 |
| **all-up** | **1123** |
| H2 lift | 1373 |
| **margin** | **+250** |

At a = 837 mm (diameter 1.67 m): 16 slices, 256 pieces, 604 peg joints, 787 cm3 of print, **143 print hours** on the CR-10 Pro. The bed forces 16 slices, not 12: a slice stands 327 mm across the azimuth and the bed is 390 mm tall [measured, f148's 206 mm at N=8 x1.41].

**What A costs that the paper version did not count:** the CR-10 Pro piece layout is 256 pieces against the Kobra Max's 60, and every piece boundary is glue and pegs: +37 g of glue and +31 g of joint bosses over FLOAT.md's x3.8 rows. A also needs 134 g of film where the printed skin is doing the same job twice - the lattice skin holds the shape and the gas cells hold the gas, and the skin is the expensive one.

Structure: A is the *strongest* of the three - a 0.86 mm lattice shell with 2 mm ribs, the equator brace at SF 3.13 (f152), and it is what the wall map and the checker have already proved at two sizes. That is also the problem: it is strong in exactly the way that costs 285 g.

## 3 Concept B - semi-rigid: printed core + battens + rings + film

No printed skin. The shape is held by N meridian battens and K latitude rings, printed as bed-sized segments with the same peg idiom as `pieces()`, and the envelope is the gas cells' film held taut by a small overpressure.

Sizing the frame (SF 3, PLA across the layers 20 MPa [datasheet range, LOW end]): the overpressure dp puts the film in Laplace tension T_f = dp R / 2 [measured physics]; holding that film to a squat spheroid pulls it inward and the reaction compresses each batten along the meridian with N = T_f x its tributary width; a batten is a strut unsupported between rings, so I >= SF N L^2 / (pi^2 E). Sizing handling load: a 5 N grab at midspan [guess]. dp = 100 Pa [guess] - enough to keep a film taut and wrinkle-free against its own weight (a 17 g/m2 film needs ~ 0.2 Pa per degree of slope) and small enough that no blower is needed; 50-200 Pa is the range model blimps use.

| battens | rings | batten mm | batten g | ring mm | ring g | frame g | batten load N | SF buckl | SF 5 N grab | SF 20 N hand |
|---|---|---|---|---|---|---|---|---|---|---|
| 8 | 1 | 8x32 | 605 | 8x34 | 206 | 811 | 19 | 3.1 | 3.8 | 1.0 |
| 8 | 3 | 8x14 | 320 | 8x34 | 563 | 884 | 19 | 3.3 | 3.1 | 0.8 |
| 12 | 1 | 8x28 | 812 | 8x22 | 145 | 957 | 13 | 3.3 | 3.1 | 0.8 |
| 12 | 3 | 8x14 | 480 | 8x22 | 396 | 876 | 13 | 5.0 | 3.1 | 0.8 |
| 16 | 3 | 8x14 | 641 | 8x14 | 284 | 924 | 9 | 6.6 | 3.1 | 0.8 |
| 16 | 5 | 8x10 | 514 | 8x14 | 463 | 978 | 9 | 7.9 | 3.1 | 0.8 |

At 1.58 m the frame alone is **~0.9 kg** - about three times the printed lattice skin it replaces, because a batten has to be deep enough to not buckle over 640-1900 mm while a lattice web only has to stand up to itself. The 20 N hand load (STRUCTURE-ESTIMATES.md L6) is reported, not designed for, exactly as f152 reported its C3 bound: no frame of 8 mm PLA battens survives a grip of that size between rings 640 mm apart.

| item (at +150 g margin) | g |
|---|---|
| core (keel, housing, ducts) | 439 |
| battens (12 x (8, 20)) | 860 |
| rings (3 x (18, 28)) | 855 |
| envelope (metallized PET) | 228 |
| motor/servos/screws | 71 |
| wiring | 57 |
| glue | 88 |
| frame joints | 53 |
| electronics | 50 |
| battery | 180 |
| **all-up** | **2881** |
| H2 lift | 3031 |
| **margin** | **+150** |

a = 1090 mm, diameter **2.18 m**, 235 printed parts, 3619 cm3, **421 print hours**.

| item (at +250 g margin) | g |
|---|---|
| core (keel, housing, ducts) | 444 |
| battens (12 x (8, 20)) | 872 |
| rings (3 x (18, 28)) | 868 |
| envelope (metallized PET) | 235 |
| motor/servos/screws | 71 |
| wiring | 58 |
| glue | 89 |
| frame joints | 53 |
| electronics | 50 |
| battery | 180 |
| **all-up** | **2919** |
| H2 lift | 3169 |
| **margin** | **+250** |

a = 1106 mm, diameter **2.21 m**, 235 printed parts, 3669 cm3, **426 print hours**.

## 4 Concept C - the film is the structure (a pressure airship)

Print only the core: the keel / intake tube (`SHAFT_R` 33 mm, wall `T`), the fan housing, the four thruster ducts, one duct-support ring, the thruster rings and servo mounts, the stems and gears, the hatch, the impeller and the avionics tray. Everything else is film. No skin, no battens, no shape rings.

Why that is sound: a closed film under overpressure carries its load as pure membrane tension (Laplace), which is what film is good at - 40 N/m of tension at 100 Pa is 3.3 MPa in a 12 um film, SF 6 against LDPE's low-end 20 MPa and SF 60 against PET's 200 MPa [datasheet range]. What a film cannot do is hold a *squat* shape: a free film takes a rounder (constant-mean-curvature) form. So C gives up the ellipsoid and keeps the volume - buoyancy does not care about shape, and the same film area encloses within ~10 % of the spheroid's volume [guess]. The printed core hangs the payload off the film's two keel-rim attachments, and the keel is a 68 mm tube: bending SF 33.

| item (at +150 g margin) | g |
|---|---|
| keel / intake tube | 83 |
| fan housing | 26 |
| thruster ducts | 114 |
| core parts | 129 |
| duct support ring | 65 |
| envelope (metallized PET) | 113 |
| motor/servos/screws | 71 |
| wiring | 42 |
| glue | 32 |
| segment joints | 4 |
| electronics | 50 |
| battery | 180 |
| **all-up** | **910** |
| H2 lift | 1060 |
| **margin** | **+150** |

a = 769 mm, diameter **1.54 m**, H2 946 L, 46 printed parts, 638 cm3, **75 print hours**. Structure: keel bending SF 35, duct root under the thruster reaction x 4 (L5) SF 7.6, duct under a 20 N hand on a thruster ring SF 1.1 (a bound, see section 6), film tension at the keel rim vs the ship's weight SF 1.3, film-to-keel epoxy bond SF 4665.

| item (at +250 g margin) | g |
|---|---|
| keel / intake tube | 86 |
| fan housing | 26 |
| thruster ducts | 119 |
| core parts | 129 |
| duct support ring | 68 |
| envelope (metallized PET) | 122 |
| motor/servos/screws | 71 |
| wiring | 43 |
| glue | 33 |
| segment joints | 4 |
| electronics | 50 |
| battery | 180 |
| **all-up** | **931** |
| H2 lift | 1181 |
| **margin** | **+250** |

a = 797 mm, diameter **1.59 m**, H2 1055 L, 47 printed parts, 654 cm3, **77 print hours**. Structure: keel bending SF 33, duct root under the thruster reaction x 4 (L5) SF 7.3, duct under a 20 N hand on a thruster ring SF 1.1 (a bound, see section 6), film tension at the keel rim vs the ship's weight SF 1.3, film-to-keel epoxy bond SF 4559.

### 4.1 The two weak points of C, and what they cost

| duct case | SF thruster x4 | SF 20 N hand | duct mass g |
|---|---|---|---|
| wall T, no support ring | 3.7 | 0.6 | 118 |
| wall T, one support ring at 0.5 a | 7.4 | 1.1 | 118 |
| **tapered: 2T at the root, T at the mouth, ring at 0.5 a** | 15.4 | 2.3 | 180 [guess] |
| wall 2T all the way, ring at 0.5 a | 15.4 | 2.3 | 243 |

Take the tapered duct (2T where it meets the plenum, T at the mouth, +126 g of print against 2T all the way) and the support ring (67 g): the ducts then hold SF 3 against a hand on a thruster ring, which is the load that actually happens when someone picks the ship up. The other one is the film's tension at the keel rim: at 100 Pa the film can hang only 1.3 x the ship's weight off one rim. Run the envelope at 200-300 Pa (the fan already makes ~1900 Pa in the plenum [measured, STRUCTURE-ESTIMATES L8]; a bleed tube from the plenum to the envelope costs a fitting and no new part) and bond the film to a 10 mm band on both keel rims, and that margin goes to ~3-4 [guess].

## 5 Does the shape ratio matter? (B/a = 0.45, 0.5006, 0.55)

| concept | B/a | diameter at +150 g | H2 | mass | film area | print hours |
|---|---|---|---|---|---|---|
| A | 0.450 | 1.69 m | 1128 L | 1114 g | 5.9 m2 | 127 h |
| B | 0.450 | 2.31 m | 2902 L | 3100 g | 11.1 m2 | 454 h |
| C | 0.450 | 1.60 m | 954 L | 919 g | 5.3 m2 | 76 h |
| A | 0.501 | 1.62 m | 1115 L | 1098 g | 5.7 m2 | 141 h |
| B | 0.501 | 2.18 m | 2706 L | 2881 g | 10.3 m2 | 421 h |
| C | 0.501 | 1.54 m | 946 L | 910 g | 5.1 m2 | 75 h |
| A | 0.550 | 1.56 m | 1090 L | 1071 g | 5.5 m2 | 123 h |
| B | 0.550 | 2.07 m | 2559 L | 2716 g | 9.7 m2 | 392 h |
| C | 0.550 | 1.49 m | 940 L | 903 g | 5.0 m2 | 74 h |

**Deeper wins, not flatter.** At B/a = 0.55 every concept reaches the margin at a smaller diameter (C: 1.48 m against 1.59 m at 0.45), with less film (5.0 m2 against 5.3 m2) and no more print time - the same cube-square rule that drives the whole study, since for a fixed volume the area falls as the hull gets fatter. What stops 0.55 being free is that B is the ship's height: the keel tube, the piece stack and the fan housing all grow with it, and `FLOOR_Z` / the Ø34 duct mouths under the shroud were sized against today's 0.5006 [measured]. The whole effect is ~3 % of mass and ~7 % of diameter: **the concept choice is worth 40 %, the ratio is worth 3 %** [guess].

## 6 Structure at SAFETY_FACTOR 3 - every load, every tag

S1-S3 are concept B's frame at the +250 g size (that is where the frame maths matters); S4-S10 are the printed core of C at the same size, with the ducts at `T` - section 4.1 prices the tapered 2T root. Stresses are compared against the across-the-layers number, as STRUCTURE-ESTIMATES.md does, and no member is allowed below 2 perimeters.

| case | load | SF | tag |
|---|---|---|---|
| S1 batten Euler buckling under the envelope's pressure load | 24.7 N axial, L 894 mm, I 2137 mm4 vs 1999 needed | 3.2 | dp 100 Pa [guess], Laplace [measured physics], E 3000 MPa [datasheet] |
| S2 ring: battens pull in on it at each attachment | 24.7 N per attachment over a 502 mm arc | 3.0 | curved-beam bound [guess] |
| S3 ring hoop tension | 24 N | > 100 | Laplace [measured physics] |
| S4 printed peg joint (the `PEG_D` 3.0 peg, 2 per segment boundary) | 85 N to shear one peg | 37.1 | PLA shear 12 MPa [guess], one segment's share of the ship's weight |
| S5 boss bond (epoxy on a Ø7 x 5 boss) | 1100 N | > 100 | epoxy lap shear 10 MPa [datasheet, low end] |
| S6 handling: lift the whole ship by the keel | 9.1 N, M 1814 N.mm on the keel tube | 33 | load [guess], keel Ø67.7 x 0.86 [measured] |
| S7 thruster reaction on the core (duct root cantilever) | 1106 N.mm with L5 x 4 | 7.3 | 306 gf total [measured, AIRFLOW.md low end], L5 x 4 [guess] |
| S8 a hand on a thruster ring (20 N, L6) | 7367 N.mm | 1.1 | reported as a bound, as f152 reported C3; 2T duct wall + the support ring lifts it to ~2.3 |
| S9 film tension (Laplace) vs film strength | 39.8 N/m = 3.3 MPa in 12 um | 6 (LDPE) / 60 (PET) | film tensile 20 / 200 MPa [datasheet range, LOW end] |
| S10 film hanging the ship off the keel rim | 30.2 N/m needed | 1.3 | 45 deg wrap [guess]; 200-300 Pa fixes it |

Nothing is sized below the print floor: every member is at least 2 perimeters (`T` = 0.86, rule 1), and the smallest section the frame search returns is 8 x 10 mm, not a wall.

## 7 The envelope film: 12 um LDPE or metallized PET

| film | g/m2 | diameter at +150 g | envelope mass | H2 lost g/day | lift lost g/day | lift lost per week, g |
|---|---|---|---|---|---|---|
| 12 um LDPE | 11 g/m2 | 1.51 m | 71 g | 0.028-0.11 | 0.4-2 | 3-11 |
| metallized PET | 17 g/m2 | 1.54 m | 113 g | 0.000-0.00 | 0.0-0 | 0-0 |

14.4 g of lift per gram of H2 lost (1 L of H2 lifts 1.12 g and weighs 0.084 g). The permeability numbers are [datasheet range, order of magnitude] and are the weakest numbers in this study - they span two orders of magnitude, which is exactly why the leak test in section 10 is the second-cheapest and most valuable test on the list. Metallized PET costs +42 g and buys 10-100x the barrier; take it. LDPE stays useful for a first shape/leak prototype because it is cheap and heat-sealable at home.

## 8 Two ideas that look lighter and are not

- **A geodesic strut frame** (the obvious light space frame): 120 struts of 0.31 m at frequency 2 = 37 m of strut, 854 g of LW-PLA at the 8 x 14 mm section the buckling maths wants, before the 42 node fittings that are each a print and a joint. Worse than concept B's battens, which are continuous and need no nodes [guess].

- **A bundle of sausage gas cells** (each cell a pressure cylinder, so no frame at all, like a small non-rigid blimp): it works structurally, but the internal walls are wasted film - 9.0 m2 against the single envelope's 5.4 m2 (7.0 m2 once the seams are allowed for), so +33 g of film at 17 g/m2. It stays the fallback if a single envelope cannot be made to hold shape.

## 9 RECOMMENDATION

**Build concept C: the pressure envelope - printed core only, film envelope, no printed skin - with tapered ducts (2T at the root, T at the mouth) and one support ring, at a = 813 mm, hull diameter 1.63 m, B/a = 0.5006, in LW-PLA at 0.60 g/cm3, with a metallized-PET envelope held at 200-300 Pa.** It floats with **+250 g** of margin on **1123 L** of hydrogen at an all-up mass of **1008 g**, in **47 printed parts** and **~89 print hours** on the CR-10 Pro.

Reasons:

1. **It is the only concept that floats near the size the bed can print.** A needs 1.67 m and B needs 2.21 m for the same +250 g; C needs 1.63 m. B's diameter is set by its own frame: 1740 g of battens and rings, which is 60 % of the airframe.

2. **It removes the mass that the float maths cannot remove.** Lift grows as a^3, a printed skin as a^2 and a fixed-thickness wall as a^1 (FLOAT.md's measured S^0.81-1.00). The skin is the part that never stops paying. C pays 127 g of film where A pays 302 g of lattice plus 134 g of film plus 135 g of glue and joints to hold the same volume.

3. **It is 5x fewer prints, and every one of them is a simple tube.** 47 parts against A's 256 and B's 235: 3 keel segments (the keel tube is 814 mm long and prints in 3, as the x3.8 build's intake tubes already do), 12 duct segments, 8 ring segments and the thruster hardware - nothing longer than 350 mm, so everything lies flat on the 290 x 290 x 390 bed with no supports. Print time ~89 h against A's 143 h and B's 426 h.

4. **Its structure is checkable and its weak points are cheap to fix.** Everything printed is a tube of revolution at `T` or 2T; the keel is at SF 30, the ducts at SF 14.9 (SF ~2.3 even against a 20 N hand once the wall is 2T and the ring is in), the film is at SF 6-60 in tension. The one number that must not be guessed is the film's grip on the keel, and it is a 10 mm band of epoxy.

5. **What it gives up is shape, not strength.** The envelope will be rounder than the spheroid. That costs drag and it costs the thrusters' clearance from the envelope, not lift. If rhY wants the ellipsoid back, the cheapest way is 2 latitude lacing lines and the 69 g support ring C already carries, not B's 1740 g of battens.

## 10 The three biggest risks, and the cheapest test that retires each

1. **The film's load path: can a bonded film hold the ship up and keep a shape?** Everything in C rests on it, and it is the one part of the study with no CAD behind it. The numbers say it is marginal at 100 Pa (SF 1.2 on the film's tension at the keel rim) and it is not a printed part, so the checker cannot see it. It is also the part the physics says will misbehave when the gas cools: at fixed volume a 15 degC drop costs ~5000 Pa of absolute pressure, 50 x the overpressure, so the envelope goes slack unless the plenum feeds it makeup air [measured physics, ideal gas].
   *Cheapest test:* print one keel rim (a 68 mm ring), bond a 400 mm balloon of the real film to it with a 10 mm band, hang 500 g from the ring, inflate it off the fan through a tube at 100 / 200 / 300 Pa (a water-column manometer), and watch for the film slipping on the bond and for the shape pulling round. One metre of film, one small print, one evening.

2. **Hydrogen out of the envelope.** Film permeation through 7 m2 of metallized PET is small: 0.0-0.0 g of lift a day. Even 12 um LDPE only reaches 2 g a day at the loose end of the permeability range [datasheet range, order of magnitude]. **The seams are the leak**: one 0.1 mm pinhole at 100 Pa passes 20 L/day, 24 g of lift a day - a hundred times the film. A home heat-sealed lap with one channel along it empties the ship overnight.
   *Cheapest test:* seal two 0.3 m2 pouches, one LDPE one metallized PET, fill them from a balloon to a known volume, hang each from a 0.1 g scale for 24 h, and read the lift loss directly (a pouch that loses 10 L of H2 reads 12 g lighter); then inflate one to 300 Pa and feel every seam with soapy water. Half a day of film and no printing.

3. **The printed mass model, i.e. whether LW-PLA really prints at 0.60 g/cm3.** Every margin here is 0.60 g/cm3 [measured, float_budget.py's assumption, never weighed on rhY's machine]. Print at 0.80 instead and the recommended ship at 1.63 m goes from **+250 g to +149 g** - it still flies, but the +250 g margin is gone, and concept A would not float at all.
   *Cheapest test:* print the 100 x 100 x 10 mm lattice coupon and the keel tube, weigh both, and put the measured density into `float_budget.MATERIALS`. It also settles `T` (rule 1) against the real line width, which is what every section modulus in this file is built from. One print, one scale.

Then, in order: the duct as a cantilever (print one 400 mm duct + ring, clamp it, hang 200 g and then 800 g at the free end - this is also test 1 of STRUCTURE-ESTIMATES.md section 8); the peg joint in the frame (print one batten segment pair and pull them apart on a scale); the fan's ability to hold the envelope at 200-300 Pa through a bleed tube (a manometer on the plenum while the fan runs).

## 11 What this study does not settle

- **The envelope's real shape and area.** C uses the spheroid's area as a conservative stand-in for the constant-mean-curvature shape a free film takes. A form-finding run (or the balloon test above with a measuring tape) will put the volume error on the record; it is believed to be under 10 % [guess].
- **Drag and steering with a rounder hull**, and whether the thruster ducts still clear the envelope at the equator once it bulges.
- **The pressure system**: a bleed from the plenum, a relief valve at ~400 Pa, and what happens overnight (section 10 item 1). None of it is designed here.
- **Whether rhY wants the ellipsoid.** If the answer is yes, the honest price is concept B's 1740 g of frame and 2.21 m of hull, or lacing lines whose behaviour nobody has measured.

## Summary

Recommended: concept C - printed core (keel tube, fan housing, 4 tapered ducts (2T root / T mouth) with one support ring, thruster and avionics mounts) + a metallized-PET envelope held at 200-300 Pa, no printed skin.
Size: a = 813 mm, hull diameter 1.63 m, B/a = 0.5006, on the CR-10 Pro bed.
Margin +250 g on 1123 L of H2 at an all-up mass of 1008 g (LW-PLA 0.60 g/cm3, 4S LiPo 1500 mAh on board).
Parts: 47 printed parts, 771 cm3 of plastic, ~89 print hours - against concept A's 256 parts / 143 h at 1.67 m and concept B's 235 parts / 426 h at 2.21 m.
Structure at SF 3: keel SF 30, ducts SF 14.9 (2T wall + ring), film tension SF 6-60, film-on-keel the only marginal joint; the three cheapest tests are a 400 mm film balloon on a bonded keel ring, two sealed pouches on a scale for 24 h, and weighing one LW-PLA print.
