# vForensIQ

**Intelligent Surveillance Analytics — CV Event Detection + LLM-based Forensic Querying**

vForensIQ combines Computer Vision for CCTV event detection with Large Language Models for natural-language querying over structured surveillance logs. CV acts as a proof-of-concept event producer; the research contribution is the LLM querying layer evaluated across two approaches (NL→SQL and Graph-RAG) on a five-level difficulty benchmark.

---

## Quick Start

```bash
# 1. Install Python dependencies
pip install openai python-dotenv neo4j chromadb python-louvain networkx

# 2. Set your OpenAI API key
echo 'OPENAI_API_KEY=sk-...' > .env

# 3. Generate simulated event data
python -m simulator ai_hw_summit_day1

# 4. Start Neo4j (required for B2 Graph-RAG)
docker compose up -d

# 5. Build the knowledge graph from SQL
python -m llm_rag.graph_builder

# 6. Launch the chat UI
pip install streamlit
streamlit run chat_ui.py
```

---

## Architecture

```
┌───────────────────────────────────────────────────────────────┐
│                    USER (Chat UI / CLI)                        │
│                   "How many cars entered today?"               │
└────────────┬──────────────────────────────┬───────────────────┘
             │                              │
     ┌───────▼────────┐          ┌──────────▼──────────┐
     │  B1: NL → SQL  │          │  B2: Graph-RAG      │
     │  (llm_sql/)    │          │  (llm_rag/)          │
     │                │          │  ├ Cypher variant     │
     │  Step 1: LLM   │          │  ├ Community variant  │
     │  generates SQL  │          │  └ Hybrid variant    │
     │  Step 2: LLM   │          │                      │
     │  synthesizes   │          │  Neo4j + Chroma      │
     └───────┬────────┘          └──────────┬──────────┘
             │                              │
     ┌───────▼──────────────────────────────▼──────────┐
     │              SQL Logbase (SQLite)                 │
     │           runtime/vforensiq_logbase.db            │
     └──────────────────────┬───────────────────────────┘
                            │
              ┌─────────────▼─────────────┐
              │    Scenario Simulator      │
              │    simulator/scenarios/    │
              └───────────────────────────┘
```

---

## Components

### 1. Scenario Simulator (`simulator/`)

Generates realistic per-second CCTV event data directly into the SQL logbase.

```bash
# List available scenarios
ls simulator/scenarios/

# Run a scenario (writes to runtime/vforensiq_logbase.db)
python -m simulator ai_hw_summit_day1
python -m simulator base_quiet_day
```

**Scenarios:**
- `ai_hw_summit_day1` — AI Hardware Summit 2025, 8 cameras, ~438k events/day
- `base_quiet_day` — minimal 2-camera scenario for smoke testing

Each scenario produces:
- Events in the SQLite logbase (same schema the MQTT subscriber would write)
- `simulator/out/<name>/ground_truth.json` for evaluation gold answers

### 2. Approach B1 — NL→SQL (`llm_sql/b1_service.py`)

Two-step Table-Augmented Generation pipeline:
1. **LLM generates SQL** against the `events` table with schema-primed prompt
2. **LLM synthesizes answer** from the executed rows

```python
from llm_sql.b1_service import answer_question

result = answer_question(
    "How many cars entered the parking lot today?",
    model="gpt-4o-mini",
    context={"scenario_label": "ai_hw_summit_day1",
             "scenario_window": {"start": "2025-12-08T00:00:00Z",
                                  "end": "2025-12-09T00:00:00Z"}}
)
print(result["answer_text"])
print(result["citations"][0]["sql"])
```

### 3. Approach B2 — Graph-RAG (`llm_rag/`)

Three variants over a Neo4j knowledge graph:

**Prerequisites:**
```bash
docker compose up -d          # Start Neo4j
python -m llm_rag.graph_builder  # Populate graph from SQL
```

**Variant 1 — Cypher** (`llm_rag/cypher_service.py`):
```python
from llm_rag.cypher_service import answer_question
result = answer_question("Which booth was more popular?", "gpt-4o-mini", context=ctx)
```

**Variant 2 — Community Summaries** (`llm_rag/community_service.py`):
```python
from llm_rag.community_service import answer_question
# First run builds Louvain communities + embeds summaries in Chroma (~1 min)
result = answer_question("Give me a security brief for the day", "gpt-4o", context=ctx)
```

**Variant 3 — Hybrid** (`llm_rag/hybrid_service.py`):
```python
from llm_rag.hybrid_service import answer_question
# Runs Cypher + Community in parallel, merges for synthesis
result = answer_question("Compare NVIDIA and Intel booth traffic", "gpt-4o", context=ctx)
```

### 4. Chat UI (`chat_ui.py`)

Interactive Streamlit chat interface supporting all approaches.

```bash
streamlit run chat_ui.py
```

**Features:**
- Chat-style conversation with message history
- Sidebar selector for approach (B1 SQL / B2 Cypher / Community / Hybrid)
- Model selector (gpt-4o-mini, gpt-4o, gpt-5-mini, gpt-5)
- Scenario context selector
- Expandable details per response: SQL/Cypher query, rows returned, token usage, duration
- Clear chat button

### 5. Evaluation Harness (`bench/`)

