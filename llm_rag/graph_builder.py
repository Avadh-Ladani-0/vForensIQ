"""Populate Neo4j from the SQL logbase. Idempotent (MERGE-based).

Graph schema (locked in project_llm_design.md):
  (:Camera {camera_id, camera_location, mode})
  (:Location {name})
  (:EventType {name})
  (:Hour {hour_utc, date})
  (:Event {event_id, event_type, timestamp_utc, confidence, object_id})   -- entry/exit only
  (:CrowdHour {crowd_hour_id, camera_id, location, hour_utc, avg_hc, peak_hc, event_count})

  (:Event)-[:DETECTED_BY]->(:Camera)
  (:Camera)-[:LOCATED_AT]->(:Location)
  (:Event)-[:OCCURRED_IN]->(:Hour)
  (:Event)-[:IS_TYPE]->(:EventType)
  (:CrowdHour)-[:AT_CAMERA]->(:Camera)
  (:CrowdHour)-[:DURING]->(:Hour)
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from neo4j import GraphDatabase

from .common import DEFAULT_LOGBASE_PATH, NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER


CONSTRAINTS = [
    "CREATE CONSTRAINT event_id IF NOT EXISTS FOR (e:Event) REQUIRE e.event_id IS UNIQUE",
    "CREATE CONSTRAINT camera_id IF NOT EXISTS FOR (c:Camera) REQUIRE c.camera_id IS UNIQUE",
    "CREATE CONSTRAINT location_name IF NOT EXISTS FOR (l:Location) REQUIRE l.name IS UNIQUE",
    "CREATE CONSTRAINT event_type_name IF NOT EXISTS FOR (et:EventType) REQUIRE et.name IS UNIQUE",
    "CREATE CONSTRAINT hour_utc IF NOT EXISTS FOR (h:Hour) REQUIRE h.hour_utc IS UNIQUE",
    "CREATE CONSTRAINT crowdhour_id IF NOT EXISTS FOR (ch:CrowdHour) REQUIRE ch.crowd_hour_id IS UNIQUE",
]


def _wipe(session) -> None:
    """Drop everything. Cheap for our size; avoids MERGE-stale-data issues."""
    session.run("MATCH (n) DETACH DELETE n")


def _apply_constraints(session) -> None:
    for stmt in CONSTRAINTS:
        session.run(stmt)


def _build_dimensions(session, conn: sqlite3.Connection) -> None:
    # EventType
    for row in conn.execute("SELECT DISTINCT event_type FROM events").fetchall():
        session.run("MERGE (:EventType {name: $n})", n=row[0])
    # Camera + Location (+ LOCATED_AT)
    cams = conn.execute(
        "SELECT DISTINCT camera_id, camera_location FROM events"
    ).fetchall()
    for cam_id, loc in cams:
        session.run("MERGE (:Location {name: $n})", n=loc)
        # Determine mode: crowd cameras emit only crowd events, entry_exit cameras only entry/exit.
        mode_row = conn.execute(
            """
            SELECT CASE WHEN SUM(CASE WHEN event_type='crowd' THEN 1 ELSE 0 END) > 0
                        THEN 'crowd' ELSE 'entry_exit' END
            FROM events WHERE camera_id = ?
            """,
            (cam_id,),
        ).fetchone()
        mode = mode_row[0] if mode_row else "unknown"
        session.run(
            """
            MERGE (c:Camera {camera_id: $cid})
            SET c.camera_location = $loc, c.mode = $mode
            WITH c
            MATCH (l:Location {name: $loc})
            MERGE (c)-[:LOCATED_AT]->(l)
            """,
            cid=cam_id, loc=loc, mode=mode,
        )


def _build_hours(session, conn: sqlite3.Connection) -> None:
    rows = conn.execute(
        """
        SELECT DISTINCT
            strftime('%Y-%m-%dT%H:00:00Z', timestamp_epoch_s, 'unixepoch') AS hour_utc,
            strftime('%Y-%m-%d', timestamp_epoch_s, 'unixepoch') AS date
        FROM events
        """
    ).fetchall()
    for hour_utc, date in rows:
        session.run(
            "MERGE (h:Hour {hour_utc: $h}) SET h.date = $d",
            h=hour_utc, d=date,
        )


def _build_entry_exit_events(session, conn: sqlite3.Connection) -> int:
    """One :Event node per entry/exit row. Returns count inserted."""
    cursor = conn.execute(
        """
        SELECT event_id, event_type, timestamp_utc, timestamp_epoch_s, confidence,
               object_id, camera_id,
               strftime('%Y-%m-%dT%H:00:00Z', timestamp_epoch_s, 'unixepoch') AS hour_utc
        FROM events
        WHERE event_type IN ('person_entry','person_exit','car_entry','car_exit')
        """
    )
    batch: list[dict] = []
    total = 0
    BATCH_SIZE = 500
    for row in cursor:
        batch.append({
            "event_id": row[0], "event_type": row[1], "timestamp_utc": row[2],
            "confidence": row[4], "object_id": row[5],
            "camera_id": row[6], "hour_utc": row[7],
        })
        if len(batch) >= BATCH_SIZE:
            session.run(
                """
                UNWIND $rows AS r
                MERGE (e:Event {event_id: r.event_id})
                SET e.event_type = r.event_type,
                    e.timestamp_utc = r.timestamp_utc,
                    e.confidence = r.confidence,
                    e.object_id = r.object_id
                WITH e, r
                MATCH (c:Camera {camera_id: r.camera_id})
                MATCH (et:EventType {name: r.event_type})
                MATCH (h:Hour {hour_utc: r.hour_utc})
                MERGE (e)-[:DETECTED_BY]->(c)
                MERGE (e)-[:IS_TYPE]->(et)
                MERGE (e)-[:OCCURRED_IN]->(h)
                """,
                rows=batch,
            )
            total += len(batch)
            batch.clear()
    if batch:
        session.run(
            """
            UNWIND $rows AS r
            MERGE (e:Event {event_id: r.event_id})
            SET e.event_type = r.event_type,
                e.timestamp_utc = r.timestamp_utc,
                e.confidence = r.confidence,
                e.object_id = r.object_id
            WITH e, r
            MATCH (c:Camera {camera_id: r.camera_id})
            MATCH (et:EventType {name: r.event_type})
            MATCH (h:Hour {hour_utc: r.hour_utc})
            MERGE (e)-[:DETECTED_BY]->(c)
            MERGE (e)-[:IS_TYPE]->(et)
            MERGE (e)-[:OCCURRED_IN]->(h)
            """,
            rows=batch,
        )
        total += len(batch)
    return total


def _build_crowd_hours(session, conn: sqlite3.Connection) -> int:
    """Hourly aggregates for crowd cameras. Keeps graph small."""
    rows = conn.execute(
        """
        SELECT
            camera_id,
            camera_location,
            strftime('%Y-%m-%dT%H:00:00Z', timestamp_epoch_s, 'unixepoch') AS hour_utc,
            ROUND(AVG(head_count), 2) AS avg_hc,
            MAX(head_count) AS peak_hc,
            COUNT(*) AS event_count
        FROM events
        WHERE event_type = 'crowd'
        GROUP BY camera_id, camera_location, hour_utc
        """
    ).fetchall()
    payload = [
        {
            "crowd_hour_id": f"{cam}_{h}",
            "camera_id": cam, "camera_location": loc, "hour_utc": h,
            "avg_hc": float(avg_hc or 0), "peak_hc": int(peak_hc or 0),
            "event_count": int(evc or 0),
        }
        for cam, loc, h, avg_hc, peak_hc, evc in rows
    ]
    if payload:
        session.run(
            """
            UNWIND $rows AS r
            MERGE (ch:CrowdHour {crowd_hour_id: r.crowd_hour_id})
            SET ch.camera_id = r.camera_id,
                ch.camera_location = r.camera_location,
                ch.hour_utc = r.hour_utc,
                ch.avg_hc = r.avg_hc,
                ch.peak_hc = r.peak_hc,
                ch.event_count = r.event_count
            WITH ch, r
            MATCH (c:Camera {camera_id: r.camera_id})
            MATCH (h:Hour {hour_utc: r.hour_utc})
            MERGE (ch)-[:AT_CAMERA]->(c)
            MERGE (ch)-[:DURING]->(h)
            """,
            rows=payload,
        )
    return len(payload)


def build_graph(
    logbase_path: Path = DEFAULT_LOGBASE_PATH,
    wipe_first: bool = True,
) -> dict:
    """Build the Neo4j graph from the SQL logbase. Returns counts."""
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    conn = sqlite3.connect(logbase_path)
    stats: dict = {}
    try:
        with driver.session() as session:
            if wipe_first:
                _wipe(session)
            _apply_constraints(session)
            _build_dimensions(session, conn)
            _build_hours(session, conn)
            stats["events"] = _build_entry_exit_events(session, conn)
            stats["crowd_hours"] = _build_crowd_hours(session, conn)

            # Summary counts
            for label in ("Camera", "Location", "EventType", "Hour", "Event", "CrowdHour"):
                rec = session.run(f"MATCH (n:{label}) RETURN count(n) AS c").single()
                stats[label] = rec["c"]
    finally:
        conn.close()
        driver.close()
    return stats


if __name__ == "__main__":
    stats = build_graph()
    print("Graph build complete:")
    for k, v in stats.items():
        print(f"  {k:<12} {v}")
