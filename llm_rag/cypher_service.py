"""B2 Graph-RAG (Cypher variant): NL -> Cypher -> Neo4j -> plain-language answer.

Two-step pipeline mirroring llm_sql.b1_service:
  1. LLM generates one read-only Cypher query against the locked graph schema
  2. Validate (no mutation keywords; must RETURN) + execute
  3. On error: one-shot Cypher repair with the error fed back to the LLM
  4. LLM synthesizes plain-language answer from the rows
"""
from __future__ import annotations

import os
import re
import time
from pathlib import Path
from typing import Any, Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from neo4j import GraphDatabase
from neo4j.exceptions import CypherSyntaxError, ClientError, DatabaseError
from openai import OpenAI, APIConnectionError, APITimeoutError, RateLimitError

from .common import NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER


SCHEMA_PROMPT = """\
You are writing Cypher for a Neo4j knowledge graph of CCTV events.

Graph schema (node labels and properties):
  (:Camera {camera_id, camera_location, mode})           -- mode is 'entry_exit' or 'crowd'
  (:Location {name})                                      -- e.g. 'Gate_MainEntrance', 'DemoBooth_NVIDIA'
  (:EventType {name})                                     -- one of: person_entry, person_exit, car_entry, car_exit, crowd
  (:Hour {hour_utc, date})                                -- hour_utc is 'YYYY-MM-DDTHH:00:00Z', date is 'YYYY-MM-DD'
  (:Event {event_id, event_type, timestamp_utc, confidence, object_id})
         -- One node per ENTRY/EXIT event only (NOT crowd)
  (:CrowdHour {crowd_hour_id, camera_id, camera_location, hour_utc, avg_hc, peak_hc, event_count})
         -- One node per camera-hour for crowd cameras (avg_hc, peak_hc, event_count aggregated from per-second crowd samples)

Relationships:
  (:Event)-[:DETECTED_BY]->(:Camera)
  (:Camera)-[:LOCATED_AT]->(:Location)
  (:Event)-[:OCCURRED_IN]->(:Hour)
  (:Event)-[:IS_TYPE]->(:EventType)
  (:CrowdHour)-[:AT_CAMERA]->(:Camera)
  (:CrowdHour)-[:DURING]->(:Hour)

Critical semantics:
- Entry/exit events are represented as :Event nodes with event_type in (person_entry, person_exit, car_entry, car_exit).
- Crowd samples are aggregated to HOURLY :CrowdHour nodes (NOT per-event :Event nodes). Use avg_hc for average head_count, peak_hc for max. Each :CrowdHour has a property `event_count` = number of underlying 1 Hz crowd samples in that hour (usually 3600 for a full hour).
- To count entry/exit events: MATCH (e:Event {event_type: 'car_entry'})-[:DETECTED_BY]->(:Camera {camera_location: 'Gate_X'})
- To get crowd statistics: MATCH (ch:CrowdHour {camera_location: 'DemoBooth_NVIDIA'})
- Time filtering on :Event uses e.timestamp_utc (ISO-8601 Z, lexicographic order = chronological). Example:
    WHERE e.timestamp_utc >= '2025-12-08T00:00:00Z' AND e.timestamp_utc < '2025-12-09T00:00:00Z'
- Time filtering on :CrowdHour uses ch.hour_utc:
    WHERE ch.hour_utc >= '2025-12-08T00:00:00Z' AND ch.hour_utc < '2025-12-09T00:00:00Z'

CRUCIAL --- Including crowd events in totals and camera activity:

Crowd samples ARE events in the user's mental model. The 1 Hz sampled crowd data is NOT stored as :Event nodes (to keep the graph small); it is compressed into :CrowdHour.event_count. Therefore, whenever the user asks about TOTAL EVENTS or ACTIVE CAMERAS or ALL EVENT TYPES, you MUST include crowd data by reading from :CrowdHour, not only from :Event.

Concrete patterns you MUST use:

1) "How many TOTAL events on day X?" --- sum both :Event and :CrowdHour.event_count:
    CALL {
      MATCH (e:Event) WHERE e.timestamp_utc >= '2025-12-08T00:00:00Z' AND e.timestamp_utc < '2025-12-09T00:00:00Z'
      RETURN count(e) AS n
      UNION ALL
      MATCH (ch:CrowdHour) WHERE ch.hour_utc >= '2025-12-08T00:00:00Z' AND ch.hour_utc < '2025-12-09T00:00:00Z'
      RETURN sum(ch.event_count) AS n
    }
    RETURN sum(n) AS total_events

2) "How many DISTINCT CAMERAS had activity in window W?" --- union the cameras from both paths:
    CALL {
      MATCH (e:Event)-[:DETECTED_BY]->(c:Camera) WHERE e.timestamp_utc >= 'W_start' AND e.timestamp_utc < 'W_end'
      RETURN c.camera_id AS cid
      UNION
      MATCH (ch:CrowdHour)-[:AT_CAMERA]->(c:Camera) WHERE ch.hour_utc >= 'W_start' AND ch.hour_utc < 'W_end'
      RETURN c.camera_id AS cid
    }
    RETURN count(DISTINCT cid) AS active_cameras

3) "Counts BY event_type" (including crowd) --- union both sources, grouping last:
    CALL {
      MATCH (e:Event) WHERE e.timestamp_utc >= 'W_start' AND e.timestamp_utc < 'W_end'
      RETURN e.event_type AS event_type, count(*) AS n
      UNION ALL
      MATCH (ch:CrowdHour) WHERE ch.hour_utc >= 'W_start' AND ch.hour_utc < 'W_end'
      RETURN 'crowd' AS event_type, sum(ch.event_count) AS n
    }
    RETURN event_type, sum(n) AS count ORDER BY event_type

4) "Count of crowd samples at location L" --- use :CrowdHour.event_count, NEVER try to match :Event for crowd:
    MATCH (ch:CrowdHour {camera_location: 'L'})
    WHERE ch.hour_utc >= 'W_start' AND ch.hour_utc < 'W_end'
    RETURN sum(ch.event_count) AS crowd_samples

5) "Hourly breakdown of ALL events" --- union hourly :Event counts with :CrowdHour.event_count, grouping by hour:
    CALL {
      MATCH (e:Event) WHERE e.timestamp_utc >= 'W_start' AND e.timestamp_utc < 'W_end'
      WITH substring(e.timestamp_utc, 0, 13) + ':00:00Z' AS hour, count(*) AS n
      RETURN hour, n
      UNION ALL
      MATCH (ch:CrowdHour) WHERE ch.hour_utc >= 'W_start' AND ch.hour_utc < 'W_end'
      RETURN ch.hour_utc AS hour, ch.event_count AS n
    }
    RETURN hour, sum(n) AS count ORDER BY hour

When the user's question is ONLY about entry/exit flow (e.g., "how many cars entered?", "person flow at Gate_X"), restrict to :Event alone --- do NOT include :CrowdHour. When the question is ONLY about crowd density (e.g., "how packed was the booth?"), read :CrowdHour alone.

Use UNION vs UNION ALL carefully: UNION deduplicates rows; UNION ALL preserves duplicates. For counts you almost always want UNION ALL followed by a final sum()/count().

DATASET SCOPE:
- Data is historical (already captured). Do NOT use date() / datetime() for 'now'.
- When the user omits a date or says 'today'/'the day', respect any time bounds given in [SESSION CONTEXT].
- Users often use informal terms. Map them with your knowledge:
    "parking lot" -> camera_location CONTAINS 'Parking'
    "main gate" -> CONTAINS 'MainEntrance'
    "NVIDIA booth" -> CONTAINS 'NVIDIA'
    "cars" -> event_type in ['car_entry','car_exit']
    "people walking in" -> event_type='person_entry'
    "crowds"/"busy"/"packed" -> :CrowdHour nodes (avg_hc, peak_hc)
    "rush" -> peak hours by COUNT or SUM

Hard constraints on your output:
- Return ONE valid read-only Cypher query. No CREATE / MERGE / DELETE / DETACH / SET / REMOVE / DROP / LOAD CSV / CALL dbms.
- Must contain RETURN.
- Return only the Cypher. No prose. No markdown fences. No bullet lists.
- Even if the question asks for a narrative/briefing, your ONLY job here is to return Cypher that retrieves the relevant rows. A downstream step turns rows into prose.
- For multi-aspect narrative questions, union/collect data needed (hourly aggregates, per-location stats, etc.) into one result set so synthesis has everything.
"""


