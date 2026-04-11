from __future__ import annotations

import hashlib
import sqlite3
import time
from pathlib import Path
from typing import Any

import pandas as pd

from .aggregation import aggregate_event_chunks, build_event_sections
from .common import (
    CANONICAL_SOURCE_CSV,
    DEFAULT_CHUNK_SIZE,
    DEFAULT_PREVIEW_LIMIT,
    EVENT_TYPES,
    SQLITE_DB_PATH,
    iso_to_epoch,
    utc_now_iso,
    QueryPlan,
)
from .db import ensure_sqlite_database, load_distinct_events
from .event_context import resolve_event_context
from .planner import (
    compile_query_plan,
    configured_openai_sql_model,
    ensure_limit,
    execute_preview_query,
    heuristic_query_plan,
    validate_sql,
)
from .summarizer import append_audit_log, build_natural_language_answer, build_summary_text
from .logging_utils import get_logger


logger = get_logger(__name__)


def _build_event_filter(event_context: list[str]) -> tuple[str, list[Any]]:
    if not event_context:
        return "", []
    placeholders = ", ".join("?" for _ in event_context)
    return f" AND captured_event IN ({placeholders})", [str(event) for event in event_context]


def _provider_model_name(provider: str) -> str:
    _ = provider
    return configured_openai_sql_model()


def _run_processed_sql_queries(
    conn: sqlite3.Connection,
    start_epoch: int,
    end_epoch: int,
    event_context: list[str],
) -> tuple[pd.DataFrame, list[dict[str, str]]]:
    logger.info(
        "Running processed SQL queries start_epoch=%s end_epoch=%s events=%s",
        start_epoch,
        end_epoch,
        event_context,
    )
    event_clause, event_params = _build_event_filter(event_context)
    base_params: list[Any] = [start_epoch, end_epoch, *event_params]

    overview_sql = f"""
SELECT
    captured_event,
    COUNT(*) AS total_events,
    COUNT(DISTINCT cam_id) AS active_cameras,
    COUNT(DISTINCT location_tag) AS active_locations,
    ROUND(AVG(person_count), 2) AS avg_person_count,
    MAX(person_count) AS peak_person_count,
    ROUND(AVG(detector_latency_ms), 2) AS avg_latency_ms,
    ROUND(MAX(detector_latency_ms), 2) AS peak_latency_ms
FROM events
WHERE timestamp_epoch_s >= ?
  AND timestamp_epoch_s < ?
  {event_clause}
GROUP BY captured_event
ORDER BY total_events DESC
    """.strip()

    top_camera_sql = f"""
WITH ranked AS (
    SELECT
        captured_event,
        cam_id,
        COUNT(*) AS cam_event_count,
        ROW_NUMBER() OVER (
            PARTITION BY captured_event
            ORDER BY COUNT(*) DESC, cam_id
        ) AS rn
    FROM events
    WHERE timestamp_epoch_s >= ?
      AND timestamp_epoch_s < ?
      {event_clause}
    GROUP BY captured_event, cam_id
)
SELECT captured_event, cam_id AS top_camera, cam_event_count
FROM ranked
WHERE rn = 1
    """.strip()

    top_location_sql = f"""
WITH ranked AS (
    SELECT
        captured_event,
        location_tag,
        COUNT(*) AS location_event_count,
        ROW_NUMBER() OVER (
            PARTITION BY captured_event
            ORDER BY COUNT(*) DESC, location_tag
        ) AS rn
    FROM events
    WHERE timestamp_epoch_s >= ?
      AND timestamp_epoch_s < ?
      {event_clause}
    GROUP BY captured_event, location_tag
)
SELECT captured_event, location_tag AS top_location, location_event_count
FROM ranked
WHERE rn = 1
    """.strip()

    peak_hour_sql = f"""
WITH ranked AS (
    SELECT
        captured_event,
        strftime('%Y-%m-%dT%H:00:00Z', timestamp_epoch_s, 'unixepoch') AS peak_hour_utc,
        COUNT(*) AS peak_hour_events,
        ROW_NUMBER() OVER (
            PARTITION BY captured_event
            ORDER BY COUNT(*) DESC, strftime('%Y-%m-%dT%H:00:00Z', timestamp_epoch_s, 'unixepoch')
        ) AS rn
    FROM events
    WHERE timestamp_epoch_s >= ?
      AND timestamp_epoch_s < ?
      {event_clause}
    GROUP BY captured_event, peak_hour_utc
)
SELECT captured_event, peak_hour_utc, peak_hour_events
FROM ranked
WHERE rn = 1
    """.strip()

    overview_df = pd.read_sql_query(overview_sql, conn, params=base_params)
    top_camera_df = pd.read_sql_query(top_camera_sql, conn, params=base_params)
    top_location_df = pd.read_sql_query(top_location_sql, conn, params=base_params)
    peak_hour_df = pd.read_sql_query(peak_hour_sql, conn, params=base_params)

    processed_df = overview_df.merge(top_camera_df, on="captured_event", how="left")
    processed_df = processed_df.merge(top_location_df, on="captured_event", how="left")
    processed_df = processed_df.merge(peak_hour_df, on="captured_event", how="left")
    processed_df = processed_df.sort_values(by=["total_events", "captured_event"], ascending=[False, True])
    logger.info("Processed SQL queries complete rows=%s", processed_df.shape[0])

    citations = [
        {"id": "primary_query", "purpose": "Primary question SQL", "sql": ""},
        {"id": "processed_overview", "purpose": "Per-event totals and latency/person_count metrics", "sql": overview_sql},
        {"id": "processed_top_camera", "purpose": "Top camera per event context", "sql": top_camera_sql},
        {"id": "processed_top_location", "purpose": "Top location per event context", "sql": top_location_sql},
        {"id": "processed_peak_hour", "purpose": "Peak hour per event context", "sql": peak_hour_sql},
    ]
    return processed_df, citations


