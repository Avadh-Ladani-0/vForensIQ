import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

_PKG_ROOT = Path(__file__).resolve().parent
if str(_PKG_ROOT) not in sys.path:
    sys.path.insert(0, str(_PKG_ROOT))

from nl_sql import CANONICAL_SOURCE_CSV, run_nl_sql_pipeline
from nl_sql.common import PIPELINE_LOG_PATH


@st.cache_data(show_spinner=False)
def load_primary_preview(path: str, rows: int = 200) -> pd.DataFrame:
    frame = pd.read_csv(path, nrows=rows)
    if "timestamp" in frame.columns:
        frame["timestamp_utc"] = pd.to_datetime(frame["timestamp"], unit="s", utc=True, errors="coerce")
    return frame


def render_envelope(title: str, envelope: dict) -> None:
    st.subheader(title)
    provider_model = envelope.get("provider_model", "unknown")
    st.markdown(
        f"Provider: `{envelope.get('provider', 'unknown')}` | Model: `{provider_model}` | Duration: `{envelope.get('duration_ms', 0)} ms`"
    )
    query_plan = envelope.get("query_plan", {})
    time_range = query_plan.get("time_range", {})
    st.markdown(
        f"UTC Window: `{time_range.get('start_utc', 'N/A')}` to `{time_range.get('end_utc', 'N/A')}`"
    )

    event_context = envelope.get("event_context", [])
    source = envelope.get("event_context_source", "unknown")
    context_display = ", ".join(event_context) if event_context else "N/A"
    st.markdown(f"Detected Event Context: `{context_display}` (source: `{source}`)")

    errors = envelope.get("errors", [])
    if errors:
        st.warning("\n".join(str(err) for err in errors))

    st.markdown("Answer")
    st.write(envelope.get("answer_text") or envelope.get("summary_text", "_No answer available._"))

    processed_rows = envelope.get("processed_rows", [])
    if processed_rows:
        processed_df = pd.DataFrame(processed_rows)
        st.markdown("Processed Evidence Data")
        st.dataframe(processed_df, use_container_width=True)
        st.download_button(
            label=f"Download {title} Processed Data (CSV)",
            data=processed_df.to_csv(index=False),
            file_name=f"{title.lower().replace(' ', '_')}_processed.csv",
            mime="text/csv",
        )
        st.download_button(
            label=f"Download {title} Processed Data (JSON)",
            data=json.dumps(processed_rows, indent=2),
            file_name=f"{title.lower().replace(' ', '_')}_processed.json",
            mime="application/json",
        )

    citations = envelope.get("citation_queries", [])
    if citations:
        st.markdown("SQL Citations")
        for item in citations:
            st.markdown(f"**{item.get('id', 'citation')}** - {item.get('purpose', '')}")
            st.code(item.get("sql", ""), language="sql")

    with st.expander("Technical Details"):
        st.markdown("Event Chunk Stats")
        st.json(envelope.get("event_chunk_stats", {}))
        st.markdown("QueryPlan")
        st.json(query_plan)
        sql_text = envelope.get("executed_sql") or query_plan.get("sql", "")
        st.markdown("Executed SQL")
        st.code(sql_text, language="sql")
        sections = envelope.get("summary_sections", {})
        if sections:
            st.markdown("Per-Event Sections")
            for event_name, section in sections.items():
                st.markdown(f"**{event_name}**")
                st.markdown(section)


st.set_page_config(page_title="vForensIQ NL->SQL Engine", layout="wide")
st.title("vForensIQ - Event-Context NL->SQL Engine")
st.caption(f"Primary source: `{CANONICAL_SOURCE_CSV}`")
st.caption(f"Pipeline log: `{PIPELINE_LOG_PATH}`")

with st.sidebar:
    st.header("Settings")
    provider_mode = "openai"
    st.text_input("Provider Mode", value="openai", disabled=True)
    chunk_size = st.slider("Chunk Size", min_value=500, max_value=20000, value=5000, step=500)

with st.expander("Primary Source Preview (Optional)"):
    preview = load_primary_preview(str(CANONICAL_SOURCE_CSV))
    st.dataframe(preview, use_container_width=True)

st.markdown("---")
st.subheader("Ask a Question")
question = st.text_area(
    "Natural language query",
    placeholder="Example: Which cameras had highest detector latency yesterday between 6pm and 11pm?",
    height=100,
)

if st.button("Run Query"):
    if not question.strip():
        st.warning("Please enter a question.")
    else:
        with st.spinner("Running NL->SQL pipeline..."):
            result = run_nl_sql_pipeline(
                question=question.strip(),
                provider_mode="openai",
                compare=False,
                chunk_size=chunk_size,
            )

        st.success("Query complete.")
        st.markdown(f"Total rows scanned during chunked summarization: `{result.get('result', {}).get('total_rows_scanned', 0)}`")
        render_envelope("OpenAI Result", result.get("result", {}))
