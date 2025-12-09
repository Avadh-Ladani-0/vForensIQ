import json
import openai
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
import os

# -----------------------------
# CONFIG
# -----------------------------
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
JSON_LOG_PATH = "logs//entry_exit_fire.json"


# -----------------------------
# LOAD LOGS INTO DATAFRAME
# -----------------------------
def load_logs(path):
    with open(path, "r") as f:
        logs = json.load(f)
    df = pd.DataFrame(logs)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


# -----------------------------
# PROCESS QUERY LOCALLY
# -----------------------------
def process_query_locally(df, user_query):
    """
    Decide what the user wants by analyzing keywords.
    Perform the statistics in Python.
    """
    user_query = user_query.lower()

    result = {}

    # Ask about gates with highest car_exit frequency
    if "car exit" in user_query or ("car" in user_query and "exit" in user_query):
        f = df[df["event_type"] == "car_exit"]
        grouped = f.groupby("camera_location").size().sort_values(ascending=False)

        result["computed_output"] = grouped.head(3).to_dict()
        result["explanation_type"] = "car_exit_frequency"
        return result

    # If no keyword matched — fallback to summary
    result["computed_output"] = df.head(30).to_dict(orient="records")
    result["explanation_type"] = "fallback"
    return result


# -----------------------------
# ASK OPENAI WITH SMALL SUMMARY
# -----------------------------
def ask_openai(user_query, local_result):
    compact_summary = str(local_result["computed_output"])[:3000]

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

    # FIXED: correct content extraction
    return response.choices[0].message.content



# -----------------------------
# MAIN
# -----------------------------
def run_query():
    df = load_logs(JSON_LOG_PATH)

    print("\nEnter your question:")
    user_query = input("> ")

    print("\nAnalyzing logs locally…")
    local_result = process_query_locally(df, user_query)

    print("\nContacting OpenAI for explanation…")
    answer = ask_openai(user_query, local_result)

    print("\n---------------- ANSWER ----------------")
    print(answer)
    print("----------------------------------------")


if __name__ == "__main__":
    run_query()