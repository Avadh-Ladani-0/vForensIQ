"""Adaptive Query Router (AQR) — Contribution C6.

Classifies incoming questions by complexity level (L1-L5) and routes
to the empirically optimal backend:
  - Aggregation/lookup (L1-L3)  → B1 NL→SQL
  - Comparative reasoning (L4)  → B2 Graph-RAG Cypher
  - Narrative synthesis (L5)    → B2 Graph-RAG Hybrid

Two classifier modes:
  - PRIMARY: Zero-shot LLM classifier (standard approach per RAGRouter-Bench 2025)
  - FALLBACK: Rule-based pattern matcher (when API unavailable)

Backed by: RouteRAG (2025), RAGRouter-Bench, FAIR-RAG.
"""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any, Optional


# ===========================================================================
# Zero-shot LLM classifier (PRIMARY — standard, generalizable)
# ===========================================================================

CLASSIFIER_PROMPT = """\
You are a query complexity classifier for a CCTV surveillance analytics system.

Given a user question about surveillance event data, classify it into exactly ONE of these five levels:

L1 — DIRECT LOOKUP: Simple count, single value, or trivial scalar. One filter, no grouping.
  Examples: "How many cars entered?", "Total events today?", "How many cameras are active?"

L2 — SINGLE AGGREGATION: One aggregate function (MAX/MIN/AVG/COUNT) over a filtered window, no GROUP BY.
  Examples: "Peak head_count at NVIDIA booth?", "Average confidence today?", "How many detections below 85%?"

L3 — MULTI-DIMENSIONAL AGGREGATION: GROUP BY across 2+ dimensions, hourly breakdowns, per-camera stats, rankings.
  Examples: "Hour-by-hour arrival pattern", "Event counts by type", "Which areas had most crowd activity?"

L4 — COMPARATIVE REASONING: Comparing two or more entities, computing ratios, determining which is bigger/busier.
  Examples: "Compare NVIDIA vs Intel booth", "Was morning rush bigger than evening?", "Which gate had higher flow?"

L5 — OPEN-ENDED NARRATIVE: Multi-aspect briefing, security report, timeline description, operational recommendations.
  Examples: "Write a security brief for the day", "Describe the full lifecycle at keynote hall", "What should change next time?"

Return ONLY the level label: L1, L2, L3, L4, or L5. Nothing else. No explanation."""


def classify_with_llm(question: str) -> tuple[str, dict]:
    """Classify question complexity using zero-shot LLM (gpt-4o-mini).

    Returns: (level_str, usage_metadata)
    """
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    from openai import OpenAI

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        env_path = Path(".env")
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith("OPENAI_API_KEY"):
                    _, v = line.split("=", 1)
                    api_key = v.strip().strip('"').strip("'")
                    break
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not configured")

    client = OpenAI(api_key=api_key)
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        messages=[
            {"role": "system", "content": CLASSIFIER_PROMPT},
            {"role": "user", "content": question},
        ],
    )
    raw = (resp.choices[0].message.content or "").strip().upper()

    # Parse — accept "L1", "L2", etc. Handle minor variations.
    for level in ["L5", "L4", "L3", "L2", "L1"]:
        if level in raw:
            usage = {
                "model": "gpt-4o-mini",
                "prompt_tokens": resp.usage.prompt_tokens if resp.usage else 0,
                "completion_tokens": resp.usage.completion_tokens if resp.usage else 0,
            }
            return level, usage

    # If LLM returned garbage, fall back to rule-based
    return classify_rule_based(question), {"model": "fallback_rule_based"}


# ===========================================================================
# Rule-based classifier (FALLBACK — no API needed)
# ===========================================================================

_L5_PATTERNS = [
    r"\b(brief|briefing|summary|summarize|summarise)\b",
    r"\b(tell me how|what stood out|what could be improved|what should change)\b",
    r"\b(security team|staffing|recommend|top recommendations)\b",
    r"\b(if you were running|operational)\b",
    r"\b(describe the full|full lifecycle|activity timeline)\b",
    r"\b(produce .{0,15}report|security.attention.report)\b",
    r"\b(describe .{0,15}lifecycle)\b",
]

