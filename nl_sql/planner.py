from __future__ import annotations

import json
import os
import re
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - optional dependency at runtime
    OpenAI = None

from .common import (
    ALLOWED_TABLES,
    DEFAULT_CAMERA_TIMEZONE,
    DEFAULT_PREVIEW_LIMIT,
    QueryPlan,
    epoch_to_iso,
    extract_json_block,
    iso_to_epoch,
)
from .db import dataset_bounds
from .logging_utils import get_logger


logger = get_logger(__name__)


def _parse_time_token(raw_time: str) -> tuple[int, int]:
    token = raw_time.strip().lower()
    match = re.match(r"^(\d{1,2})(?::(\d{2}))?\s*(am|pm)?$", token)
    if not match:
        raise ValueError(f"Unsupported time token: {raw_time}")
    hour = int(match.group(1))
    minute = int(match.group(2) or 0)
    ampm = match.group(3)
    if ampm == "pm" and hour != 12:
        hour += 12
    if ampm == "am" and hour == 12:
        hour = 0
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        raise ValueError(f"Invalid time token: {raw_time}")
    return hour, minute


def derive_time_range(question: str, conn: sqlite3.Connection) -> tuple[str, str]:
    lower = question.lower()
    min_epoch, max_epoch = dataset_bounds(conn)
    camera_tz_name = os.getenv("CAMERA_TIMEZONE", DEFAULT_CAMERA_TIMEZONE)
    camera_tz = ZoneInfo(camera_tz_name)

    anchor_utc = datetime.fromtimestamp(max_epoch, tz=timezone.utc)
    anchor_local = anchor_utc.astimezone(camera_tz)
    base_end = datetime(anchor_local.year, anchor_local.month, anchor_local.day, tzinfo=camera_tz) + timedelta(days=1)
    base_start = base_end - timedelta(days=7)

    if "last 24h" in lower or "last 24 hours" in lower:
        base_end = anchor_local
        base_start = base_end - timedelta(hours=24)
    elif "last 7 days" in lower:
        base_end = anchor_local
        base_start = base_end - timedelta(days=7)
    elif "yesterday" in lower:
        day_start = datetime(anchor_local.year, anchor_local.month, anchor_local.day, tzinfo=camera_tz) - timedelta(days=1)
        day_end = day_start + timedelta(days=1)
        base_start, base_end = day_start, day_end
    elif "today" in lower:
        day_start = datetime(anchor_local.year, anchor_local.month, anchor_local.day, tzinfo=camera_tz)
        day_end = min(day_start + timedelta(days=1), anchor_local + timedelta(seconds=1))
        base_start, base_end = day_start, day_end

    date_match = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", lower)
    if date_match:
        parsed = datetime.strptime(date_match.group(1), "%Y-%m-%d").replace(tzinfo=camera_tz)
        base_start = datetime(parsed.year, parsed.month, parsed.day, tzinfo=camera_tz)
        base_end = base_start + timedelta(days=1)

    between_match = re.search(
        r"\bbetween\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)\s+and\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)\b",
        lower,
    )
    if between_match:
        start_h, start_m = _parse_time_token(between_match.group(1))
        end_h, end_m = _parse_time_token(between_match.group(2))
        day_anchor = datetime(base_start.year, base_start.month, base_start.day, tzinfo=camera_tz)
        start_local = day_anchor.replace(hour=start_h, minute=start_m, second=0, microsecond=0)
        end_local = day_anchor.replace(hour=end_h, minute=end_m, second=0, microsecond=0)
        if end_local <= start_local:
            end_local += timedelta(days=1)
        base_start, base_end = start_local, end_local

    start_utc = base_start.astimezone(timezone.utc)
    end_utc = base_end.astimezone(timezone.utc)
    if end_utc <= start_utc:
        end_utc = start_utc + timedelta(hours=1)

    min_allowed = datetime.fromtimestamp(min_epoch, tz=timezone.utc)
    max_allowed = datetime.fromtimestamp(max_epoch + 1, tz=timezone.utc)
    if end_utc < min_allowed or start_utc > max_allowed:
        end_utc = max_allowed
        start_utc = max(end_utc - timedelta(days=7), min_allowed)

    start_iso = start_utc.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    end_iso = end_utc.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    logger.info(
        "Derived UTC time range for question: start=%s end=%s timezone=%s",
        start_iso,
        end_iso,
        camera_tz_name,
    )
    return (start_iso, end_iso)


