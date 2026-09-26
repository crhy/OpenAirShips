# Electronics: 926 tethered bench demo

- **Parts list:** [BOM.md](BOM.md), with Amazon links.
- **Firmware:** [`firmware/airship_bench`](firmware/airship_bench).

## Wiring

```mermaid
flowchart LR
  PSU["12 V 10 A bench supply"] -->|"+12 V"| FUSE["15 A inline fuse"]
  FUSE -->|"tether, 2-3 m, 16 AWG"| XT["XT60 on the ship"]
  XT --> ESC["30 A ESC"]
  XT --> UBEC["5 V 5 A UBEC"]
  ESC -->|"3 phase wires"| MOTOR["A2212 1000 KV + impeller"]
  ESC -->|"BEC 5 V + GND"| ESP["ESP32 DevKitC: 5V / GND pins"]
  UBEC -->|"5 V servo rail"| PCA["PCA9685: V+ terminal"]
  ESP -->|"3V3 -> VCC, GPIO21 -> SDA, GPIO22 -> SCL, GND"| PCA
  PCA -->|"ch 0-7"| SERVOS["8 x MG90S swivel servos"]
  PCA -->|"ch 8, signal + GND only"| ESC
```

- **Common ground:** tie together the grounds of the ESC, the UBEC, the ESP32 and the PCA9685.
- **ESC red wire:** pull the red (BEC +5 V) pin out of the ESC's signal plug before it goes on PCA9685 channel 8. The ESC's BEC powers the ESP32 through separate leads, and the red wire would otherwise feed into the servo rail.
- **Separate supplies:** the servos run from the UBEC. The ESP32 and the PCA9685 logic run from the ESC's BEC, so servo stalls can't brown out the ESP32.
- **Thruster numbering:** thruster *i* is on seam *i*, at azimuth 22.5° + 45° × *i*, counter-clockwise from +X seen from above. It plugs into PCA9685 channel *i*.
- **Wire routing:**
  - Run the motor wires up one arm of the spider and up the shaft to the top opening, so the plenum stays airtight.
  - The servos sit inside the hull; run their leads along the decks to the electronics bay on the main deck.

## Power budget

| Load | Typical | Peak |
|---|---|---|
| Fan (A2212 + 88 mm impeller, capped at 60 % in firmware) | 30–60 W | ~100 W |
| 8 × MG90S | 1–1.5 A at 5 V | 5.6 A at 5 V if all stall (the UBEC limits this) |
| ESP32 + PCA9685 | 0.25 A at 5 V | 0.5 A |

A 12 V 10 A supply covers this with margin.

## Bench bring-up
1. **Flash the firmware.**
   - Install the ESP32 board package and the "Adafruit PWM Servo Driver Library".
   - Open `firmware/airship_bench/airship_bench.ino` and flash it to the "ESP32 Dev Module".
2. **Check the servos with the impeller off.**
   - Join Wi-Fi "OpenAirShip" (the password is in the sketch; change it) and open http://192.168.4.1.
   - All 8 servos should centre, with lift at +1 and every jet pointing down.
   - Move the Yaw slider: every thruster should tilt the same way.
   - Set per-servo trim in `SERVO_TRIM_DEG`.
3. **Calibrate the ESC (impeller off).** Follow its manual: throttle high at power-on, then low. The firmware sends 1000–2000 µs.
4. **First spin (impeller on).**
   - Press ARM and raise the throttle slowly.
   - The firmware caps the throttle at 60 % (`THROTTLE_LIMIT`) until the impeller has been spun up and checked.
   - The fan stops on STOP, or within 1 s if the page loses its link.
5. **Measure.**
   - Put the ship on a kitchen scale: the weight drop is the lift.
   - With the optional sensors (BOM items 17–18), log plenum pressure and power against throttle.

## Firmware
- **`mixer.h`:** turns lift, surge, sway and yaw commands into 8 swivel angles. Every thruster pushes with about the same force because they share one fan, so the mixer steers direction only; the throttle sets magnitude.
- **Host test:** `g++ -std=c++17 -Iairship_bench test/test_mixer.cpp && ./a.out`, run from `firmware/`. It checks pure lift, yaw, surge, sway, the ±90° limits and the servo pulses. All of these pass.
- **`airship_bench.ino`:** the Wi-Fi access point, the control page, ESC arming and the link-loss failsafe. It has been compiled on a PC against stand-ins for the Arduino APIs, **but not yet built or run on a real ESP32**.
