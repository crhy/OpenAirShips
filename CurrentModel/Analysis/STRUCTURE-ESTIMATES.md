# Structure estimates: what the servo pad and the equator brace have to be

f151 shipped `BRACE_W` 6.0 x `BRACE_D` 3.0 and `PAD_T` 1.5 as a **sturdy first guess**.
This file replaces the guess with an estimate whose every input is tagged:

- **[measured]** - measured off this repo's CAD, STL or airflow model, by a named task;
- **[datasheet]** - a published part or material figure;
- **[guess]** - an engineering assumption. Everything that is a guess is listed again in
  section 7 with the test that would replace it.

rhY 2026-11-18 (f152): *"Lighter is better but we need it to be structurally solid. These
are competing requests, and we will have to make trade offs. Until one is built for actual
physical testing and flight, we are going to have to do some educated guesses."*

**`SAFETY_FACTOR = 3` [guess, until a physical test]** - the ratio of the load that would
break the part to the biggest load we expect it to see. It is 3 because (a) the loads below
are guesses, (b) FDM PLA varies by a factor of two between printers, orientations and
batches, and (c) nothing has been tested. When a slice is built and pushed on a scale until
something yields, put the measured number in `brace_sizing.py` and the factor can come down.

The arithmetic is in `CurrentModel/Analysis/brace_sizing.py` - run it, it prints all of the
numbers below:

    /home/rhy/.venvs/cadquery/bin/python -I CurrentModel/Analysis/brace_sizing.py

## 1 Material and printability

| Quantity | Value | Tag |
|---|---|---|
| PLA tensile, along the layers | 35 MPa (range 35-50) | [datasheet range, LOW end used] |
| PLA tensile, **across** the layers | **20 MPa** (range 20-35) | [datasheet range, LOW end used] |
| PLA shear | 12 MPa (= 0.6 x tensile) | [guess] |
| PLA tensile modulus E | 3000 MPa | [datasheet] |
| PLA density / LW-PLA (moderate foam) | 1.24 / 0.80 g/cm3 | [measured, float_budget.py] |
| allowable tensile | 20 / `SAFETY_FACTOR` = **6.67 MPa** | |
| allowable shear | 12 / `SAFETY_FACTOR` = 4.0 MPa | |
| thinnest printable wall | 0.86 mm = 2 perimeters of 0.43 mm | [measured, rule 1] |
| epoxy lap shear | 10 MPa | [datasheet, low end] |

Every stress below is compared against the **across-the-layers** value, because a slice is
printed on its seam face and the brace and the pad both have layer bonds standing in the
path of the interesting loads. The along-the-layers value would be 75 % higher; it is not
used. Rule 1 still wins if the two disagree: **nothing in the model is thinner than 0.86 mm.**

## 2 The parts and the geometry they sit in

