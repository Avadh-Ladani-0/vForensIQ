# vForensIQ
Smart Video Footage Analysis with Computer Vision and LLM

vForensIQ is an intelligent surveillance analytics system that combines **Computer Vision (CV)** for CCTV event detection with **Large Language Models (LLMs)** for reasoning, querying, and insight generation over structured surveillance logs.

CV event detection is a proof-of-concept supporting the LLM layer; the research contribution is the LLM-based querying system (B1 NL→SQL and B2 Graph-RAG).

---

## Architecture

![System Architecture Overview](Report/system_architecture.png)

Four modules:
1. **CCTV nodes** running CV event detection → publish events via MQTT.
2. **Central SQL logbase** (`runtime/vforensiq_logbase.db`) — MQTT subscriber writes events; simulator writes directly.
3. **LLM analytics** — two approaches run side-by-side and compared (B1 NL→SQL, B2 Graph-RAG).
4. **Evaluation harness** — L1–L5 bench scoring.

---

## Data & message contract

See [`docs/contracts.md`](docs/contracts.md) for the authoritative event JSON schema, MQTT transport, simulator output contract, and SQL logbase schema.

Event vocabulary (frozen, 5 values): `person_entry`, `person_exit`, `car_entry`, `car_exit`, `crowd`.

---

## Scenario-driven simulator

`simulator/` generates per-second event data directly into the SQL logbase. Scenarios are JSON configs defining cameras, traffic patterns, and peak-hour multipliers.

```bash
python -m simulator base_quiet_day          # 1-day minimal scenario
python -m simulator ai_hw_summit_day1       # themed: AI Hardware Summit 2025
```

Writes to `runtime/vforensiq_logbase.db`; also emits `simulator/out/<scenario>/ground_truth.json` for the eval harness.

---

## B1 — NL→SQL approach (Sprint 1)

Two-step pipeline in [`llm_sql/b1_service.py`](llm_sql/b1_service.py):

1. LLM #1 generates one SELECT against the `events` table (schema described in the system prompt).
2. SQL is validated (SELECT/WITH only, no mutations) and executed. On `OperationalError`, one-shot repair asks the LLM for a corrected query.
3. LLM #2 synthesizes a concise plain-language answer from the rows.

Both `gpt-4o-mini` and `gpt-4o` are evaluated at every level.

---

## B2 — Graph-RAG (Sprints 3–4)

Neo4j-backed. Three sub-variants compared: NL→Cypher, community-summary retrieval (Microsoft GraphRAG-style), hybrid. Details frozen in project memory.

---

## L1–L5 evaluation harness

```bash
# full matrix (b1_sql only for now; RAG lands Sprint 3+)
python -m bench.run_eval --approach b1_sql --model all --level all

# L1 only, both models
python -m bench.run_eval --approach b1_sql --model all --level L1
```

Results land under `bench/results/<run_id>/`:
- `manifest.json` — run metadata
- `comparison.csv` — one row per cell
- `by_config/<approach>__<model>/<level>/<question_id>.json` — per-cell envelopes

Scorers:
- L1: `exact_numeric` (deterministic)
- L2: `numeric_tolerance_1pct` (deterministic, ±1%)
- L3: `set_match_with_tolerance` (deterministic, set equality + per-value tolerance)
- L4: `structured_facts` (deterministic, fact-by-fact match with tolerances)
- L5: `rubric_coverage` (LLM-as-judge using gpt-4o; coverage fraction vs threshold)

---

## Environment

- Python 3.10+ with `openai`, `python-dotenv`. (Legacy prototype dependencies: `pandas`, `streamlit`, `reportlab` — only used by `app2.py`.)
- `.env` at repo root with `OPENAI_API_KEY=...`
- Pipeline log: `logs/llm_sql_pipeline.log`
- Audit log: `logs/query_audit.jsonl` (legacy path; will migrate in Sprint 2)

---

## Repo layout

```
docs/             # contracts.md (event schema, MQTT, SQL), mosquitto.conf
simulator/        # scenario generator + base_quiet_day / ai_hw_summit_day1 scenarios
logbase/          # MQTT subscriber (lands Sprint 3)
llm_sql/          # B1 NL->SQL (b1_service.py + logging/common utilities)
llm_rag/          # B2 graph RAG (lands Sprint 3-4)
bench/            # run_eval.py + questions/{L1,L2,L3,L4,L5}/*.json
tools/            # replay publisher, admin scripts (lands Sprint 3)
detectors/        # CV detectors (PoC, retarget Sprint 3)
```

---

## Legacy UI

The original Streamlit prototype (`app.py`, `chat.py`, `sql_pipeline.py`) was removed at end of Sprint 1 along with the legacy `llm_sql/{service,planner,aggregation,event_context,summarizer,db}.py` modules. A new UI fronting `llm_sql.b1_service` will land in a later sprint.

`app2.py` (an older single-file Streamlit prototype that predates the event-context pipeline) is self-contained and still works against `Data/Augmented_Data/out/data.csv` if pandas/streamlit are installed.
