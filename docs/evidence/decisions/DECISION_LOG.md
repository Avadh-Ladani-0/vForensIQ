# Decision Log

Every architectural, prompt, and approach decision with rationale and evidence.

| # | Date | Decision | Rationale | Evidence/Reference |
|---|---|---|---|---|
| D001 | 2026-04-13 | 5-event vocabulary (person_entry/exit, car_entry/exit, crowd) | Matches MTech report | `docs/contracts.md` |
| D002 | 2026-04-13 | Simulator writes directly to SQL, bypasses MQTT | Decouples eval from CV pipeline | User instruction |
| D003 | 2026-04-13 | B1 = two-step NL→SQL (TAG pattern) | Simplicity; backed by Biswal et al. 2024 | `llm_sql/b1_service.py` |
| D004 | 2026-04-13 | B2 = Neo4j graph-RAG with 3 sub-variants | Comprehensive comparison; backed by Edge et al. 2024 | `llm_rag/*.py` |
| D005 | 2026-04-13 | Crowd compressed to CrowdHour (hourly aggregates in graph) | Avoids 6M+ nodes; backed by GraphRAG hierarchical design | `llm_rag/graph_builder.py` |
| D006 | 2026-04-13 | L1-L5 evaluation taxonomy | Novel stratification; no existing benchmark does this | `bench/README.md` |
| D007 | 2026-04-13 | Session-context injection for abstract questions | Real operators say "today" not ISO timestamps | `llm_sql/b1_service.py:_contextualize` |
| D008 | 2026-04-14 | Crowd-UNION prompt guidance for Cypher | Fixed 98.6% undercount in crowd queries | `llm_rag/cypher_service.py` SCHEMA_PROMPT |
| D009 | 2026-04-14 | temperature split: 0 for gen/repair/judge, default for synthesis | gpt-4o supports temp=0; synthesis benefits from natural prose | All service files |
| D010 | 2026-04-14 | LLM-as-judge for L5 scoring (gpt-4o) | Rubric coverage can't be deterministic | `bench/run_eval.py:score_rubric_coverage` |
| D011 | 2026-04-14 | IMPLEMENTED: AQR with LLM zero-shot classifier + rule-based fallback | Standard per RAGRouter-Bench; 100% accuracy on 75Q bench | `llm_aqr/router.py` |
| D012 | 2026-04-15 | IMPLEMENTED: Full graph with per-second :CrowdEvent nodes (432k) | Fixed crowd-exclusion; B2 jumped from 58.7% to 80.0% | `llm_rag/full_graph_builder.py` |
| D013 | 2026-04-15 | Removed base_quiet_day from logbase | Eliminates cross-scenario contamination | Direct DB deletion |
| D014 | 2026-04-15 | Scenario-scoped community index (11 clean communities) | No more Platform_1/Gate_01 leaks in L5 narratives | Community rebuild |
| D015 | 2026-04-15 | Expanded bench to 75 questions (15 per level, 14 graph-native) | Exercises B2 strengths: multi-hop, correlation, temporal flow | `bench/questions/` |
| D016 | 2026-04-15 | Manual evaluation replaces auto-scoring for thesis results | Auto-scorer underestimates L3-L5 by ~15 pts (40 cells upgraded) | `docs/evidence/manual_reviews/sprint4_DEFINITIVE_review.md` |
| D017 | 2026-04-15 | AQR routing table: L1,L2,L4→B1; L3→B2-Cypher; L5→B2-Hybrid | Based on per-level winners from Sprint 4 manual review | FINDINGS_AND_RESULTS.md |