def run_single_provider_query(
    question: str,
    provider_mode: str,
    db_path: Path | str = SQLITE_DB_PATH,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> dict[str, Any]:
    start_time = time.time()
    errors: list[str] = []
    requested_provider_mode = provider_mode.lower().strip()
    provider_mode = "openai"
    if requested_provider_mode not in {"openai", "auto"}:
        errors.append(
            f"Provider '{requested_provider_mode}' requested, but local/compare providers are disabled. Using openai."
        )
    strict_provider_mode = True
    query_id = hashlib.sha1(f"{question}:{utc_now_iso()}:{provider_mode}".encode("utf-8")).hexdigest()[:16]
    logger.info(
        "Run single provider query start query_id=%s provider_mode=%s requested_provider_mode=%s strict=%s chunk_size=%s",
        query_id,
        provider_mode,
        requested_provider_mode,
        strict_provider_mode,
        chunk_size,
    )

    conn = sqlite3.connect(Path(db_path), timeout=30)
    try:
        conn.execute("PRAGMA busy_timeout=30000")
        plan, plan_provider, compile_errors = compile_query_plan(
            question=question,
            provider_mode=provider_mode,
            conn=conn,
            event_types=EVENT_TYPES,
            allow_heuristic_fallback=not strict_provider_mode,
        )
        provider_model = _provider_model_name(plan_provider)
        errors.extend(compile_errors)
        logger.info(
            "Compiled query_id=%s provider=%s model=%s intent=%s",
            query_id,
            plan_provider,
            provider_model,
            plan.intent,
        )
        available_events = load_distinct_events(conn, EVENT_TYPES)
        event_context, context_source, cross_event_requested = resolve_event_context(
            question=question,
            sql=plan.sql,
            available_events=available_events,
            event_types=EVENT_TYPES,
        )
        logger.info(
            "Resolved event context query_id=%s context=%s source=%s cross_event=%s",
            query_id,
            event_context,
            context_source,
            cross_event_requested,
        )

        if context_source in {"explicit_nl", "metric_inference"} and "captured_event" not in plan.sql.lower():
            if strict_provider_mode:
                errors.append(
                    "Generated SQL did not include captured_event filter; strict provider mode kept provider SQL."
                )
                logger.warning(
                    "Strict mode SQL missing captured_event filter query_id=%s provider=%s",
                    query_id,
                    provider_mode,
                )
            else:
                plan = heuristic_query_plan(
                    question=question,
                    start_utc=plan.time_range["start_utc"],
                    end_utc=plan.time_range["end_utc"],
                    event_context=event_context,
                    event_types=EVENT_TYPES,
                )
                plan.sql = validate_sql(plan.sql)
                plan.sql = ensure_limit(plan.sql, plan.result_constraints.get("max_rows", DEFAULT_PREVIEW_LIMIT))
                plan.result_constraints["max_rows"] = min(plan.result_constraints.get("max_rows", DEFAULT_PREVIEW_LIMIT), 5000)
                errors.append(
                    "SQL was rebuilt with event-context filter to prevent cross-event blending in summarization."
                )
                logger.warning("Rebuilt SQL with heuristic event filter query_id=%s", query_id)

        preview_max_rows = min(max(plan.result_constraints.get("max_rows", DEFAULT_PREVIEW_LIMIT), 1), 5000)
        try:
            preview_df, executed_sql = execute_preview_query(conn, plan.sql, preview_max_rows)
            logger.info(
                "Preview execution success query_id=%s rows=%s",
                query_id,
                preview_df.shape[0],
            )
        except Exception as sql_exec_exc:
            if strict_provider_mode:
                logger.error(
                    "Preview execution failed in strict mode query_id=%s provider=%s error=%s",
                    query_id,
                    provider_mode,
                    sql_exec_exc,
                )
                raise RuntimeError(
                    f"Generated SQL failed execution in strict {provider_mode} mode: {sql_exec_exc}"
                ) from sql_exec_exc
            errors.append(
                f"Generated SQL failed execution; switched to heuristic SQL: {sql_exec_exc}"
            )
            plan = heuristic_query_plan(
                question=question,
                start_utc=plan.time_range["start_utc"],
                end_utc=plan.time_range["end_utc"],
                event_context=event_context,
                event_types=EVENT_TYPES,
            )
            plan.sql = validate_sql(plan.sql)
            plan.sql = ensure_limit(plan.sql, plan.result_constraints.get("max_rows", DEFAULT_PREVIEW_LIMIT))
            preview_max_rows = min(max(plan.result_constraints.get("max_rows", DEFAULT_PREVIEW_LIMIT), 1), 5000)
            preview_df, executed_sql = execute_preview_query(conn, plan.sql, preview_max_rows)
            logger.warning("Switched to heuristic SQL after execution failure query_id=%s", query_id)

        start_epoch = iso_to_epoch(plan.time_range["start_utc"])
        end_epoch = iso_to_epoch(plan.time_range["end_utc"])
        processed_df, citation_queries = _run_processed_sql_queries(
            conn=conn,
            start_epoch=start_epoch,
            end_epoch=end_epoch,
            event_context=event_context,
        )
        for citation in citation_queries:
            if citation["id"] == "primary_query":
                citation["sql"] = executed_sql or plan.sql

        per_event_stats, event_chunk_stats, total_rows_scanned = aggregate_event_chunks(
            conn=conn,
            start_epoch=start_epoch,
            end_epoch=end_epoch,
            event_context=event_context,
            chunk_size=chunk_size,
        )
        logger.info(
            "Chunk aggregation complete query_id=%s total_rows_scanned=%s events=%s",
            query_id,
            total_rows_scanned,
            list(event_chunk_stats.keys()),
        )
        sections = build_event_sections(per_event_stats)
        summary_text = build_summary_text(
            question=question,
            start_utc=plan.time_range["start_utc"],
            end_utc=plan.time_range["end_utc"],
            event_context=event_context,
            event_stats=per_event_stats,
            sections=sections,
            cross_event_requested=cross_event_requested,
            summary_provider="openai",
        )
        answer_text = build_natural_language_answer(
            question=question,
            start_utc=plan.time_range["start_utc"],
            end_utc=plan.time_range["end_utc"],
            event_context=event_context,
            processed_rows=processed_df.to_dict(orient="records"),
            fallback_summary=summary_text,
            cross_event_requested=cross_event_requested,
        )
        logger.info(
            "Built response query_id=%s processed_rows=%s preview_rows=%s",
            query_id,
            processed_df.shape[0],
            preview_df.shape[0],
        )
    except Exception as exc:
        errors.append(str(exc))
        logger.exception("Run single provider query failed query_id=%s provider_mode=%s", query_id, provider_mode)
        preview_df = pd.DataFrame()
        processed_df = pd.DataFrame()
        citation_queries = []
        executed_sql = ""
        provider_model = _provider_model_name(provider_mode)
        plan = QueryPlan(
            intent="sql_lookup",
            time_range={"start_utc": utc_now_iso(), "end_utc": utc_now_iso()},
            sql="",
            result_constraints={"max_rows": DEFAULT_PREVIEW_LIMIT},
        )
        event_context = []
        context_source = "error"
        event_chunk_stats = {}
        sections = {}
        summary_text = f"Query failed: {exc}"
        answer_text = summary_text
        total_rows_scanned = 0
        plan_provider = provider_mode
    finally:
        conn.close()

    duration_ms = int((time.time() - start_time) * 1000)
    envelope = {
        "query_id": query_id,
        "provider": plan_provider,
        "provider_model": provider_model,
        "requested_provider_mode": requested_provider_mode,
        "question": question,
        "query_plan": {
            "intent": plan.intent,
            "time_range": plan.time_range,
            "sql": plan.sql,
            "result_constraints": plan.result_constraints,
        },
        "executed_sql": executed_sql,
        "event_context": event_context,
        "event_context_source": context_source,
        "event_chunk_stats": event_chunk_stats,
        "summary_sections": sections,
        "summary_text": summary_text,
        "answer_text": answer_text,
        "citation_queries": citation_queries,
        "processed_columns": processed_df.columns.tolist(),
        "processed_row_count": int(processed_df.shape[0]),
        "processed_rows": processed_df.to_dict(orient="records"),
        "preview_columns": preview_df.columns.tolist(),
        "preview_row_count": int(preview_df.shape[0]),
        "preview_rows": preview_df.head(200).to_dict(orient="records"),
        "total_rows_scanned": int(total_rows_scanned),
        "duration_ms": duration_ms,
        "errors": errors,
        "generated_at_utc": utc_now_iso(),
    }
    logger.info(
        "Run single provider query end query_id=%s provider=%s model=%s duration_ms=%s errors=%s",
        query_id,
        plan_provider,
        provider_model,
        duration_ms,
        len(errors),
    )
    append_audit_log(
        {
            "query_id": query_id,
            "provider": plan_provider,
            "question": question,
            "event_context": event_context,
            "event_chunk_stats": event_chunk_stats,
            "citation_ids": [item.get("id") for item in citation_queries],
            "duration_ms": duration_ms,
            "errors": errors,
            "generated_at_utc": envelope["generated_at_utc"],
        }
    )
    return envelope


def run_nl_sql_pipeline(
    question: str,
    provider_mode: str = "openai",
    compare: bool = False,
    csv_path: Path | str = CANONICAL_SOURCE_CSV,
    db_path: Path | str = SQLITE_DB_PATH,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> dict[str, Any]:
    requested_provider_mode = provider_mode.lower().strip()
    provider_mode = "openai"
    logger.info(
        "Run pipeline start provider_mode=%s requested_provider_mode=%s compare=%s chunk_size=%s csv_path=%s db_path=%s",
        provider_mode,
        requested_provider_mode,
        compare,
        chunk_size,
        csv_path,
        db_path,
    )
    if compare or requested_provider_mode in {"compare", "local"}:
        logger.warning(
            "Local/compare provider modes are disabled. requested_provider_mode=%s compare=%s",
            requested_provider_mode,
            compare,
        )
    db = ensure_sqlite_database(csv_path=csv_path, db_path=db_path)

    result = run_single_provider_query(
        question=question,
        provider_mode="openai",
        db_path=db,
        chunk_size=chunk_size,
    )
    envelope = {
        "mode": "single",
        "primary_source": str(Path(csv_path)),
        "result": result,
    }
    logger.info("Run pipeline end mode=single provider=%s", result.get("provider"))
    return envelope