L1–L5 benchmark with 41 questions across schema-aware and abstract real-user styles.

```bash
# Run B1 only
python -m bench.run_eval --approach b1_sql --model all --level all

# Run all approaches
python -m bench.run_eval --approach all --model all --level all

# Run specific level/model
python -m bench.run_eval --approach b2_rag_cypher --model gpt-4o --level L4,L5

# Custom run ID
python -m bench.run_eval --approach all --model all --level all --run-id my_experiment
```

**Results** land in `bench/results/<run_id>/`:
- `manifest.json` — run metadata
- `comparison.csv` — one row per cell (approach × model × question)
- `by_config/<approach>__<model>/<level>/<question>.json` — full envelope per cell

**Scoring:**
| Level | Scorer | Method |
|---|---|---|
| L1 | `exact_numeric` | Deterministic integer match |
| L2 | `numeric_tolerance_1pct` | ±1% tolerance |
| L3 | `set_match_with_tolerance` | GROUP BY row-set match |
| L4 | `structured_facts` | Fact-by-fact match with tolerances |
| L5 | `rubric_coverage` | LLM-as-judge over rubric items |

---

## Setup

### Python Dependencies

```bash
pip install openai python-dotenv neo4j chromadb python-louvain networkx streamlit
```

### Environment Variables

Create `.env` in the project root:
```
OPENAI_API_KEY=sk-proj-...
```

Optional:
```
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=vforensiq_dev
```

### Neo4j (Docker)

```bash
docker compose up -d        # Start
docker compose down          # Stop
docker compose down -v       # Stop + delete data
```

Neo4j Browser: http://localhost:7474 (neo4j / vforensiq_dev)

### Data Contract

See [`docs/contracts.md`](docs/contracts.md) for the authoritative event schema, MQTT transport spec, and SQL logbase DDL.

**Event types:** `person_entry`, `person_exit`, `car_entry`, `car_exit`, `crowd`

**Event JSON:**
```json
{
  "timestamp": "2025-12-08T09:15:42Z",
  "camera_id": "CAM_01",
  "event_type": "car_entry",
  "object_id": "347",
  "confidence": 0.94,
  "camera_location": "Gate_ParkingLot",
  "head_count": 0
}
```

---

## Project Structure

```
vForensIQ/
├── chat_ui.py               # Streamlit chat interface
├── docker-compose.yml        # Neo4j container
├── .env                      # OpenAI API key (gitignored)
│
├── docs/
│   ├── contracts.md          # Authoritative data contract (v2)
│   └── mosquitto.conf        # MQTT broker config (for CV pipeline)
│
├── simulator/
│   ├── core.py               # Scenario runner (JSON → SQL + ground_truth)
│   ├── __main__.py           # CLI: python -m simulator <name>
│   └── scenarios/
│       ├── ai_hw_summit_day1.json
│       └── base_quiet_day.json
│
├── llm_sql/
│   ├── b1_service.py         # B1: NL→SQL two-step pipeline
│   ├── common.py             # Shared constants
│   └── logging_utils.py
│
├── llm_rag/
│   ├── common.py             # Neo4j/Chroma config
│   ├── graph_builder.py      # SQL → Neo4j graph population
│   ├── cypher_service.py     # B2 variant 1: NL→Cypher
│   ├── community_service.py  # B2 variant 2: Louvain + embeddings + retrieval
│   └── hybrid_service.py     # B2 variant 3: Cypher + Community combined
│
├── bench/
│   ├── run_eval.py           # Evaluation harness CLI
│   ├── README.md             # Bench format spec
│   ├── questions/
│   │   ├── L1/ ... L5/       # 41 question JSONs
│   └── results/              # (gitignored) per-run outputs
│
├── logbase/                  # MQTT subscriber (future: CV edge pipeline)
├── tools/                    # Replay publisher (future)
├── detectors/                # CV detectors (proof-of-concept)
│
├── runtime/                  # (gitignored)
│   ├── vforensiq_logbase.db  # SQLite event logbase
│   └── chroma_communities/   # Chroma vector store
│
└── Report/                   # MTech report artifacts
```

---

## End-to-End Workflow

```bash
# Step 1: Generate data
python -m simulator ai_hw_summit_day1

# Step 2: Start Neo4j + build graph
docker compose up -d
python -m llm_rag.graph_builder

# Step 3: Chat with the data
streamlit run chat_ui.py

# Step 4: Run formal evaluation
python -m bench.run_eval --approach all --model gpt-4o-mini,gpt-4o --level all --run-id eval_v1

# Step 5: View results
cat bench/results/eval_v1/comparison.csv
```

---

## Research References

Key papers backing the approaches:

| Technique | Citation |
|---|---|
| Text-to-SQL benchmark | Yu et al., Spider, EMNLP 2018 |
| LLM-grounded Text-to-SQL | Li et al., BIRD, NeurIPS 2023 |
| DIN-SQL self-correction | Pourreza & Rafiei, NeurIPS 2023 |
| Graph-RAG community summaries | Edge et al., Microsoft GraphRAG, 2024 |
| Louvain community detection | Blondel et al., J. Stat. Mech. 2008 |

Full bibliography: `MTech_Report_Avadh/mybib.bib`

---

## License

See [LICENSE](LICENSE).