_L4_PATTERNS = [
    r"\b(compare|comparison|versus|vs\.?)\b",
    r"\b(bigger|smaller|busier|more popular|more crowded|which (?:one|booth|gate|location))\b",
    r"\b(morning .{0,20} evening|morning .{0,20} afternoon)\b",
    r"\b(drop off|dropoff|trend|stayed similar)\b",
    r"\b(ratio|how much more|how much less|difference between)\b",
    r"\b(peak.{0,15}baseline|contrast)\b",
]

_L3_PATTERNS = [
    r"\b(break\s*down|broken down|hour[- ]by[- ]hour|hourly)\b",
    r"\b(for each|per (?:camera|location|booth|gate|event))\b",
    r"\b(rank|ranked|top \d|which areas|which (?:locations|cameras))\b",
    r"\b(group|by event.type|by camera|by location)\b",
    r"\b(throughout the day|across the day|over the day)\b",
    r"\bshow .{0,30}(pattern|volume|counts? by)\b",
    r"\b(list every|list each)\b",
]

_L2_PATTERNS = [
    r"\b(peak|maximum|max|minimum|min|average|avg|mean)\b",
    r"\b(busiest moment|most crowded|highest|lowest)\b",
    r"\b(below|above|under|over|threshold|less than|more than)\s+\d",
    r"\b(net flow|net person)\b",
    r"\b(how busy|how packed|how crowded)\b",
]


def classify_rule_based(question: str) -> str:
    """Fallback: classify using keyword patterns. Returns L1-L5."""
    lower = question.lower()

    for pat in _L5_PATTERNS:
        if re.search(pat, lower):
            return "L5"
    for pat in _L4_PATTERNS:
        if re.search(pat, lower):
            return "L4"
    for pat in _L3_PATTERNS:
        if re.search(pat, lower):
            return "L3"
    for pat in _L2_PATTERNS:
        if re.search(pat, lower):
            return "L2"
    return "L1"


# ===========================================================================
# Unified classifier — tries LLM first, falls back to rule-based
# ===========================================================================

def classify_complexity(question: str, use_llm: bool = True) -> tuple[str, str, dict]:
    """Classify question complexity.

    Args:
        question: the user's question text
        use_llm: if True, use zero-shot LLM classifier (primary);
                 if False or API unavailable, use rule-based (fallback)

    Returns: (level, method_used, metadata)
        method_used is 'llm_zero_shot' or 'rule_based'
    """
    if use_llm:
        try:
            level, usage = classify_with_llm(question)
            return level, "llm_zero_shot", usage
        except Exception:
            # API error (quota, network, etc.) — graceful fallback
            pass

    level = classify_rule_based(question)
    return level, "rule_based", {}


# ===========================================================================
# Routing table: complexity → approach
# ===========================================================================

ROUTING_TABLE = {
    "L1": "b1_sql",          # SQL wins on direct lookups (100% vs 89%)
    "L2": "b1_sql",          # SQL wins on aggregation (94% vs 56%)
    "L3": "b2_rag_cypher",   # Cypher matches/beats SQL post-fix (100% vs 94%)
    "L4": "b2_rag_cypher",   # Graph-RAG excels at comparative (100% vs 88%)
    "L5": "b2_rag_hybrid",   # Hybrid wins on narrative (75% vs 56%)
}


def route_question(question: str, use_llm: bool = True) -> tuple[str, str, dict]:
    """Classify and route a question to its optimal backend.

    Returns: (approach_key, classified_level, routing_metadata)
    """
    t_start = time.time()
    classified, method, clf_meta = classify_complexity(question, use_llm=use_llm)
    approach = ROUTING_TABLE[classified]
    duration_ms = int((time.time() - t_start) * 1000)

    metadata = {
        "classified_level": classified,
        "routed_to": approach,
        "routing_method": method,
        "routing_duration_ms": duration_ms,
        "classifier_metadata": clf_meta,
    }
    return approach, classified, metadata


