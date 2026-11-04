# PhysioBand AI - Hardware Setup

Only the approved components are used: ESP32 DevKit V1, 2 x MPU6050 (GY-521), S-type load cell,
HX711, protected 18650 cell + holder, TP4056 charger (with protection), regulated 5 V boost converter,
resistance band, jumper wires, general-purpose PCB, arm straps and mounting hardware.

> **First test on USB power.** Wire and test all sensors with the ESP32 powered from the PC's USB port.
> Connect the battery circuit only after everything works.

## 1. Wiring

### 1.1 Two MPU6050 (GY-521) on one I2C bus

| GY-521 pin | Upper-arm sensor | Forearm sensor | ESP32 |
|---|---|---|---|
| VCC | -> | -> | **3V3** |
| GND | -> | -> | **GND** |
| SCL | -> | -> | **GPIO 22** |
| SDA | -> | -> | **GPIO 21** |
| AD0 | **GND** (address 0x68) | **3V3** (address 0x69) | - |
| XDA, XCL, INT | not connected | not connected | - |

* Both modules share SDA/SCL. The address pin AD0 is what makes them distinguishable: LOW = 0x68, HIGH = 0x69.
  Never leave AD0 floating - wire it explicitly.
* GY-521 boards have their own regulator and I2C pull-up resistors; powering them from 3V3 keeps the bus at 3.3 V (safe for the ESP32).
* The forearm sensor is further away: keep the I2C wires short (ideally < 50 cm), twist SDA with GND and SCL with GND,
  and strap the cable along the arm. If you see I2C errors, lower `I2C_CLOCK_HZ` in `config.h` to `100000UL`.
* Verify with the serial command `i2c` - it must list `0x68` and `0x69`.

### 1.2 S-type load cell -> HX711 -> ESP32

| Load-cell wire | HX711 terminal | Function |
|---|---|---|
| Excitation + | **E+** | bridge supply + |
| Excitation - | **E-** | bridge supply - |
| Signal + | **A+** | output + (channel A, gain 128) |
| Signal - | **A-** | output - |
| Shield (if present) | GND | optional, reduces noise |

| HX711 pin | ESP32 | Notes |
|---|---|---|
| VCC (and VDD if separate) | **3V3** | the DT logic level equals the HX711 supply, so 3.3 V keeps it ESP32-safe |
| GND | **GND** | |
| DT (DOUT) | **GPIO 16** | `PIN_HX711_DT` in `config.h` |
| SCK (PD_SCK) | **GPIO 4** | `PIN_HX711_SCK` in `config.h` |

**Wire colours are not standardised.** A common scheme is red = E+, black = E-, green = A+, white = A-, but many
S-type cells differ. Always use the manufacturer's datasheet/label. If it is missing:

1. With a multimeter on the resistance range, measure all six pairs of the four wires.
2. The two pairs that are *not* "opposite" read about 3/4 of the bridge resistance; the excitation pair and the signal pair read the full bridge resistance.
3. The excitation (input) pair usually reads slightly higher (e.g. ~400 ohm) than the signal (output) pair (e.g. ~350 ohm).
4. If the force reads negative when you pull the band, swap A+ and A- (or let calibration use a negative factor).

The HX711 produces 10 samples/s on most modules (RATE pin to GND) or 80 samples/s (RATE pin high). The firmware
samples at 50 Hz and holds the latest load-cell value between conversions; the ML pipeline low-pass filters it.

### 1.3 Power supply (after USB tests pass)

```text
 protected 18650  -->  TP4056 (with protection)  -->  5 V boost converter  -->  ESP32 VIN (5V) + GND
 in 18650 holder      B+ / B-  = battery              IN+ / IN- from OUT+/OUT-      ESP32 3V3 -> sensors
                      OUT+/OUT- = load
                      USB socket = charging input
```

| From | To |
|---|---|
| Battery holder + / - | TP4056 **B+ / B-** |
| TP4056 **OUT+ / OUT-** | Boost converter **IN+ / IN-** |
| Boost converter **OUT+ (5.0 V)** | ESP32 **VIN** (labelled VIN or 5V) |
| Boost converter **OUT-** | ESP32 **GND** |
| ESP32 **3V3 / GND** | MPU6050 x 2 and HX711 (as above) |

* **TP4056 is a charger, not a voltage regulator.** Its OUT pins carry the raw battery voltage (about 3.0 - 4.2 V).
  Never connect them, or the battery, directly to the ESP32 5V/VIN or 3V3 pins - always go through the boost converter.
