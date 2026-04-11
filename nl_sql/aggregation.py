from __future__ import annotations

import sqlite3
from collections import Counter
from typing import Any

import pandas as pd

from .common import epoch_to_iso
from .logging_utils import get_logger


logger = get_logger(__name__)


def _init_event_stats(event_name: str) -> dict[str, Any]:
    return {
        "event": event_name,
        "row_count": 0,
        "chunk_count": 0,
        "first_epoch": None,
        "last_epoch": None,
        "cam_counter": Counter(),
        "location_counter": Counter(),
        "hour_counter": Counter(),
        "latency_sum": 0.0,
        "latency_samples": 0,
        "latency_peak": None,
        "person_count_sum": 0.0,
        "person_count_samples": 0,
        "person_count_peak": None,
    }


def _update_stats_with_chunk(event_stats: dict[str, Any], chunk: pd.DataFrame) -> None:
    if chunk.empty:
        return
    event_stats["row_count"] += len(chunk)
    event_stats["chunk_count"] += 1

    min_epoch = int(chunk["timestamp_epoch_s"].min())
    max_epoch = int(chunk["timestamp_epoch_s"].max())
    if event_stats["first_epoch"] is None or min_epoch < event_stats["first_epoch"]:
        event_stats["first_epoch"] = min_epoch
    if event_stats["last_epoch"] is None or max_epoch > event_stats["last_epoch"]:
        event_stats["last_epoch"] = max_epoch

    event_stats["cam_counter"].update(chunk["cam_id"].astype(str).tolist())
    event_stats["location_counter"].update(chunk["location_tag"].astype(str).tolist())

    hours = (chunk["timestamp_epoch_s"] // 3600) * 3600
    event_stats["hour_counter"].update(hours.astype(int).tolist())

    latency_series = pd.to_numeric(chunk["detector_latency_ms"], errors="coerce").dropna()
    if not latency_series.empty:
        event_stats["latency_sum"] += float(latency_series.sum())
        event_stats["latency_samples"] += int(latency_series.shape[0])
        peak_idx = latency_series.idxmax()
        peak_val = float(latency_series.loc[peak_idx])
        peak_row = chunk.loc[peak_idx]
        previous_peak = event_stats["latency_peak"]["value"] if event_stats["latency_peak"] else float("-inf")
        if peak_val > previous_peak:
            event_stats["latency_peak"] = {
                "value": peak_val,
                "timestamp_utc": str(peak_row["timestamp_utc"]),
                "cam_id": str(peak_row["cam_id"]),
                "location_tag": str(peak_row["location_tag"]),
            }

    person_series = pd.to_numeric(chunk["person_count"], errors="coerce").dropna()
    if not person_series.empty:
        event_stats["person_count_sum"] += float(person_series.sum())
        event_stats["person_count_samples"] += int(person_series.shape[0])
        peak_idx = person_series.idxmax()
        peak_val = float(person_series.loc[peak_idx])
        peak_row = chunk.loc[peak_idx]
        previous_peak = event_stats["person_count_peak"]["value"] if event_stats["person_count_peak"] else float("-inf")
        if peak_val > previous_peak:
            event_stats["person_count_peak"] = {
                "value": peak_val,
                "timestamp_utc": str(peak_row["timestamp_utc"]),
                "cam_id": str(peak_row["cam_id"]),
                "location_tag": str(peak_row["location_tag"]),
            }


def aggregate_event_chunks(
    conn: sqlite3.Connection,
    start_epoch: int,
    end_epoch: int,
    event_context: list[str],
    chunk_size: int,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], int]:
    chunk_size = max(int(chunk_size), 1)
    logger.info(
        "Aggregate event chunks start start_epoch=%s end_epoch=%s chunk_size=%s events=%s",
        start_epoch,
        end_epoch,
        chunk_size,
        event_context,
    )
    all_stats: dict[str, dict[str, Any]] = {}
    chunk_stats: dict[str, dict[str, Any]] = {}
    total_scanned = 0

    for event in event_context:
        event_stats = _init_event_stats(event)
        last_ts = start_epoch - 1
        last_event_id = ""
        while True:
            chunk = pd.read_sql_query(
                """
                SELECT
                    event_id,
                    timestamp_epoch_s,
                    timestamp_utc,
                    cam_id,
                    location_tag,
                    person_count,
                    detector_latency_ms
                FROM events
                WHERE captured_event = ?
                  AND timestamp_epoch_s >= ?
                  AND timestamp_epoch_s < ?
                  AND (
                        timestamp_epoch_s > ?
                        OR (timestamp_epoch_s = ? AND event_id > ?)
                  )
                ORDER BY timestamp_epoch_s, event_id
                LIMIT ?
                """,
                conn,
                params=(event, start_epoch, end_epoch, last_ts, last_ts, last_event_id, chunk_size),
            )
            if chunk.empty:
                break
            _update_stats_with_chunk(event_stats, chunk)
            rows = int(chunk.shape[0])
            total_scanned += rows
            tail = chunk.iloc[-1]
            last_ts = int(tail["timestamp_epoch_s"])
            last_event_id = str(tail["event_id"])

        all_stats[event] = event_stats
        chunk_stats[event] = {
            "chunks": int(event_stats["chunk_count"]),
            "rows_scanned": int(event_stats["row_count"]),
            "window_start_utc": epoch_to_iso(start_epoch),
            "window_end_utc": epoch_to_iso(end_epoch),
        }
        logger.info(
            "Event aggregation complete event=%s rows=%s chunks=%s",
            event,
            event_stats["row_count"],
            event_stats["chunk_count"],
        )
    logger.info("Aggregate event chunks end total_rows_scanned=%s", total_scanned)
    return all_stats, chunk_stats, total_scanned


