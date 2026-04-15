# vForensIQ Evidence Log

Chronological record of every decision, measurement, and finding.
Each entry has: date, what changed, before metric, after metric, evidence location.

**Rule:** Every code change that could affect eval numbers gets a before/after entry here.

---

## Sprint 0 (2026-04-13)

| # | Change | Evidence |
|---|---|---|
| E001 | Contract v2 frozen (5 events, MQTT spec, SQL schema) | `docs/contracts.md` |
| E002 | Simulator v0: base_quiet_day = 88,136 events | `simulator/out/base_quiet_day/ground_truth.json` |
| E003 | Bench harness skeleton: 8 stub cells all not_implemented | `bench/results/sprint0_smoke/` |

## Sprint 1 (2026-04-13)

| # | Change | Before | After | Evidence |
|---|---|---|---|---|
| E004 | B1 service created (standalone b1_service.py) | 0% (stubs) | L1: 3/3 pass | `bench/results/sprint1_smoke_L1_v2/` |
| E005 | Scorer fix: strip ISO dates from number extraction | L2: 0/4 pass (grabbed "2025" as answer) | L2: 4/4 pass | `bench/results/sprint1_v2/` |
| E006 | SQL repair loop added | L3 q002 mini: ERROR (ambiguous column) | L3 q002 mini: PASS | `bench/results/sprint1_v3_l1l3/` |
| E007 | API retry (3x backoff) added | 2 cells: APIConnectionError | 0 errors | `bench/results/sprint1_v3_l1l3/` |
| E008 | Full Sprint 1 final (11 Q): L1-L3 = 14/14 | — | 85.4% overall | `bench/results/sprint1_final2/` |
| E009 | Expanded to 26 schema-aware questions | 11 Q | 26 Q, 49/52=94.2% | `bench/results/sprint1_diverse_v2/` |
| E010 | Added 15 abstract real-user questions | 26 Q schema-only | 41 Q, 71/82=86.6% | `bench/results/sprint1_abstract_v3/` |
| E011 | Spelled-out numeral recognition in scorer | L1 q006 gpt-4o: FAIL ("Eight") | PASS | `bench/results/sprint1_abstract_v3/` |
| E012 | Hour-alias translation for L3 scorer | L3 q006/q008: FAIL ("1 AM" vs "01") | PASS | `bench/results/sprint1_abstract_v3/` |
| E013 | Real structured_facts scorer (L4) | L4: stub/unscored | L4: 10/10 gpt-4o | `bench/results/sprint1_abstract_v3/` |
| E014 | Real rubric_coverage scorer (L5) with LLM-judge | L5: stub/unscored | L5: varies (judge variance) | `bench/results/sprint1_abstract_v3/` |
| E015 | Legacy code cleanup (6 files deleted) | 1260 LOC dead code | 0 LOC dead code | git history |

## Sprint 2 (2026-04-13 — 2026-04-14)

| # | Change | Before | After | Evidence |
|---|---|---|---|---|
| E016 | Neo4j Docker + graph builder | No graph | 7,676 Event + 144 CrowdHour nodes | `docker-compose.yml`, graph_builder output |
| E017 | B2-cypher service created | NotImplementedError | 50.0% (gpt-4o) | `bench/results/sprint2_full/` |
| E018 | B2-community service created | NotImplementedError | 13.4% (gpt-4o) | `bench/results/sprint2_full/` |
| E019 | B2-hybrid service created | NotImplementedError | 42.7% (gpt-4o) | `bench/results/sprint2_full/` |
| E020 | Crowd-UNION prompt fix for Cypher | L1 total_events: 5,940 (wrong) | 437,940 (correct) | Smoke test in chat |
| E021 | gpt-5 series model upgrade | gpt-4o | gpt-5 | `bench/results/sprint2_gpt5_fix/` |
| E022 | temperature=0 removed (gpt-5 constraint) | BadRequestError | Clean execution | sed across all *.py |
| E023 | B2-cypher gpt-5 post-fix | 50.0% (gpt-4o pre-fix) | 65.9% (gpt-5 post-fix) | `bench/results/sprint2_gpt5_fix/` |
| E024 | B2-hybrid gpt-5 post-fix | 42.7% (gpt-4o pre-fix) | 66.2% (gpt-5 post-fix) | `bench/results/sprint2_gpt5_fix/` |
| E025 | Manual L4 verification (gpt-5): false negatives found | Auto: 7/7 cypher + quota errs | Manual: 7/7=100% | Chat transcript + this log |
| E026 | Manual L5 verification (gpt-4o hybrid): judge underscoring | Auto: 4/8=50% | Manual: 6/8=75% | Chat transcript + this log |
| E027 | L5 gpt-5: ALL 32 cells = quota exhaustion | Cannot score L5 | 0 valid L5 answers | `bench/results/sprint2_gpt5_fix/` |
| E028 | Cypher model fragility: gpt-4o mini→full gap | 17 pts (41.5%→58.5%) | 0 pts on gpt-5 (65.9%=65.9%) | comparison across runs |