* Set / verify the boost converter output to **5.0 V with a multimeter before connecting the ESP32**.
* Use a protected 18650 cell (over-discharge / short-circuit protection) and a TP4056 module *with* the protection IC (6 pins: IN+/IN-, B+/B-, OUT+/OUT-).
* The default TP4056 charge current is about 1 A (R_PROG = 1.2 k); check that your cell accepts it.
* **Do not connect USB and the battery supply at the same time** unless you have confirmed from your board's schematic
  that USB 5 V and VIN are isolated by a diode. Disconnect the boost converter output while programming over USB.
* There is no power switch in the approved component list: switch off by disconnecting the boost-converter output jumper
  or removing the cell from the holder.
* Rough runtime estimate (not measured): ESP32 with BLE ~100-130 mA at 5 V, through a ~85 % efficient boost from 3.7 V
  -> ~0.2 A from a 2500 mAh cell -> roughly 10 hours.

### 1.4 Safety checklist

- [ ] All grounds connected together (ESP32, both GY-521, HX711, boost OUT-).
- [ ] No sensor is powered from 5 V; MPU6050s and HX711 use 3V3.
- [ ] Boost converter output measured at 5.0 V before connecting.
- [ ] Battery polarity in the holder checked; no exposed battery contacts can short against the PCB.
- [ ] TP4056 OUT and battery wires never touch the ESP32 5V/3V3 pins directly.
- [ ] Load cell, eye bolts and carabiners rated above the maximum band force with margin (section 3).
- [ ] Cables strain-relieved at the PCB and the load cell; no wire is pulled by the band.
- [ ] USB and battery never connected at the same time.

## 2. Mechanical placement

```text
            shoulder
               |
        [ UPPER-ARM IMU 0x68 ]   lateral side, mid upper arm, X arrow pointing to the hand
               |
        [ PCB: ESP32 + HX711 + power ]  on the upper-arm strap above the IMU (or a waist belt)
               |
             elbow
               |
        [ FOREARM IMU 0x69 ]     lateral side, mid forearm, SAME orientation as the upper-arm IMU
               |
             wrist
               |
           [ handle ] --carabiner-- [ S-type LOAD CELL ] --carabiner-- [ resistance band ] --> anchored under the foot
```

* **Same orientation for both IMUs** is essential: chip side facing away from the body, printed X arrow pointing
  towards the hand when the arm hangs straight. The ML pipeline computes the elbow angle as the angle between the
  two gravity directions, which is only valid when both sensors share the same orientation relative to their segment.
* Strap the IMUs firmly (elastic + hook-and-loop) on flat, muscular areas so they do not slide or rotate during curls.
  Re-check orientation after every donning.
* Put the PCB (ESP32, HX711, TP4056, boost, battery holder) on the upper-arm strap or a waist belt so cables to both IMUs and the load cell stay short.
* Leave the TP4056 USB socket accessible for charging.

## 3. Load cell selection and safe mounting

1. **Measure the expected tension.** Hook the strongest band you will use to a luggage scale and stretch it to the
   longest length reached at the top of a curl; note the reading (kg). Or use the manufacturer's rated resistance at that stretch.
2. **Apply a safety factor of at least 2** for dynamic loads and jerks: required capacity >= 2 x measured maximum.
   Example: a band reaching 12 kg (~118 N) needs a cell of >= 24 kg, so a 30 kg or 50 kg S-type cell is appropriate.
   Do not pick a vastly larger capacity (e.g. 500 kg): the signal becomes small and noisy.
3. **Every part in the load path** - eye bolts, threads, carabiners, band attachment - must be rated above the cell capacity.
4. **Mount in pure tension along the cell's axis:** thread eye bolts fully into both threaded ends (use the thread size
   on the datasheet, typically M6/M8/M10), secure with lock nuts, and connect handle and band with carabiners. Avoid side
   loads and bending; the cell must hang freely in line with the band.
5. Never exceed the rated capacity; inspect threads, bolts and the band before each session; replace worn bands.

## 4. Calibration

1. Upload the firmware, open the Serial Monitor at 115200 baud.
2. `tare` with the band attached but slack.
3. Hang a known mass (e.g. 2 kg dumbbell or a weighed water bottle) from the load cell and send `cal 2.0`.
   The factor is saved in flash (NVS). Check with `read`: force should read about 2 x 9.81 = 19.6 N.
4. Place both IMUs flat and still and send `gyrocal` (or use **Calibrate gyro** in the app).
5. `status` should now show *calibrated* for both.
