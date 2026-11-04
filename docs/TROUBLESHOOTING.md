# PhysioBand AI - Testing & Troubleshooting

Serial Monitor: Arduino IDE -> Tools -> Serial Monitor, **115200 baud**, line ending **Newline**.
Useful commands: `status`, `i2c`, `read`, `debug on`, `tare`, `cal <kg>`, `gyrocal`.

| Problem | How to verify | Fix |
|---|---|---|
| **MPU6050 not detected** | `i2c` does not list 0x68 / 0x69; boot log says `NOT FOUND` | Check VCC->3V3, GND, SDA->21, SCL->22; re-seat jumpers; test one module alone |
| **I2C address conflict** | `i2c` lists only one address, or both modules answer 0x68 | Upper-arm AD0 -> GND, forearm AD0 -> 3V3; never leave AD0 floating |
| **I2C errors with long cables** | values freeze, status bit0/bit1 drop to 0 | Shorten / twist wires; set `I2C_CLOCK_HZ` to `100000UL` |
| **Incorrect sensor orientation** | `read` with arm hanging: both sensors show about the same accel vector; elbow angle (Live Workout) stays near 0 deg when straight | Mount both with X arrow towards the hand and chip facing outward; re-strap |
| **HX711 shows zero / no data** | boot log `HX711 NOT RESPONDING`; app shows *Load cell: Not detected* | DT->GPIO16, SCK->GPIO4, VCC->3V3; check E+/E-/A+/A- screw terminals |
| **Force does not change / wrong sign** | `read` while pulling the band | Wrong wire pairs (identify with multimeter), swap A+/A- for sign |
| **Load-cell calibration wrong** | known 2 kg reads far from 19.6 N | `tare` with no load, hang mass, `cal 2.0`; make sure the mass hangs freely in line with the cell |
| **Force drifts** | reading creeps with no load | let the cell warm up 2-3 min, re-`tare`; keep cables still and away from the boost converter |
| **BLE device not discovered** | phone scan finds nothing | Serial shows `[BLE] Advertising`; Bluetooth on; grant Nearby devices permission; you must use a development build, not Expo Go; ESP32 within a few metres |
| **BLE disconnects** | Live Workout shows *Reconnecting* | Keep phone close; avoid USB+battery power mixing; firmware re-advertises automatically and the app retries 5 times |
| **Packets invalid / "MTU too small"** | Device screen shows invalid packets | Android: the app requests MTU 185 on connect; reconnect. Firmware adapts samples per packet to the MTU |
| **App permission issues** | scan shows *Permission needed* | Android Settings -> Apps -> PhysioBand AI -> Permissions -> Nearby devices: Allow (Android 12+) / Location (Android 11 and below) |
| **Cannot reach server** | login shows *Cannot reach the PhysioBand server at ...* | Phone and PC on the same Wi-Fi; `EXPO_PUBLIC_API_URL` uses the PC's IPv4 (not `localhost`); start uvicorn with `--host 0.0.0.0`; allow Python through Windows Firewall (private networks); restart Expo after editing `.env` |
| **MongoDB Atlas connection error** | `GET /health` shows `database.connected: false`; API returns 503 | Check `MONGODB_URI` user/password (URL-encode special characters), Atlas Network Access includes your IP, cluster is not paused |
| **ML model not loading** | `/health` -> `model.available: false`; log `Quality model unavailable` | Run `python scripts/train_model.py ...`; check `ML_MODEL_PATH`; scikit-learn version must match the one used for training (1.6.1) |
| **Invalid sensor packets / 422** | API error `VALIDATION_ERROR` with field details | `ua` and `fa` must have exactly 6 values; batch <= 500 samples |
| **Incorrect repetition count** | count differs from reps performed | Curl through > 25 deg of elbow motion; check orientation and that both IMU status bits are OK; thresholds in `ml/src/physioband_ml/config.py` (`min_rep_prominence_deg`, `min_peak_distance_s`) can be tuned with collected data |
| **Live feedback lags** | reps appear several seconds late | Reps are reported 0.6 s after they finish by design; check upload latency / network; the app shows queued batches when offline |

## Automated tests

```powershell
cd backend;  .\.venv\Scripts\python.exe -m pytest -q      # 24 API + integration tests (in-memory MongoDB)
cd ..\ml;    ..\backend\.venv\Scripts\python.exe -m pytest -q   # 18 pipeline tests
cd ..\frontend; npx tsc --noEmit; npx expo-doctor
```

## End-to-end test without hardware

`scripts/simulate_device.py` acts as the phone + ESP32 and streams a synthetic workout to a running backend.

## Tests that need the physical hardware (not verifiable in software)

* Both MPU6050 modules detected at 0x68 / 0x69 on the real bus, correct orientation on the arm.
* HX711 readings and the load-cell calibration factor.
* BLE advertising, MTU negotiation, notification throughput and reconnection with a real phone.
* Battery runtime and charging.
* Repetition-count and classification accuracy on real volunteers (requires collected, labelled data).
