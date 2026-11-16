from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.db.models import IncidentSeverity, IncidentStatus


class TelemetryIngest(BaseModel):
    machine_code: str = Field(..., min_length=3, max_length=50, examples=["TURBINE-GN-04"])
    facility_zone: str = Field(default="SECTOR-A", max_length=100)
    temperature_c: float = Field(..., ge=-40.0, le=500.0, examples=[84.5])
    vibration_mm_s: float = Field(..., ge=0.0, le=100.0, examples=[4.2])
    rpm: float = Field(..., ge=0.0, le=50000.0, examples=[3200.0])
    pressure_bar: float = Field(..., ge=0.0, le=500.0, examples=[14.8])


class TelemetryAck(BaseModel):
    status: str = "accepted"
    task_id: str
    machine_code: str
    message: str = "Telemetry queued for asynchronous ML inference"


class IncidentResponse(BaseModel):
    id: int
    machine_code: str
    severity: IncidentSeverity
    status: IncidentStatus
    predicted_rul: float
    anomaly_score: float
    diagnostic_summary: str
    resolved_by: str | None
    created_at: datetime
    resolved_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
