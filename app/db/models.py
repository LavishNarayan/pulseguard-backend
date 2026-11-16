import enum
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Enum, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship
from app.db.session import Base


class IncidentSeverity(str, enum.Enum):
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class IncidentStatus(str, enum.Enum):
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"


class MachineAsset(Base):
    __tablename__ = "machine_assets"

    id = Column(Integer, primary_key=True, index=True)
    machine_code = Column(String(50), unique=True, nullable=False, index=True)
    facility_zone = Column(String(100), nullable=False)
    model_type = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    incidents = relationship("MaintenanceIncident", back_populates="machine")


class MaintenanceIncident(Base):
    __tablename__ = "maintenance_incidents"

    id = Column(Integer, primary_key=True, index=True)
    machine_code = Column(String(50), ForeignKey("machine_assets.machine_code"), nullable=False)
    severity = Column(Enum(IncidentSeverity), nullable=False)
    status = Column(Enum(IncidentStatus), default=IncidentStatus.OPEN, nullable=False)
    predicted_rul = Column(Float, nullable=False)
    anomaly_score = Column(Float, nullable=False)
    diagnostic_summary = Column(String(255), nullable=False)
    resolved_by = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    machine = relationship("MachineAsset", back_populates="incidents")

    __table_args__ = (
        Index("idx_machine_status", "machine_code", "status"),
    )