def sql_has_time_bounds(sql: str) -> bool:
    lower = sql.lower()
    has_between = (
        "timestamp_epoch_s between" in lower
        or "timestamp_utc between" in lower
        or "hour_bucket_utc between" in lower
    )
    if has_between:
        return True
    has_start = (
        "timestamp_epoch_s >=" in lower
        or "timestamp_utc >=" in lower
        or "hour_bucket_utc >=" in lower
    )
    has_end = (
        "timestamp_epoch_s <" in lower
        or "timestamp_utc <" in lower
        or "hour_bucket_utc <" in lower
    )
    return has_start and has_end


def validate_sql(sql: str) -> str:
    cleaned = sql.strip().rstrip(";")
    if not cleaned:
        raise ValueError("SQL is empty.")
    lower = cleaned.lower()
    if not lower.startswith("select"):
        raise ValueError("Only SELECT statements are allowed.")
    if re.search(r"\bfrom\b", lower) is None:
        raise ValueError("SQL must include a FROM clause.")
    if ";" in cleaned:
        raise ValueError("Multiple statements are not allowed.")
    if re.search(r"\b(insert|update|delete|drop|alter|create|attach|pragma|replace|truncate)\b", lower):
        raise ValueError("Mutating SQL is not allowed.")
    if re.search(r"\b(date_trunc|extract)\s*\(", lower):
        raise ValueError("Use SQLite-compatible time functions (strftime), not DATE_TRUNC/EXTRACT.")
    if re.search(r"\bhour\s*\(", lower):
        raise ValueError("Use SQLite strftime('%H', ...) instead of HOUR(...).")
    if re.search(r"\binterval\b", lower):
        raise ValueError("SQLite INTERVAL syntax is not supported.")
    table_matches = list(re.finditer(r"\b(?:from|join)\s+([a-zA-Z_][a-zA-Z0-9_]*)", lower))
    if not table_matches:
        raise ValueError("SQL must reference an allowed table.")
    used_tables: set[str] = set()
    for match in table_matches:
        table = match.group(1)
        if table not in ALLOWED_TABLES:
            raise ValueError(f"Table not allowed: {table}")
        used_tables.add(table)
    if "events_hourly_rollup" in used_tables:
        unsupported_rollup_columns = ["timestamp_utc", "timestamp_epoch_s", "person_count", "detector_latency_ms"]
        for column in unsupported_rollup_columns:
            if re.search(rf"\b{column}\b", lower):
                raise ValueError(
                    "events_hourly_rollup query used unsupported base-event column "
                    f"'{column}'. Use rollup columns (hour_bucket_utc, event_count, avg_person_count, avg_detector_latency_ms, p95_latency_ms)."
                )
    if not sql_has_time_bounds(cleaned):
        raise ValueError("SQL must include explicit timestamp start and end bounds.")
    logger.debug("Validated SQL successfully. length=%s", len(cleaned))
    return cleaned


def build_event_filter_clause(event_context: list[str], event_types: list[str]) -> str:
    if not event_context or set(event_context) == set(event_types):
        return ""
    values = ", ".join(f"'{event}'" for event in event_context)
    return f" AND captured_event IN ({values})"


