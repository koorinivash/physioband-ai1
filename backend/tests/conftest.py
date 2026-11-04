"""Test fixtures: the real FastAPI app on an in-memory MongoDB (mongomock-motor).

The real ML package and the saved demo model are used, so these are integration
tests of API + pipeline. Atlas itself is exercised manually (see docs).
"""
import os
import sys
from pathlib import Path

# mongomock reads its emulated server version from $MONGODB; some Windows MongoDB
# installs set that variable to an install path, so pin it before importing.
os.environ["MONGODB"] = "6.0"

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from mongomock_motor import AsyncMongoMockClient  # noqa: E402

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND.parent / "ml" / "src"))
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-pytest-only-0123456789")
os.environ.setdefault("ENVIRONMENT", "test")

from app.database.mongodb import mongodb  # noqa: E402
from app.main import create_app  # noqa: E402


@pytest_asyncio.fixture
async def app():
    application = create_app(connect_database=False)
    application.state.ml.load_model()
    mongodb.use(AsyncMongoMockClient(tz_aware=True), "physioband_test")
    await mongodb.prepare()
    yield application
    mongodb.connected = False


@pytest_asyncio.fixture
async def client(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def register(client: AsyncClient, email: str = "alex@example.com", password: str = "Strong123") -> dict:
    res = await client.post("/api/v1/auth/register", json={"name": "Alex Doe", "email": email, "password": password})
    assert res.status_code == 201, res.text
    return res.json()


@pytest_asyncio.fixture
async def auth(client):
    data = await register(client)
    return {"Authorization": f"Bearer {data['access_token']}"}


def stream_samples(seed: int = 3) -> list[dict]:
    """SYNTHETIC mixed-quality workout converted to the API sample format."""
    from physioband_ml.synthetic import generate_mixed_stream

    df = generate_mixed_stream(seed=seed)
    return [
        {
            "timestamp_ms": int(r.timestamp_ms),
            "ua": [r.ua_ax, r.ua_ay, r.ua_az, r.ua_gx, r.ua_gy, r.ua_gz],
            "fa": [r.fa_ax, r.fa_ay, r.fa_az, r.fa_gx, r.fa_gy, r.fa_gz],
            "force_n": r.force_n,
            "status": 15,
        }
        for r in df.itertuples()
    ]


@pytest.fixture(scope="session")
def samples():
    return stream_samples()
