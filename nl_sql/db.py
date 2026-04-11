from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path
from typing import Any

import pandas as pd

from .common import epoch_to_iso, utc_now_iso
from .logging_utils import get_logger


logger = get_logger(__name__)


def load_distinct_events(conn: sqlite3.Connection, event_types: list[str]) -> list[str]:
    rows = conn.execute(
        "SELECT DISTINCT captured_event FROM events WHERE captured_event IS NOT NULL ORDER BY captured_event"
    ).fetchall()
    discovered = [str(row[0]) for row in rows]
    if not discovered:
        logger.info("No distinct events discovered in DB; using configured event type list.")
        return event_types[:]
    ordered = [event for event in event_types if event in discovered]
    extras = [event for event in discovered if event not in event_types]
    logger.info("Loaded distinct events from DB count=%s", len(ordered + extras))
    return ordered + extras


def _init_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS events (
            event_id TEXT PRIMARY KEY,
            cam_id TEXT NOT NULL,
            captured_event TEXT NOT NULL,   
            timestamp_epoch_s INTEGER NOT NULL,
            timestamp_utc TEXT NOT NULL,
            location_tag TEXT,
            object_id TEXT,
            person_count INTEGER,
            confidence REAL,
            detector_latency_ms REAL,
            source_track_age_s REAL,
            is_synthetic_artifact INTEGER DEFAULT 0
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS events_hourly_rollup (
            hour_bucket_utc TEXT NOT NULL,
            cam_id TEXT NOT NULL,
            location_tag TEXT NOT NULL,
            captured_event TEXT NOT NULL,
            event_count INTEGER NOT NULL,
            avg_person_count REAL,
            avg_detector_latency_ms REAL,
            p95_latency_ms REAL,
            PRIMARY KEY (hour_bucket_utc, cam_id, location_tag, captured_event)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS source_ingestion (
            source_path TEXT PRIMARY KEY,
            source_mtime_ns INTEGER NOT NULL,
            source_size INTEGER NOT NULL,
            row_count INTEGER NOT NULL,
            ingested_at_utc TEXT NOT NULL
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_events_ts ON events(timestamp_epoch_s)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_events_cam_ts ON events(cam_id, timestamp_epoch_s)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_events_loc_ts ON events(location_tag, timestamp_epoch_s)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_events_type_ts ON events(captured_event, timestamp_epoch_s)")


def _source_is_current(conn: sqlite3.Connection, source: Path) -> bool:
    stat = source.stat()
    row = conn.execute(
        """
        SELECT source_mtime_ns, source_size
        FROM source_ingestion
        WHERE source_path = ?
        """,
        (str(source.resolve()),),
    ).fetchone()
    if not row:
        logger.info("Source ingestion metadata missing for %s", source)
        return False
    is_current = int(row[0]) == int(stat.st_mtime_ns) and int(row[1]) == int(stat.st_size)
    logger.info("Source currency check source=%s is_current=%s", source, is_current)
    return is_current


def _normalize_chunk(chunk: pd.DataFrame, source_path: Path, start_index: int) -> list[tuple[Any, ...]]:
    required_columns = [
        "cam_id",
        "captured_event",
        "timestamp",
        "location_tag",
        "object_id",
        "person_count",
        "confidence",
        "detector_latency_ms",
        "source_track_age_s",
        "is_synthetic_artifact",
    ]
    for col in required_columns:
        if col not in chunk.columns:
            chunk[col] = None

    epoch = pd.to_numeric(chunk["timestamp"], errors="coerce").fillna(0).astype("int64")
    timestamp_utc = pd.to_datetime(epoch, unit="s", utc=True, errors="coerce").dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    source_prefix = hashlib.sha1(str(source_path.resolve()).encode("utf-8")).hexdigest()[:10]
    records: list[tuple[Any, ...]] = []
    for local_idx, row in enumerate(chunk.itertuples(index=False), start=start_index):
        event_id = f"{source_prefix}_{local_idx}"
        captured_event = str(getattr(row, "captured_event", "") or "")
        cam_id = str(getattr(row, "cam_id", "") or "")
        location_tag = str(getattr(row, "location_tag", "") or "")
        object_id = str(getattr(row, "object_id", "") or "")

        person_count = pd.to_numeric(getattr(row, "person_count", None), errors="coerce")
        confidence = pd.to_numeric(getattr(row, "confidence", None), errors="coerce")
        latency = pd.to_numeric(getattr(row, "detector_latency_ms", None), errors="coerce")
        track_age = pd.to_numeric(getattr(row, "source_track_age_s", None), errors="coerce")
        synthetic = pd.to_numeric(getattr(row, "is_synthetic_artifact", 0), errors="coerce")
        ts_epoch = int(epoch.iloc[local_idx - start_index])
        ts_utc = timestamp_utc.iloc[local_idx - start_index]

        records.append(
            (
                event_id,
                cam_id,
                captured_event,
                ts_epoch,
                str(ts_utc) if isinstance(ts_utc, str) and ts_utc else epoch_to_iso(ts_epoch),
                location_tag,
                object_id,
                None if pd.isna(person_count) else int(person_count),
                None if pd.isna(confidence) else float(confidence),
                None if pd.isna(latency) else float(latency),
                None if pd.isna(track_age) else float(track_age),
                0 if pd.isna(synthetic) else int(synthetic),
            )
        )
    return records


def _ingest_source_csv(conn: sqlite3.Connection, source: Path) -> None:
    logger.info("Starting CSV ingestion source=%s", source)
    conn.execute("DELETE FROM events")
    insert_sql = """
        INSERT INTO events (
            event_id,
            cam_id,
            captured_event,
            timestamp_epoch_s,
            timestamp_utc,
            location_tag,
            object_id,
            person_count,
            confidence,
            detector_latency_ms,
            source_track_age_s,
            is_synthetic_artifact
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    chunk_size = 50_000
    offset = 0
    chunk_count = 0
    for chunk in pd.read_csv(source, chunksize=chunk_size):
        records = _normalize_chunk(chunk, source, offset)
        if records:
            conn.executemany(insert_sql, records)
        chunk_count += 1
        offset += len(chunk)
        logger.info("Ingested chunk index=%s rows=%s cumulative_rows=%s", chunk_count, len(chunk), offset)
    logger.info("Completed CSV ingestion source=%s total_rows=%s chunks=%s", source, offset, chunk_count)


def _refresh_rollups(conn: sqlite3.Connection) -> None:
    logger.info("Refreshing hourly rollup table.")
    conn.execute("DELETE FROM events_hourly_rollup")
    conn.execute(
        """
        INSERT INTO events_hourly_rollup (
            hour_bucket_utc,
            cam_id,
            location_tag,
            captured_event,
            event_count,
            avg_person_count,
            avg_detector_latency_ms,
            p95_latency_ms
        )
        SELECT
            strftime('%Y-%m-%dT%H:00:00Z', timestamp_epoch_s, 'unixepoch') AS hour_bucket_utc,
            cam_id,
            COALESCE(location_tag, '') AS location_tag,
            captured_event,
            COUNT(*) AS event_count,
            AVG(person_count) AS avg_person_count,
            AVG(detector_latency_ms) AS avg_detector_latency_ms,
            NULL AS p95_latency_ms
        FROM events
        GROUP BY 1, 2, 3, 4
        """
    )
    rollup_rows = conn.execute("SELECT COUNT(*) FROM events_hourly_rollup").fetchone()[0]
    logger.info("Rollup refresh complete rows=%s", int(rollup_rows))


def _record_source_metadata(conn: sqlite3.Connection, source: Path) -> None:
    stat = source.stat()
    row_count = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    conn.execute(
        """
        INSERT OR REPLACE INTO source_ingestion (
            source_path,
            source_mtime_ns,
            source_size,
            row_count,
            ingested_at_utc
        ) VALUES (?, ?, ?, ?, ?)
        """,
        (str(source.resolve()), int(stat.st_mtime_ns), int(stat.st_size), int(row_count), utc_now_iso()),
    )
    logger.info("Recorded source metadata source=%s row_count=%s", source, int(row_count))


def ensure_sqlite_database(
    csv_path: Path | str,
    db_path: Path | str,
) -> Path:
    source = Path(csv_path)
    if not source.exists():
        raise FileNotFoundError(f"Primary source not found: {source}")

    logger.info("Ensuring SQLite database source=%s db=%s", source, db_path)
    target_db = Path(db_path)
    target_db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(target_db, timeout=30)
    try:
        conn.execute("PRAGMA busy_timeout=30000")
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        _init_schema(conn)
        if _source_is_current(conn, source):
            logger.info("Using existing SQLite database without re-ingestion db=%s", target_db)
            return target_db
        _ingest_source_csv(conn, source)
        _refresh_rollups(conn)
        _record_source_metadata(conn, source)
        conn.commit()
        logger.info("SQLite database refreshed successfully db=%s", target_db)
        return target_db
    finally:
        conn.close()


def dataset_bounds(conn: sqlite3.Connection) -> tuple[int, int]:
    row = conn.execute("SELECT MIN(timestamp_epoch_s), MAX(timestamp_epoch_s) FROM events").fetchone()
    if not row or row[0] is None or row[1] is None:
        from time import time

        now_epoch = int(time())
        logger.warning("Dataset bounds unavailable; using synthetic default 7-day window.")
        return now_epoch - 7 * 24 * 3600, now_epoch
    logger.info("Dataset bounds min=%s max=%s", int(row[0]), int(row[1]))
    return int(row[0]), int(row[1])
