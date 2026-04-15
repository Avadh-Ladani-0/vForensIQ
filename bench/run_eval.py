"""vForensIQ evaluation harness. Runs bench questions through configured (approach, model) pairs."""
from __future__ import annotations

import argparse
import csv
import json
import re
import sqlite3
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

_PKG_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _PKG_DIR.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from simulator.core import DEFAULT_LOGBASE_PATH, run_scenario

QUESTIONS_DIR = _PKG_DIR / "questions"
RESULTS_DIR = _PKG_DIR / "results"

ALL_LEVELS = ["L1", "L2", "L3", "L4", "L5"]
ALL_APPROACHES = ["b1_sql", "b2_rag_cypher", "b2_rag_community", "b2_rag_hybrid", "b3_aqr"]
ALL_MODELS = ["gpt-4o-mini", "gpt-4o"]


def utc_now_iso_z() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


# ===========================================================================
# Approach invokers (stubs for Sprint 0 — real impls land in Sprints 1-4)
# ===========================================================================

def _build_session_context(question: dict[str, Any]) -> dict[str, Any] | None:
    scenario_name = question.get("scenario")
    if not scenario_name:
        return None
    scenarios_dir = _REPO_ROOT / "simulator" / "scenarios"
    path = scenarios_dir / f"{scenario_name}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return {"scenario_label": scenario_name, "scenario_window": data.get("window_utc")}


def invoke_b1_sql(question: dict[str, Any], model: str) -> dict[str, Any]:
    from llm_sql.b1_service import answer_question
    return answer_question(question["question_text"], model, context=_build_session_context(question))


def invoke_b2_rag_cypher(question: dict[str, Any], model: str) -> dict[str, Any]:
    from llm_rag.cypher_service import answer_question
    return answer_question(question["question_text"], model, context=_build_session_context(question))


def invoke_b2_rag_community(question: dict[str, Any], model: str) -> dict[str, Any]:
    from llm_rag.community_service import answer_question
    return answer_question(question["question_text"], model, context=_build_session_context(question))


def invoke_b2_rag_hybrid(question: dict[str, Any], model: str) -> dict[str, Any]:
    from llm_rag.hybrid_service import answer_question
    return answer_question(question["question_text"], model, context=_build_session_context(question))


def invoke_b3_aqr(question: dict[str, Any], model: str) -> dict[str, Any]:
    from llm_aqr.router import answer_question
    return answer_question(question["question_text"], model, context=_build_session_context(question))


INVOKERS: dict[str, Callable[[dict[str, Any], str], dict[str, Any]]] = {
    "b1_sql": invoke_b1_sql,
    "b2_rag_cypher": invoke_b2_rag_cypher,
    "b2_rag_community": invoke_b2_rag_community,
    "b2_rag_hybrid": invoke_b2_rag_hybrid,
    "b3_aqr": invoke_b3_aqr,
}


# ===========================================================================
# Gold resolution
# ===========================================================================

def _resolve_sql_gold(sql: str, logbase_path: Path) -> Any:
    conn = sqlite3.connect(logbase_path)
    try:
        rows = conn.execute(sql).fetchall()
    finally:
        conn.close()
    # Scalar shortcut: single row, single column -> raw value (typical L1/L2).
    if len(rows) == 1 and len(rows[0]) == 1:
        return rows[0][0]
    return [list(r) for r in rows]


def resolve_gold(question: dict[str, Any], logbase_path: Path) -> Any:
    gold = question["gold"]
    gold_type = gold["type"]
    if gold_type == "sql":
        return _resolve_sql_gold(gold["sql"], logbase_path)
    if gold_type == "structured_facts":
        return gold["facts"]
    if gold_type == "rubric_coverage":
        return {"rubric": gold["rubric"], "threshold": gold.get("coverage_threshold")}
    raise ValueError(f"Unknown gold type: {gold_type!r}")


# ===========================================================================
# Scorers
# ===========================================================================

_NUMBER_RE = re.compile(r"-?\d+(?:\.\d+)?")
# Strip patterns that contain digits but are NOT the answer: ISO dates,
# ISO timestamps, HH:MM clock times, CAM_NN / ABC_NN identifiers.
_DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}(?::\d{2})?Z?)?\b")
_CLOCK_RE = re.compile(r"\b\d{1,2}:\d{2}(?::\d{2})?\b")
_ID_WITH_DIGITS_RE = re.compile(r"\b[A-Za-z]+_\d+\b")

