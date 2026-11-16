from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import get_current_engineer
from app.db.models import IncidentStatus, MaintenanceIncident
from app.db.session import get_db
from app.schemas.telemetry import IncidentResponse

router = APIRouter()


@router.get("/", response_model=list[IncidentResponse], dependencies=[Depends(get_current_engineer)])
async def list_incidents(
    status_filter: IncidentStatus | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(MaintenanceIncident).order_by(MaintenanceIncident.created_at.desc()).limit(limit)
    if status_filter:
        stmt = stmt.where(MaintenanceIncident.status == status_filter)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.patch("/{incident_id}/resolve", response_model=IncidentResponse)
async def resolve_incident(
    incident_id: int,
    db: AsyncSession = Depends(get_db),
    engineer: str = Depends(get_current_engineer),
):
    result = await db.execute(
        select(MaintenanceIncident).where(MaintenanceIncident.id == incident_id)
    )
    incident = result.scalar_one_or_none()
    if not incident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")

    incident.status = IncidentStatus.RESOLVED
    incident.resolved_by = engineer
    incident.resolved_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(incident)
    return incident
