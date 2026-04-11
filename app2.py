import streamlit as st
import pandas as pd
import openai
from dotenv import load_dotenv
import os
import re
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import tempfile

# ----------------------------------------------------
# CONFIG
# ----------------------------------------------------
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
CSV_LOG_PATH = "Data/Augmented_Data/out/data.csv"

# ----------------------------------------------------
# LOAD LOGS
# ----------------------------------------------------
@st.cache_data
def load_logs(path):
    df = pd.read_csv(path, low_memory=False)

    required_columns = [
        "cam_id",
        "captured_event",
        "timestamp",
        "location_tag",
        "object_id",
        "person_count",
        "confidence",
        "detector_latency_ms",
        "source_track_age_s",
        "is_synthetic_artifact",
    ]
    for col in required_columns:
        if col not in df.columns:
            df[col] = None

    epoch_ts = pd.to_numeric(df["timestamp"], errors="coerce")
    if epoch_ts.notna().any():
        df["timestamp"] = pd.to_datetime(epoch_ts, unit="s", utc=True, errors="coerce")
    else:
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    return df

# ----------------------------------------------------
# LOCAL QUERY PROCESSING
# ----------------------------------------------------
def _extract_top_n(user_query, default=3):
    match = re.search(r"\btop\s+(\d+)\b", user_query)
    if match:
        return min(max(int(match.group(1)), 1), 50)

    fallback = re.search(r"\b(\d+)\b", user_query)
    if fallback:
        return min(max(int(fallback.group(1)), 1), 50)

    return default


def _event_from_query(user_query):
    event_keywords = [
        ("vehicle_exit", ["car exit", "vehicle exit"]),
        ("vehicle_entry", ["car entry", "vehicle entry"]),
        ("person_exit", ["person exit"]),
        ("person_entry", ["person entry"]),
        ("unattended_object", ["unattended object"]),
        ("person_count", ["person count", "headcount", "crowd"]),
    ]

    for event_name, phrases in event_keywords:
        if any(phrase in user_query for phrase in phrases):
            return event_name

    if ("car" in user_query or "vehicle" in user_query) and "exit" in user_query:
        return "vehicle_exit"
    if ("car" in user_query or "vehicle" in user_query) and "entry" in user_query:
        return "vehicle_entry"
    if "person" in user_query and "exit" in user_query:
        return "person_exit"
    if "person" in user_query and "entry" in user_query:
        return "person_entry"

    return None


def process_query_locally(df, user_query):
    user_query = user_query.lower()
    result = {}
    top_n = _extract_top_n(user_query)

    event_name = _event_from_query(user_query)
    group_col = "cam_id" if "camera" in user_query else "location_tag"

    if event_name:
        events = df["captured_event"].fillna("").astype(str).str.lower()
        filtered = df[events == event_name].copy()

        if filtered.empty:
            result["computed_output"] = pd.DataFrame(columns=[group_col, "count"])
            result["filter_applied"] = f"No rows found for captured_event='{event_name}'"
            return result

        if event_name == "person_count" and any(word in user_query for word in ["average", "avg", "mean"]):
            grouped = (
                filtered.groupby(group_col)["person_count"]
                .mean()
                .sort_values(ascending=False)
                .head(top_n)
            )
            filtered_df = pd.DataFrame(
                {
                    group_col: grouped.index,
                    "avg_person_count": grouped.values,
                }
            )
            result["computed_output"] = filtered_df
            result["filter_applied"] = f"Top {top_n} {group_col} by average person_count for {event_name}"
            return result

        grouped = (
            filtered[group_col]
            .fillna("unknown")
            .value_counts()
            .head(top_n)
        )

        filtered_df = pd.DataFrame(
            {
                group_col: grouped.index,
                "count": grouped.values,
            }
        )

        result["computed_output"] = filtered_df
        result["filter_applied"] = f"Top {top_n} {group_col} with highest {event_name} frequency"
        return result

    if "confidence" in user_query and any(word in user_query for word in ["top", "highest"]):
        ranked = (
            df.sort_values(by="confidence", ascending=False)
            [["cam_id", "location_tag", "captured_event", "confidence", "timestamp"]]
            .head(top_n)
        )
        result["computed_output"] = ranked
        result["filter_applied"] = f"Top {top_n} rows by confidence"
        return result

    if "latency" in user_query and any(word in user_query for word in ["top", "highest", "slowest"]):
        ranked = (
            df.sort_values(by="detector_latency_ms", ascending=False)
            [["cam_id", "location_tag", "captured_event", "detector_latency_ms", "timestamp"]]
            .head(top_n)
        )
        result["computed_output"] = ranked
        result["filter_applied"] = f"Top {top_n} rows by detector latency"
        return result

    # Fallback: show first 30 rows
    result["computed_output"] = df.head(30)
    result["filter_applied"] = "Fallback: first 30 rows"
    return result