# Spelled-out cardinal numbers (case-insensitive). Covers 0-20 + tens.
_WORD_NUMBERS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40,
    "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
}
_WORD_NUMBER_RE = re.compile(
    r"\b(" + "|".join(_WORD_NUMBERS.keys()) + r")\b",
    flags=re.IGNORECASE,
)


def _extract_number(text: str) -> Optional[float]:
    cleaned = text
    cleaned = _DATE_RE.sub(" ", cleaned)
    cleaned = _CLOCK_RE.sub(" ", cleaned)
    cleaned = _ID_WITH_DIGITS_RE.sub(" ", cleaned)
    cleaned = cleaned.replace(",", "")
    # Try digit form first
    match = _NUMBER_RE.search(cleaned)
    if match:
        return float(match.group(0))
    # Fall back to spelled-out cardinal
    word_match = _WORD_NUMBER_RE.search(cleaned)
    if word_match:
        return float(_WORD_NUMBERS[word_match.group(1).lower()])
    return None


def score_exact_numeric(answer_text: str, gold: Any) -> tuple[Optional[bool], str]:
    extracted = _extract_number(answer_text)
    if extracted is None:
        return False, "no_number_in_answer"
    try:
        gold_value = float(gold)
    except (TypeError, ValueError):
        return None, f"non_numeric_gold ({gold!r})"
    if extracted == gold_value:
        return True, "match"
    return False, f"expected={gold_value} got={extracted}"


def score_numeric_tolerance_1pct(answer_text: str, gold: Any) -> tuple[Optional[bool], str]:
    extracted = _extract_number(answer_text)
    if extracted is None:
        return False, "no_number_in_answer"
    try:
        gold_value = float(gold)
    except (TypeError, ValueError):
        return None, f"non_numeric_gold ({gold!r})"
    tol = abs(gold_value) * 0.01
    if abs(extracted - gold_value) <= tol:
        return True, f"within_1pct (expected={gold_value} got={extracted})"
    return False, f"exceeds_1pct (expected={gold_value} got={extracted})"


def _extract_all_numbers(text: str) -> list[float]:
    cleaned = text
    cleaned = _DATE_RE.sub(" ", cleaned)
    cleaned = _CLOCK_RE.sub(" ", cleaned)
    cleaned = _ID_WITH_DIGITS_RE.sub(" ", cleaned)
    cleaned = cleaned.replace(",", "")
    return [float(m) for m in _NUMBER_RE.findall(cleaned)]


def score_structured_facts(answer_text: str, gold: Any) -> tuple[Optional[bool], str]:
    """L4 scorer. Gold is a dict of fact_name -> expected_value.

    - If expected_value is a string: case-insensitive substring must appear in answer_text.
    - If expected_value is {"value": N, "tolerance": T}: some number extracted from the answer
      (excluding dates / IDs / clock times) must lie within N ± T.
    Passes iff every gold fact is satisfied.
    """
    if not isinstance(gold, dict) or not gold:
        return None, "non_dict_gold"

    answer_lower = answer_text.lower()
    answer_numbers = _extract_all_numbers(answer_text)
    missing: list[str] = []

    for key, expected in gold.items():
        if isinstance(expected, str):
            if expected.lower() not in answer_lower:
                missing.append(f"{key}={expected!r}_not_mentioned")
        elif isinstance(expected, dict) and "value" in expected:
            target = float(expected["value"])
            tol = float(expected.get("tolerance", max(abs(target) * 0.1, 0.5)))
            if not any(abs(n - target) <= tol for n in answer_numbers):
                missing.append(f"{key}={target}+-{tol}_no_match (numbers_seen={answer_numbers[:5]})")
        else:
            missing.append(f"{key}=<unrecognized_shape>")

    if not missing:
        return True, f"all_{len(gold)}_facts_satisfied"
    return False, f"missing={missing[:4]}"


