"""vForensIQ Chat UI — interactive surveillance analytics with B1 (SQL) and B2 (Graph-RAG) approaches."""
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
# Sidebar — settings
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Settings")

    approach = st.selectbox(
        "LLM Approach",
        ["B1 — NL→SQL", "B2 — Graph-RAG (Cypher)", "B2 — Graph-RAG (Community)", "B2 — Graph-RAG (Hybrid)"],
        index=0,
    )
    approach_map = {
        "B1 — NL→SQL": "b1_sql",
        "B2 — Graph-RAG (Cypher)": "b2_cypher",
        "B2 — Graph-RAG (Community)": "b2_community",
        "B2 — Graph-RAG (Hybrid)": "b2_hybrid",
    }
    approach_key = approach_map[approach]

    model = st.selectbox("Model", ["gpt-4o-mini", "gpt-4o", "gpt-5-mini", "gpt-5"], index=0)

    scenario = st.selectbox(
        "Scenario (session context)",
        ["ai_hw_summit_day1", "base_quiet_day", "None (no context)"],
        index=0,
    )

    st.markdown("---")
    st.caption("Data source: `runtime/vforensiq_logbase.db`")
    st.caption("Neo4j: `bolt://localhost:7687`")

    if st.button("Clear Chat"):
        st.session_state.messages = []
        st.rerun()


# ---------------------------------------------------------------------------
# Build session context from scenario
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
# Invoke the selected approach
# ---------------------------------------------------------------------------
def _invoke(question: str, approach_key: str, model: str, context: dict | None) -> dict:
    if approach_key == "b1_sql":
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
    else:
        return {"answer_text": f"Unknown approach: {approach_key}", "errors": []}


# ---------------------------------------------------------------------------
# Chat interface
# ---------------------------------------------------------------------------
st.title("vForensIQ — CCTV Analytics Chat")
st.caption(f"Approach: **{approach}** | Model: `{model}` | Scenario: `{scenario}`")

# Init message history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("details"):
            with st.expander("Details"):
                st.json(msg["details"])

# Chat input
if prompt := st.chat_input("Ask about the surveillance data..."):
    # Show user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Get response
    with st.chat_message("assistant"):
        with st.spinner(f"Querying via {approach}..."):
            ctx = _get_context(scenario)
            t0 = time.time()
            try:
                result = _invoke(prompt, approach_key, model, ctx)
            except Exception as exc:
                result = {"answer_text": f"Error: {exc}", "errors": [str(exc)]}
            elapsed = time.time() - t0

        answer = result.get("answer_text") or "No answer generated."
        errors = result.get("errors", [])

        if errors and not result.get("answer_text"):
            st.error(f"Pipeline error: {errors[0]}")
            answer = f"Error: {errors[0]}"
        else:
            st.markdown(answer)

        # Build details for expander
        details = {}

        # Citations
        citations = result.get("citations", [])
        for cit in citations:
            if cit.get("type") == "sql_query" and cit.get("sql"):
                details["SQL Query"] = cit["sql"]
                details["Row Count"] = cit.get("row_count", "?")
            elif cit.get("type") == "cypher_query" and cit.get("cypher"):
                details["Cypher Query"] = cit["cypher"]
                details["Row Count"] = cit.get("row_count", "?")
            elif cit.get("type") == "community":
                details.setdefault("Communities Retrieved", []).append(cit.get("community_id"))

        # Structured answer (sample rows)
        sa = result.get("structured_answer", {})
        if sa.get("columns") and sa.get("rows"):
            details["Columns"] = sa["columns"]
            details["Sample Rows (first 5)"] = sa["rows"][:5]
            details["Total Rows"] = sa.get("total_rows", len(sa.get("rows", [])))
        if sa.get("retrieved_communities"):
            details["Retrieved Summaries"] = [
                {"id": r.get("community_id"), "distance": r.get("distance"), "summary": r.get("summary", "")[:200]}
                for r in sa["retrieved_communities"][:3]
            ]

        # LLM calls
        llm_calls = result.get("llm_calls", [])
        if llm_calls:
            total_tokens = sum(c.get("prompt_tokens", 0) + c.get("completion_tokens", 0) for c in llm_calls)
            details["LLM Calls"] = len(llm_calls)
            details["Total Tokens"] = total_tokens

        details["Duration (ms)"] = result.get("duration_ms", int(elapsed * 1000))

        if errors:
            details["Errors"] = errors

        with st.expander("Details"):
            st.json(details)

    # Save to history
    st.session_state.messages.append({
        "role": "assistant",
        "content": answer,
        "details": details,
    })
