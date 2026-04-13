from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - optional dependency at runtime
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv()


CANONICAL_SOURCE_CSV = Path("Data/Augmented_Data/out/data.csv")
SQLITE_DB_PATH = Path("runtime/vforensiq_events.db")
LOG_DIR_PATH = Path("logs")
AUDIT_LOG_PATH = LOG_DIR_PATH / "query_audit.jsonl"
PIPELINE_LOG_PATH = LOG_DIR_PATH / "llm_sql_pipeline.log"

EVENT_TYPES = [
    "person_count",
    "person_entry",
    "person_exit",
    "vehicle_entry",
    "vehicle_exit",
    "unattended_object",
]
ALLOWED_TABLES = {"events", "events_hourly_rollup"}

DEFAULT_CAMERA_TIMEZONE = "Asia/Kolkata"
DEFAULT_CHUNK_SIZE = 5000
DEFAULT_PREVIEW_LIMIT = 200


@dataclass
class QueryPlan:
    intent: str
    time_range: Dict[str, str]
    sql: str
    result_constraints: Dict[str, int]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def iso_to_epoch(iso_value: str) -> int:
    normalized = iso_value.replace("Z", "+00:00")
    return int(datetime.fromisoformat(normalized).timestamp())


def epoch_to_iso(epoch_value: int) -> str:
    return datetime.fromtimestamp(epoch_value, timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def safe_json_default(value: Any) -> Any:
    if isinstance(value, (datetime,)):
        return value.isoformat()
    return str(value)


def extract_json_block(text: str) -> dict[str, Any]:
    start_idx = text.find("{")
    end_idx = text.rfind("}")
    if start_idx == -1 or end_idx == -1 or end_idx <= start_idx:
        raise ValueError("No JSON object found in model output.")
    return json.loads(text[start_idx : end_idx + 1])