def heuristic_query_plan(
    question: str,
    start_utc: str,
    end_utc: str,
    event_context: list[str],
    event_types: list[str],
) -> QueryPlan:
    lower = question.lower()
    start_epoch = iso_to_epoch(start_utc)
    end_epoch = iso_to_epoch(end_utc)
    window_seconds = end_epoch - start_epoch

    aggregate_markers = ["count", "highest", "top", "peak", "average", "avg", "trend", "latency"]
    lookup_markers = ["show", "list", "records", "raw", "rows", "latest", "recent"]
    is_lookup = any(token in lower for token in lookup_markers) and not any(token in lower for token in aggregate_markers)
    intent = "sql_lookup" if is_lookup else "sql_aggregate"

    event_filter = build_event_filter_clause(event_context, event_types)
    if intent == "sql_lookup":
        sql = f"""
SELECT
    event_id,
    captured_event,
    cam_id,
    location_tag,
    timestamp_utc,
    object_id,
    person_count,
    confidence,
    detector_latency_ms
FROM events
WHERE timestamp_epoch_s >= {start_epoch}
  AND timestamp_epoch_s < {end_epoch}
  {event_filter}
ORDER BY timestamp_epoch_s DESC
LIMIT {DEFAULT_PREVIEW_LIMIT}
        """.strip()
    else:
        if "latency" in lower:
            metric_sql = "AVG(detector_latency_ms) AS avg_detector_latency_ms, MAX(detector_latency_ms) AS peak_detector_latency_ms,"
        elif "person_count" in lower or "headcount" in lower or "head count" in lower:
            metric_sql = "AVG(person_count) AS avg_person_count, MAX(person_count) AS peak_person_count,"
        else:
            metric_sql = ""

        if window_seconds > 24 * 3600:
            sql = f"""
SELECT
    captured_event,
    cam_id,
    location_tag,
    SUM(event_count) AS event_count,
    AVG(avg_person_count) AS avg_person_count,
    MAX(avg_detector_latency_ms) AS peak_detector_latency_ms
FROM events_hourly_rollup
WHERE hour_bucket_utc >= '{start_utc[:13]}:00:00Z'
  AND hour_bucket_utc < '{end_utc[:13]}:00:00Z'
  {event_filter}
GROUP BY captured_event, cam_id, location_tag
ORDER BY event_count DESC
LIMIT {DEFAULT_PREVIEW_LIMIT}
            """.strip()
        else:
            sql = f"""
SELECT
    captured_event,
    cam_id,
    location_tag,
    COUNT(*) AS event_count,
    {metric_sql}
    MIN(timestamp_utc) AS window_first_seen_utc,
    MAX(timestamp_utc) AS window_last_seen_utc
FROM events
WHERE timestamp_epoch_s >= {start_epoch}
  AND timestamp_epoch_s < {end_epoch}
  {event_filter}
GROUP BY captured_event, cam_id, location_tag
ORDER BY event_count DESC
LIMIT {DEFAULT_PREVIEW_LIMIT}
            """.strip()

    return QueryPlan(
        intent=intent,
        time_range={"start_utc": start_utc, "end_utc": end_utc},
        sql=sql,
        result_constraints={"max_rows": DEFAULT_PREVIEW_LIMIT},
    )


def build_dataset_prompt_profile(conn: sqlite3.Connection, event_types: list[str]) -> dict[str, object]:
    total_rows = int(conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] or 0)
    min_epoch, max_epoch = dataset_bounds(conn)
    distinct_cameras = int(conn.execute("SELECT COUNT(DISTINCT cam_id) FROM events").fetchone()[0] or 0)
    distinct_locations = int(
        conn.execute("SELECT COUNT(DISTINCT COALESCE(location_tag, '')) FROM events").fetchone()[0] or 0
    )

    event_rows = conn.execute(
        """
        SELECT captured_event, COUNT(*) AS row_count
        FROM events
        GROUP BY captured_event
        ORDER BY row_count DESC, captured_event
        """
    ).fetchall()
    event_distribution = {str(row[0]): int(row[1]) for row in event_rows if row[0] is not None}

    top_camera_rows = conn.execute(
        """
        SELECT cam_id, COUNT(*) AS row_count
        FROM events
        GROUP BY cam_id
        ORDER BY row_count DESC, cam_id
        LIMIT 5
        """
    ).fetchall()
    top_location_rows = conn.execute(
        """
        SELECT COALESCE(location_tag, '') AS location_tag, COUNT(*) AS row_count
        FROM events
        GROUP BY COALESCE(location_tag, '')
        ORDER BY row_count DESC, location_tag
        LIMIT 5
        """
    ).fetchall()
    ranges = conn.execute(
        """
        SELECT
            MIN(person_count), MAX(person_count),
            MIN(detector_latency_ms), MAX(detector_latency_ms),
            MIN(confidence), MAX(confidence)
        FROM events
        """
    ).fetchone()

    profile = {
        "canonical_source": "Data/Augmented_Data/out/data.csv",
        "rows_total": total_rows,
        "time_range_utc": {
            "min": epoch_to_iso(min_epoch),
            "max": epoch_to_iso(max_epoch),
        },
        "distinct_entities": {
            "cameras": distinct_cameras,
            "locations": distinct_locations,
        },
        "event_types_expected": event_types,
        "event_distribution": event_distribution,
        "top_cameras_by_rows": [
            {"cam_id": str(row[0]), "rows": int(row[1])} for row in top_camera_rows if row[0] is not None
        ],
        "top_locations_by_rows": [
            {"location_tag": str(row[0]), "rows": int(row[1])} for row in top_location_rows
        ],
        "metric_ranges": {
            "person_count": {
                "min": None if ranges is None or ranges[0] is None else int(ranges[0]),
                "max": None if ranges is None or ranges[1] is None else int(ranges[1]),
            },
            "detector_latency_ms": {
                "min": None if ranges is None or ranges[2] is None else float(ranges[2]),
                "max": None if ranges is None or ranges[3] is None else float(ranges[3]),
            },
            "confidence": {
                "min": None if ranges is None or ranges[4] is None else float(ranges[4]),
                "max": None if ranges is None or ranges[5] is None else float(ranges[5]),
            },
        },
    }
    logger.info(
        "Built dataset prompt profile rows_total=%s cameras=%s locations=%s events=%s",
        total_rows,
        distinct_cameras,
        distinct_locations,
        len(event_distribution),
    )
    return profile


