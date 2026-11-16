from httpx import ASGITransport, AsyncClient
import pytest
from app.core.config import settings
from app.main import app


@pytest.mark.asyncio
async def test_reject_unauthenticated_telemetry():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/telemetry/ingest",
            json={
                "machine_code": "TURBINE-01",
                "temperature_c": 75.0,
                "vibration_mm_s": 2.1,
                "rpm": 2950.0,
                "pressure_bar": 14.5,
            },
        )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_accept_valid_telemetry_with_api_key(monkeypatch):
    class DummyTask:
        id = "mock-task-uuid-1234"

    from app.api.v1.endpoints import telemetry

    async def mock_rate_limit(machine_code: str):
        return None

    monkeypatch.setattr(telemetry, "enforce_rate_limit", mock_rate_limit)
    monkeypatch.setattr(telemetry.process_telemetry_task, "delay", lambda payload: DummyTask())

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/telemetry/ingest",
            headers={"X-API-Key": settings.EDGE_API_KEY},
            json={
                "machine_code": "TURBINE-GN-01",
                "facility_zone": "NORTH-PLANT",
                "temperature_c": 112.5,
                "vibration_mm_s": 11.4,
                "rpm": 2610.0,
                "pressure_bar": 11.1,
            },
        )
    assert resp.status_code == 202
    data = resp.json()
    assert data["task_id"] == "mock-task-uuid-1234"
    assert data["status"] == "accepted"
