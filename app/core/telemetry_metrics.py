import json
import logging
import sys
from prometheus_client import Counter, Histogram

TELEMETRY_INGESTED_TOTAL = Counter(
    "pulseguard_telemetry_ingested_total",
    "Total telemetry packets accepted at the edge API",
    ["facility_zone"],
)

INFERENCE_LATENCY_SECONDS = Histogram(
    "pulseguard_ml_inference_duration_seconds",
    "Time spent running RUL and Isolation Forest inference in Celery worker",
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5),
)

INCIDENTS_CREATED_TOTAL = Counter(
    "pulseguard_incidents_created_total",
    "Total maintenance incidents created after Redis deduplication",
    ["severity"],
)


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "request_id"):
            log_record["request_id"] = record.request_id
        return json.dumps(log_record)


def configure_structured_logging():
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)