# ----------------------------------------------------
# OPENAI CALL
# ----------------------------------------------------
def ask_openai(user_query, local_result):
    compact_summary = str(local_result["computed_output"].to_dict(orient="records"))[:3000]

    prompt = f"""
You are a CCTV forensic analysis assistant.

User question:
{user_query}

Local computed results from the logs:
{compact_summary}

Explain the findings clearly and meaningfully.
"""
    response = openai.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )
    return response.choices[0].message.content


# ----------------------------------------------------
# PDF REPORT GENERATOR
# ----------------------------------------------------
def generate_pdf(user_query, computation_desc, df):
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    c = canvas.Canvas(temp.name, pagesize=letter)
    
    c.setFont("Helvetica", 12)
    y = 750

    c.drawString(30, y, "vForensIQ - CCTV Forensic Report")
    y -= 30
    c.drawString(30, y, f"Query: {user_query}")
    y -= 20
    c.drawString(30, y, f"Computation Applied: {computation_desc}")
    y -= 30

    c.drawString(30, y, "Results (Top rows):")
    y -= 20

    for idx, row in df.head(10).iterrows():
        text = str(row.to_dict())
        c.drawString(30, y, text[:100])
        y -= 20
        if y < 50:
            c.showPage()
            y = 750

    c.save()
    return temp.name


# ----------------------------------------------------
# STREAMLIT UI
# ----------------------------------------------------
st.set_page_config(page_title="vForensIQ Log Query Engine", layout="wide")

st.title("🔍 vForensIQ — CCTV Log Query Engine")

st.sidebar.header("⚙️ Settings")
log_file_path = st.sidebar.text_input("CSV File Path:", CSV_LOG_PATH)

# Load logs
df = load_logs(log_file_path)

st.subheader("📄 Log Preview (auto-updates after query)")
table_placeholder = st.empty()
table_placeholder.dataframe(df.head(50), use_container_width=True)

st.markdown("---")

st.subheader("💬 Ask a Question")
user_query = st.text_input(
    "Example: Show me the top 3 locations with highest vehicle exit frequency"
)

if st.button("Run Query"):
    if user_query.strip() == "":
        st.warning("Please enter a question.")
    else:
        with st.spinner("Analyzing logs locally..."):
            local_result = process_query_locally(df, user_query)
            filtered_df = local_result["computed_output"]

        st.success("Local computation applied!")

        # 🔥 UPDATE EXISTING TABLE (no new table)
        table_placeholder.dataframe(filtered_df, use_container_width=True)

        with st.spinner("Contacting OpenAI for explanation..."):
            answer = ask_openai(user_query, local_result)

        st.subheader("🤖 LLM Explanation")
        st.write(answer)

        st.markdown("---")

        # JSON report download
        st.download_button(
            label="📥 Download JSON Report",
            data=filtered_df.to_json(orient="records", indent=2),
            file_name="cctv_query_report.json",
            mime="application/json"
        )

        # PDF report download
        pdf_path = generate_pdf(
            user_query,
            local_result["filter_applied"],
            filtered_df
        )
        with open(pdf_path, "rb") as f:
            st.download_button(
                label="📄 Download PDF Report",
                data=f,
                file_name="cctv_forensic_report.pdf",
                mime="application/pdf"
            )
