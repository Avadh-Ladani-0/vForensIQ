# vForensIQ
Smart Video Footage Analysis with Computer Vision and LLM

vForensIQ is an intelligent surveillance analytics system that combines **Computer Vision (CV)** for CCTV event detection with **Large Language Models (LLMs)** for reasoning, querying, and insight generation over structured surveillance logs.

---

## Demo

![System Architecture Overview](Report/system_architecture.png)

---

## LLM Reasoning

The LLM layer acts as the core intelligence of the system. It translates human natural-language queries into structured database operations, performs temporal and spatial reasoning over historical logs, and generates meaningful summaries and forensic insights.

![LLM Reasoning](Report/RAG_working.png)

---

## NL->SQL Engine (Event-Context Aware)

The repository now includes an event-context NL->SQL pipeline powered by the canonical source:

- `Data/Augmented_Data/out/data.csv`

Key behavior:

- Natural language -> QueryPlan -> SQL (read-only)
- SQLite execution with hourly rollup support
- Chunked summarization partitioned by `captured_event`
- Separate per-event summaries (no mixed-event narrative unless user asks to compare)
- Answer-first output in normal language
- Downloadable processed evidence tables (CSV/JSON)
- SQL citation list for both primary and post-processing queries
- Provider mode: `openai` only

### Models and Logging

- OpenAI SQL model: `OPENAI_SQL_MODEL` (default: `gpt-3.5-turbo`, set to any higher model as needed)
- Pipeline log file: `logs/nl_sql_pipeline.log`
- Audit log file: `logs/query_audit.jsonl`

### Run Streamlit UI

```bash
streamlit run app.py
```

### Run CLI

```bash
python chat.py
```

### Tests

```bash
python -m unittest discover -s tests -p "test_event_context_pipeline.py"
```

```mermaid
%%{init: {"flowchart": {"curve": "linear", "nodeSpacing": 35, "rankSpacing": 35}}}%%
flowchart LR

subgraph OFFLINE["OFFLINE: transforms -> embeddings -> indexes"]
direction LR

RAW[(Event rows\ncam_id, location_tag, timestamp\ncaptured_event, person_count, confidence, ...)]
EPW[(Episode windows\n30-120s buckets\nepisode_id + episode_text)]

NR["Deterministic narrative renderer\nEvent row -> narrative string"]
HS["Hierarchical summaries\nEpisodes -> higher-level summaries\nOptional"]

EMB["Embedding strategy\nBGE-M3 dense 1024d\nOptional sparse vectors\nStore embedding_version metadata\nmodel_name, model_version, dim, normalization"]

MIL[(Milvus vector store\nDense vectors + scalar filters\ncam_id/location_tag/timestamp/confidence)]
SRCH[(OpenSearch or Elasticsearch\nSparse retrieval: BM25 or neural sparse\nHybrid query support)]

RAW --> NR --> EMB --> MIL
EPW --> HS --> EMB
EPW --> SRCH
HS --> SRCH

end

subgraph ONLINE["ONLINE: router -> hybrid retrieve -> rerank -> grounded answer"]
direction LR

Q["User question q"]
ROUTER["Router\nChoose rag_semantic"]

HYB["Hybrid candidate retrieval\nDense top-k + Sparse top-k\nApply metadata/scalar filters"]

RERANK{"Rerank optional\nCross-encoder or LLM scoring"}

TOP["Top evidence snippets\nInclude episode_id or event_id\nInclude time bounds, cam_id, location_tag"]

PROMPT["RAG summarizer prompt\nUse ONLY evidence blocks\nIf insufficient: say what is missing\nSuggest a narrower query"]

OUT["Structured answer JSON\nanswer_text\ntime_bounds: start_utc, end_utc\nkey_findings: finding, supporting_event_ids, confidence\nevidence: event_id, timestamp, cam_id, location_tag\ncaveats"]

Q --> ROUTER --> HYB
MIL --> HYB
SRCH --> HYB
HYB --> RERANK
RERANK --> TOP
TOP --> PROMPT --> OUT

end
```