def _dataset_guidance_block(dataset_profile: dict[str, object]) -> str:
    return (
        "Dataset context (authoritative, derived from canonical data.csv):\n"
        f"{json.dumps(dataset_profile, indent=2)}\n\n"
        "Field semantics:\n"
        "- events.timestamp_epoch_s is UTC epoch seconds and is preferred for filtering.\n"
        "- events.timestamp_utc is UTC ISO string for display and grouping.\n"
        "- captured_event values include person_count, person_entry, person_exit, vehicle_entry, vehicle_exit, unattended_object.\n"
        "- person_count metric is meaningful for captured_event='person_count' rows only.\n"
        "- entry/exit events are flow events; do not infer flow from person_count snapshots.\n"
        "- detector_latency_ms is per-detection latency; aggregate via AVG/MAX/PERCENTILE-style summaries.\n"
    )


def build_sql_generation_prompt(
    question: str,
    start_utc: str,
    end_utc: str,
    dataset_profile: dict[str, object],
) -> str:
    dataset_block = _dataset_guidance_block(dataset_profile)
    return f"""
You are a query compiler. Produce ONLY a JSON object matching QueryPlan.
Rules:
- Use only SELECT.
- Use only tables: events, events_hourly_rollup.
- Always include timestamp bounds with start/end in UTC.
- SQLite dialect only. Do NOT use DATE_TRUNC, HOUR(), EXTRACT, INTERVAL.
- Prefer strftime('%Y-%m-%dT%H:00:00Z', timestamp_epoch_s, 'unixepoch') for hour bucketing.
- events columns: event_id, cam_id, captured_event, timestamp_epoch_s, timestamp_utc, location_tag, object_id, person_count, confidence, detector_latency_ms, source_track_age_s, is_synthetic_artifact.
- events_hourly_rollup columns: captured_event, cam_id, location_tag, hour_bucket_utc, event_count, avg_person_count, avg_detector_latency_ms, p95_latency_ms.
- If using events_hourly_rollup, never reference timestamp_utc/timestamp_epoch_s/person_count/detector_latency_ms directly.
- Prefer events_hourly_rollup if time window > 24h.

QueryPlan schema:
{{
  "intent": "sql_aggregate|sql_lookup",
  "time_range": {{"start_utc":"ISO-8601 UTC","end_utc":"ISO-8601 UTC"}},
  "sql": "SELECT ...",
  "result_constraints": {{"max_rows": 1..5000}}
}}

Required bounds:
start_utc={start_utc}
end_utc={end_utc}

{dataset_block}

User question:
{question}
    """.strip()


