from __future__ import annotations

import json
import os
from typing import Any

from .aggregation import build_cross_event_block
from .common import AUDIT_LOG_PATH, safe_json_default
from .logging_utils import get_logger
from .planner import compile_with_openai


logger = get_logger(__name__)


def build_summarizer_prompt(
    question: str,
    start_utc: str,
    end_utc: str,
    event_context: list[str],
    sections: dict[str, str],
    cross_event_requested: bool,
) -> str:
    return (
        "You are a CCTV event analytics summarizer.\n"
        "Use ONLY the supplied event-wise stats.\n"
        "Never mix inferences across event types unless cross-event comparison is explicitly requested.\n"
        "Do not infer person_count insights from non-person_count events.\n"
        "Do not infer flow insights from person_count snapshots.\n\n"
        f"Question: {question}\n"
        f"UTC Window: {start_utc} to {end_utc}\n"
        f"Event context: {event_context}\n"
        f"Cross-event comparison requested: {cross_event_requested}\n\n"
        f"Per-event stats: {json.dumps(sections, indent=2)}\n\n"
        "Write concise markdown with one section per event in context."
    )


def llm_summarize(provider: str, prompt: str) -> str:
    logger.info("Running LLM summarizer provider=%s prompt_chars=%s", provider, len(prompt))
    if provider != "openai":
        raise RuntimeError(f"Unsupported summary provider in openai-only mode: {provider}")
    return compile_with_openai(prompt)


def build_summary_text(
    question: str,
    start_utc: str,
    end_utc: str,
    event_context: list[str],
    event_stats: dict[str, dict[str, Any]],
    sections: dict[str, str],
    cross_event_requested: bool,
    summary_provider: str,
) -> str:
    use_llm_summary = os.getenv("USE_LLM_SUMMARY", "0") == "1"
    logger.info(
        "Build summary text use_llm_summary=%s provider=%s event_count=%s",
        use_llm_summary,
        summary_provider,
        len(event_context),
    )
    if use_llm_summary:
        prompt = build_summarizer_prompt(
            question=question,
            start_utc=start_utc,
            end_utc=end_utc,
            event_context=event_context,
            sections=sections,
            cross_event_requested=cross_event_requested,
        )
        try:
            return llm_summarize(summary_provider, prompt).strip()
        except Exception:
            logger.exception("LLM summarization failed; falling back to template summary.")
            pass

    lines: list[str] = []
    lines.append(f"UTC Window: {start_utc} to {end_utc}")
    lines.append(f"Detected event context: {', '.join(event_context)}")
    if len(event_context) == 1:
        only = event_context[0]
        lines.append(f"\n[{only}]")
        lines.append(sections.get(only, "- No matching rows found."))
    else:
        lines.append("\nEvent-wise findings (context separated):")
        for event_name in event_context:
            lines.append(f"\n[{event_name}]")
            lines.append(sections.get(event_name, "- No matching rows found."))
        if cross_event_requested:
            lines.append("")
            lines.append(build_cross_event_block(event_stats))
    return "\n".join(lines).strip()


def build_natural_language_answer(
    question: str,
    start_utc: str,
    end_utc: str,
    event_context: list[str],
    processed_rows: list[dict[str, Any]],
    fallback_summary: str,
    cross_event_requested: bool,
) -> str:
    if not processed_rows:
        return (
            f"Between {start_utc} and {end_utc}, no matching records were found for "
            f"the requested event context ({', '.join(event_context) or 'none'})."
        )

    lines: list[str] = []
    lines.append(
        f"Between {start_utc} and {end_utc}, I analyzed {', '.join(event_context)} and derived SQL-backed insights."
    )

    for row in processed_rows:
        event_name = str(row.get("captured_event", "unknown"))
        total_events = int(row.get("total_events") or 0)
        active_cameras = int(row.get("active_cameras") or 0)
        top_camera = str(row.get("top_camera") or "N/A")
        top_location = str(row.get("top_location") or "N/A")
        peak_hour_utc = str(row.get("peak_hour_utc") or "N/A")
        avg_latency = row.get("avg_latency_ms")
        peak_latency = row.get("peak_latency_ms")
        avg_person_count = row.get("avg_person_count")
        peak_person_count = row.get("peak_person_count")

        base = (
            f"For {event_name}, there were {total_events} events across {active_cameras} cameras; "
            f"the busiest camera was {top_camera}, with activity concentrated at {top_location} "
            f"and a peak hour around {peak_hour_utc}."
        )
        if avg_latency is not None:
            base += f" Average detector latency was {float(avg_latency):.2f} ms"
            if peak_latency is not None:
                base += f", peaking at {float(peak_latency):.2f} ms."
            else:
                base += "."
        if event_name == "person_count" and avg_person_count is not None:
            base += (
                f" Crowd intensity averaged {float(avg_person_count):.2f} "
                f"with a peak person_count of {int(peak_person_count or 0)}."
            )
        lines.append(base)

    if cross_event_requested and len(processed_rows) > 1:
        dominant = max(processed_rows, key=lambda r: int(r.get("total_events") or 0))
        lines.append(
            f"Cross-event comparison: {dominant.get('captured_event')} was the dominant stream "
            f"with {int(dominant.get('total_events') or 0)} events."
        )

    if fallback_summary:
        lines.append(f"Analyst note: {fallback_summary.splitlines()[0]}")

    return " ".join(lines).strip()


def append_audit_log(payload: dict[str, Any]) -> None:
    AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT_LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, default=safe_json_default) + "\n")
    logger.info("Appended audit log entry path=%s", AUDIT_LOG_PATH)
