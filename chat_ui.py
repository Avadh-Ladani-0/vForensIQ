"""vForensIQ Chat UI — surveillance analytics powered by B1/B2/B3(AQR) LLM backends."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import streamlit as st

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(page_title="vForensIQ Chat", page_icon="🔍", layout="wide")

# ---------------------------------------------------------------------------
# Example queries, organised by complexity level
# ---------------------------------------------------------------------------
_EXAMPLES = {
    "L1 — Direct Lookup": [
        "How many cars came into the parking lot during the day?",
        "How many people left through the main entrance gate today?",
        "How many cameras are deployed at this venue?",
        "How many total events were recorded across all cameras today?",
        "How many crowd readings were taken on the expo floor today?",
    ],
    "L2 — Single Aggregation": [
        "How packed did the NVIDIA booth get at its busiest moment?",
        "How busy was the food court during lunch hours on average?",
        "How many people entered the venue in total today, counting all gates?",
        "What was the quietest moment at the keynote stage?",
        "On average, how confident were the detections for entries at the main gate?",
    ],
    "L3 — Multi-Dim Aggregation": [
        "Show me when people were arriving at the main entrance throughout the day, broken down hour by hour.",
        "Which areas of the venue had the most crowd activity? Rank them by average crowd size.",
        "What was the peak crowd at each location across the venue?",
        "For each gate, how many people came in versus how many went out during the day?",
        "How does activity change throughout the day? Show total events per hour.",
    ],
    "L4 — Comparative Reasoning": [
        "Was the morning rush bigger than the evening rush at the main entrance?",
        "Which demo booth attracted bigger crowds — NVIDIA or Intel? Roughly how much more popular was the winner?",
        "During lunch hours (12–14), did the food court get more crowded than the expo floor?",
        "Did the keynote stage attendance drop off later in the day, or stay similar?",
        "At the parking lot gate, what's the ratio of car traffic to pedestrian traffic?",
    ],
    "L5 — Narrative Synthesis": [
        "Tell me how the day went at the conference — what stood out and when were the big moments?",
        "If you were running security here, what would you tell your team? Where do we need the most eyes?",
        "Looking at how this conference day played out, what could be improved next time?",
        "Describe how the crowd moved through the venue — from gates to expo floor to keynote hall.",
        "Something happened at the keynote hall around 9 AM — the crowd surged. Investigate what the data shows.",
    ],
}

_LEVEL_ICONS = {
    "L1 — Direct Lookup":          "🔵",
    "L2 — Single Aggregation":     "🟢",
    "L3 — Multi-Dim Aggregation":  "🟠",
    "L4 — Comparative Reasoning":  "🔴",
    "L5 — Narrative Synthesis":    "🟣",
}

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Settings")

    approach = st.selectbox(
        "LLM Approach",
        [
            "B3 — AQR (Adaptive Router)",
            "B1 — NL→SQL",
            "B2 — Graph-RAG (Cypher)",
            "B2 — Graph-RAG (Community)",
            "B2 — Graph-RAG (Hybrid)",
        ],
        index=0,
        help="B3 AQR automatically routes each question to the best backend.",
    )
    _APPROACH_MAP = {
        "B3 — AQR (Adaptive Router)":  "b3_aqr",
        "B1 — NL→SQL":                 "b1_sql",
        "B2 — Graph-RAG (Cypher)":     "b2_cypher",
        "B2 — Graph-RAG (Community)":  "b2_community",
        "B2 — Graph-RAG (Hybrid)":     "b2_hybrid",
    }
    approach_key = _APPROACH_MAP[approach]

    model = st.selectbox("Model", ["gpt-4o-mini", "gpt-4o"], index=0)

    scenario = st.selectbox(
        "Scenario (session context)",
        ["ai_hw_summit_day1", "base_quiet_day", "None (no context)"],
        index=0,
    )

    st.markdown("---")
    st.caption("Data: `runtime/vforensiq_logbase.db`")
    st.caption("Neo4j: `bolt://localhost:7687`")

    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.pop("pending_question", None)
        st.rerun()

    # ── Example queries ────────────────────────────────────────────────
    st.markdown("---")
    st.header("💡 Example Queries")
    st.caption("Click any question to send it.")

    for level_label, questions in _EXAMPLES.items():
        icon = _LEVEL_ICONS[level_label]
        with st.expander(f"{icon} {level_label}", expanded=False):
            for q in questions:
                if st.button(q, key=f"ex_{hash(q)}", use_container_width=True):
                    st.session_state.pending_question = q
                    st.rerun()


# ---------------------------------------------------------------------------
# Session context helper
# ---------------------------------------------------------------------------
def _get_context(scenario_name: str) -> dict | None:
    if scenario_name == "None (no context)":
        return None
    path = _ROOT / "simulator" / "scenarios" / f"{scenario_name}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    return {"scenario_label": scenario_name, "scenario_window": data.get("window_utc")}


# ---------------------------------------------------------------------------
# Backend invocation
# ---------------------------------------------------------------------------
def _invoke(question: str, approach_key: str, model: str, context: dict | None) -> dict:
    if approach_key == "b3_aqr":
        from llm_aqr.router import answer_question
        return answer_question(question, model, context=context)
    elif approach_key == "b1_sql":
        from llm_sql.b1_service import answer_question
        return answer_question(question, model, context=context)
    elif approach_key == "b2_cypher":
        from llm_rag.cypher_service import answer_question
        return answer_question(question, model, context=context)
    elif approach_key == "b2_community":
        from llm_rag.community_service import answer_question
        return answer_question(question, model, context=context)
    elif approach_key == "b2_hybrid":
        from llm_rag.hybrid_service import answer_question
        return answer_question(question, model, context=context)
    return {"answer_text": f"Unknown approach: {approach_key}", "errors": []}


# ---------------------------------------------------------------------------
# AQR routing badge
# ---------------------------------------------------------------------------
def _routing_badge(result: dict) -> str:
    routing = result.get("routing", {})
    if not routing:
        return ""
    level   = routing.get("classified_level", "?")
    backend = routing.get("routed_to", "?")
    method  = routing.get("routing_method", "?")
    backend_labels = {
        "b1_sql":        "B1 NL→SQL",
        "b2_rag_cypher": "B2 Cypher",
        "b2_rag_hybrid": "B2 Hybrid",
    }
    return (f"🔀 Classified as **{level}** → routed to **{backend_labels.get(backend, backend)}** "
            f"*(classifier: {method})*")


# ---------------------------------------------------------------------------
# Main chat area
# ---------------------------------------------------------------------------
st.title("vForensIQ — CCTV Analytics Chat")
st.caption(f"Approach: **{approach}** · Model: `{model}` · Scenario: `{scenario}`")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Render existing chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("badge"):
            st.caption(msg["badge"])
        if msg.get("details"):
            with st.expander("Details", expanded=False):
                st.json(msg["details"])

# Resolve the active prompt — example click takes precedence over typed input
pending: str | None = None
if "pending_question" in st.session_state:
    pending = st.session_state.pending_question
    del st.session_state["pending_question"]

typed = st.chat_input("Ask about the surveillance data…")
active_prompt = pending or typed

if active_prompt:
    # Show user bubble
    st.session_state.messages.append({"role": "user", "content": active_prompt})
    with st.chat_message("user"):
        st.markdown(active_prompt)

    # Call backend
    with st.chat_message("assistant"):
        with st.spinner(f"Querying via {approach}…"):
            ctx = _get_context(scenario)
            t0 = time.time()
            try:
                result = _invoke(active_prompt, approach_key, model, ctx)
            except Exception as exc:
                result = {"answer_text": f"⚠️ Error: {exc}", "errors": [str(exc)]}
            elapsed = time.time() - t0

        answer = result.get("answer_text") or "No answer generated."
        errors  = result.get("errors", [])

        if errors and not result.get("answer_text"):
            st.error(f"Pipeline error: {errors[0]}")
            answer = f"Error: {errors[0]}"
        else:
            st.markdown(answer)

        # Routing badge (AQR only)
        badge = _routing_badge(result) if approach_key == "b3_aqr" else ""
        if badge:
            st.caption(badge)

        # Details expander
        details: dict = {}

        for cit in result.get("citations", []):
            if cit.get("type") == "sql_query" and cit.get("sql"):
                details["SQL Query"]  = cit["sql"]
                details["Row Count"]  = cit.get("row_count", "?")
            elif cit.get("type") == "cypher_query" and cit.get("cypher"):
                details["Cypher Query"] = cit["cypher"]
                details["Row Count"]    = cit.get("row_count", "?")
            elif cit.get("type") == "community":
                details.setdefault("Communities Retrieved", []).append(cit.get("community_id"))

        sa = result.get("structured_answer", {})
        if sa.get("columns") and sa.get("rows"):
            details["Columns"]              = sa["columns"]
            details["Sample Rows (first 5)"] = sa["rows"][:5]
            details["Total Rows"]           = sa.get("total_rows", len(sa.get("rows", [])))
        if sa.get("retrieved_communities"):
            details["Retrieved Summaries"] = [
                {"id": r.get("community_id"), "distance": r.get("distance"),
                 "summary": r.get("summary", "")[:200]}
                for r in sa["retrieved_communities"][:3]
            ]

        if routing := result.get("routing"):
            details["AQR Routing"] = routing

        llm_calls = result.get("llm_calls", [])
        if llm_calls:
            details["LLM Calls"]    = len(llm_calls)
            details["Total Tokens"] = sum(
                c.get("prompt_tokens", 0) + c.get("completion_tokens", 0) for c in llm_calls
            )

        details["Duration (ms)"] = result.get("duration_ms", int(elapsed * 1000))
        if errors:
            details["Errors"] = errors

        with st.expander("Details", expanded=False):
            st.json(details)

    # Persist to history
    st.session_state.messages.append({
        "role": "assistant",
        "content": answer,
        "badge": badge,
        "details": details,
    })