def build_sql_only_prompt(
    question: str,
    start_utc: str,
    end_utc: str,
    dataset_profile: dict[str, object],
) -> str:
    start_epoch = iso_to_epoch(start_utc)
    end_epoch = iso_to_epoch(end_utc)
    dataset_block = _dataset_guidance_block(dataset_profile)
    return f"""
You are a SQLite query generator.
Return ONLY one SELECT statement. No markdown. No explanation.

Allowed tables:
- events(event_id, cam_id, captured_event, timestamp_epoch_s, timestamp_utc, location_tag, object_id, person_count, confidence, detector_latency_ms, source_track_age_s, is_synthetic_artifact)
- events_hourly_rollup(captured_event, cam_id, location_tag, hour_bucket_utc, event_count, avg_person_count, avg_detector_latency_ms, p95_latency_ms)

Hard constraints:
- SELECT only.
- No writes/mutations.
- SQLite dialect only (no DATE_TRUNC, HOUR(), EXTRACT, INTERVAL).
- Use only allowed tables and fields.
- Must include UTC time bounds using one of:
  events: timestamp_epoch_s >= {start_epoch} AND timestamp_epoch_s < {end_epoch}
  events_hourly_rollup: hour_bucket_utc >= '{start_utc[:13]}:00:00Z' AND hour_bucket_utc < '{end_utc[:13]}:00:00Z'
- If querying events_hourly_rollup, use only: captured_event, cam_id, location_tag, hour_bucket_utc, event_count, avg_person_count, avg_detector_latency_ms, p95_latency_ms.
- Prefer events_hourly_rollup if the window is larger than 24 hours.
- Include LIMIT {DEFAULT_PREVIEW_LIMIT} unless aggregation naturally returns fewer rows.

{dataset_block}

Question: {question}
SQL:
    """.strip()


def build_sql_repair_prompt(
    question: str,
    start_utc: str,
    end_utc: str,
    dataset_profile: dict[str, object],
    invalid_output: str,
    validation_error: str,
) -> str:
    dataset_block = _dataset_guidance_block(dataset_profile)
    start_epoch = iso_to_epoch(start_utc)
    end_epoch = iso_to_epoch(end_utc)
    trimmed_invalid = (invalid_output or "").strip()
    if len(trimmed_invalid) > 1800:
        trimmed_invalid = trimmed_invalid[:1800]
    return f"""
You are fixing an invalid SQLite SELECT query.
Return ONLY one corrected SELECT statement. No markdown. No explanation.

Invalid model output (for reference):
{trimmed_invalid}

Validation/execution error:
{validation_error}

Hard constraints:
- SQLite dialect only (no DATE_TRUNC, HOUR(), EXTRACT, INTERVAL).
- Use only tables: events, events_hourly_rollup.
- events columns: event_id, cam_id, captured_event, timestamp_epoch_s, timestamp_utc, location_tag, object_id, person_count, confidence, detector_latency_ms, source_track_age_s, is_synthetic_artifact.
- events_hourly_rollup columns: captured_event, cam_id, location_tag, hour_bucket_utc, event_count, avg_person_count, avg_detector_latency_ms, p95_latency_ms.
- If using events_hourly_rollup, do not use timestamp_utc/timestamp_epoch_s/person_count/detector_latency_ms.
- Must include UTC time bounds using one of:
  events: timestamp_epoch_s >= {start_epoch} AND timestamp_epoch_s < {end_epoch}
  events_hourly_rollup: hour_bucket_utc >= '{start_utc[:13]}:00:00Z' AND hour_bucket_utc < '{end_utc[:13]}:00:00Z'
- Include LIMIT {DEFAULT_PREVIEW_LIMIT}.

{dataset_block}

Question: {question}
Corrected SQL:
    """.strip()


def extract_sql_statement(text: str) -> str:
    candidate = text.strip()
    fence_match = re.search(r"```(?:sql)?\s*(.*?)```", candidate, flags=re.IGNORECASE | re.DOTALL)
    if fence_match:
        candidate = fence_match.group(1).strip()

    select_match = re.search(r"\bselect\b[\s\S]*", candidate, flags=re.IGNORECASE)
    if not select_match:
        raise ValueError("No SQL SELECT statement found in model output.")

    sql = select_match.group(0).strip()
    semi_idx = sql.find(";")
    if semi_idx != -1:
        sql = sql[:semi_idx]
    return sql.strip()


