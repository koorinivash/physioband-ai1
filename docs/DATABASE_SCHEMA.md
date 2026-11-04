# PhysioBand AI - MongoDB Schema

Database: **`physioband_ai`** on MongoDB Atlas (name configurable with `MONGODB_DB_NAME`).
Indexes and the exercise catalogue are created automatically when the backend starts
(`backend/app/database/mongodb.py`). Document shapes are typed in `backend/app/models/documents.py`.

## users

| Field | Type | Notes |
|---|---|---|
| `_id` | ObjectId | User ID |
| `name` | string | |
| `email` | string | lower-case, **unique index `uniq_email`** |
| `password_hash` | string | bcrypt (12 rounds); never returned by the API |
| `profile` | object | `age, gender, height_cm, weight_kg, dominant_arm, training_arm` |
| `created_at`, `updated_at` | date (UTC) | |

## devices

| Field | Type | Notes |
|---|---|---|
| `_id` | ObjectId | |
| `user_id` | string | owner |
| `device_id` | string | from the ESP32, e.g. `PB-3C61A2F0`; **unique per user (`uniq_user_device`)** |
| `device_name` | string | BLE name `PhysioBand-A2F0` |
| `firmware_version`, `protocol_version` | string, int | |
| `ble_address` | string | platform BLE identifier (connection information) |
| `sample_rate_hz` | int | |
| `registered_at`, `last_connected_at` | date | upserted on every BLE connection |

## exercises

| Field | Type | Notes |
|---|---|---|
| `_id` | string | slug: `biceps_curl`, `shoulder_press`, `chest_press`, `seated_row`, `triceps_extension` |
| `name`, `description` | string | |
| `target_muscles` | string[] | |
| `supported_movement_types` | string[] | `correct, incomplete, too_fast, irregular` for Biceps Curl, empty for the others |
| `is_active` | bool | only `biceps_curl` is `true` (implemented and tested) |
| `order` | int | display order |

## workout_sessions

| Field | Type | Notes |
|---|---|---|
| `_id` | ObjectId | Session ID |
| `user_id`, `device_id`, `exercise_id`, `exercise_name` | string | |
| `status` | string | `active`, `completed`, `interrupted` |
| `start_time`, `end_time` | date | |
| `duration_s` | number | wall-clock duration |
| `total_reps`, `correct_reps`, `incorrect_reps` | int | |
| `incomplete_reps`, `too_fast_reps`, `irregular_reps` | int | breakdown of incorrect reps |
| `quality_score` | number / null | exercise-quality score in % |
| `avg_tension_n`, `peak_tension_n` | number / null | band tension during reps |
| `sample_count`, `batch_count`, `last_data_at` | int, int, date | upload bookkeeping |
| `end_reason` | string | `user_completed`, `device_disconnected`, `app_interrupted`, `superseded` |
| `suggestions` | string[] | improvement tips |
| `classification_available`, `model_dataset_type` | bool, string | whether / which model produced the labels |

Indexes: `user_history (user_id, start_time desc)` for paginated history, `user_status (user_id, status)`.

## sensor_records (batched)

One document per uploaded batch (~50 samples = 1 s), **not** one per sample. A 5-minute workout is about
300 documents instead of 15 000, keeping Atlas write volume low. Arrays are index-aligned.

| Field | Type | Notes |
|---|---|---|
| `session_id`, `user_id`, `device_id` | string | |
| `batch_seq` | int | **unique with `session_id` (`uniq_session_batch`)** -> idempotent retries |
| `protocol_version`, `sample_count` | int | |
| `start_timestamp_ms`, `end_timestamp_ms` | int | device clock |
| `timestamp_ms` | int[] | per sample |
| `upper_arm_accel`, `upper_arm_gyro` | [x,y,z][] | g, deg/s |
| `forearm_accel`, `forearm_gyro` | [x,y,z][] | g, deg/s |
| `force_n` | number[] | load-cell tension (N), `null` if invalid |
| `status` | int[] | firmware status flags |
| `received_at` | date | server time |

## workout_feedback

| Field | Type | Notes |
|---|---|---|
| `session_id` | string | |
| `repetition_number` | int | **unique with `session_id` (`uniq_session_rep`)** |
| `classification` | string | `correct`, `incomplete`, `too_fast`, `irregular`, `unclassified` |
| `label_display`, `message` | string | |
| `confidence` | number / null | Random Forest probability of the predicted class |
| `duration_s`, `rom_deg`, `avg_force_n` | number | rep metrics |
| `device_start_ms`, `device_end_ms` | number | device timestamps of the rep |
| `timestamp` | date | when the feedback was stored |

## Verifying data in Atlas

1. Atlas -> your cluster -> **Browse Collections** -> database `physioband_ai`.
2. `workout_sessions`: filter `{ "status": "completed" }`, sort `{ "start_time": -1 }` - the newest workout should show the totals the app displayed.
3. Copy its `_id` (as a string) and filter `workout_feedback` with `{ "session_id": "<id>" }` - one document per rep.
4. Filter `sensor_records` with the same `session_id` - `sample_count` values should add up to the session's `sample_count`.
5. **Indexes** tab of each collection should list the indexes above.