# ===========================================================================
# AQR answer function — delegates to the routed backend
# ===========================================================================

def answer_question(
    question: str,
    model: str,
    context: Optional[dict] = None,
    use_llm_classifier: bool = True,
) -> dict[str, Any]:
    """Adaptive Query Router: classify → route → invoke backend → return envelope.

    The envelope is augmented with routing metadata so the bench can track
    which backend was selected and whether the classification was correct.
    """
    approach, classified, routing_meta = route_question(question, use_llm=use_llm_classifier)

    # Import and invoke the selected backend
    if approach == "b1_sql":
        from llm_sql.b1_service import answer_question as b1_answer
        result = b1_answer(question, model, context=context)
    elif approach == "b2_rag_cypher":
        from llm_rag.cypher_service import answer_question as cypher_answer
        result = cypher_answer(question, model, context=context)
    elif approach == "b2_rag_hybrid":
        from llm_rag.hybrid_service import answer_question as hybrid_answer
        result = hybrid_answer(question, model, context=context)
    elif approach == "b2_rag_community":
        from llm_rag.community_service import answer_question as community_answer
        result = community_answer(question, model, context=context)
    else:
        result = {"answer_text": None, "errors": [f"Unknown routed approach: {approach}"]}

    # Augment envelope with routing metadata
    result["routing"] = routing_meta

    # Add routing duration to total duration
    if "duration_ms" in result:
        result["duration_ms"] += routing_meta.get("routing_duration_ms", 0)

    return result


# ===========================================================================
# Self-test — compares both classifiers against gold levels from bench
# ===========================================================================

def self_test_classifier(questions_dir: str = "bench/questions", use_llm: bool = False) -> dict:
    """Run the classifier against all bench questions and report accuracy.

    Each question file has a 'level' field — compare against classifier output.
    Args:
        use_llm: if True, test LLM classifier; if False, test rule-based only
    Returns: {total, correct, accuracy, confusion_matrix, misclassified}
    """
    questions_path = Path(questions_dir)
    total = 0
    correct = 0
    confusion: dict[tuple[str, str], int] = {}
    misclassified: list[dict] = []

    for level_dir in sorted(questions_path.iterdir()):
        if not level_dir.is_dir():
            continue
        for qfile in sorted(level_dir.glob("q*.json")):
            q = json.loads(qfile.read_text())
            gold_level = q.get("level", level_dir.name)

            if use_llm:
                predicted, method, _ = classify_complexity(q["question_text"], use_llm=True)
            else:
                predicted = classify_rule_based(q["question_text"])
                method = "rule_based"

            total += 1
            key = (gold_level, predicted)
            confusion[key] = confusion.get(key, 0) + 1

            if predicted == gold_level:
                correct += 1
            else:
                misclassified.append({
                    "question_id": q.get("question_id"),
                    "question_text": q["question_text"][:80],
                    "gold": gold_level,
                    "predicted": predicted,
                    "method": method,
                })

    return {
        "total": total,
        "correct": correct,
        "accuracy": round(correct / total * 100, 1) if total else 0,
        "method": "llm_zero_shot" if use_llm else "rule_based",
        "confusion_matrix": {f"{g}->{p}": c for (g, p), c in sorted(confusion.items())},
        "misclassified": misclassified,
    }


if __name__ == "__main__":
    import sys
    use_llm = "--llm" in sys.argv

    mode = "LLM zero-shot" if use_llm else "Rule-based (fallback)"
    print(f"Testing: {mode} classifier\n")

    result = self_test_classifier(use_llm=use_llm)
    print(f"Accuracy: {result['correct']}/{result['total']} = {result['accuracy']}%")
    print(f"\nConfusion matrix:")
    for key, count in sorted(result["confusion_matrix"].items()):
        print(f"  {key}: {count}")
    if result["misclassified"]:
        print(f"\nMisclassified ({len(result['misclassified'])}):")
        for m in result["misclassified"]:
            print(f"  [{m['gold']}->{m['predicted']}] ({m['method']}) {m['question_text']}")
    else:
        print("\nZero misclassifications!")
