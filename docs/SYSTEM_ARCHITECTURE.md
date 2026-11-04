# PhysioBand AI - System Architecture

PhysioBand AI is a wearable resistance-exercise monitoring system. Two MPU6050 IMUs (upper arm, forearm)
and an S-type load cell (band tension) are read by an ESP32, streamed over Bluetooth Low Energy to 
React Native app, and analysed in the cloud by a FastAPI backend running the Python ML pipeline. Results
are stored in MongoDB Atlas and shown in the app.

> PhysioBand AI gives training feedback only. It is not a medical device, does not provide clinical
> diagnosis and does not guarantee injury prevention.

## 1. Components

```text
                    PHYSIOBAND AI
                          |
          +---------------+---------------+
          |               |               |
       HARDWARE         MOBILE           CLOUD
          |               |               |
     MPU6050 x 2      React Native      FastAPI
          |               |               |
      S-Type Load     BLE Connection    REST APIs
        Cell              |               |
          |           Live Sensor          |
        HX711           Dashboard          |
          |               |               |
         ESP32 -------- BLE Data ---------+
                                          |
                                   Sensor Processing
                                          |
                                    Python ML Engine
                                          |
                              Exercise Recognition
                                          |
                               Repetition Counting
                                          |
                              Quality Classification
                                          |
                                    MongoDB Atlas
                                          |
                                  Workout Analytics
                                          |
                                  Mobile Feedback
```

| Layer | Folder | Technology | Responsibility |
|---|---|---|---|
| Firmware | `firmware/esp32_physioband` | Arduino C++ (ESP32 core 3.x, HX711 lib) | 50 Hz sampling of 2 IMUs + load cell, timestamps, validation flags, calibration, BLE GATT server |
| Mobile app | `frontend/` | Expo SDK 58, React Native 0.88, TypeScript, React Navigation, react-native-ble-plx, Axios | BLE scan/connect, packet decoding, batching + upload, live feedback UI, history, profile |
| Backend | `backend/` | FastAPI, Pydantic v2, Motor (async MongoDB), PyJWT, bcrypt | Auth, devices, workouts, sensor storage, ML integration, analytics |
| ML | `ml/` | NumPy, SciPy, pandas, scikit-learn (Random Forest), joblib | Preprocessing, elbow kinematics, repetition counting, features, training, evaluation, inference |
| Database | MongoDB Atlas | database `physioband_ai` | users, devices, exercises, workout_sessions, sensor_records, workout_feedback |

## 2. Data flow (the only data path in the system)

1. **Sense** - MPU6050 x2 (I2C 0x68 / 0x69) and HX711 are sampled by the ESP32 every 20 ms (50 Hz).
2. **Timestamp & validate** - each sample gets `millis()` and a status byte (sensor OK / calibrated flags).
3. **BLE** - up to 4 samples are packed into one 140-byte binary notification (see section 4).
4. **App receives** - `DeviceContext` decodes packets (`services/ble/protocol.ts`), detects lost packets.
5. **Validate & batch** - `useWorkoutSession` drops out-of-order / empty samples and buffers ~1 s (50 samples).
6. **Upload** - `POST /api/v1/workouts/{id}/sensor-data` over HTTPS with an increasing `batch_seq`.
7. **ML pipeline** - FastAPI calls `physioband_ml.analysis.analyze_frame` in a worker thread.
8. **Analysis** - resampling -> calibration -> low-pass filter -> elbow angle -> repetition counting -> features -> Random Forest.
9. **Store** - the batch goes to `sensor_records`; new reps to `workout_feedback`; totals to `workout_sessions`.
10. **Respond** - the response contains the live analysis (rep count, new reps with labels / confidence, movement status).
11. **Display** - the Live Workout screen animates the counter, shows per-rep feedback and haptics.

When the phone is offline, batches stay queued and the app shows *"Cloud AI analysis unavailable"*; it
never invents classifications locally. Band tension and sensor status shown during the workout are direct
measurements, not predictions.

## 3. Repetition counting vs. classification

Repetitions are counted by a deterministic peak / cycle detector on the filtered elbow-flexion angle
(`ml/src/physioband_ml/repetition_counting/counter.py`). The Random Forest only labels the quality of each
detected repetition. Counting therefore keeps working when no model is loaded; such reps are reported as
`unclassified`.

