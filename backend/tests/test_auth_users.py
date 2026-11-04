import pytest

from tests.conftest import register

pytestmark = pytest.mark.asyncio


async def test_register_login_me(client):
    data = await register(client)
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "alex@example.com"
    assert "password_hash" not in data["user"]

    res = await client.post("/api/v1/auth/login", json={"email": "ALEX@example.com", "password": "Strong123"})
    assert res.status_code == 200
    token = res.json()["access_token"]

    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200 and me.json()["name"] == "Alex Doe"


async def test_duplicate_email_rejected(client):
    await register(client)
    res = await client.post("/api/v1/auth/register", json={"name": "Bob", "email": "alex@example.com", "password": "Strong123"})
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "EMAIL_ALREADY_REGISTERED"


async def test_wrong_password(client):
    await register(client)
    res = await client.post("/api/v1/auth/login", json={"email": "alex@example.com", "password": "Wrong123"})
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "INVALID_CREDENTIALS"


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "A", "email": "a@example.com", "password": "Strong123"},
        {"name": "Alex", "email": "not-an-email", "password": "Strong123"},
        {"name": "Alex", "email": "a@example.com", "password": "short1"},
        {"name": "Alex", "email": "a@example.com", "password": "nodigitshere"},
    ],
)
async def test_register_validation(client, payload):
    res = await client.post("/api/v1/auth/register", json=payload)
    assert res.status_code == 422
    body = res.json()["error"]
    assert body["code"] == "VALIDATION_ERROR" and body["details"]


async def test_protected_routes_require_token(client):
    assert (await client.get("/api/v1/auth/me")).status_code == 401
    res = await client.get("/api/v1/workouts", headers={"Authorization": "Bearer garbage"})
    assert res.status_code == 401 and res.json()["error"]["code"] == "INVALID_TOKEN"


async def test_profile_update_and_password_change(client, auth):
    res = await client.patch("/api/v1/users/me", headers=auth, json={"name": "Alex D", "profile": {"age": 22, "dominant_arm": "right"}})
    assert res.status_code == 200
    assert res.json()["profile"]["age"] == 22 and res.json()["name"] == "Alex D"

    bad = await client.post("/api/v1/users/me/password", headers=auth, json={"current_password": "nope", "new_password": "Newpass123"})
    assert bad.status_code == 401
    ok = await client.post("/api/v1/users/me/password", headers=auth, json={"current_password": "Strong123", "new_password": "Newpass123"})
    assert ok.status_code == 200
    login = await client.post("/api/v1/auth/login", json={"email": "alex@example.com", "password": "Newpass123"})
    assert login.status_code == 200


async def test_database_unavailable_returns_503(client):
    from app.database.mongodb import mongodb

    mongodb.connected = False
    res = await client.post("/api/v1/auth/login", json={"email": "a@example.com", "password": "x"})
    assert res.status_code == 503
    assert res.json()["error"]["code"] == "DATABASE_UNAVAILABLE"