def score_rubric_coverage(answer_text: str, gold: Any) -> tuple[Optional[bool], str]:
    """L5 scorer. LLM-as-judge evaluates whether each rubric item is covered.

    Gold is {"rubric": [strings], "threshold": 0.0..1.0, optional "grounding_required": bool}.
    Uses gpt-4o for the judge call (single call; JSON response covering all rubric items).
    Passes iff (covered_count / total) >= threshold.
    """
    if not isinstance(gold, dict) or "rubric" not in gold:
        return None, "non_rubric_gold"

    rubric = gold["rubric"]
    threshold = float(gold.get("threshold", 0.7))
    if not isinstance(rubric, list) or not rubric:
        return None, "empty_rubric"

    # Lazy import of the OpenAI client wrapper from b1_service (avoids duplicating env-key logic).
    try:
        from llm_sql.b1_service import _get_client, _chat_with_retry
    except Exception as exc:  # pragma: no cover
        return None, f"judge_unavailable: {exc}"

    rubric_block = "\n".join(f"{i+1}. {item}" for i, item in enumerate(rubric))
    judge_system = (
        "You are a strict evaluator checking whether a CCTV analytics answer covers specific facts. "
        "For each rubric item, decide YES if the answer explicitly supports or clearly implies it, "
        "NO otherwise. Do not penalize paraphrasing. Do not reward unrelated information.\n"
        "Return STRICT JSON only, no prose, no markdown:\n"
        '{"coverage": [true|false, ...]}   // one bool per rubric item, in the order given'
    )
    judge_user = (
        f"ANSWER_UNDER_TEST:\n{answer_text}\n\n"
        f"RUBRIC (one bool per item, in order):\n{rubric_block}\n"
    )
    try:
        client = _get_client()
        resp = _chat_with_retry(
            client,
            model="gpt-4o", temperature=0,
             
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": judge_system},
                {"role": "user", "content": judge_user},
            ],
        )
        raw = resp.choices[0].message.content or "{}"
        data = json.loads(raw)
        coverage_list = data.get("coverage", [])
        if not isinstance(coverage_list, list) or len(coverage_list) != len(rubric):
            return None, f"judge_shape_error (got {len(coverage_list)} of {len(rubric)})"
        covered = sum(1 for c in coverage_list if bool(c))
        frac = covered / len(rubric)
        passed = frac >= threshold
        return passed, f"coverage={covered}/{len(rubric)}={frac:.2f} (threshold={threshold})"
    except Exception as exc:
        return None, f"judge_error: {type(exc).__name__}: {exc}"


# Map 2-digit UTC hour strings to all common natural-language forms.
# Used by score_set_match_with_tolerance so a hourly-pattern gold like '01'
# matches 'one AM', '1 a.m.', 'midnight', '01:00', etc.
def _hour_aliases(hour_str: str) -> list[str]:
    if len(hour_str) != 2 or not hour_str.isdigit():
        return [hour_str]
    h = int(hour_str)
    if not (0 <= h <= 23):
        return [hour_str]
    aliases = [hour_str, f"{h}", f"{hour_str}:00", f"{h}:00"]
    if h == 0:
        aliases += ["midnight", "12 am", "12am", "12 a.m."]
    elif h == 12:
        aliases += ["noon", "12 pm", "12pm", "12 p.m."]
    elif h < 12:
        aliases += [f"{h} am", f"{h}am", f"{h} a.m."]
    else:
        aliases += [f"{h - 12} pm", f"{h - 12}pm", f"{h - 12} p.m."]
    return aliases


def score_set_match_with_tolerance(answer_text: str, gold: Any) -> tuple[Optional[bool], str]:
    """L3 scorer: gold is a list of rows (typically GROUP BY result).

    Accept if every gold row's key (non-numeric columns) is mentioned in the answer
    AND every gold numeric value is present in the answer within ±1% tolerance.
    Handles HH-format hour keys via natural-language aliases ('01' matches '1 AM' etc.).
    """
    if not isinstance(gold, list) or not gold:
        return None, "non_list_gold"

    text = answer_text.replace(",", "")
    lower_text = text.lower()
    answer_numbers = [float(m) for m in re.findall(r"-?\d+(?:\.\d+)?", text)]

    missing_keys: list[str] = []
    missing_numbers: list[float] = []
    for row in gold:
        if not isinstance(row, list):
            continue
        for cell in row:
            if isinstance(cell, str):
                aliases = _hour_aliases(cell)
                if not any(a.lower() in lower_text for a in aliases):
                    missing_keys.append(cell)
            elif isinstance(cell, (int, float)):
                cell_val = float(cell)
                tol = max(abs(cell_val) * 0.01, 0.5)
                if not any(abs(n - cell_val) <= tol for n in answer_numbers):
                    missing_numbers.append(cell_val)

    if not missing_keys and not missing_numbers:
        return True, f"all_keys_and_values_matched (rows={len(gold)})"
    detail = []
    if missing_keys:
        detail.append(f"missing_keys={missing_keys[:5]}")
    if missing_numbers:
        detail.append(f"missing_numbers={missing_numbers[:5]}")
    return False, " ".join(detail)


