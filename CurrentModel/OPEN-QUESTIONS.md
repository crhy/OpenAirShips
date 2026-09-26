# Open questions (after the 926 bench demo)

## 1. Flight-control code
The bench firmware (`Electronics/firmware`) maps stick commands straight to thruster angles. Flight needs these next:
- **Attitude and heading hold:** a PID loop on yaw from an IMU (BOM item 19), then altitude hold from a barometer.
- **Thrust model:** measure thrust against fan throttle and swivel angle on the scale, then fit a curve so the mixer can command forces rather than angles.
- **Buoyancy trim:** once gas is aboard, fan lift only has to cancel the error between weight and buoyancy. That changes the control design from "hover on thrust" to "trim, then manoeuvre".
- **Failsafes:** tether or link loss, low battery, a stalled servo (measure current per channel).

## 2. Hydrogen, ballonets and pressure control: deferred to a larger model
The printed 926 hull holds only 0.0188 m³ (4/3·π·0.2078²·0.104). Filled with hydrogen that lifts about **21 g** (≈1.1 kg/m³ net), against about 450 g of printed hull alone. With fixed wall thickness, lift grows with size³ but hull mass only with size². Break-even is therefore roughly 450/21 ≈ **20× this size, about 8–9 m in diameter**, before counting payload, gas cells or propulsion. So:
- **Envelope:** at larger scale the gas lives in lightweight cells inside the frame, not in the printed skin.
- **Ballonet material candidates** (to compare on cost per m², g/m², H₂ permeability, and whether they can be heat-sealed):
  - metallised BoPET (Mylar) film
  - TPU-coated nylon ripstop
  - LDPE or LLDPE film (cheapest, but permeable)
  - laminated polyethylene / EVOH barrier film
- **Pressure regulation:**
  - differential pressure sensors per cell
  - a small blower or valve per ballonet
  - relief valves sized for the maximum climb rate
- **Hydrogen safety** needs its own review: venting paths, keeping ignition sources out of gas spaces, antistatic materials, and leak detection.

These need their own design pass at the larger model's scale.
