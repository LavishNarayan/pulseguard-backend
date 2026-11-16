import json
import logging
import time
from celery import Celery
import redis
from app.core.config import settings
from app.core.telemetry_metrics import INCIDENTS_CREATED_TOTAL, INFERENCE_LATENCY_SECONDS
from app.db.models import IncidentSeverity, IncidentStatus, MachineAsset, MaintenanceIncident
from app.db.session import SyncSessionLocal
from app.ml.predictor import PredictiveMaintenanceEngine

logger = logging.getLogger(__name__)

celery_app = Celery(
    "pulseguard_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=5)
def process_telemetry_task(self, payload: dict) -> dict:
    try:
        engine = PredictiveMaintenanceEngine()
        machine_code = payload["machine_code"]

        inf_start = time.perf_counter()
        prediction = engine.predict(
            temp=payload["temperature_c"],
            vibration=payload["vibration_mm_s"],
            rpm=payload["rpm"],
            pressure=payload["pressure_bar"],
        )
        INFERENCE_LATENCY_SECONDS.observe(time.perf_counter() - inf_start)

        live_state = {
            "machine_code": machine_code,
            "facility_zone": payload["facility_zone"],
            "sensors": {
                "temperature_c": payload["temperature_c"],
                "vibration_mm_s": payload["vibration_mm_s"],
                "rpm": payload["rpm"],
                "pressure_bar": payload["pressure_bar"],
            },
            "inference": prediction,
        }
        redis_client.setex(f"machine:live:{machine_code}", 3600, json.dumps(live_state))

        with SyncSessionLocal() as db:
            asset = db.query(MachineAsset).filter_by(machine_code=machine_code).first()
            if not asset:
                asset = MachineAsset(
                    machine_code=machine_code,
                    facility_zone=payload["facility_zone"],
                    model_type="Industrial-Turbine-Gen4",
                )
                db.add(asset)
                db.commit()

            rul = prediction["predicted_rul"]
            is_anomaly = prediction["is_anomaly"]

            if rul < settings.CRITICAL_RUL_THRESHOLD or is_anomaly:
                cooldown_key = f"alert:cooldown:{machine_code}"
                if redis_client.set(cooldown_key, "1", nx=True, ex=settings.ALERT_COOLDOWN_SECONDS):
                    severity = (
                        IncidentSeverity.CRITICAL
                        if rul < (settings.CRITICAL_RUL_THRESHOLD / 2)
                        else IncidentSeverity.WARNING
                    )
                    summary = (
                        f"Degradation detected: RUL={rul} cycles, "
                        f"Temp={payload['temperature_c']}C, Vib={payload['vibration_mm_s']}mm/s"
                    )
                    incident = MaintenanceIncident(
                        machine_code=machine_code,
                        severity=severity,
                        status=IncidentStatus.OPEN,
                        predicted_rul=rul,
                        anomaly_score=prediction["anomaly_score"],
                        diagnostic_summary=summary,
                    )
                    db.add(incident)
                    db.commit()
                    INCIDENTS_CREATED_TOTAL.labels(severity=severity.value).inc()
                    logger.warning(f"[{severity.value}] Created incident for {machine_code}")

        return {"machine_code": machine_code, "status": "processed", **prediction}

    except Exception as exc:
        logger.error(f"Telemetry processing failed: {exc}")
        raise self.retry(exc=exc)
