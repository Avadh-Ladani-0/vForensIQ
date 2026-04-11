import sqlite3
import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_PKG_ROOT = _ROOT
if str(_PKG_ROOT) not in sys.path:
    sys.path.insert(0, str(_PKG_ROOT))

from nl_sql.aggregation import aggregate_event_chunks, build_event_sections
from nl_sql.common import EVENT_TYPES
from nl_sql.event_context import resolve_event_context
from nl_sql.summarizer import build_natural_language_answer, build_summary_text


def _seed_test_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.execute(
        """
        CREATE TABLE events (
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

    rows = [
        ("e1", "7", "person_entry", 1739507400, "2025-02-14T04:30:00Z", "entrance_1", "p1", None, 0.9, 100, 1, 0),
        ("e2", "7", "person_entry", 1739507460, "2025-02-14T04:31:00Z", "entrance_1", "p2", None, 0.91, 90, 1, 0),
        ("e3", "8", "person_entry", 1739507520, "2025-02-14T04:32:00Z", "entrance_2", "p3", None, 0.89, 110, 1, 0),
        ("e4", "12", "person_count", 1739507400, "2025-02-14T04:30:00Z", "main_hall", "pc1", 12, 0.95, 80, 1, 0),
        ("e5", "12", "person_count", 1739507460, "2025-02-14T04:31:00Z", "main_hall", "pc2", 18, 0.96, 85, 1, 0),
        ("e6", "12", "person_count", 1739507520, "2025-02-14T04:32:00Z", "main_hall", "pc3", 15, 0.94, 82, 1, 0),
        ("e7", "2", "vehicle_exit", 1739507580, "2025-02-14T04:33:00Z", "gate_2", "v1", None, 0.9, 125, 2, 0),
    ]
    conn.executemany(
        """
        INSERT INTO events (
            event_id, cam_id, captured_event, timestamp_epoch_s, timestamp_utc,
            location_tag, object_id, person_count, confidence, detector_latency_ms,
            source_track_age_s, is_synthetic_artifact
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    return conn


class EventContextPipelineTests(unittest.TestCase):
    def test_resolve_context_from_question(self) -> None:
        context, source, cross = resolve_event_context(
            question="Show person entry spikes for yesterday",
            sql="SELECT * FROM events WHERE timestamp_epoch_s >= 1 AND timestamp_epoch_s < 2",
            available_events=["person_entry", "person_count"],
            event_types=EVENT_TYPES,
        )
        self.assertEqual(context, ["person_entry"])
        self.assertEqual(source, "explicit_nl")
        self.assertFalse(cross)

    def test_resolve_context_from_sql_filter(self) -> None:
        context, source, _ = resolve_event_context(
            question="Show activity",
            sql=(
                "SELECT * FROM events WHERE timestamp_epoch_s >= 1 AND timestamp_epoch_s < 2 "
                "AND captured_event IN ('vehicle_entry','vehicle_exit')"
            ),
            available_events=["vehicle_entry", "vehicle_exit", "person_count"],
            event_types=EVENT_TYPES,
        )
        self.assertEqual(context, ["vehicle_entry", "vehicle_exit"])
        self.assertEqual(source, "sql_filter")

    def test_chunked_aggregation_and_guardrails(self) -> None:
        conn = _seed_test_db()
        try:
            stats, chunk_stats, _ = aggregate_event_chunks(
                conn=conn,
                start_epoch=1739507300,
                end_epoch=1739507700,
                event_context=["person_entry", "person_count"],
                chunk_size=2,
            )
            self.assertEqual(chunk_stats["person_entry"]["chunks"], 2)
            self.assertEqual(chunk_stats["person_count"]["chunks"], 2)

            sections = build_event_sections(stats)
            person_entry_section = sections["person_entry"].lower()
            person_count_section = sections["person_count"].lower()

            self.assertIn("total person entry events", person_entry_section)
            self.assertNotIn("average person_count", person_entry_section)
            self.assertIn("average person_count", person_count_section)

            summary = build_summary_text(
                question="Give me event trends",
                start_utc="2025-02-14T04:30:00Z",
                end_utc="2025-02-14T04:40:00Z",
                event_context=["person_entry", "person_count"],
                event_stats=stats,
                sections=sections,
                cross_event_requested=False,
                summary_provider="openai",
            ).lower()
            self.assertIn("[person_entry]", summary)
            self.assertIn("[person_count]", summary)
            self.assertNotIn("cross-event comparison", summary)
        finally:
            conn.close()

    def test_cross_event_summary_enabled(self) -> None:
        conn = _seed_test_db()
        try:
            stats, _, _ = aggregate_event_chunks(
                conn=conn,
                start_epoch=1739507300,
                end_epoch=1739507700,
                event_context=["person_entry", "person_count", "vehicle_exit"],
                chunk_size=3,
            )
            sections = build_event_sections(stats)
            summary = build_summary_text(
                question="Compare person entry and person count",
                start_utc="2025-02-14T04:30:00Z",
                end_utc="2025-02-14T04:40:00Z",
                event_context=["person_entry", "person_count", "vehicle_exit"],
                event_stats=stats,
                sections=sections,
                cross_event_requested=True,
                summary_provider="openai",
            ).lower()
            self.assertIn("cross-event comparison", summary)
        finally:
            conn.close()

    def test_natural_language_answer_from_processed_rows(self) -> None:
        answer = build_natural_language_answer(
            question="Show insights",
            start_utc="2025-02-14T04:30:00Z",
            end_utc="2025-02-14T05:30:00Z",
            event_context=["person_count"],
            processed_rows=[
                {
                    "captured_event": "person_count",
                    "total_events": 72000,
                    "active_cameras": 20,
                    "top_camera": "11",
                    "top_location": "ISRO stall",
                    "peak_hour_utc": "2025-02-14T04:00:00Z",
                    "avg_latency_ms": 148.16,
                    "peak_latency_ms": 731.0,
                    "avg_person_count": 4.76,
                    "peak_person_count": 45,
                }
            ],
            fallback_summary="UTC Window: 2025-02-14T04:30:00Z to 2025-02-14T05:30:00Z",
            cross_event_requested=False,
        ).lower()
        self.assertIn("sql-backed insights", answer)
        self.assertIn("person_count", answer)
        self.assertIn("peak person_count of 45", answer)


if __name__ == "__main__":
    unittest.main()
