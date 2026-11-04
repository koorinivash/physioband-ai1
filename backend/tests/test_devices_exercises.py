import pytest

pytestmark = pytest.mark.asyncio

DEVICE = {"device_id": "PB-3C61A2F0", "device_name": "PhysioBand-A2F0", "firmware_version": "1.0.0", "protocol_version": 1}


async def test_device_register_list_get_delete(client, auth):
    res = await client.post("/api/v1/devices/register", headers=auth, json=DEVICE)
    assert res.status_code == 200
    assert res.json()["device_id"] == DEVICE["device_id"]

    # Re-registering (every BLE connection) updates instead of duplicating.
    await client.post("/api/v1/devices/register", headers=auth, json={**DEVICE, "firmware_version": "1.0.1"})
    devices = (await client.get("/api/v1/devices", headers=auth)).json()
    assert len(devices) == 1 and devices[0]["firmware_version"] == "1.0.1"

    assert (await client.get(f"/api/v1/devices/{DEVICE['device_id']}", headers=auth)).status_code == 200
    assert (await client.get("/api/v1/devices/PB-UNKNOWN", headers=auth)).status_code == 404
    assert (await client.delete(f"/api/v1/devices/{DEVICE['device_id']}", headers=auth)).status_code == 200
    assert (await client.get("/api/v1/devices", headers=auth)).json() == []


async def test_device_id_validation(client, auth):
    res = await client.post("/api/v1/devices/register", headers=auth, json={**DEVICE, "device_id": "bad id!"})
    assert res.status_code == 422


async def test_exercises_seeded(client, auth):
    exercises = (await client.get("/api/v1/exercises", headers=auth)).json()
    ids = [e["id"] for e in exercises]
    assert ids[0] == "biceps_curl" and len(ids) == 5
    active = [e["id"] for e in exercises if e["is_active"]]
    assert active == ["biceps_curl"]
    assert (await client.get("/api/v1/exercises/biceps_curl", headers=auth)).json()["name"] == "Biceps Curl"
    assert (await client.get("/api/v1/exercises/yoga", headers=auth)).status_code == 404


async def test_inactive_exercise_cannot_start(client, auth):
    res = await client.post("/api/v1/workouts/start", headers=auth, json={"exercise_id": "shoulder_press"})
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "EXERCISE_NOT_AVAILABLE"


async def test_unregistered_device_cannot_start(client, auth):
    res = await client.post("/api/v1/workouts/start", headers=auth, json={"exercise_id": "biceps_curl", "device_id": "PB-NOPE"})
    assert res.status_code == 404
