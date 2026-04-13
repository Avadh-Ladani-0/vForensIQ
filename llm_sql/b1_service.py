"""B1 NL->SQL two-step approach (standalone).

Step 1: LLM #1 generates a SQLite SELECT against the contract-v2 `events` table.
Step 2: validate + execute the SQL.
Step 3: LLM #2 synthesizes a plain-language answer from the rows.

Does NOT import from the legacy prototype modules (service.py, planner.py,
aggregation.py, etc.). Reads the logbase directly at the path simulator writes to.
"""
from __future__ import annotations

import os
import re
import sqlite3
import time
from pathlib import Path
from typing import Any, Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from openai import OpenAI, APIConnectionError, APITimeoutError, RateLimitError


_PKG_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _PKG_DIR.parent
DEFAULT_LOGBASE_PATH = _REPO_ROOT / "runtime" / "vforensiq_logbase.db"


SCHEMA_PROMPT = """\
You are writing SQL for a CCTV event logbase in SQLite. There is ONE table:

CREATE TABLE events (
    event_id          TEXT PRIMARY KEY,     -- sha1 hash; use for citations
    timestamp_utc     TEXT NOT NULL,         -- ISO 8601 UTC ending in 'Z'
    timestamp_epoch_s INTEGER NOT NULL,      -- UTC epoch seconds; fastest for range filters
    camera_id         TEXT NOT NULL,         -- 'CAM_01' .. 'CAM_99'
    event_type        TEXT NOT NULL,         -- one of: 'person_entry','person_exit','car_entry','car_exit','crowd'
    object_id         TEXT,                   -- tracker id for entry/exit; NULL for crowd
    confidence        REAL NOT NULL,          -- [0.0, 1.0]
    camera_location   TEXT NOT NULL,          -- e.g. 'Gate_MainEntrance', 'DemoBooth_NVIDIA', 'KeynoteHall_Stage'
    head_count        INTEGER NOT NULL,       -- persons in frame; 0 for non-crowd events
    ingested_at_utc   TEXT NOT NULL
);

Semantic rules:
- 'crowd' events are emitted periodically at 1 Hz per crowd camera; head_count is meaningful ONLY for them.
- entry/exit events (person_entry, person_exit, car_entry, car_exit) are sparse and event-driven; head_count=0 always.
- object_id is set for entry/exit, NULL for crowd.
- Time filters: timestamp_utc supports lexicographic comparison because ISO-8601 Z format sorts chronologically.
  Example: timestamp_utc >= '2025-12-08T00:00:00Z' AND timestamp_utc < '2025-12-09T00:00:00Z'
- SQLite dialect. Use strftime('%H', timestamp_epoch_s, 'unixepoch') for UTC hour bucketing; do NOT use HOUR()/EXTRACT/DATE_TRUNC.

DATASET SCOPE:
- The data is HISTORICAL (already captured), not live. Do NOT use DATE('now'),
  CURRENT_TIMESTAMP, or relative date functions.
- When the user asks about "today", "yesterday", "the day", "this week", or omits
  any date, query across the full available data (no time filter, OR derive
  bounds from the data itself using MIN/MAX(timestamp_epoch_s) in a CTE).
- Users will typically NOT use exact field names. Map informal terms using your
  knowledge: "parking lot" -> camera_location LIKE '%Parking%'; "the main gate"
  -> '%MainEntrance%'; "NVIDIA booth" -> '%NVIDIA%'; "cars" -> car_entry/car_exit;
  "people walking in" -> person_entry; "crowds"/"busy"/"packed" -> head_count
  for crowd events; "rush" -> peak hours by event count or head_count.

Hard constraints on your output:
- Return ONE valid SELECT (may begin with WITH for CTEs). No INSERT/UPDATE/DELETE/DROP/ALTER/CREATE/ATTACH/PRAGMA.
- Must reference the `events` table.
- No multiple statements. No trailing semicolon required.
- Return only the SQL. No prose. No markdown fences. No bullet lists. No explanations.

CRITICAL: Even if the user question asks for a briefing, summary, narrative, timeline, security report, or comparison, your ONLY job here is to return SQL that retrieves the RELEVANT ROWS. A separate downstream step turns the rows into narrative text. Do NOT write the narrative yourself. Do NOT output bullet points. Do NOT output prose.

For multi-aspect narrative questions, return a single SQL that unions or CTE-combines the data needed (e.g., hourly aggregates per camera, peak-hour identification, per-location summaries). Use GROUP BY, strftime for hour bucketing, and UNION ALL where needed to get all relevant aspects in one result set.
"""


