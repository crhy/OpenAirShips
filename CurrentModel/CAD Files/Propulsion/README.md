# Propulsion: fan, thrust pipes and air-multiplier thrusters (926, v0)

![thruster](thruster.png)
![fan unit](fan_unit.png)
![ship with thrusters](ship_with_thrusters.png)

## How the air moves
1. The impeller at the bottom of the central shaft pulls air **down the shaft**.
2. It throws the air outward into the **plenum** between the floor (z = −70) and the keel. The shaft, floor and keel are solid, airtight walls; glue their seams with epoxy.
3. The plenum feeds the **8 thrust pipes**. Their outlets open through the hull at the seams around the equator.
4. An **outlet hood** is glued over each outlet. It carries a swivel sleeve and a servo bracket.
5. A rotating **stem** carries a printed **air-multiplier ring** with a Coanda lip and a 0.8 mm slot.
6. An MG90S servo turns the stem through a 1:1 pair of 36-tooth gears, giving ±90° of travel. The swivel axis is radial, so each jet can point anywhere between up/down and sideways along the hull. Together the 8 thrusters give lift, yaw, surge and sway.

## Parts
Print from `print/*.stl`. Each file is already posed for printing: PLA, 0.2 mm layers, 0.4 mm nozzle, MK3S+.

| Part | Qty | cm³ each | Print notes |
|---|---|---|---|
| `impeller` | 1 | 9.7 | Backplate on the bed; no supports. Open (unshrouded) backward-curved rotor, 88 mm, 7 blades. Balance it on a pencil and sand the heavy side. |
| `motor_spider` | 1 | 8.0 | Flat; no supports. Sits on the 2 mm ledge inside the shaft at z = −46. The A2212 bolts **under** it (4 × M3 × 6, 16 or 19 mm pattern). |
| `outlet_hood` | 8 | 11.7 | Sleeve up. **Tree supports under the curved flange only.** Epoxy it over the seam outlet; it also locks the two slices together there. |
| `stem` | 8 | 2.4 | Flange down; no supports. Put it into the hood from the inside **before** gluing the hood on. Wrap it in PTFE tape. |
| `stem_gear` | 8 | 2.8 | Flat. Glue it on the stem's D-flat. |
| `servo_gear` | 8 | 3.4 | Flat. Glue an MG90S single-arm horn into the pocket and screw it to the servo. |
| `thruster_ring` | 8 | 11.1 | Exit down, axis vertical; no supports. Every surface faces up or overhangs 45° or less. Check the 0.8 mm slot is clear; a blade of 0.6 mm shim works. |

- **Total printed propulsion:** about 275 cm³, roughly 340 g of PLA.
- **Parametric source:** `propulsion.py`. All dimensions are at the top.
- **Fit checks:** `check_fit.py` checks the parts against the hull: the motor unit, the hoods, and the rings at −90…+90°, including against the neighbouring thruster. They all pass.

## Assembly order
1. Assemble the slices. Epoxy the shaft, floor and keel seams so they are airtight.
2. **Stems into the hoods.** Put each stem into its hood from the inside, then epoxy the hood over its seam outlet.
3. **Servos and gears.**
   - Screw the servo to its bracket, then centre it (the firmware centres every servo at boot).
   - Mesh the gears with the ring's exit pointing **down**, then glue the ring onto the stem.
4. **Fan unit.**
   - Bolt the A2212 under the spider and clamp the impeller on the prop adapter.
   - Lower the whole unit **down the shaft from the top** until the spider sits on the ledge. The 88 mm impeller passes the ledge's 90.8 mm bore.
   - The impeller's blade tops end 0.8 mm below the shaft mouth. The prop adapter's shoulder sets the height; adjust `ADAPTER_SHOULDER` if yours differs.
5. Wire it up as in [../../Electronics/README.md](../../Electronics/README.md).

## Known limits of v0 (to bench-test)
- **Impeller:** it's open, so some air slips over the blade tops. If plenum pressure comes out low, a printed shroud ring is the next step.
- **Motor choice:** the A2212 is the cheap, common choice but heavy (~50 g). A 2205–2207 drone motor saves ~25 g if the fan needs less power than expected.
- **Swivel seal:** it's a plain sleeve with PTFE tape, and some leakage is expected. Measure it before adding an O-ring.
- **Air-multiplier slot:** 0.8 mm is at the limit of FDM accuracy. Try 0.6 or 1.0 mm (`SLOT`) and compare thrust on the scale.
