# OpenAirShips
Free Travel and Total Liberty for All Humanity

All relevant information is on http://OpenAirShips.com. Pop in and join the conversation on our Discord: https://discord.gg/wZ6nu7H

![OpenAirShipsLogo](https://github.com/user-attachments/assets/ed0b83d8-38ed-4dbf-87db-a51a390f2581)

## Build it: the 1026 model, v0.2.1

![OpenAirShips 1026 v0.2.1, double Kobra size, self-contained](CurrentModel/Renders/v0.2-double-Kobra-ship.png)

The first buildable OpenAirShip is a 3D-printable model. It has a smooth ellipsoid hull of printed slices, a shrouded fan in a smooth central intake, and vectoring air-multiplier thrusters on the equator. Everything is open source.

### New in v0.2.1 (October 2026)
- **Flush fan housing:** each thrust duct now runs straight on from the fan housing, with no step inside or out. The ducts hug the hull curve all the way from the fan.
- **Lighter keel:** the ovals and diamonds now reach right up to the fan housing, so the hull is 4–7% lighter in every size.
- **Renamed 1026** for October 2026. The 926 files are in [`OldFiles`](OldFiles).
- **Corrected float numbers:** the v0.2 budget undercounted the double-Kobra hull (it measured 350 cm³ instead of 502). The figures below are the corrected ones, for the new, lighter hull.

### The double-Kobra build: it floats
The **double-Kobra build** is 1.58 m across. It carries its own battery and ESP32 controller and **floats on hydrogen alone**, for indoor flights in a garage or warehouse.
- **Hull:** 12 slices (4 left, 4 right, 4 plain). Each prints in 5 pieces on an Anycubic Kobra Max, and the intake shaft is two printed tubes.
- **Weight:** 977 g all-up in full-foam lightweight PLA with a 1500 mAh LiPo. Its 1022 L of hydrogen lifts 1145 g, so it has **168 g to spare**, and about 44 minutes of flight.
  - An 18650 pack gives 83 minutes, with 153 g to spare.
  - **Use full-foam LW-PLA:** in moderate foam it only just floats (+27 g with the LiPo, +12 g with the 18650 pack), and the 21700 pack makes it 93 g too heavy. See [FLOAT.md](CurrentModel/Analysis/FLOAT.md).
  - On helium (about 7% less lift) the full-foam LiPo build still floats, with about 84 g to spare.
- **Downloads:**
  - [Print files: 15 hull pieces + 2 intake tubes](CurrentModel/Print%20Files/v0.2.1%20double%20Kobra)
  - [Propulsion and avionics tray STLs](CurrentModel/CAD%20Files/Propulsion/4T/small/12s/x3.8/print)
  - [Build notes](CurrentModel/CAD%20Files/SimplifiedSlice/README.md#v02-double-kobra-build-x38-158-m-12-slices-in-pieces)
  - [Self-contained electronics](CurrentModel/Electronics/README.md#v02-self-contained-build-no-tether)
  - [BOM changes](CurrentModel/Electronics/BOM.md#v02-self-contained-double-kobra-build-changes-to-the-list-above)

### Bench and Kobra Max models (tethered)
| | 8 thrusters | 4 thrusters |
|---|---|---|
| **Bench size, 415 mm** (Prusa MK3S+) | [PieSlice1026-v0.2.1-8T.stl](CurrentModel/Print%20Files/PieSlice1026-v0.2.1-8T.stl), print 8 | [left](CurrentModel/Print%20Files/PieSlice1026-v0.2.1-4T-left.stl) and [right](CurrentModel/Print%20Files/PieSlice1026-v0.2.1-4T-right.stl), print 4 of each |
| **Kobra Max size, 790 mm** (Anycubic Kobra Max) | [PieSlice1026-v0.2.1-8T-KobraMax.stl](CurrentModel/Print%20Files/PieSlice1026-v0.2.1-8T-KobraMax.stl), print 8 | [left](CurrentModel/Print%20Files/PieSlice1026-v0.2.1-4T-left-KobraMax.stl) and [right](CurrentModel/Print%20Files/PieSlice1026-v0.2.1-4T-right-KobraMax.stl), print 4 of each |
| **Propulsion parts (STL)** | [bench](CurrentModel/CAD%20Files/Propulsion/print) · [Kobra Max](CurrentModel/CAD%20Files/Propulsion/x1.9/print) | [bench](CurrentModel/CAD%20Files/Propulsion/4T/print) · [Kobra Max](CurrentModel/CAD%20Files/Propulsion/4T/x1.9/print) |
| **Expected thrust** | ≈ 408 gf | ≈ 422 gf |

These don't float on hydrogen alone, but they can hover on their fan. The 4-thruster Kobra Max model in full-foam lightweight PLA (503 g, 124 L of hydrogen) has 55 g to spare, and the 4-thruster bench model in full foam (368 g) has 73 g.

| | |
|---|---|
| **CAD (FreeCAD, STEP, parametric Python)** | [Hull slices](CurrentModel/CAD%20Files/SimplifiedSlice) · [Propulsion](CurrentModel/CAD%20Files/Propulsion) |
| **Bill of materials** | [Electronics/BOM.md](CurrentModel/Electronics/BOM.md): about $230–320 for the core parts, with Amazon links, a lightweight-PLA option and the v0.2 changes |
| **Build notes** | [Hull slice](CurrentModel/CAD%20Files/SimplifiedSlice/README.md) · [Propulsion](CurrentModel/CAD%20Files/Propulsion/README.md) · [Electronics and firmware](CurrentModel/Electronics/README.md) |
| **Engineering** | [Will it float?](CurrentModel/Analysis/FLOAT.md) · [Airflow](CurrentModel/Analysis/AIRFLOW.md) · [Airflow, 4 thrusters](CurrentModel/Analysis/AIRFLOW-4T.md) · [Design constraints](CurrentModel/DESIGN-CONSTRAINTS.md) · [Open questions](CurrentModel/OPEN-QUESTIONS.md) |
| **Changelog** | [v0 → 1026 v0.2.1](CurrentModel/CHANGELOG.md) |

<p>
<img src="CurrentModel/Renders/v0.2-double-Kobra-below.png" width="49%" alt="v0.2 from below: fan hatch, avionics tray, intake tubes">
<img src="CurrentModel/Renders/v0.1-8T-section.png" width="49%" alt="8 thrusters, section through a seam">
</p>

**At a glance**
- **Hull:** 0.86 mm airtight walls. The outside is a smooth ellipsoid, and it's lattice everywhere except the air path. The intake is Ø66 from the bellmouth down to the fan.
- **Fan:** a 2207 1750 KV motor on 4S drives an 88 mm PETG impeller, and the hull's housing wall is its shroud. It comes out through a bayonet hatch in the keel.
- **Thrusters:** 8 or 4, each swivelling ±90° on a micro servo, exactly on the equator.
- **Control:** an ESP32 with a Wi-Fi control page and a link-loss failsafe. It drives a PCA9685 on the bench models, or the servos and ESC directly on v0.2, with a battery monitor.

## Repository layout
| Folder | What's in it |
|---|---|
| [`CurrentModel/`](CurrentModel) | **The current buildable model (1026 v0.2.1):** CAD, print files, propulsion, electronics, firmware, analysis and [changelog](CurrentModel/CHANGELOG.md) |
| [`web/`](web) | Source for [OpenAirShips.com](http://OpenAirShips.com) (static site on Cloudflare) |
| [`docs/`](docs) | Project notes: website deployment and content audit, the Unreal diagnostic report |
| [`WhitePaper/`](WhitePaper) | Whitepaper and builder guide |
| [`Art/`](Art), [`vidz/`](vidz) | Logos, concept art and concept videos |
| [`WebSnap2024/`](WebSnap2024) | PDFs of the 2024 website |
| [`OldFiles/`](OldFiles) | Earlier models and print files, kept for history |
