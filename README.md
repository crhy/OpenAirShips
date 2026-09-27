# OpenAirShips
Free Travel and Total Liberty for All Humanity

All relevant information is on http://OpenAirShips.com. Pop in and join the conversation on our Discord: https://discord.gg/wZ6nu7H

![OpenAirShipsLogo](https://github.com/user-attachments/assets/ed0b83d8-38ed-4dbf-87db-a51a390f2581)

## Build it: the 926 bench model, v0

![OpenAirShips 926 bench model v0](CurrentModel/CAD%20Files/Propulsion/ship_with_thrusters.png)

The first buildable OpenAirShip is a 415 mm, 3D-printable, tethered bench model. It is made of 8 identical hull slices, a shrouded fan in the central shaft, and 8 vectoring air-multiplier thrusters on the equator. It's built to measure and control thrust on the bench, not to fly yet. Everything is open source.

![section through a seam](CurrentModel/CAD%20Files/SimplifiedSlice/section.png)

| | |
|---|---|
| **Printable STL** | Hull slice, print 8: [PieSlice926clauderevE.stl](CurrentModel/Print%20Files/PieSlice926clauderevE.stl) · Propulsion parts: [CAD Files/Propulsion/print](CurrentModel/CAD%20Files/Propulsion/print) |
| **CAD (FreeCAD)** | [airship pie slice 926.FCStd](CurrentModel/CAD%20Files/SimplifiedSlice/airship%20pie%20slice%20926.FCStd) · [propulsion 926.FCStd](CurrentModel/CAD%20Files/Propulsion/propulsion%20926.FCStd) · plus STEP and parametric Python sources |
| **Bill of materials** | [Electronics/BOM.md](CurrentModel/Electronics/BOM.md): about $230–320 for the core parts, with Amazon links |
| **Build notes** | [Hull slice](CurrentModel/CAD%20Files/SimplifiedSlice/README.md) · [Propulsion](CurrentModel/CAD%20Files/Propulsion/README.md) · [Electronics and firmware](CurrentModel/Electronics/README.md) |
| **Engineering** | [Airflow analysis](CurrentModel/Analysis/AIRFLOW.md) · [Design constraints](CurrentModel/DESIGN-CONSTRAINTS.md) · [Open questions](CurrentModel/OPEN-QUESTIONS.md) |
| **Changelog** | [v0 changelog](CurrentModel/CHANGELOG.md) |

**At a glance**
- **Hull:** 8 × ≈ 40 g PLA slices (≈ 320 g) on a Prusa MK3S+. The outside is a smooth ellipsoid. It's lattice everywhere except the airtight air path.
- **Fan:** a 2207 1750 KV motor on 4S drives an 88 mm PETG impeller, and the hull's housing wall is its shroud. It comes out through a bayonet hatch in the keel.
- **Thrust:** about 410 gf expected (306–564 gf until measured), from 8 thrusters that each swivel ±90° on MG90S servos.
- **Control:** an ESP32 and a PCA9685, with a Wi-Fi control page and a link-loss failsafe.

<p>
<img src="CurrentModel/CAD%20Files/SimplifiedSlice/slice.png" width="32%" alt="one slice">
<img src="CurrentModel/CAD%20Files/Propulsion/fan_unit.png" width="32%" alt="shrouded fan">
<img src="CurrentModel/CAD%20Files/Propulsion/thruster.png" width="32%" alt="air-multiplier thruster">
</p>

## Archive
Download the PDFs of the 2024 website here: https://github.com/crhy/OpenAirShips/tree/main/WebSnap2024