## 4. BLE protocol v1

| Item | Value |
|---|---|
| Advertised name | `PhysioBand-XXXX` (last 4 hex digits of the device ID) |
| Service UUID | `7b1e0001-5c3a-4d8e-9f21-6a0b3c4d5e6f` |
| SENSOR_DATA (notify) | `7b1e0002-5c3a-4d8e-9f21-6a0b3c4d5e6f` |
| CONTROL (write) | `7b1e0003-5c3a-4d8e-9f21-6a0b3c4d5e6f` - `0x01` start, `0x02` stop, `0x03` tare, `0x04` gyro calibration |
| DEVICE_INFO (read) | `7b1e0004-5c3a-4d8e-9f21-6a0b3c4d5e6f` - JSON `{device_id, name, firmware, protocol, sample_rate_hz, max_samples_per_packet}` |
| MTU | App requests 185; firmware fits `(MTU-3-8)/33` samples per packet (max 4) |

SENSOR_DATA packet (little-endian):

| Offset | Size | Type | Field |
|---|---|---|---|
| 0 | 1 | uint8 | protocol version (1) |
| 1 | 1 | uint8 | sample count N (1-4) |
| 2 | 2 | uint16 | packet sequence (wraps) |
| 4 | 4 | uint32 | device ID (lower 32 bits of MAC-derived ID) |
| 8 + 33*i | 4 | uint32 | sample timestamp (ms) |
| +4 | 12 | int16 x 6 | upper arm ax, ay, az (mg), gx, gy, gz (0.1 deg/s) |
| +16 | 12 | int16 x 6 | forearm, same layout |
| +28 | 4 | int32 | force (0.01 N) |
| +32 | 1 | uint8 | status: bit0 upper-arm OK, bit1 forearm OK, bit2 load cell OK, bit3 load cell calibrated, bit4 gyro calibrated |

The same constants exist in `firmware/esp32_physioband/config.h` and `frontend/src/constants/ble.ts`.
The layout was cross-checked by encoding a packet in Python exactly as `ble_service.h` does and decoding
it with the app's TypeScript decoder (values and status-dependent `null`s round-trip exactly).

## 5. Reliability design

| Situation | Behaviour |
|---|---|
| BLE drops | App retries the connection 5 times (2.5 s apart); firmware restarts advertising. Banner shown in Live Workout. |
| Device never comes back | User ends the workout -> `end_reason: device_disconnected` -> session `interrupted`, data received so far analysed. |
| App killed mid-workout | Session stays `active`; it is closed as `interrupted / superseded` (and analysed) when the next workout starts. Dashboard shows an "Unfinished workout" banner. |
| Upload retried | `(session_id, batch_seq)` unique index makes uploads idempotent (`duplicate: true`). |
| Internet lost | Batches queued (up to 600) and re-sent in order; only the newest batch requests live analysis to avoid redundant work. |
| Faulty sensor | Status bits blank that sensor's values (`null`); the pipeline interpolates short gaps and flags long ones. |
| Database down | API starts anyway; `/health` reports it; DB routes return `503 DATABASE_UNAVAILABLE`. |
| Model missing | Reps counted, labelled `unclassified`; app shows "AI quality model unavailable". |

## 6. Performance (measured on the development PC)

* Full live analysis of a 6-minute session (~17 000 samples, 48 reps): about 0.25 s.
* End-to-end `sensor-data` request including MongoDB writes and live analysis (2.8k-sample session, local MongoDB): median 121 ms, max 382 ms per 1-second batch.

These timings are from the synthetic device simulator (`scripts/simulate_device.py`), not from a phone on mobile data.

## 7. Extending to new exercises

1. Collect labelled data for the new exercise (same CSV format, new `exercise_id`).
2. Add a joint-angle definition / rep-counter configuration for it in the ML package and include it in `SUPPORTED_EXERCISES`.
3. Train and evaluate a model for that exercise.
4. Set `is_active: true` for the exercise in `backend/app/database/mongodb.py` (`EXERCISE_SEED`).

The app already lists Shoulder Press, Chest Press, Seated Row and Triceps Extension as *Coming soon* and
only allows starting exercises that the backend marks active.