def enforce_time_bounds(sql: str, start_utc: str, end_utc: str) -> str:
    cleaned = sql.strip().rstrip(";")
    if sql_has_time_bounds(cleaned):
        return cleaned

    lower = cleaned.lower()
    if "events_hourly_rollup" in lower:
        field = "hour_bucket_utc"
        start_value = f"'{start_utc[:13]}:00:00Z'"
        end_value = f"'{end_utc[:13]}:00:00Z'"
    else:
        field = "timestamp_utc"
        start_value = f"'{start_utc}'"
        end_value = f"'{end_utc}'"

    bounds = f"{field} >= {start_value}\n  AND {field} < {end_value}"
    if re.search(r"\bwhere\b", lower):
        clause_match = re.search(r"\b(group\s+by|having|order\s+by|limit)\b", cleaned, flags=re.IGNORECASE)
        if clause_match:
            idx = clause_match.start()
            head = cleaned[:idx].rstrip()
            tail = cleaned[idx:].lstrip()
            return f"{head}\n  AND {bounds}\n{tail}"
        return f"{cleaned}\n  AND {bounds}"

    clause_match = re.search(r"\b(group\s+by|having|order\s+by|limit)\b", cleaned, flags=re.IGNORECASE)
    if clause_match:
        idx = clause_match.start()
        head = cleaned[:idx].rstrip()
        tail = cleaned[idx:].lstrip()
        return f"{head}\nWHERE {bounds}\n{tail}"
    return f"{cleaned}\nWHERE {bounds}"


def normalize_generated_sql(raw_sql: str, start_utc: str, end_utc: str) -> str:
    bounded = enforce_time_bounds(raw_sql, start_utc, end_utc)
    return validate_sql(bounded)


def parse_local_plan_from_text(raw: str, start_utc: str, end_utc: str) -> QueryPlan:
    try:
        payload = extract_json_block(raw)
        return parse_query_plan_object(payload, start_utc, end_utc)
    except Exception:
        sql_text = extract_sql_statement(raw)
        normalized_sql = normalize_generated_sql(sql_text, start_utc, end_utc)
        lowered_sql = normalized_sql.lower()
        intent = "sql_lookup" if " group by " not in lowered_sql and "count(" not in lowered_sql else "sql_aggregate"
        return QueryPlan(
            intent=intent,
            time_range={"start_utc": start_utc, "end_utc": end_utc},
            sql=normalized_sql,
            result_constraints={"max_rows": DEFAULT_PREVIEW_LIMIT},
        )


def configured_openai_sql_model() -> str:
    return os.getenv("OPENAI_SQL_MODEL", "gpt-3.5-turbo").strip() or "gpt-3.5-turbo"


def compile_with_openai(prompt: str) -> str:
    if OpenAI is None:
        raise RuntimeError("OpenAI SDK is not available.")
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        env_path = Path(".env")
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith("OPENAI_API_KEY"):
                    _, value = line.split("=", 1)
                    api_key = value.strip().strip('"').strip("'")
                    if api_key:
                        break
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured.")

    model = configured_openai_sql_model()
    logger.info("OpenAI compile request model=%s prompt_chars=%s", model, len(prompt))
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        temperature=0,
        messages=[
            {"role": "system", "content": "You output only strict JSON objects."},
            {"role": "user", "content": prompt},
        ],
    )
    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("OpenAI returned empty content.")
    logger.info("OpenAI compile response model=%s content_chars=%s", model, len(content))
    return content


def parse_query_plan_object(payload: dict[str, object], start_utc: str, end_utc: str) -> QueryPlan:
    if "intent" not in payload or "sql" not in payload:
        raise ValueError("Missing required keys in QueryPlan payload.")
    time_range = payload.get("time_range") or {}
    if not isinstance(time_range, dict):
        time_range = {}
    parsed_start = str(time_range.get("start_utc") or start_utc)
    parsed_end = str(time_range.get("end_utc") or end_utc)
    constraints = payload.get("result_constraints") or {}
    if not isinstance(constraints, dict):
        constraints = {}
    max_rows = int(constraints.get("max_rows") or DEFAULT_PREVIEW_LIMIT)
    max_rows = min(max(max_rows, 1), 5000)

    sql = normalize_generated_sql(str(payload["sql"]), start_utc, end_utc)
    return QueryPlan(
        intent=str(payload.get("intent", "sql_aggregate")),
        time_range={"start_utc": parsed_start, "end_utc": parsed_end},
        sql=sql,
        result_constraints={"max_rows": max_rows},
    )


