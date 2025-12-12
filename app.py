import streamlit as st
import json
import pandas as pd
from datetime import datetime
import openai
from dotenv import load_dotenv
import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import tempfile

# ----------------------------------------------------
# CONFIG
# ----------------------------------------------------
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
JSON_LOG_PATH = "logs/entry_exit_fire.json"

# ----------------------------------------------------
# LOAD LOGS
# ----------------------------------------------------
@st.cache_data
def load_logs(path):
    with open(path, "r") as f:
        logs = json.load(f)
    df = pd.DataFrame(logs)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df

# ----------------------------------------------------
# LOCAL QUERY PROCESSING
# ----------------------------------------------------
def process_query_locally(df, user_query):
    user_query = user_query.lower()
    result = {}

    # Car exit frequency
    if "car exit" in user_query or ("car" in user_query and "exit" in user_query):
        f = df[df["event_type"] == "car_exit"]
        grouped = f.groupby("camera_location").size().sort_values(ascending=False)

        top3 = grouped.head(3)
        filtered_df = pd.DataFrame({
            "camera_location": top3.index,
            "count": top3.values
        })

        result["computed_output"] = filtered_df
        result["filter_applied"] = "Top 3 gates with highest car exits"
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
        model="gpt-4o-mini",
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
log_file_path = st.sidebar.text_input("Log File Path:", JSON_LOG_PATH)

# Load logs
df = load_logs(log_file_path)

st.subheader("📄 Log Preview (auto-updates after query)")
table_placeholder = st.empty()
table_placeholder.dataframe(df.head(50), use_container_width=True)

st.markdown("---")

st.subheader("💬 Ask a Question")
user_query = st.text_input(
    "Example: Show me the top 3 gates with highest car exit frequency"
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