ANSWER_SYNTH_PROMPT = """\
You are a CCTV forensic analyst. Given a user question and rows returned by the Cypher query, write a concise, direct, plain-language answer.

Rules:
- Quote numbers exactly from the rows.
- Cite camera_location / camera_id / timestamp_utc / hour_utc when grounding a claim.
- When a single value answers the question, state it plainly ("There were 223 car_entry events...").
- Do not speculate beyond the rows.
- Do not repeat the Cypher. Do not mention that you ran a query.
- Keep it to 1-3 sentences unless the question asks for a detailed summary.
"""


_DISALLOWED_KEYWORDS = (
    r"\bcreate\b",
    r"\bmerge\b",
    r"\bdelete\b",
    r"\bdetach\b",
    r"\bset\b",
    r"\bremove\b",
    r"\bdrop\b",
    r"\bload\s+csv\b",
)


def _strip_code_fence(text: str) -> str:
    m = re.search(r"```(?:cypher|neo4j)?\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return text.strip()


def validate_cypher(cypher: str) -> str:
    cleaned = cypher.strip().rstrip(";").strip()
    if not cleaned:
        raise ValueError("Empty Cypher")
    lower = cleaned.lower()
    if not re.search(r"\breturn\b", lower):
        raise ValueError("Cypher must contain RETURN")
    for pat in _DISALLOWED_KEYWORDS:
        if re.search(pat, lower):
            raise ValueError(f"Disallowed Cypher keyword: {pat}")
    if ";" in cleaned:
        raise ValueError("Multiple statements not allowed")
    return cleaned


def _get_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        env_path = Path(".env")
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("OPENAI_API_KEY"):
                    _, v = line.split("=", 1)
                    api_key = v.strip().strip('"').strip("'")
                    break
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    return OpenAI(api_key=api_key)


_TRANSIENT = (APIConnectionError, APITimeoutError, RateLimitError)


def _chat_with_retry(client: OpenAI, **kwargs: Any) -> Any:
    last: Exception | None = None
    for attempt in range(3):
        try:
            return client.chat.completions.create(**kwargs)
        except _TRANSIENT as exc:
            last = exc
            if attempt < 2:
                time.sleep(1.5 * (attempt + 1))
    assert last is not None
    raise last


def generate_cypher(question: str, model: str, client: OpenAI) -> tuple[str, dict]:
    resp = _chat_with_retry(
        client, model=model,  
        messages=[
            {"role": "system", "content": SCHEMA_PROMPT},
            {"role": "user", "content": question},
        ],
    )
    raw = resp.choices[0].message.content or ""
    cypher = _strip_code_fence(raw)
    usage = {
        "stage": "cypher_gen", "model": model,
        "prompt_tokens": resp.usage.prompt_tokens if resp.usage else 0,
        "completion_tokens": resp.usage.completion_tokens if resp.usage else 0,
    }
    return cypher, usage


def repair_cypher(question: str, bad: str, err: str, model: str, client: OpenAI) -> tuple[str, dict]:
    user = (
        f"Your previous Cypher failed.\n\nUser question:\n{question}\n\n"
        f"Previous Cypher:\n{bad}\n\nNeo4j error:\n{err}\n\n"
        "Return a corrected read-only Cypher. Output only Cypher, no prose."
    )
    resp = _chat_with_retry(
        client, model=model,  
        messages=[
            {"role": "system", "content": SCHEMA_PROMPT},
            {"role": "user", "content": user},
        ],
    )
    raw = resp.choices[0].message.content or ""
    cypher = _strip_code_fence(raw)
    usage = {
        "stage": "cypher_repair", "model": model,
        "prompt_tokens": resp.usage.prompt_tokens if resp.usage else 0,
        "completion_tokens": resp.usage.completion_tokens if resp.usage else 0,
    }
    return cypher, usage


def execute_cypher(cypher: str) -> tuple[list[str], list[list[Any]]]:
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    try:
        with driver.session() as session:
            result = session.run(cypher)
            records = list(result)
            keys = result.keys() if records else []
            rows = [[_sanitize(r.get(k)) for k in keys] for r in records]
            return list(keys), rows
    finally:
        driver.close()


def _sanitize(val: Any) -> Any:
    """Neo4j returns Node/Relationship objects; coerce to primitives for JSON output."""
    if hasattr(val, "items"):
        return dict(val)
    if isinstance(val, list):
        return [_sanitize(v) for v in val]
    return val


def synthesize_answer(question: str, cypher: str, columns: list[str], rows: list[list[Any]],
                      model: str, client: OpenAI) -> tuple[str, dict]:
    preview = rows[:100]
    lines = [f"Columns: {columns}", f"Row count returned: {len(rows)}", "Rows (up to first 100):"]
    for r in preview:
        lines.append(f"  {r}")
    user = (
        f"User question:\n{question}\n\n"
        f"Cypher executed:\n{cypher}\n\n" + "\n".join(lines)
    )
    resp = _chat_with_retry(
        client, model=model,  
        messages=[
            {"role": "system", "content": ANSWER_SYNTH_PROMPT},
            {"role": "user", "content": user},
        ],
    )
    answer = (resp.choices[0].message.content or "").strip()
    usage = {
        "stage": "answer_synth", "model": model,
        "prompt_tokens": resp.usage.prompt_tokens if resp.usage else 0,
        "completion_tokens": resp.usage.completion_tokens if resp.usage else 0,
    }
    return answer, usage


def _contextualize(question: str, context: Optional[dict]) -> str:
    if not context:
        return question
    win = context.get("scenario_window") or {}
    start, end = win.get("start"), win.get("end")
    label = context.get("scenario_label", "the dataset")
    if not (start and end):
        return question
    return (
        f"[SESSION CONTEXT: The user is viewing '{label}', covering events from "
        f"{start} to {end} (UTC). Interpret references to 'today'/'yesterday'/'the day' "
        f"as this window. Always include time bounds in your Cypher.]\n\n"
        f"USER QUESTION: {question}"
    )


def answer_question(
    question: str,
    model: str,
    context: Optional[dict] = None,
) -> dict:
    t_start = time.time()
    errors: list[str] = []
    llm_calls: list[dict] = []
    cypher = ""
    columns: list[str] = []
    rows: list[list[Any]] = []
    answer_text: Optional[str] = None

    contextualized = _contextualize(question, context)

    try:
        client = _get_client()
        cypher_raw, u1 = generate_cypher(contextualized, model, client)
        llm_calls.append(u1)
        cypher = validate_cypher(cypher_raw)
        try:
            columns, rows = execute_cypher(cypher)
        except (CypherSyntaxError, ClientError, DatabaseError) as exec_err:
            repaired, ur = repair_cypher(contextualized, cypher, str(exec_err), model, client)
            llm_calls.append(ur)
            cypher = validate_cypher(repaired)
            columns, rows = execute_cypher(cypher)
        answer_text, u2 = synthesize_answer(question, cypher, columns, rows, model, client)
        llm_calls.append(u2)
    except Exception as exc:
        errors.append(f"{type(exc).__name__}: {exc}")

    duration_ms = int((time.time() - t_start) * 1000)
    return {
        "answer_text": answer_text,
        "structured_answer": {
            "columns": columns,
            "rows": rows[:100],
            "total_rows": len(rows),
        },
        "citations": [
            {"type": "cypher_query", "cypher": cypher, "row_count": len(rows)},
        ],
        "duration_ms": duration_ms,
        "llm_calls": llm_calls,
        "errors": errors,
    }
