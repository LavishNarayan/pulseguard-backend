import time
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
import redis.asyncio as aioredis
from sqlalchemy import text
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.telemetry_metrics import configure_structured_logging
from app.db.session import Base, async_engine
from app.ml.predictor import PredictiveMaintenanceEngine

configure_structured_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    PredictiveMaintenanceEngine()
    yield
    await async_engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="High-throughput Industrial IoT Telemetry Ingestion & Asynchronous ML Predictive Maintenance Engine",
    lifespan=lifespan,
)


@app.middleware("http")
async def observability_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - start) * 1000
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time-Ms"] = f"{elapsed_ms:.2f}"
    return response


@app.get("/health", tags=["Observability"])
async def health_check():
    db_ok = False
    redis_ok = False
    try:
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            db_ok = True
    except Exception:
        pass

    try:
        r = aioredis.from_url(settings.REDIS_URL)
        await r.ping()
        await r.aclose()
        redis_ok = True
    except Exception:
        pass

    return {
        "status": "healthy" if (db_ok and redis_ok) else "degraded",
        "database": "connected" if db_ok else "unreachable",
        "redis": "connected" if redis_ok else "unreachable",
        "version": settings.VERSION,
    }


@app.get("/metrics", tags=["Observability"])
async def prometheus_metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


app.include_router(api_router, prefix=settings.API_V1_STR)