def score_stub(answer_text: str, gold: Any) -> tuple[Optional[bool], str]:
    return None, "scorer_not_implemented"


SCORERS: dict[str, Callable[[str, Any], tuple[Optional[bool], str]]] = {
    "exact_numeric": score_exact_numeric,
    "numeric_tolerance_1pct": score_numeric_tolerance_1pct,
    "set_match_with_tolerance": score_set_match_with_tolerance,
    "structured_facts": score_structured_facts,
    "rubric_coverage": score_rubric_coverage,
}


# ===========================================================================
# Main loop
# ===========================================================================

def load_questions(levels: list[str]) -> list[dict[str, Any]]:
    questions: list[dict[str, Any]] = []
    for level in levels:
        level_dir = QUESTIONS_DIR / level
        if not level_dir.exists():
            continue
        for qfile in sorted(level_dir.glob("q*.json")):
            questions.append(json.loads(qfile.read_text(encoding="utf-8")))
    return questions


def materialize_scenarios(scenario_names: set[str]) -> None:
    for name in sorted(scenario_names):
        print(f"[materialize] {name}")
        run_scenario(name)


def _run_one_cell(
    question: dict[str, Any],
    approach: str,
    model: str,
    gold: Any,
    gold_error: str | None,
) -> dict[str, Any]:
    envelope: dict[str, Any] = {
        "question_id": question["question_id"],
        "level": question["level"],
        "approach": approach,
        "model": model,
        "scenario": question["scenario"],
        "question_text": question["question_text"],
        "gold_value": gold,
    }
    invoker = INVOKERS[approach]
    try:
        envelope.update(invoker(question, model))
        # Graceful-degradation invokers can populate `errors[]` while still
        # returning a (partial) envelope — treat any errors as invocation failure.
        if envelope.get("errors"):
            envelope["invocation_status"] = "error"
        else:
            envelope["invocation_status"] = "ok"
    except NotImplementedError as exc:
        envelope.update({
            "invocation_status": "not_implemented",
            "answer_text": None,
            "errors": [str(exc)],
        })
    except Exception as exc:
        envelope.update({
            "invocation_status": "error",
            "answer_text": None,
            "errors": [f"{type(exc).__name__}: {exc}"],
        })

    scoring_key = question["gold"].get("scoring")
    if gold_error is not None:
        envelope["scoring"] = {"key": scoring_key, "passed": None, "detail": f"gold_unavailable: {gold_error}"}
    elif envelope.get("answer_text"):
        scorer = SCORERS.get(scoring_key, score_stub)
        passed, detail = scorer(envelope["answer_text"], gold)
        envelope["scoring"] = {"key": scoring_key, "passed": passed, "detail": detail}
    else:
        envelope["scoring"] = {
            "key": scoring_key,
            "passed": None,
            "detail": envelope["invocation_status"],
        }
    return envelope


