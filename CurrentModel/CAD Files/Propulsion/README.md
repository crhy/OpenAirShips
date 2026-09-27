# Propulsion: fan, thrust pipes and air-multiplier thrusters (926, rev E)

![thruster](thruster.png)
![fan unit](fan_unit.png)
![impeller](impeller.png)
![ship with thrusters](ship_with_thrusters.png)

## How the air moves
1. The impeller at the bottom of the central shaft pulls air in over the bellmouth at the top of the hull and **down the shaft**. Nothing sits in the shaft: the motor stands on a pedestal on the keel, under the impeller.
2. It throws the air outward into the **fan housing (plenum)** under the floor (z = −70). The shaft, the housing ceiling and the keel under it are solid, airtight walls; glue their seams with epoxy.
3. The plenum feeds the **8 thrust ducts**, which run *inside* the skin to the equator. The hull's outside stays smooth.
4. At each seam a rotating **stem** passes through a round hole in the skin. Its flange sits behind a bearing boss inside the duct, and it carries a printed **air-multiplier ring** with a Coanda lip and a 1.2 mm slot.
5. An MG90S servo **inside the hull** turns the stem through a 1:1 pair of 36-tooth gears just outside the skin, giving ±90° of travel. Only the stem and the servo gear's hub pass through the skin. The swivel axis is radial, so each jet can point anywhere between up/down and sideways along the hull. Together the 8 thrusters give lift, yaw, surge and sway.

## Parts
Print from `print/*.stl`. Each file is already posed for printing: PLA, 0.2 mm layers, 0.4 mm nozzle, MK3S+.

| Part | Qty | cm³ each | Print notes |
|---|---|---|---|
| `impeller` | 1 | 6.2 | **PETG**; the tip runs at 72 m/s. Backplate on the bed; no supports, as the cup top bridges 31 mm. Open (unshrouded) backward-curved rotor, 88 mm, 7 blades, sized by the airflow analysis. Lightened: 0.8 mm backplate, 0.86 mm blades, scalloped rim. A 0.86 mm **cup** fits over the motor bell, and its 2 mm top disc is clamped between the bell and the prop nut. About 8 g. It is balanced by design; still check it on a pencil. |
| `motor_pedestal` | 1 | 2.5 | Top plate on the bed; no supports. A low drum whose bottom follows the keel. The 2207 bolts to its top from below (4 × M3 × 6, 16 × 16 mm). Then it glues into the socket ring on the keel. The wire notch lines up with a Ø6 hole you drill in the keel for the phase wires; seal it with epoxy. |
| `servo_mount` | 8 | 4.3 | Plate down; no supports. Epoxy it to the inside of the skin, centred on the Ø8 servo hole. The servo drops in with its spline outward and is held by two M2 screws driven from inside the hull. |
| `stem` | 8 | 3.6 | Flange down; no supports. Put it into the stem hole from inside the half-duct **before** joining the neighbouring slice. Wrap it in PTFE tape. |
| `stem_gear` | 8 | 2.1 | Flat. Glue it on the stem's D-flat. |
| `servo_gear` | 8 | 3.8 | Hub down. Its hub reaches through the Ø8 skin hole onto the servo spline. Glue it and fix it with the servo's horn screw from outside. |
| `thruster_ring` | 8 | 14.0 | Exit down, axis vertical; no supports. Every surface faces up or overhangs 45° or less. Check the 1.2 mm slot is clear; a 1.0 mm shim works. |

- **Total printed propulsion:** about 225 cm³ of PLA (≈ 280 g), plus the PETG impeller (≈ 8 g).
- **Motor:** 2207 1750 KV on 4S (≈ 32 g, ≈ 25 A at full throttle). The impeller needs about 15,700 rpm; see [../../Analysis/AIRFLOW.md](../../Analysis/AIRFLOW.md).
- **Parametric source:** `propulsion.py`. All dimensions are at the top.
- **Fit checks:** `check_fit.py` checks the parts against the hull: the impeller, motor, pedestal and prop nut (and that nothing sits in the shaft bore), the stems, the servos and their mounts, the gears, and the rings at −90…+90°, including against the neighbouring thruster. They all pass.

## Assembly order
1. Assemble the slices. Epoxy the shaft, floor and keel seams so they are airtight.
2. **Stems and servo mounts, while the slices are still apart.**
   - Put each stem into its stem hole from inside the open half-duct, then join and epoxy the neighbouring slice. This closes the duct and traps the stem's flange behind the boss.
   - Epoxy each servo mount inside the skin over its Ø8 hole. Drop the servo in and screw it from inside.
3. **Gears and rings.**
   - Centre the servos (the firmware centres every servo at boot).
   - Mesh the gears with the ring's exit pointing **down**, then glue the ring onto the stem.
4. **Fan unit** (before the last slice closes the ring, or later down the shaft).
   - Drill a Ø6 hole in the keel beside the socket ring and pass the motor wires through it.
   - Bolt the 2207 to the pedestal (4 × M3 × 6 from below), line the wire notch up with the hole, and epoxy the pedestal into the socket ring. Seal the wire hole.
   - Drop the impeller **down the shaft from the top** (88 mm through the 94.75 mm bore), onto the motor shaft. Its cup sits on the bell. Fix it with the M5 prop nut.
   - The blade tops end 0.8 mm below the housing ceiling. That relies on the motor measuring 20 mm from mount face to bell top (`MOTOR_L`); shim under the pedestal plate or change `MOTOR_L` if yours differs.
   - Trim any motor shaft that sticks up past the nut, so it doesn't poke into the shaft mouth.
5. Wire it up as in [../../Electronics/README.md](../../Electronics/README.md).

## Known limits (to bench-test)
- **Impeller:** it's open, so some air slips over the blade tops. The scalloped rim also lets some air fall back from the plenum into the passages. If plenum pressure comes out low, try `IMP_SCALLOP_R = 44` (no scallops, +3.5 g) before adding a printed shroud ring.
- **Motor cooling:** the 2207 sits under the impeller, in the housing's airflow. Check it's warm, not hot, after a full-throttle run.
- **Swivel seal:** it's a plain bore through the skin and boss, with PTFE tape, and some leakage is expected. Measure it before adding an O-ring.
- **Servo height:** it depends on your MG90S. If the gear hub doesn't reach the spline, shim under the servo's tabs.
- **Air-multiplier slot:** 1.2 mm is the analysis optimum for this fan. Try 1.0 or 1.5 mm (`SLOT`) and compare thrust on the scale.