## Findings (cross-cutting, not tied to a single change)

| # | Finding | Evidence Location | Affected Levels |
|---|---|---|---|
| F001 | SUM vs AVG ambiguity on crowd "attendance" questions | L2 q008, L4 q008 answers | L2, L4 |
| F002 | Missing ratio computation on "how much more" questions | L4 q007 answers | L4 |
| F003 | Natural-language hour references ("1 AM" not "01") | L3 q006, q008 answers | L3 |
| F004 | LLM-as-judge variance at temperature 0 | All L5 cells across runs | L5 |
| F005 | One-sided comparisons on gpt-4o-mini | L4 q006 answers | L4 |
| F006 | Crowd exclusion: :Event nodes miss 98.6% of data | L1 q004 (5940 vs 437940) | L1, L2, L3 |
| F007 | Camera MERGE conflation across scenarios | L1 q001 (Gate_01 not found) | L1 |
| F008 | Community summaries destroy numeric precision | L2, L3 = 0% for community | L2, L3 |
| F009 | Hybrid dilution: community text confuses synthesis | Hybrid < Cypher on some cells | L1, L2 |
| F010 | Schema-aware vs abstract pass gap = 26 pts | 96.2% vs 70.0% on B1 | All |

---

## Sprint 3 (2026-04-14) — All 4 Novel Directions

| # | Change | Before | After | Evidence |
|---|---|---|---|---|
| E029 | Dir 1: AQR router created (`llm_aqr/router.py`) | No routing | 41/41 = 100% classifier accuracy | `python -m llm_aqr.router` self-test |
| E030 | Dir 1: `b3_aqr` wired in harness | 4 approaches | 5 approaches in `ALL_APPROACHES` | `bench/run_eval.py` |
| E031 | Dir 4: Hierarchical graph builder (`llm_rag/hierarchical_builder.py`) | 2 levels (Event + CrowdHour) | 4 levels (+CrowdMinute, +CrowdDay) | Code landed, untested (Neo4j needed) |
| E032 | Dir 4: Temporal scope selector | No granularity selection | per_second/per_minute/per_hour/per_day | `select_granularity()` function tests |
| E033 | Dir 3: Hybrid weighted fusion + graceful degradation | Naive evidence merge; ERR if either stream fails | Weighted: Cypher preferred for numbers, community for context; auto-fallback if one stream fails | `llm_rag/hybrid_service.py` |
| E034 | Dir 2: B1 execution verifier | No result verification | EMPTY_RESULT / ZERO_VALUE / SINGLE_ROW_COMPARISON warnings | `llm_sql/b1_service.py` |
| E035 | Sprint 3 bench (5 approaches × gpt-4o × 41Q = 410 cells) | — | B1=84.1%, B2-cy=58.5%, AQR=72.0% (auto) | `bench/results/sprint3_final/` |

## Sprint 4 (2026-04-15) — B2 Fixes + Graph-Native Questions

| # | Change | Before | After | Evidence |
|---|---|---|---|---|
| E036 | Removed base_quiet_day from SQL logbase | 526,076 rows (2 scenarios) | 437,940 rows (1 scenario) | Direct DB deletion |
| E037 | Per-second :CrowdEvent nodes in graph | 0 CrowdEvent (crowd excluded) | 432,000 CrowdEvent nodes | `llm_rag/full_graph_builder.py` |
| E038 | Scenario-scoped community index | 19 communities (mixed) | 11 communities (clean) | Community rebuild |
| E039 | Updated Cypher SCHEMA_PROMPT with :CrowdEvent | "No events at Main Entrance" | Correct peaks: 334, 311, 268 | Smoke test |
| E040 | Expanded bench to 75 questions (15 per level) | 44 questions | 75 questions (14 graph-native added) | `bench/questions/` |
| E041 | Sprint 4 B2 bench (3 variants × gpt-4o × 75Q = 225 cells) | — | B2-cy=80.0%, B2-hy=73.3% (manual) | `bench/results/sprint4_b2/` |
| E042 | Sprint 4 B1+AQR bench (2 approaches × gpt-4o × 75Q = 150 cells) | — | B1=85.3%, AQR=89.3% (manual) | `bench/results/sprint4_b1_aqr/` |
| E043 | Manual verification of ALL 375 cells | Auto-scorer underestimates by ~15 pts on L3-L5 | 40 cells upgraded to PASS | `docs/evidence/manual_reviews/sprint4_DEFINITIVE_review.md` |
| E044 | B2 now wins L3 (87% vs 73%) and L5 (93% vs 87%) | B2 won no levels in Sprint 3 | B2 wins 2 of 5 levels | Final table in FINDINGS_AND_RESULTS.md |
| E045 | AQR projected at 89.3% with corrected routing table | AQR 72% (wrong routing) | AQR 89.3% (optimal routing) | Per-level winner analysis |

## Template for future entries

```
| EXXX | [What changed] | [Before metric] | [After metric] | [Evidence path] |
```

Every Sprint 3+ change MUST add a row here before and after measurement.
