"""Full Graph Builder — includes per-second crowd events as :CrowdEvent nodes.

Fixes the crowd-exclusion problem: MATCH (e:Event) + MATCH (ce:CrowdEvent)
now covers 100% of the data (no more 98.6% loss).

Node types:
  (:Camera), (:Location), (:EventType), (:Hour)
  (:Event)       — entry/exit events (person_entry/exit, car_entry/exit)
  (:CrowdEvent)  — individual per-second crowd samples with head_count
  (:CrowdHour)   — hourly crowd aggregates (avg_hc, peak_hc, event_count)
  (:CrowdMinute) — per-minute crowd aggregates
  (:CrowdDay)    — per-day crowd aggregates
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
from .hierarchical_builder import (
    EXTRA_CONSTRAINTS, _build_crowd_minutes, _build_crowd_days,
)


CROWD_EVENT_CONSTRAINT = "CREATE CONSTRAINT crowd_event_id IF NOT EXISTS FOR (ce:CrowdEvent) REQUIRE ce.event_id IS UNIQUE"


def _build_crowd_events(session, conn: sqlite3.Connection) -> int:
    """Create one :CrowdEvent node per per-second crowd sample.
    These are the raw 1Hz samples — gives graph parity with SQL for COUNT queries.
    """
    cursor = conn.execute(
        """
        SELECT event_id, timestamp_utc, timestamp_epoch_s, camera_id,
               camera_location, head_count, confidence,
               strftime('%Y-%m-%dT%H:00:00Z', timestamp_epoch_s, 'unixepoch') AS hour_utc
        FROM events
        WHERE event_type = 'crowd'
        """
    )
    batch: list[dict] = []
    total = 0
    BATCH_SIZE = 5000
    for row in cursor:
        batch.append({
            "event_id": row[0], "timestamp_utc": row[1],
            "camera_id": row[3], "camera_location": row[4],
            "head_count": row[5], "confidence": row[6],
            "hour_utc": row[7],
        })
        if len(batch) >= BATCH_SIZE:
            _insert_crowd_batch(session, batch)
            total += len(batch)
            batch.clear()
            if total % 50000 == 0:
                print(f"  ... {total} crowd events ingested")
    if batch:
        _insert_crowd_batch(session, batch)
        total += len(batch)
    return total


def _insert_crowd_batch(session, batch: list[dict]) -> None:
    session.run(
        """
        UNWIND $rows AS r
        MERGE (ce:CrowdEvent {event_id: r.event_id})
        SET ce.timestamp_utc = r.timestamp_utc,
            ce.camera_id = r.camera_id,
            ce.camera_location = r.camera_location,
            ce.head_count = r.head_count,
            ce.confidence = r.confidence
        WITH ce, r
        MATCH (c:Camera {camera_id: r.camera_id})
        MERGE (ce)-[:DETECTED_BY]->(c)
        """,
        rows=batch,
    )


def build_full_graph(
    logbase_path: Path = DEFAULT_LOGBASE_PATH,
    wipe_first: bool = True,
) -> dict:
    """Build the complete graph: base + hierarchical + per-second crowd events."""
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
            session.run(CROWD_EVENT_CONSTRAINT)

            print("Building dimensions...")
            _build_dimensions(session, conn)
            _build_hours(session, conn)

            print("Building entry/exit events...")
            stats["events"] = _build_entry_exit_events(session, conn)

            print("Building per-second crowd events (this takes a minute)...")
            stats["crowd_events"] = _build_crowd_events(session, conn)

            print("Building crowd aggregates (hour/minute/day)...")
            stats["crowd_hours"] = _build_crowd_hours(session, conn)
            stats["crowd_minutes"] = _build_crowd_minutes(session, conn)
            stats["crowd_days"] = _build_crowd_days(session, conn)

            for label in ("Camera", "Location", "EventType", "Hour",
                          "Event", "CrowdEvent", "CrowdHour", "CrowdMinute", "CrowdDay"):
                rec = session.run(f"MATCH (n:{label}) RETURN count(n) AS c").single()
                stats[label] = rec["c"]
    finally:
        conn.close()
        driver.close()
    return stats


if __name__ == "__main__":
    stats = build_full_graph()
    print("\nFull graph build complete:")
    for k, v in stats.items():
        print(f"  {k:<14} {v}")