| Quantity | Value | Tag |
|---|---|---|
| servo bracket `servo_mount.stl` | 42.3 x 24.2 x 16 mm, 4.3 cm3 = 5.33 g PLA | [measured, Propulsion README] |
| `servo_gear.stl` | 3.8 cm3 = 4.71 g PLA | [measured, Propulsion README] |
| SG90 servo | 9.0 g, stall 1.8 kg-cm | [datasheet] - the double-Kobra v0.2 build |
| MG90S servo | 13.4 g, stall 2.2 kg-cm | [datasheet] - the 8T / 4T bench and CR-10 Pro builds |
| gear pair | 36T m1 spur, pitch radius 18 mm, 20 deg pressure angle | [measured + datasheet] |
| servo spline axis and stem axis | both **radial** (normal to the skin at the equator), 36 mm apart along the tangent (`SERVO_T`) | [measured, generator] |
| brace span (arc on the equator) | **107.1 mm** at scale 1, **174.0 mm** at 1.41 | [measured, `brace_span()`] |
| hull radius at the equator | 207.8 mm / 293.0 mm; circumference 1305 / 1841 mm | [measured] |
| pad footprint (f154's rule) | 42.45 x 28.2 mm = 1190 mm2 | [measured] |
| skin band `T` | 0.86 mm everywhere else | [measured, rule 1] |

The hardware does **not** scale with `OAS_SCALE` (rule: only the hull grows), so the same
brace and pad serve the bench slice and the CR-10 Pro one - and the CR-10 Pro brace is 62 %
longer, which is why the span-dependent cases are checked at 174 mm.

## 3 The loads

| # | Load | Value | Tag |
|---|---|---|---|
| L1 | mass hanging on the pad: servo + bracket + servo gear | 19.0 g (SG90) / 23.4 g (MG90S) = 0.19 / 0.23 N | [measured + datasheet] |
| L2 | servo **stall torque** | 176.6 N.mm (SG90) / 215.8 N.mm (MG90S) | [datasheet] |
| L3 | gear teeth force at stall: tangential / separating | 9.8 / 3.6 N (SG90), 12.0 / 4.4 N (MG90S) | [datasheet + geometry] |
| L4 | fan thrust, whole ship / per 8T thruster / per 4T thruster | 306 gf = 3.0 N / 0.375 N / 0.750 N | [measured, AIRFLOW.md low end of 306-564] |
| L5 | handling / gust / bump factor on L1 and L4 | x 4 | **[guess]** |
| L6 | a hand pressing on a thruster ring | 20 N | **[guess]** |
| L7 | crash deceleration (for the skin buckling check) | 20 g on a 940 g ship | **[guess]** |
| L8 | plenum pressure over the hatch | ~1900 Pa, 13 N | [measured, Propulsion README] |

L5 is **not** applied to L2: the stall torque is already the most the drivetrain can apply
without stripping a gear, so multiplying it by a handling factor would double-count.

## 4 The pad (`servo_pad`, `PAD_T`)

The pad is the wall the bracket is epoxied to. Three ways it can go:

1. **The bond shears.** The gear force (L3) plus the stall torque (L2) put 9.8-12 N of
   in-plane shear and a torsion into a 1190 mm2 bond: 0.008 + 0.017 = **0.026 MPa**
   (SG90), 0.031 MPa (MG90S). Against the PLA's 12 MPa that is SF ~ 400, against epoxy's
   10 MPa SF ~ 320. **The glue is never the limit.**
2. **The pad bends under the bracket.** Model: the bracket's 42.3 mm foot as a strip,
   24.2 mm wide, simply supported, carrying the factored servo weight plus the gear
   separating force: P = 4.3 N (SG90) / 5.3 N (MG90S) -> 1.6-2.0 N.mm per mm of width ->
   `t_min = sqrt(6 m / sigma_allow)` = **1.21 mm (SG90) / 1.34 mm (MG90S)**.
3. **Peel at the pad's near edge** (the edge next to the stem hole): ~0.02 MPa, SF ~ 1000.
   Not a limit; the near edge stands `PAD_RING_CLEAR` off the stem keep-out ring anyway.

**PAD_T = 1.5 mm** (unchanged from f151). The estimate needs 1.34 mm; 1.5 is that rounded
up, and it is the value f154 already proved through the wall map at both print sizes. The
pad adds `PAD_T - T` = 0.64 mm below the band: 1190 mm2 x 0.64 = 761 mm3 = **0.94 g** a
slice. Cutting it to 1.4 would save 0.12 g a slice and has never been printed.

## 5 The brace (`servo_brace`, `BRACE_W` x `BRACE_D`)

Model: a beam **fixed at both ends** - fused into the servo pad at one end and into the
uncut solid band round the far duct's stem bearing boss at the other - spanning the equator
arc L. `BRACE_W` stands up/down the hull, `BRACE_D` is radial, so

    Z (bending about the radial axis) = BRACE_D * BRACE_W^2 / 6
    Z (bending about z, in the skin plane) = BRACE_W * BRACE_D^2 / 6

The servo's stall torque is about a **radial** axis (the spline is radial), so it is the
first of those two that matters, and it is bought with `BRACE_W` **squared**. That is the
whole finding of this estimate: f151's 6.0 x 3.0 put its material in the wrong direction.

| Case | What it is | M at 174 mm span | Tag |
|---|---|---|---|
| C1 | the servo assembly's weight x the handling factor, midspan: `P L / 8` | 20.0 N.mm | L1 x L5 |
| C2 | one thruster's thrust x 4, **shared round the equator**: the brace's tributary width is its own width, because the load enters the hull at the stem's bearing sleeve - 12 mm of solid band at the load point - and the brace is one stringer in a shell of circumference 1841 mm | 0.1 N.mm | L4 x L5, share **[guess]** |
| C2b | the same thrust, all of it on the brace (a bound, reported not designed for) | 32.6 N.mm | L4 x L5 |
| C3 | a hand on a ring, all of it on the brace (a bound, reported not designed for) | 435 N.mm | L6 |
| C4 | **the stall torque as an end moment: the bracket's bond lets go and the brace alone holds the servo at full stall** | 176.6 / 215.8 N.mm | L2, single-failure bound |
| T | torsion of the brace: the factored thrust applied 1 mm off its axis | 1.5 N.mm -> tau 0.09 MPa, SF 129 | [guess] eccentricity |

C4 is the design case, and it is deliberately a **single-failure bound**: section 4 shows the
bond carries the stall reaction with SF ~ 400, so in one piece the brace sees almost none of
it. Sizing the brace for the case where the bond has failed is what "thick enough to support
the servo bracket" (rhY, 2026-11-18) actually means, and it costs about half a gram a slice.

Safety factors for f151's 6.0 x 3.0 (Z = 18.0 / 9.0 mm3):

| Case | stress | SF |
|---|---|---|
| C1 weight | 0.6-1.1 MPa | 18-36 |
| C2 thrust share | 0.01 MPa | > 1000 |
| C2b thrust bound | 2.2-3.6 MPa | 5.5-9.0 |
| **C4 stall bound, SG90** | **9.8 MPa** | **2.04** |
| **C4 stall bound, MG90S** | **12.0 MPa** | **1.67** |
| C3 ring-load bound | 29.7-48.3 MPa | 0.4-0.7 (not a design case) |

So 6.0 x 3.0 does **not** hold `SAFETY_FACTOR = 3` against the one load the brace is there
for. The lightest section that does, searched on a 0.25 mm grid with the print floor (0.86 mm)
and a depth floor of 2.5 mm (see below), is:

    BRACE_W = 9.0 mm, BRACE_D = 2.5 mm   Z = 33.8 / 9.4 mm3
        C4 SG90 SF 3.82, C4 MG90S SF 3.13, C1 SF >= 34, C2b SF 5.7, torsion SF 129

The depth floor `BRACE_D >= 2.5` **[guess]** is there because the maths alone wants a wide,
shallow shelf (10 x 1.72 also passes, and is lighter): 2.5 mm is the 0.86 mm band plus about
four extruded lines of rib, and f150's 1.72 mm rib - band plus two lines, the same section as
a lattice web - is exactly what rhY rejected: *"the equator brace isn't thick enough to
support the servo bracket"*. A 2.5 mm depth also stands further off the duct's air than
f151's 3.0 mm did (the far end keeps >= AIR_KEEP by construction, `servo_brace()`).

## 6 What the brace does to the skin at the equator

The equator is the hull's widest line, the thrusters hang off it, and it is the line a
squeeze or a crash dimsple inward. Classical curved-shell buckling,
`sigma_cr = 0.605 E t / R` with an imperfection knockdown of 0.2 **[guess]**:

| | skin alone (t = 0.86) | with a 2.5 mm brace | with a 3.0 mm brace |
|---|---|---|---|
| scale 1.0, sigma_cr | 1.50 MPa | 4.37 MPa | 5.24 MPa |
| scale 1.41, sigma_cr | 1.07 MPa | 3.10 MPa | 3.72 MPa |
| crash stress (L7: 20 g on 940 g spread round the circumference) | 0.164 / 0.117 MPa | same | same |
| **margin** | **9.1** | **26.6** | **31.9** |

The brace acts as a hoop stringer over its span, so `t` there becomes `BRACE_D` and the
margin rises by `BRACE_D / T`. Going from 3.0 to 2.5 mm gives back 17 % of that margin and
still leaves it an order of magnitude above the crash load: buckling does not choose the
depth, the servo does.

## 7 The trade-off, and what was chosen

Printed material the brace + its lattice corridor + the pad add, per slice and per 8-slice
hull (every 8T slice carries a servo), PLA at 1.24 g/cm3 - LW-PLA gives 65 % of it:

| size W x D | worst SF | g/slice bench | g/hull bench | g/slice x1.41 | g/hull x1.41 |
|---|---|---|---|---|---|
| **9.0 x 2.5 (chosen)** | **3.13** | 4.05 | 32.4 | 5.98 | 47.9 |
| 8.0 x 2.5 (middle) | 2.47 | 3.71 | 29.7 | 5.44 | 43.6 |
| 6.0 x 3.0 (f151) | 1.67 | 3.45 | 27.6 | 5.01 | 40.1 |

**Measured on the rebuild, not estimated:** the bench slice went 30.42 -> **30.77 cm3**
(37.7 -> **38.2 g** PLA), so the change costs **+0.43 g a slice**, a little under the +0.53 g
the table's difference predicts - `added_mm3()` counts the whole corridor strip as new
material, and part of it was already solid band.

**Chosen: `BRACE_W` 9.0, `BRACE_D` 2.5, `PAD_T` 1.5.** It costs +0.53 g a slice (+4.2 g a
hull) at bench and +0.97 g a slice (+7.8 g a hull) at CR-10 Pro scale over f151's guess by the
table, **+0.43 g measured** on the rebuilt bench slice - about 1 % of the printed hull - and it
is the lightest section that holds `SAFETY_FACTOR = 3` against the load the brace exists for. 8.0 x 2.5 is 0.34 g a slice
lighter and holds SF 3.02 for an SG90 but only 2.47 for the MG90S the 8T hulls actually
carry, so it was not taken. 6.0 x 3.0 is 0.6 g a slice lighter again but sits at SF 1.67.

If rhY wants the grams back, the honest way to get them is the physical test in section 8,
not a different load-sharing guess: at 6.0 x 3.0 the brace is fine (SF >= 5) for every load
that is not the single-failure bound.

## 8 What to measure, to turn the [guess] rows into [measured] rows

1. **Push a built slice on a scale until the equator yields**, load at the servo pad with
   the brace free, then again with the brace cut away. That replaces C4's load-sharing
   guess and the whole `SAFETY_FACTOR` argument: if the braced slice survives well past
   216 N.mm at the servo, `BRACE_W` can come back toward 6-7 mm.
2. **Strip an epoxied bracket**: pull the `servo_mount` off a printed pad on a scale. If it
   debonds below the stall load, C4 stops being a bound and becomes the design case; if it
   holds (SF ~ 400 predicted), the brace's own working load is C1 + C2 and the minimum size
   drops to the print floor.
3. **Stall a real servo in the real gear pair** and read the current: the datasheet stall
   torque (1.8 / 2.2 kg-cm) is the only reason the brace is 9 mm wide.
4. **Weigh a printed slice** against the 37.7 g (bench) / 55.1 g (CR-10 Pro) the model
   predicts, and check the actual line width against 0.43 mm: `T`, and with it every section
   modulus here, is derived from it.
5. Note which way the slice was printed: the across-the-layers 20 MPa used everywhere is the
   worst orientation. A brace whose layers run along its length is closer to 35 MPa, which
   would let `BRACE_W` come down about 20 %.

## Summary of what the generator now uses

| Parameter | f151 (guess) | f152 (estimated) | Set by |
|---|---|---|---|
| `BRACE_W` | 6.0 mm | **9.0 mm** | C4 stall bound, Z = BRACE_D x BRACE_W^2 / 6 |
| `BRACE_D` | 3.0 mm | **2.5 mm** | the 2.5 mm depth floor [guess], not the loads |
| `PAD_T` | 1.5 mm | **1.5 mm** | pad plate bending needs 1.34 mm; rounded up |
| `SAFETY_FACTOR` | - | **3** [guess] | this file, section 0 |