def compile_query_plan(
    question: str,
    provider_mode: str,
    conn: sqlite3.Connection,
    event_types: list[str],
    allow_heuristic_fallback: bool = True,
) -> tuple[QueryPlan, str, list[str]]:
    from .event_context import extract_event_mentions

    errors: list[str] = []
    start_utc, end_utc = derive_time_range(question, conn)
    explicit_context = extract_event_mentions(question, event_types)
    heuristic = heuristic_query_plan(question, start_utc, end_utc, explicit_context, event_types)

    provider_mode = provider_mode.lower().strip()
    logger.info(
        "Compile query plan start provider_mode=%s allow_heuristic_fallback=%s start_utc=%s end_utc=%s",
        provider_mode,
        allow_heuristic_fallback,
        start_utc,
        end_utc,
    )
    if provider_mode not in {"openai", "auto"}:
        message = (
            f"Provider '{provider_mode}' is not supported. OpenAI-only mode is enabled."
        )
        if not allow_heuristic_fallback:
            raise RuntimeError(message)
        errors.append(message)
        return heuristic, "heuristic", errors

    dataset_profile = build_dataset_prompt_profile(conn, event_types)
    prompt = build_sql_generation_prompt(
        question=question,
        start_utc=start_utc,
        end_utc=end_utc,
        dataset_profile=dataset_profile,
    )
    sql_only_prompt = build_sql_only_prompt(
        question=question,
        start_utc=start_utc,
        end_utc=end_utc,
        dataset_profile=dataset_profile,
    )
    try:
        logger.info("Compile attempt provider=openai")
        try:
            raw = compile_with_openai(prompt)
            payload = extract_json_block(raw)
            plan = parse_query_plan_object(payload, start_utc, end_utc)
        except Exception as first_openai_exc:
            logger.warning(
                "Primary OpenAI JSON compile failed; retrying with SQL-only prompt. error=%s",
                first_openai_exc,
            )
            sql_raw = compile_with_openai(sql_only_prompt)
            try:
                plan = parse_local_plan_from_text(sql_raw, start_utc, end_utc)
            except Exception as second_openai_parse_exc:
                logger.warning(
                    "OpenAI SQL-only parse failed; retrying with repair prompt. error=%s",
                    second_openai_parse_exc,
                )
                repair_prompt = build_sql_repair_prompt(
                    question=question,
                    start_utc=start_utc,
                    end_utc=end_utc,
                    dataset_profile=dataset_profile,
                    invalid_output=sql_raw,
                    validation_error=str(second_openai_parse_exc),
                )
                repair_raw = compile_with_openai(repair_prompt)
                plan = parse_local_plan_from_text(repair_raw, start_utc, end_utc)
        logger.info("Compile success provider=openai intent=%s", plan.intent)
        return plan, "openai", errors
    except Exception as exc:
        errors.append(f"openai compile failed: {exc}")
        logger.warning("Compile failed provider=openai error=%s", exc)

    if not allow_heuristic_fallback:
        joined = "; ".join(errors) if errors else "No compile attempts were made."
        logger.error("Compile failed in strict mode. errors=%s", joined)
        raise RuntimeError(joined)
    logger.warning("All providers failed; using heuristic fallback.")
    return heuristic, "heuristic_fallback", errors


def ensure_limit(sql: str, max_rows: int) -> str:
    cleaned = sql.strip().rstrip(";")
    if re.search(r"\blimit\s+\d+\b", cleaned, flags=re.IGNORECASE):
        return cleaned
    return f"{cleaned}\nLIMIT {max_rows}"


def execute_preview_query(
    conn: sqlite3.Connection,
    sql: str,
    max_rows: int,
) -> tuple[pd.DataFrame, str]:
    validated = validate_sql(sql)
    bounded = ensure_limit(validated, max_rows)
    logger.info("Executing preview query max_rows=%s", max_rows)
    frame = pd.read_sql_query(bounded, conn)
    logger.info("Preview query complete rows=%s cols=%s", frame.shape[0], frame.shape[1])
    return frame, bounded
