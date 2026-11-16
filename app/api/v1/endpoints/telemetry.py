import json
from fastapi import APIRouter, Depends, HTTPException, status
import redis.asyncio as aioredis
from app.core.config import settings
from app.core.security import get_current_engineer, verify_edge_api_key
from app.core.telemetry_metrics import TELEMETRY_INGESTED_TOTAL
from app.schemas.telemetry import TelemetryAck, TelemetryIngest
from app.workers.tasks import process_telemetry_task

router = APIRouter()
async_redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)


async def enforce_rate_limit(machine_code: str):
    key = f"ratelimit:ingest:{machine_code}"
    current = await async_redis.incr(key)
    if current == 1:
        await async_redis.expire(key, 60)
    if current > 60:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded for sensor {machine_code} (max 60 msg/min)",
        )


@router.post(
    "/ingest",
    response_model=TelemetryAck,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(verify_edge_api_key)],
)
async def ingest_telemetry(payload: TelemetryIngest):
    await enforce_rate_limit(payload.machine_code)
    TELEMETRY_INGESTED_TOTAL.labels(facility_zone=payload.facility_zone).inc()
    task = process_telemetry_task.delay(payload.model_dump())
    return TelemetryAck(task_id=task.id, machine_code=payload.machine_code)


@router.get("/live/{machine_code}", dependencies=[Depends(get_current_engineer)])
async def get_live_machine_state(machine_code: str):
    cached = await async_redis.get(f"machine:live:{machine_code}")
    if not cached:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No recent telemetry cached for {machine_code}",
        )
    return json.loads(cached)