def run_eval(
    approaches: list[str],
    models: list[str],
    levels: list[str],
    run_id: str,
) -> dict[str, Any]:
    run_dir = RESULTS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    questions = load_questions(levels)
    if not questions:
        print(f"No questions found under levels={levels}", file=sys.stderr)
        manifest = {"run_id": run_id, "started_at_utc": utc_now_iso_z(), "question_count": 0}
        (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        return manifest

    materialize_scenarios({q["scenario"] for q in questions})

    manifest = {
        "run_id": run_id,
        "started_at_utc": utc_now_iso_z(),
        "approaches": approaches,
        "models": models,
        "levels": levels,
        "question_count": len(questions),
        "total_cells": len(questions) * len(approaches) * len(models),
    }

    comparison_rows: list[dict[str, Any]] = []
    for q in questions:
        try:
            gold = resolve_gold(q, DEFAULT_LOGBASE_PATH)
            gold_error: str | None = None
        except Exception as exc:
            print(f"[gold-error] {q['question_id']}: {exc}", file=sys.stderr)
            gold, gold_error = None, str(exc)

        for approach in approaches:
            for model in models:
                envelope = _run_one_cell(q, approach, model, gold, gold_error)

                cfg_key = f"{approach}__{model}"
                cfg_dir = run_dir / "by_config" / cfg_key / q["level"]
                cfg_dir.mkdir(parents=True, exist_ok=True)
                (cfg_dir / f"{q['question_id']}.json").write_text(
                    json.dumps(envelope, indent=2) + "\n", encoding="utf-8",
                )

                comparison_rows.append({
                    "approach": approach,
                    "model": model,
                    "level": q["level"],
                    "question_id": q["question_id"],
                    "scoring": envelope["scoring"]["key"],
                    "invocation_status": envelope["invocation_status"],
                    "passed": "" if envelope["scoring"]["passed"] is None else str(envelope["scoring"]["passed"]),
                    "detail": envelope["scoring"]["detail"],
                })

    manifest["finished_at_utc"] = utc_now_iso_z()
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    csv_path = run_dir / "comparison.csv"
    fieldnames = [
        "approach", "model", "level", "question_id",
        "scoring", "invocation_status", "passed", "detail",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(comparison_rows)

    return manifest


def _summarize(manifest: dict[str, Any]) -> None:
    run_dir = RESULTS_DIR / manifest["run_id"]
    print()
    print(f"== Run: {manifest['run_id']} ==")
    print(f"Questions:   {manifest.get('question_count', 0)}")
    print(f"Total cells: {manifest.get('total_cells', 0)}")
    print(f"Results:     {run_dir}")

    csv_path = run_dir / "comparison.csv"
    if not csv_path.exists():
        return
    with csv_path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    by_cfg: dict[tuple[str, str], Counter] = {}
    for row in rows:
        key = (row["approach"], row["model"])
        c = by_cfg.setdefault(key, Counter())
        if row["invocation_status"] != "ok":
            c["not_impl_or_err"] += 1
        elif row["passed"] == "True":
            c["pass"] += 1
        elif row["passed"] == "False":
            c["fail"] += 1
        else:
            c["unscored"] += 1
    print()
    print(f"  {'approach':<22} {'model':<14} pass  fail  unscored  not_impl/err")
    for (approach, model), c in sorted(by_cfg.items()):
        print(f"  {approach:<22} {model:<14} {c['pass']:>4}  {c['fail']:>4}  {c['unscored']:>8}  {c['not_impl_or_err']:>12}")


def _parse_multi(value: str, universe: list[str]) -> list[str]:
    value = value.strip()
    if value.lower() == "all":
        return universe[:]
    selected = [v.strip() for v in value.split(",") if v.strip()]
    for v in selected:
        if v not in universe:
            raise SystemExit(f"Invalid value: {v!r}. Allowed: {universe} or 'all'")
    return selected


def main() -> int:
    parser = argparse.ArgumentParser(description="vForensIQ bench runner")
    parser.add_argument("--approach", default="all",
                        help=f"comma-list or 'all' from: {','.join(ALL_APPROACHES)}")
    parser.add_argument("--model", default="all",
                        help=f"comma-list or 'all' from: {','.join(ALL_MODELS)}")
    parser.add_argument("--level", default="all",
                        help=f"comma-list or 'all' from: {','.join(ALL_LEVELS)}")
    parser.add_argument("--run-id", default=None, help="Run folder name (default: UTC timestamp)")
    args = parser.parse_args()

    approaches = _parse_multi(args.approach, ALL_APPROACHES)
    models = _parse_multi(args.model, ALL_MODELS)
    levels = _parse_multi(args.level, ALL_LEVELS)

    run_id = args.run_id or datetime.now(timezone.utc).strftime("run_%Y%m%dT%H%M%SZ")
    manifest = run_eval(approaches, models, levels, run_id)
    _summarize(manifest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
