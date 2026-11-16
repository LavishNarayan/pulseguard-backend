from fastapi import APIRouter
from app.api.v1.endpoints import auth, incidents, telemetry

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(telemetry.router, prefix="/telemetry", tags=["Edge Telemetry"])
api_router.include_router(incidents.router, prefix="/incidents", tags=["Maintenance Incidents"])
