import pytest

from tests.conftest import register

pytestmark = pytest.mark.asyncio

BATCH = 100


async def start(client, auth) -> str:
    res = await client.post("/api/v1/workouts/start", headers=auth, json={"exercise_id": "biceps_curl"})
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["status"] == "active"
    return body["id"]


async def upload_all(client, auth, session_id, samples):
    seen_reps, counts = set(), []
    for seq, i in enumerate(range(0, len(samples), BATCH)):
        res = await client.post(
            f"/api/v1/workouts/{session_id}/sensor-data",
            headers=auth,
            json={"batch_seq": seq, "device_id": "PB-TEST", "samples": samples[i : i + BATCH]},
        )
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["accepted"]
        analysis = body["analysis"]
        if analysis:
            counts.append(analysis["total_reps"])
            for rep in analysis["new_reps"]:
                assert rep["number"] not in seen_reps  # each rep is reported as new exactly once
                seen_reps.add(rep["number"])
    return counts, seen_reps


async def test_full_workout_flow(client, auth, samples):
    session_id = await start(client, auth)
    counts, seen = await upload_all(client, auth, session_id, samples)
    assert counts == sorted(counts) and counts[-1] >= 7
    assert seen == set(range(1, len(seen) + 1))

    # Retried batch is ignored, not double-stored.
    dup = await client.post(f"/api/v1/workouts/{session_id}/sensor-data", headers=auth,
                            json={"batch_seq": 0, "samples": samples[:BATCH]})
    assert dup.json()["duplicate"] is True and dup.json()["total_samples"] == len(samples)

    analysis = (await client.post(f"/api/v1/workouts/{session_id}/analyze", headers=auth)).json()
    assert analysis["mode"] == "final" and analysis["total_reps"] == 8
    assert analysis["model"]["available"] and analysis["model"]["dataset_type"] == "synthetic"
    assert analysis["model"]["validated"] is False

    done = await client.post(f"/api/v1/workouts/{session_id}/complete", headers=auth, json={"end_reason": "user_completed"})
    assert done.status_code == 200
    detail = done.json()
    assert detail["status"] == "completed"
    assert detail["total_reps"] == 8 == len(detail["feedback"])
    assert detail["correct_reps"] + detail["incorrect_reps"] == 8
    assert detail["avg_tension_n"] > 0 and detail["duration_s"] >= 0
    assert detail["sample_count"] == len(samples)
    assert [f["repetition_number"] for f in detail["feedback"]] == list(range(1, 9))

    # Completing twice is idempotent; uploads after completion are rejected.
    again = await client.post(f"/api/v1/workouts/{session_id}/complete", headers=auth)
    assert again.json()["status"] == "completed"
    late = await client.post(f"/api/v1/workouts/{session_id}/sensor-data", headers=auth,
                             json={"batch_seq": 999, "samples": samples[:10]})
    assert late.status_code == 409 and late.json()["error"]["code"] == "SESSION_NOT_ACTIVE"

    history = (await client.get("/api/v1/workouts?page=1&page_size=10", headers=auth)).json()
    assert history["total"] == 1 and history["items"][0]["id"] == session_id

    summary = (await client.get("/api/v1/dashboard/summary", headers=auth)).json()
    assert summary["today"]["total_reps"] == 8 and summary["today"]["sessions"] == 1
    assert summary["active_session_id"] is None
    perf = (await client.get("/api/v1/dashboard/performance?days=7", headers=auth)).json()
    assert len(perf["points"]) == 7 and perf["total_reps"] == 8


async def test_disconnect_marks_interrupted(client, auth, samples):
    session_id = await start(client, auth)
    await upload_all(client, auth, session_id, samples[:600])
    res = await client.post(f"/api/v1/workouts/{session_id}/complete", headers=auth, json={"end_reason": "device_disconnected"})
    assert res.json()["status"] == "interrupted"
    assert res.json()["end_reason"] == "device_disconnected"


async def test_new_workout_closes_stale_session(client, auth):
    first = await start(client, auth)
    second = await start(client, auth)
    old = (await client.get(f"/api/v1/workouts/{first}", headers=auth)).json()
    assert old["status"] == "interrupted" and old["end_reason"] == "superseded"
    assert old["total_reps"] == 0 and old["suggestions"]
    assert (await client.get(f"/api/v1/workouts/{second}", headers=auth)).json()["status"] == "active"


async def test_invalid_samples_rejected(client, auth):
    session_id = await start(client, auth)
    bad = {"batch_seq": 0, "samples": [{"timestamp_ms": 1, "ua": [0, 0, 1], "fa": [0] * 6, "force_n": 1}]}
    res = await client.post(f"/api/v1/workouts/{session_id}/sensor-data", headers=auth, json=bad)
    assert res.status_code == 422 and res.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_missing_values_and_faulty_sensor_flags_are_tolerated(client, auth, samples):
    session_id = await start(client, auth)
    damaged = [dict(s) for s in samples]
    for i in range(50, 60):
        damaged[i] = {**damaged[i], "force_n": None, "ua": [None] * 6}
    damaged[70] = {**damaged[70], "status": 0b1101}  # forearm IMU fault flag
    await upload_all(client, auth, session_id, damaged)
    detail = (await client.post(f"/api/v1/workouts/{session_id}/complete", headers=auth)).json()
    assert detail["total_reps"] == 8


async def test_users_cannot_see_each_other(client, auth):
    session_id = await start(client, auth)
    other = await register(client, email="other@example.com")
    headers = {"Authorization": f"Bearer {other['access_token']}"}
    assert (await client.get(f"/api/v1/workouts/{session_id}", headers=headers)).status_code == 404
    assert (await client.get("/api/v1/workouts/not-an-id", headers=headers)).status_code == 404


async def test_analyze_without_data(client, auth):
    session_id = await start(client, auth)
    res = await client.post(f"/api/v1/workouts/{session_id}/analyze", headers=auth)
    assert res.status_code == 422 and res.json()["error"]["code"] == "INSUFFICIENT_DATA"


async def test_ml_predict_and_model_info(client, auth, samples):
    info = (await client.get("/api/v1/ml/model-info", headers=auth)).json()
    assert info["available"] and info["dataset_type"] == "synthetic" and info["validated"] is False
    assert set(info["classes"]) == {"correct", "incomplete", "too_fast", "irregular"}

    res = await client.post("/api/v1/ml/predict", headers=auth, json={"samples": samples, "include_features": True})
    assert res.status_code == 200
    body = res.json()
    assert body["mode"] == "standalone" and body["total_reps"] == 8
    rep = body["reps"][0]
    assert rep["label"] in info["classes"] and 0 <= rep["confidence"] <= 1 and rep["features"]

    unsupported = await client.post("/api/v1/ml/predict", headers=auth, json={"exercise_id": "chest_press", "samples": samples[:50]})
    assert unsupported.status_code == 422 and unsupported.json()["error"]["code"] == "EXERCISE_NOT_SUPPORTED"


async def test_health(client):
    res = await client.get("/health")
    assert res.status_code == 200
    assert res.json()["model"]["available"] is True