def _top_label(counter: Counter) -> tuple[str, int]:
    if not counter:
        return "N/A", 0
    label, value = counter.most_common(1)[0]
    return str(label), int(value)


def _peak_hour(counter: Counter) -> tuple[str, int]:
    if not counter:
        return "N/A", 0
    epoch_hour, count = counter.most_common(1)[0]
    return epoch_to_iso(int(epoch_hour)), int(count)


def _render_person_count_section(stats: dict[str, Any]) -> str:
    rows = int(stats["row_count"])
    avg_person_count = (
        stats["person_count_sum"] / stats["person_count_samples"] if stats["person_count_samples"] else 0.0
    )
    peak = stats["person_count_peak"]
    top_cam, top_cam_count = _top_label(stats["cam_counter"])
    top_location, top_loc_count = _top_label(stats["location_counter"])
    peak_hour_utc, peak_hour_count = _peak_hour(stats["hour_counter"])
    lines = [
        f"- Rows analyzed: {rows}",
        f"- Average person_count: {avg_person_count:.2f}",
        f"- Busiest camera: {top_cam} ({top_cam_count} observations)",
        f"- Busiest location: {top_location} ({top_loc_count} observations)",
        f"- Peak activity hour (UTC): {peak_hour_utc} ({peak_hour_count} rows)",
    ]
    if peak:
        lines.append(
            "- Peak person_count: "
            f"{int(peak['value'])} at {peak['timestamp_utc']} (cam {peak['cam_id']}, {peak['location_tag']})"
        )
    return "\n".join(lines)


def _render_flow_section(stats: dict[str, Any], flow_label: str) -> str:
    rows = int(stats["row_count"])
    top_cam, top_cam_count = _top_label(stats["cam_counter"])
    top_location, top_loc_count = _top_label(stats["location_counter"])
    peak_hour_utc, peak_hour_count = _peak_hour(stats["hour_counter"])
    avg_latency = stats["latency_sum"] / stats["latency_samples"] if stats["latency_samples"] else 0.0
    lines = [
        f"- Total {flow_label} events: {rows}",
        f"- Busiest camera: {top_cam} ({top_cam_count} events)",
        f"- Busiest location: {top_location} ({top_loc_count} events)",
        f"- Peak interval (UTC): {peak_hour_utc} ({peak_hour_count} events)",
        f"- Average detector latency: {avg_latency:.2f} ms",
    ]
    if stats["latency_peak"]:
        peak = stats["latency_peak"]
        lines.append(
            "- Highest detector latency: "
            f"{peak['value']:.2f} ms at {peak['timestamp_utc']} (cam {peak['cam_id']}, {peak['location_tag']})"
        )
    return "\n".join(lines)


def _render_unattended_section(stats: dict[str, Any]) -> str:
    rows = int(stats["row_count"])
    top_cam, top_cam_count = _top_label(stats["cam_counter"])
    top_location, top_loc_count = _top_label(stats["location_counter"])
    peak_hour_utc, peak_hour_count = _peak_hour(stats["hour_counter"])
    lines = [
        f"- Unattended object detections: {rows}",
        f"- Top camera hotspot: {top_cam} ({top_cam_count} detections)",
        f"- Top location hotspot: {top_location} ({top_loc_count} detections)",
        f"- Most concentrated hour (UTC): {peak_hour_utc} ({peak_hour_count} detections)",
    ]
    if stats["latency_peak"]:
        peak = stats["latency_peak"]
        lines.append(
            "- Highest detector latency: "
            f"{peak['value']:.2f} ms at {peak['timestamp_utc']} (cam {peak['cam_id']}, {peak['location_tag']})"
        )
    return "\n".join(lines)


def build_event_sections(
    event_stats: dict[str, dict[str, Any]],
) -> dict[str, str]:
    logger.info("Building event sections for %s events", len(event_stats))
    sections: dict[str, str] = {}
    for event_name, stats in event_stats.items():
        if event_name == "person_count":
            sections[event_name] = _render_person_count_section(stats)
        elif event_name == "person_entry":
            sections[event_name] = _render_flow_section(stats, "person entry")
        elif event_name == "person_exit":
            sections[event_name] = _render_flow_section(stats, "person exit")
        elif event_name == "vehicle_entry":
            sections[event_name] = _render_flow_section(stats, "vehicle entry")
        elif event_name == "vehicle_exit":
            sections[event_name] = _render_flow_section(stats, "vehicle exit")
        elif event_name == "unattended_object":
            sections[event_name] = _render_unattended_section(stats)
        else:
            rows = int(stats["row_count"])
            sections[event_name] = f"- Rows analyzed: {rows}"
    return sections


def build_cross_event_block(event_stats: dict[str, dict[str, Any]]) -> str:
    ranked = sorted(
        ((event, int(stats["row_count"])) for event, stats in event_stats.items()),
        key=lambda item: item[1],
        reverse=True,
    )
    if not ranked:
        return "No events matched the selected window."
    dominant_event, dominant_count = ranked[0]
    lines = [
        "Cross-Event Comparison:",
        f"- Dominant event type: {dominant_event} ({dominant_count} rows)",
    ]
    for event, count in ranked:
        lines.append(f"- {event}: {count} rows")
    return "\n".join(lines)
