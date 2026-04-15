"""Hierarchical Graph Builder — 4-level temporal granularity (Direction 4).

Adds to the base graph schema:
  (:CrowdMinute {cm_id, camera_id, camera_location, minute_utc, avg_hc, peak_hc, event_count})
  (:CrowdDay    {cd_id, camera_id, camera_location, date, avg_hc, peak_hc, event_count})

Existing nodes kept: :Event (entry/exit), :CrowdHour, :Camera, :Location, :EventType, :Hour.

The temporal scope selector (in this module) picks the right granularity per query.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from neo4j import GraphDatabase

from .common import DEFAULT_LOGBASE_PATH, NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER
from .graph_builder import (
    _wipe, _apply_constraints, _build_dimensions, _build_hours,
    _build_entry_exit_events, _build_crowd_hours,
)


EXTRA_CONSTRAINTS = [
    "CREATE CONSTRAINT cm_id IF NOT EXISTS FOR (cm:CrowdMinute) REQUIRE cm.cm_id IS UNIQUE",
    "CREATE CONSTRAINT cd_id IF NOT EXISTS FOR (cd:CrowdDay) REQUIRE cd.cd_id IS UNIQUE",
]


def _build_crowd_minutes(session, conn: sqlite3.Connection) -> int:
    """Per-minute crowd aggregates."""
    rows = conn.execute(
        """
        SELECT
            camera_id,
            camera_location,
            strftime('%Y-%m-%dT%H:%M:00Z', timestamp_epoch_s, 'unixepoch') AS minute_utc,
            ROUND(AVG(head_count), 2) AS avg_hc,
            MAX(head_count) AS peak_hc,
            COUNT(*) AS event_count
        FROM events
        WHERE event_type = 'crowd'
        GROUP BY camera_id, camera_location, minute_utc
        """
    ).fetchall()
    payload = [
        {
            "cm_id": f"{cam}_{m}",
            "camera_id": cam, "camera_location": loc, "minute_utc": m,
            "avg_hc": float(avg_hc or 0), "peak_hc": int(peak_hc or 0),
            "event_count": int(evc or 0),
        }
        for cam, loc, m, avg_hc, peak_hc, evc in rows
    ]
    BATCH = 2000
    for i in range(0, len(payload), BATCH):
        batch = payload[i:i+BATCH]
        session.run(
            """
            UNWIND $rows AS r
            MERGE (cm:CrowdMinute {cm_id: r.cm_id})
            SET cm.camera_id = r.camera_id,
                cm.camera_location = r.camera_location,
                cm.minute_utc = r.minute_utc,
                cm.avg_hc = r.avg_hc,
                cm.peak_hc = r.peak_hc,
                cm.event_count = r.event_count
            WITH cm, r
            MATCH (c:Camera {camera_id: r.camera_id})
            MERGE (cm)-[:AT_CAMERA]->(c)
            """,
            rows=batch,
        )
    return len(payload)


def _build_crowd_days(session, conn: sqlite3.Connection) -> int:
    """Per-day crowd aggregates."""
    rows = conn.execute(
        """
        SELECT
            camera_id,
            camera_location,
            strftime('%Y-%m-%d', timestamp_epoch_s, 'unixepoch') AS date,
            ROUND(AVG(head_count), 2) AS avg_hc,
            MAX(head_count) AS peak_hc,
            COUNT(*) AS event_count
        FROM events
        WHERE event_type = 'crowd'
        GROUP BY camera_id, camera_location, date
        """
    ).fetchall()
    payload = [
        {
            "cd_id": f"{cam}_{d}",
            "camera_id": cam, "camera_location": loc, "date": d,
            "avg_hc": float(avg_hc or 0), "peak_hc": int(peak_hc or 0),
            "event_count": int(evc or 0),
        }
        for cam, loc, d, avg_hc, peak_hc, evc in rows
    ]
    if payload:
        session.run(
            """
            UNWIND $rows AS r
            MERGE (cd:CrowdDay {cd_id: r.cd_id})
            SET cd.camera_id = r.camera_id,
                cd.camera_location = r.camera_location,
                cd.date = r.date,
                cd.avg_hc = r.avg_hc,
                cd.peak_hc = r.peak_hc,
                cd.event_count = r.event_count
            WITH cd, r
            MATCH (c:Camera {camera_id: r.camera_id})
            MERGE (cd)-[:AT_CAMERA]->(c)
            """,
            rows=payload,
        )
    return len(payload)


def build_hierarchical_graph(
    logbase_path: Path = DEFAULT_LOGBASE_PATH,
    wipe_first: bool = True,
) -> dict:
    """Build the full hierarchical graph: base schema + minute + day levels."""
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    conn = sqlite3.connect(logbase_path)
    stats: dict = {}
    try:
        with driver.session() as session:
            if wipe_first:
                _wipe(session)
            _apply_constraints(session)
            for stmt in EXTRA_CONSTRAINTS:
                session.run(stmt)
            _build_dimensions(session, conn)
            _build_hours(session, conn)
            stats["events"] = _build_entry_exit_events(session, conn)
            stats["crowd_hours"] = _build_crowd_hours(session, conn)
            stats["crowd_minutes"] = _build_crowd_minutes(session, conn)
            stats["crowd_days"] = _build_crowd_days(session, conn)

            for label in ("Camera", "Location", "EventType", "Hour", "Event",
                          "CrowdHour", "CrowdMinute", "CrowdDay"):
                rec = session.run(f"MATCH (n:{label}) RETURN count(n) AS c").single()
                stats[label] = rec["c"]
    finally:
        conn.close()
        driver.close()
    return stats


# ---------------------------------------------------------------------------
# Temporal scope selector
# ---------------------------------------------------------------------------

import re

def select_granularity(question: str) -> str:
    """Infer the right crowd-granularity level from the question's temporal scope.

    Returns one of: 'per_second' (SQL only), 'per_minute', 'per_hour', 'per_day'.
    """
    lower = question.lower()

    # Per-day indicators (weekly, multi-day, trend over days)
    if re.search(r"\b(week|weekly|last \d+ days|daily trend|per day|day by day)\b", lower):
        return "per_day"

    # Per-minute indicators (specific minutes, sub-hour precision)
    if re.search(r"\b(minute|per minute|minute[- ]by[- ]minute|\d{2}:\d{2}:\d{2})\b", lower):
        return "per_minute"

    # Per-second indicators (exact moment, specific second)
    if re.search(r"\b(exact|per second|specific second|at \d{2}:\d{2}:\d{2})\b", lower):
        return "per_second"

    # Default: per-hour (most queries are hourly-scope)
    return "per_hour"


# ---------------------------------------------------------------------------
# Cypher node-type mapping per granularity
# ---------------------------------------------------------------------------

GRANULARITY_NODE_MAP = {
    "per_second": "events (SQL fallback — no per-second graph nodes; use B1 SQL path)",
    "per_minute": "CrowdMinute",
    "per_hour": "CrowdHour",
    "per_day": "CrowdDay",
}


if __name__ == "__main__":
    stats = build_hierarchical_graph()
    print("Hierarchical graph build complete:")
    for k, v in stats.items():
        print(f"  {k:<14} {v}")
