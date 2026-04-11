from __future__ import annotations

import re
from typing import Iterable

from .logging_utils import get_logger


logger = get_logger(__name__)


def extract_event_filter_from_sql(sql: str, event_types: list[str]) -> list[str]:
    found: list[str] = []
    lower = sql.lower()
    eq_matches = re.findall(r"captured_event\s*=\s*'([^']+)'", lower)
    in_matches = re.findall(r"captured_event\s+in\s*\(([^)]*)\)", lower)
    for match in eq_matches:
        found.append(match.strip())
    for blob in in_matches:
        values = [item.strip().strip("'").strip('"') for item in blob.split(",") if item.strip()]
        found.extend(values)
    return [event for event in event_types if event in found]


def extract_event_mentions(question: str, event_types: list[str]) -> list[str]:
    lower = question.lower()
    explicit: list[str] = []
    aliases = {
        "person_count": ["person_count", "headcount", "head count", "crowd count"],
        "person_entry": ["person_entry", "person entry", "people entered"],
        "person_exit": ["person_exit", "person exit", "people exited"],
        "vehicle_entry": ["vehicle_entry", "vehicle entry", "car entry", "vehicle arrived"],
        "vehicle_exit": ["vehicle_exit", "vehicle exit", "car exit", "vehicle departed"],
        "unattended_object": ["unattended_object", "unattended object", "left object", "suspicious object"],
    }
    for event, words in aliases.items():
        if any(word in lower for word in words):
            explicit.append(event)
    return [event for event in event_types if event in explicit]


def is_cross_event_request(question: str) -> bool:
    lower = question.lower()
    keywords = [
        "compare",
        "comparison",
        "versus",
        "vs ",
        "difference",
        "across events",
        "between events",
    ]
    return any(keyword in lower for keyword in keywords)


def resolve_event_context(
    question: str,
    sql: str,
    available_events: Iterable[str],
    event_types: list[str],
) -> tuple[list[str], str, bool]:
    all_events = [event for event in event_types if event in set(available_events)] or event_types[:]

    explicit = extract_event_mentions(question, event_types)
    if explicit:
        logger.info("Event context resolved from explicit NL mention: %s", explicit)
        return explicit, "explicit_nl", is_cross_event_request(question)

    from_sql = extract_event_filter_from_sql(sql, event_types)
    if from_sql:
        logger.info("Event context resolved from SQL filter: %s", from_sql)
        return from_sql, "sql_filter", is_cross_event_request(question)

    lower = question.lower()
    if "person_count" in lower or "headcount" in lower or "head count" in lower:
        logger.info("Event context resolved from metric inference: person_count")
        return ["person_count"], "metric_inference", is_cross_event_request(question)

    logger.info("Event context resolved from fallback all events: %s", all_events)
    return all_events, "fallback_all_events", is_cross_event_request(question)
