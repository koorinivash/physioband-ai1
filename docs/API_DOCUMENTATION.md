# PhysioBand AI - REST API

Base URL: `http://<host>:8000/api/v1` (use HTTPS when deployed). Interactive Swagger UI: `http://<host>:8000/docs`,
OpenAPI JSON: `/openapi.json`, health check: `GET /health` (no prefix, no auth).

All endpoints except `register`, `login` and `/health` need `Authorization: Bearer <access_token>`.
Every example below was produced by the real application code (`docs/examples/api_examples.json`).

## Error format

```json
{ "error": { "code": "SESSION_NOT_ACTIVE", "message": "Workout session is not active", "details": null } }
```

| HTTP | Typical codes |
|---|---|
| 401 | `NOT_AUTHENTICATED`, `INVALID_TOKEN`, `TOKEN_EXPIRED`, `INVALID_CREDENTIALS` |
| 404 | `SESSION_NOT_FOUND`, `DEVICE_NOT_FOUND`, `EXERCISE_NOT_FOUND`, `NOT_FOUND` |
| 409 | `EMAIL_ALREADY_REGISTERED`, `SESSION_NOT_ACTIVE` |
| 422 | `VALIDATION_ERROR` (with `details: [{field, message}]`), `EXERCISE_NOT_AVAILABLE`, `EXERCISE_NOT_SUPPORTED`, `INVALID_SENSOR_DATA`, `INSUFFICIENT_DATA`, `BATCH_TOO_LARGE`, `SESSION_FULL` |
| 503 | `DATABASE_UNAVAILABLE`, `DATABASE_ERROR` |
| 500 | `INTERNAL_ERROR` |

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/auth/register` | Create account `{name, email, password}` -> token + user (201) |
| POST | `/auth/login` | `{email, password}` -> token + user |
| GET | `/auth/me` | Current user |
| GET / PATCH | `/users/me` | Read / update `name` and `profile` (age, gender, height_cm, weight_kg, dominant_arm, training_arm) |
| POST | `/users/me/password` | `{current_password, new_password}` |
| POST | `/devices/register` | Register or refresh an ESP32 `{device_id, device_name, firmware_version, protocol_version, ble_address?, sample_rate_hz?}` |
| GET | `/devices` | Devices of the current user |
| GET / DELETE | `/devices/{device_id}` | One device / unlink it |
| GET | `/exercises?active_only=false` | Exercise catalogue (only `is_active` ones can be started) |
| GET | `/exercises/{exercise_id}` | One exercise |
| POST | `/workouts/start` | `{exercise_id, device_id?}` -> new `active` session (closes stale active sessions) |
| POST | `/workouts/{session_id}/sensor-data` | Upload a sensor batch; returns live analysis |
| POST | `/workouts/{session_id}/analyze` | Full re-analysis of all data so far (session stays open) |
| POST | `/workouts/{session_id}/complete` | `{end_reason}` -> final analysis, closes the session, returns detail + feedback |
| GET | `/workouts?page=1&page_size=20&exercise_id=&status=` | Paginated history (newest first) |
| GET | `/workouts/{session_id}` | Session detail with per-rep feedback |
| POST | `/ml/predict` | Stateless analysis of `{exercise_id, samples[], include_features}` (nothing stored) |
| GET | `/ml/model-info` | Loaded model: algorithm, version, dataset type, validated flag, metrics |
| GET | `/dashboard/summary?tz_offset_minutes=330` | Today / all-time stats, 5 recent sessions, active session id, model status |
| GET | `/dashboard/performance?days=14&tz_offset_minutes=330` | Daily points (reps, quality, tension) + trend |

`end_reason` values: `user_completed` (status `completed`), `device_disconnected`, `app_interrupted`
(status `interrupted`). `superseded` is set by the server when a new workout replaces a forgotten one.

## Sensor upload

`POST /api/v1/workouts/{session_id}/sensor-data`

```json
{
  "batch_seq": 4,
  "device_id": "PB-3C61A2F0",
  "protocol_version": 1,
  "samples": [
    {
      "timestamp_ms": 3997,
      "ua": [-0.9966, 0.0165, 0.005, -0.0026, 0.1004, 0.6697],
      "fa": [-0.8275, 0.005, 0.5428, -0.785, 88.5373, -0.3532],
      "force_n": 30.3138,
      "status": 15
    }
  ],
  "analyze": true
}
```

* `ua` / `fa` = `[ax, ay, az (g), gx, gy, gz (deg/s)]` for upper arm (0x68) and forearm (0x69).
* Any value may be `null` (sensor fault / invalid). Max 500 samples per batch, 90 000 per session.
* `batch_seq` must increase; re-sending the same `batch_seq` is ignored (`duplicate: true`).

Response (abridged - `reps` contains every rep so far, `new_reps` only the ones first reported now):

```json
{
  "session_id": "6aeac003ba18737a91c7a777",
  "batch_seq": 4,
  "accepted": true,
  "duplicate": false,
  "stored_samples": 50,
  "total_samples": 250,
  "analysis": {
    "exercise_id": "biceps_curl",
    "mode": "live",
    "sample_count": 250,
    "duration_s": 4.98,
    "total_reps": 1,
    "correct_reps": 1,
    "incorrect_reps": 0,
    "incomplete_reps": 0,
    "too_fast_reps": 0,
    "irregular_reps": 0,
    "unclassified_reps": 0,
    "quality_score": 100.0,
    "avg_tension_n": 52.79,
    "peak_tension_n": 68.56,
    "classification_available": true,
    "new_reps": [
      {
        "number": 1,
        "start_timestamp_ms": 1900.0,
        "end_timestamp_ms": 4100.0,
        "duration_s": 2.2,
        "rom_deg": 106.6,
        "avg_force_n": 52.79,
        "peak_force_n": 68.56,
        "label": "correct",
        "label_display": "Correct Movement",
        "confidence": 0.9582,
        "probabilities": { "correct": 0.9582, "incomplete": 0.0351, "irregular": 0.005, "too_fast": 0.0017 },
        "feedback": "Good repetition: full range of motion with a controlled tempo."
      }
    ],
    "live": {
      "movement_phase": "resting",
      "upper_arm_status": "stable",
      "forearm_status": "active",
      "current_angle_deg": 13.2,
      "current_force_n": 22.61,
      "upper_arm_swing_deg": 0.3
    },
    "suggestions": ["Excellent consistency. Maintain this tempo and range in your next session."],
    "model": {
      "available": true,
      "algorithm": "RandomForestClassifier",
      "dataset_type": "synthetic",
      "validated": false,
      "status_note": "DEMO MODEL trained on synthetic data. ..."
    }
  },
  "analysis_error": null
}
```

The complete captured request / response pair is in `docs/examples/api_examples.json`.

## Completing a workout

`POST /api/v1/workouts/{session_id}/complete` with `{"end_reason": "user_completed"}` returns the session:

```json
{
  "id": "6aeac003ba18737a91c7a777",
  "exercise_name": "Biceps Curl",
  "status": "completed",
  "total_reps": 8, "correct_reps": 5, "incorrect_reps": 3,
  "incomplete_reps": 1, "too_fast_reps": 1, "irregular_reps": 1,
  "quality_score": 62.5,
  "avg_tension_n": 49.86, "peak_tension_n": 77.94,
  "duration_s": 7.8, "sample_count": 2668, "batch_count": 54,
  "suggestions": ["Use the full range of motion: ...", "Slow the tempo: ...", "Keep the movement smooth ..."],
  "feedback": [
    { "repetition_number": 1, "classification": "correct", "label_display": "Correct Movement",
      "confidence": 0.9649, "message": "Good repetition: full range of motion with a controlled tempo.",
      "duration_s": 2.3, "rom_deg": 108.0, "avg_force_n": 51.61, "timestamp": "2026-11-04T05:18:02.924000Z" }
  ]
}
```

These numbers come from a **synthetic** test stream and a **demo** model; they demonstrate the format only.

`quality_score` = correct reps / classified reps x 100 (unclassified reps are excluded; `null` if none).

## Testing the API without hardware

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
# second terminal, from the project root:
backend\.venv\Scripts\python.exe scripts\simulate_device.py --api http://localhost:8000/api/v1
```

The simulator registers a user, streams a synthetic workout in 1-second batches and completes it.
