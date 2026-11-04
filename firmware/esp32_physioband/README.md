# PhysioBand AI - ESP32 firmware

| File | Purpose |
|---|---|
| `esp32_physioband.ino` | setup / loop, 50 Hz scheduler, serial commands, calibration |
| `config.h` | pins, sensor ranges, BLE UUIDs, packet constants, command codes |
| `sensors.h` | MPU6050 register driver (x2) and HX711 load-cell wrapper with NVS-stored calibration |
| `ble_service.h` | BLE GATT server, packet encoder, reconnection (re-advertising) |

## Build

* Arduino IDE 2.x, board package **esp32 by Espressif** (tested with 3.3.7), board **ESP32 Dev Module**.
* Library: **HX711** by Bogdan Necula (Library Manager). BLE, Wire and Preferences come with the ESP32 core.
* Compile check done with `arduino-cli compile --fqbn esp32:esp32:esp32` (85 % flash, 13 % RAM).

## Pins

| Signal | GPIO |
|---|---|
| I2C SDA (both MPU6050) | 21 |
| I2C SCL (both MPU6050) | 22 |
| HX711 DT | 16 |
| HX711 SCK | 4 |

Upper-arm MPU6050 AD0 -> GND (0x68), forearm AD0 -> 3V3 (0x69). Change pins in `config.h` if needed.

## Serial commands (115200 baud)

`help`, `status`, `read`, `i2c`, `tare`, `cal <kg>`, `factor <value>`, `gyrocal`, `csv on|off`, `debug on|off`.

`HX711_DEFAULT_CALIBRATION_FACTOR` is only a placeholder: the real factor depends on your load cell and must be
measured with `cal <kg>` using a known mass. It is then stored in flash.

## BLE

Service `7b1e0001-5c3a-4d8e-9f21-6a0b3c4d5e6f`; see `docs/SYSTEM_ARCHITECTURE.md` section 4 for characteristics and
the 140-byte packet layout. Streaming starts when the app writes `0x01` to the CONTROL characteristic and stops on
`0x02` or disconnect.
