# Bill of materials: 926 tethered bench demo

The links are **Amazon search links**, not specific listings. Listings and prices change constantly, so pick a well-reviewed seller. Prices are rough USD estimates as of September 2026. **Check each listing's specs against the "Must match" column before buying.** Those dimensions are the ones the printed parts are designed around.

## Propulsion and control

| # | Part | Qty | Must match | ~USD | Link |
|---|---|---|---|---|---|
| 1 | **2207 1750 KV** brushless motor (5" FPV racing size, 4S rated). The airflow analysis needs about 15,700 rpm; see `../Analysis/AIRFLOW.md` | 1 (+1 spare) | ≈28 mm bell, ≤ 20 mm mount face to bell top, M3 holes on a **16 × 16 mm** square, M5 threaded shaft with a nut, ≈30–35 g | 15–25 each | [search](https://www.amazon.com/s?k=2207+1750KV+brushless+motor+4S) |
| 1a | 45 A BLHeli_S (or BLHeli_32) single ESC, 2–6S | 1 | Standard PWM input (1000–2000 µs); a BEC is optional | 15–25 | [search](https://www.amazon.com/s?k=45A+BLHeli+ESC+2-6S+single) |
| 2 | MG90S metal-gear micro servo | 8 (+2 spare) | 22.8 × 12.2 mm body, 27.8 mm screw pitch, 180° travel | 25–30 for 10 | [search](https://www.amazon.com/s?k=MG90S+metal+gear+micro+servo+10+pack) |
| 3 | ESP32-WROOM-32 DevKitC (38-pin) | 1 (+spare) | Classic ESP32 with Wi-Fi | 15–20 for 3 | [search](https://www.amazon.com/s?k=ESP32+WROOM-32+DevKitC+38+pin) |
| 4 | PCA9685 16-channel 12-bit PWM / servo driver | 1 | Address 0x40; has a V+ screw terminal | 8–12 for 2 | [search](https://www.amazon.com/s?k=PCA9685+16+channel+servo+driver) |
| 5 | 5 V 5 A UBEC (switch-mode regulator for the servo rail) | 1 | 7–25 V in, 5 A continuous | 8–12 | [search](https://www.amazon.com/s?k=5V+5A+UBEC) |

## Power and tether

| # | Part | Qty | Must match | ~USD | Link |
|---|---|---|---|---|---|
| 6 | 4S 1500 mAh LiPo (XT60) + a balance charger. Alternative: a 15 V 350 W supply, with the throttle capped at 90 % | 1–2 | 14.8 V, ≥ 75C (the fan draws about 25 A at full throttle) | 30–45 + 25–40 charger | [search](https://www.amazon.com/s?k=4S+1500mAh+LiPo+XT60) |
| 7 | Inline fuse holder + 30 A fuses (ATC blade or MIDI) | 1 | Rated for 12 AWG | 8–12 | [search](https://www.amazon.com/s?k=inline+fuse+holder+12+AWG+30A) |
| 8 | 12 AWG silicone wire, red/black (battery leads, ≤ 30 cm) + 470 µF 35 V low-ESR capacitor | 1 | Flexible silicone jacket | 10–14 | [search](https://www.amazon.com/s?k=12+AWG+silicone+wire+red+black) |
| 9 | XT60 connector pairs | 1 pack | | 7–10 | [search](https://www.amazon.com/s?k=XT60+connectors+male+female) |
| 10 | Servo extension leads, 30 cm | 10 | JR/Futaba 3-pin | 7–10 | [search](https://www.amazon.com/s?k=servo+extension+cable+30cm+10+pack) |
| 11 | Dupont jumper wires (F-F) | 1 pack | | 6–8 | [search](https://www.amazon.com/s?k=dupont+jumper+wires+female+female) |

## Hardware and consumables

| # | Part | Qty | Must match | ~USD | Link |
|---|---|---|---|---|---|
| 12 | M3 socket-head screw assortment | 1 | Motor to pedestal: 4 × M3 × 6 (check your motor's thread depth) | 10–14 | [search](https://www.amazon.com/s?k=M3+socket+head+screw+assortment) |
| 13 | PLA filament, 1.75 mm, 1 kg | 1 | Hull ≈ 325 g (8 × ≈ 40 g), propulsion except the impeller ≈ 250 g | 18–22 | [search](https://www.amazon.com/s?k=PLA+filament+1.75mm+1kg) |
| 13a | PETG filament, 1.75 mm (the impeller: its tip runs at 72 m/s, and PLA creeps when warm) | 1 small spool | ≈ 8 g per impeller; print 2 | 18–22 | [search](https://www.amazon.com/s?k=PETG+filament+1.75mm) |
| 14 | 5-minute epoxy (airtight seams: shaft, floor, keel, ducts; servo mounts) | 1 | | 7–10 | [search](https://www.amazon.com/s?k=5+minute+epoxy) |
| 15 | CA glue, thin + gel | 1 | | 7–10 | [search](https://www.amazon.com/s?k=CA+glue+thin+gel) |
| 16 | PTFE thread-seal tape (swivel bearing wrap) | 1 | | 3–5 | [search](https://www.amazon.com/s?k=PTFE+tape) |

## Optional, for measurements and later work

| # | Part | Qty | Why | ~USD | Link |
|---|---|---|---|---|---|
| 17 | MPXV7002DP differential pressure sensor | 1 | Plenum pressure versus fan throttle | 12–18 | [search](https://www.amazon.com/s?k=MPXV7002DP) |
| 18 | INA219 or INA226 current/power sensor | 1 | Fan power draw | 6–10 | [search](https://www.amazon.com/s?k=INA226+current+sensor) |
| 19 | BNO085 or MPU6050 IMU | 1 | Heading hold, first flight-control code | 8–25 | [search](https://www.amazon.com/s?k=BNO085+IMU) |
| 20 | Digital kitchen scale, 0.1 g (on the bench as a thrust stand) | 1 | Measuring lift and thrust | 10–15 | [search](https://www.amazon.com/s?k=digital+scale+0.1g) |
| 21 | Spare 4S 1500 mAh LiPo | 1 | Longer bench sessions | 30–45 | [search](https://www.amazon.com/s?k=4S+1500mAh+LiPo+XT60) |

**Core cost (items 1–16):** about $230–320. The optional items add about $40–140.