ANSWER_SYNTH_PROMPT = """\
You are a CCTV forensic analyst. Given a user question and the rows returned by the SQL query, write a concise, direct, plain-language answer.

Rules:
- Be specific: quote numbers exactly, cite camera_location / camera_id / timestamp_utc from the rows.
- When a single integer answers the question, state it plainly (e.g., "There were 223 car_entry events...").
- Do not speculate beyond the rows.
- Do not repeat the SQL. Do not mention that you ran a query.
- Keep it to 1-3 sentences unless the question explicitly asks for a detailed summary.
"""


_DISALLOWED_KEYWORDS = (
    r"\binsert\b",
    r"\bupdate\b",
    r"\bdelete\b",
    r"\bdrop\b",
    r"\balter\b",
    r"\bcreate\b",
    r"\battach\b",
    r"\bdetach\b",
    r"\bpragma\b",
    r"\breplace\b",
    r"\btruncate\b",
)


def _strip_code_fence(text: str) -> str:
    m = re.search(r"```(?:sql)?\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return text.strip()


def validate_sql(sql: str) -> str:
    cleaned = sql.strip().rstrip(";").strip()
    if not cleaned:
        raise ValueError("Empty SQL")
    lower = cleaned.lower()
    if not (lower.startswith("select") or lower.startswith("with")):
        raise ValueError("SQL must start with SELECT or WITH")
    if ";" in cleaned:
        raise ValueError("Multiple statements not allowed")
    for pat in _DISALLOWED_KEYWORDS:
        if re.search(pat, lower):
            raise ValueError(f"Disallowed keyword in SQL: {pat}")
    if not re.search(r"\bevents\b", lower):
        raise ValueError("SQL must reference the events table")
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


_TRANSIENT_ERRORS = (APIConnectionError, APITimeoutError, RateLimitError)


def _chat_with_retry(client: OpenAI, **kwargs: Any) -> Any:
    """Retry chat.completions.create up to 2 times on transient network/rate errors."""
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            return client.chat.completions.create(**kwargs)
        except _TRANSIENT_ERRORS as exc:
            last_exc = exc
            if attempt < 2:
                time.sleep(1.5 * (attempt + 1))  # 1.5s, 3s backoff
    assert last_exc is not None
    raise last_exc


def generate_sql(question_text: str, model: str, client: OpenAI) -> tuple[str, dict[str, Any]]:
    resp = _chat_with_retry(
        client,
        model=model,
        temperature=0,
        messages=[
            {"role": "system", "content": SCHEMA_PROMPT},
            {"role": "user", "content": question_text},
        ],
    )
    raw = resp.choices[0].message.content or ""
    sql = _strip_code_fence(raw)
    usage = {
        "stage": "sql_gen",
        "model": model,
        "prompt_tokens": resp.usage.prompt_tokens if resp.usage else 0,
        "completion_tokens": resp.usage.completion_tokens if resp.usage else 0,
    }
    return sql, usage


def execute_sql(sql: str, logbase_path: Path) -> tuple[list[str], list[list[Any]]]:
    conn = sqlite3.connect(logbase_path)
    try:
        cursor = conn.execute(sql)
        columns = [d[0] for d in cursor.description] if cursor.description else []
        rows = [list(r) for r in cursor.fetchall()]
    finally:
        conn.close()
    return columns, rows


def synthesize_answer(
    question_text: str,
    sql: str,
    columns: list[str],
    rows: list[list[Any]],
    model: str,
    client: OpenAI,
) -> tuple[str, dict[str, Any]]:
    rows_for_prompt = rows[:100]
    preview_lines = [f"Columns: {columns}", f"Row count returned: {len(rows)}", "Rows (up to first 100):"]
    for r in rows_for_prompt:
        preview_lines.append(f"  {r}")
    user_content = (
        f"User question:\n{question_text}\n\n"
        f"SQL executed:\n{sql}\n\n"
        + "\n".join(preview_lines)
    )
    resp = _chat_with_retry(
        client,
        model=model,
        temperature=0,
        messages=[
            {"role": "system", "content": ANSWER_SYNTH_PROMPT},
            {"role": "user", "content": user_content},
        ],
    )
    answer = (resp.choices[0].message.content or "").strip()
    usage = {
        "stage": "answer_synth",
        "model": model,
        "prompt_tokens": resp.usage.prompt_tokens if resp.usage else 0,
        "completion_tokens": resp.usage.completion_tokens if resp.usage else 0,
    }
    return answer, usage


def repair_sql(
    question_text: str,
    bad_sql: str,
    error_msg: str,
    model: str,
    client: OpenAI,
) -> tuple[str, dict[str, Any]]:
    """One-shot retry: feed the error back to the LLM and ask for corrected SQL."""
    repair_user = (
        f"Your previous SQL failed to execute.\n\n"
        f"User question:\n{question_text}\n\n"
        f"Previous SQL:\n{bad_sql}\n\n"
        f"SQLite error:\n{error_msg}\n\n"
        f"Return a corrected SQL SELECT. Output only the SQL, no prose, no markdown."
    )
    resp = _chat_with_retry(
        client,
        model=model,
        temperature=0,
        messages=[
            {"role": "system", "content": SCHEMA_PROMPT},
            {"role": "user", "content": repair_user},
        ],
    )
    raw = resp.choices[0].message.content or ""
    sql = _strip_code_fence(raw)
    usage = {
        "stage": "sql_repair",
        "model": model,
        "prompt_tokens": resp.usage.prompt_tokens if resp.usage else 0,
        "completion_tokens": resp.usage.completion_tokens if resp.usage else 0,
    }
    return sql, usage


def _contextualize(question_text: str, context: Optional[dict[str, Any]]) -> str:
    """Prepend session context (scenario window etc.) to the question, mirroring
    how a real CCTV UI would carry session state into an LLM call.
    Without context, abstract questions like 'how many cars came in today' are
    ambiguous when the logbase contains multiple historical days."""
    if not context:
        return question_text
    win = context.get("scenario_window") or {}
    start = win.get("start")
    end = win.get("end")
    label = context.get("scenario_label", "the dataset")
    if not (start and end):
        return question_text
    return (
        f"[SESSION CONTEXT: The user is currently viewing '{label}', which covers "
        f"events from {start} to {end} (UTC). Interpret references to 'today', "
        f"'yesterday', 'the day', 'this week', 'now', or any unspecified time as "
        f"referring to this window. Always include time bounds in your SQL.]\n\n"
        f"USER QUESTION: {question_text}"
    )


def answer_question(
    question_text: str,
    model: str,
    logbase_path: Path = DEFAULT_LOGBASE_PATH,
    context: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Run the two-step pipeline on one question. Returns the unified envelope fields.

    `context` (optional) is a session-context dict consumed by `_contextualize`,
    typically `{"scenario_label": str, "scenario_window": {"start": iso, "end": iso}}`.
    """
    t_start = time.time()
    errors: list[str] = []
    llm_calls: list[dict[str, Any]] = []
    sql = ""
    columns: list[str] = []
    rows: list[list[Any]] = []
    answer_text: Optional[str] = None

    contextualized_question = _contextualize(question_text, context)

    try:
        client = _get_client()
        sql_raw, usage1 = generate_sql(contextualized_question, model, client)
        llm_calls.append(usage1)
        sql = validate_sql(sql_raw)
        try:
            columns, rows = execute_sql(sql, logbase_path)
        except sqlite3.OperationalError as exec_err:
            # One-shot repair: feed the error back to the LLM for a corrected SQL.
            repaired_raw, usage_repair = repair_sql(contextualized_question, sql, str(exec_err), model, client)
            llm_calls.append(usage_repair)
            sql = validate_sql(repaired_raw)
            columns, rows = execute_sql(sql, logbase_path)
        answer_text, usage2 = synthesize_answer(question_text, sql, columns, rows, model, client)
        llm_calls.append(usage2)
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
            {"type": "sql_query", "sql": sql, "row_count": len(rows)},
        ],
        "duration_ms": duration_ms,
        "llm_calls": llm_calls,
        "errors": errors,
    }
