# Conclusions and Findings Register

Every conclusion derived from testing, with the evidence chain that supports it.
Updated after each benchmark run. Each conclusion has a STATUS: CONFIRMED / PROVISIONAL / INVALIDATED.

---

## Accuracy Conclusions

### C-ACC-01: B1 (NL→SQL) dominates aggregation queries (L1-L3)
**Status:** CONFIRMED
**Evidence:** L1=100%, L2=94%, L3=94% on gpt-4o (sprint1_abstract_v3). No B2 variant exceeds B1 on L1 or L2.
**Implication:** For production CCTV analytics where most queries are counts/aggregates, B1 is sufficient.

### C-ACC-02: B2 (Graph-RAG) dominates comparative reasoning (L4)
**Status:** CONFIRMED (manually verified)
**Evidence:** B2-cypher L4=100% on gpt-4o and gpt-5 (manually verified, sprint2_full + sprint2_gpt5_fix). B1 L4=88%. Graph traversal enables relational comparison queries (A vs B, ranking) that SQL handles less naturally.
**Implication:** Comparative questions should be routed to graph-RAG.

### C-ACC-03: B2-Hybrid produces the best narrative answers (L5)
**Status:** CONFIRMED (manually verified, auto-scorer underestimates by 25%)
**Evidence:** Manual review: hybrid L5 = 75% (6/8) on gpt-4o. Auto-scorer said 50% (4/8). Two false negatives due to judge failing to recognize paraphrased rubric items.
**Implication:** Open-ended briefings should be routed to hybrid. LLM-as-judge scores should be treated as lower bounds.

### C-ACC-04: Community-only retrieval is not viable for structured event data
**Status:** CONFIRMED
**Evidence:** B2-community = 2.4-13.4% across all model configs. 0% on L2 and L3 (every run). Hierarchical summaries destroy the numeric precision needed for aggregation queries.
**Implication:** Community summaries are useful ONLY as a component inside hybrid, never standalone.

### C-ACC-05: No single approach dominates all levels
**Status:** CONFIRMED
**Evidence:** B1 wins L1-L2, ties L3, loses L4, loses L5. B2-cypher wins L4. B2-hybrid wins L5. Comparison table in FINDINGS_AND_RESULTS.md §9.
**Implication:** Adaptive routing is the natural architecture for maximizing overall accuracy.

### C-ACC-06: Prompt-only crowd-UNION guidance substantially improves B2
**Status:** CONFIRMED
**Evidence:** B2-cypher went from 50.0% (gpt-4o pre-fix) to 65.9% (gpt-5 post-fix). L1 went from 56% to 89%. L3 went from 50% to 100%. Evidence entries E020, E023.
**Implication:** Graph-RAG on aggregated schemas requires explicit query-reformulation guidance in the prompt.

---

## Latency Conclusions

### C-LAT-01: All approaches answer within 5s median on L1-L3
**Status:** CONFIRMED
**Evidence:** B1 p50=2.7-4.4s, B2-cypher p50=2.6-3.5s, B2-community p50=1.8-3.2s, Hybrid p50=3.0-4.2s on gpt-4o for L1-L3.
**Implication:** Latency is not a differentiator for simple queries. Accuracy drives the choice.

### C-LAT-02: L5 narrative queries are 2-4× slower than L1-L3
**Status:** CONFIRMED
**Evidence:** B1 L5 p50=7.9s (vs L1=2.7s). Hybrid L5 p50=15.3s (vs L1=3.0s). Complex queries generate longer SQL/Cypher, larger result sets, and longer synthesis prompts.
**Implication:** L5 latency budget should be 10-20s; real-time UX should show a progress indicator.

### C-LAT-03: GPT-5 is 6-8× slower than GPT-4o
**Status:** CONFIRMED
**Evidence:** B2-cypher gpt-4o p50=3.5s, gpt-5 p50=24.2s (6.9× slower). Hybrid gpt-4o p50=4.3s, gpt-5 p50=35.4s (8.2× slower). Latency_raw.csv.
**Implication:** GPT-5 is not viable for real-time CCTV analytics at current speeds. Use gpt-4o for production; gpt-5 for offline batch evaluation only.

### C-LAT-04: AQR would be Pareto-optimal (projected)
**Status:** PROVISIONAL (not yet implemented)
**Evidence:** Projected: routes L1-L3 to B1 (3.9s p50) and L4-L5 to B2 (5-15s p50). Average p50 across all levels ≈ 3.5s. B1 alone = 3.9s, Hybrid alone = 4.3s. AQR routing overhead = ~50-100ms.
**Implication:** AQR saves latency AND improves accuracy — rare win-win.

---

## Model Conclusions

### C-MOD-01: SQL generation is model-robust; Cypher generation is model-fragile (on gpt-4o)
**Status:** CONFIRMED
**Evidence:** B1 gap = 2.4 pts (85.4% mini vs 87.8% full). B2-cypher gap = 17.0 pts (41.5% mini vs 58.5% full) on gpt-4o.
**Implication:** Cypher is under-represented in gpt-4o pretraining. Organizations must use the full model for Cypher.

### C-MOD-02: GPT-5 eliminated the Cypher model gap
**Status:** CONFIRMED
**Evidence:** B2-cypher gpt-5 = 65.9%, gpt-5-mini = 65.9%. Zero gap. Evidence entry E028.
**Implication:** GPT-5 has significantly better Cypher pretraining than GPT-4o. Future model generations may equalize SQL and Cypher generation quality.

### C-MOD-03: gpt-4o-mini gives one-sided comparisons
**Status:** CONFIRMED (observed, not universal)
**Evidence:** L4 q006 on gpt-4o-mini states only the morning total without the evening total. gpt-4o does not show this. Finding F005.
**Implication:** Model-specific behavioral testing is needed per query type.

---

## Evaluation Methodology Conclusions

### C-EVL-01: Schema-aware vs abstract question gap = 26 points
**Status:** CONFIRMED
**Evidence:** B1 schema-aware = 96.2%, abstract = 70.0%, gap = 26.2 pts. Evidence entry E010, finding F010.
**Implication:** Standard schema-aware benchmarks (Spider, BIRD) overestimate real-world LLM querying capability by ~26 points.

### C-EVL-02: LLM-as-judge underscores paraphrased coverage by ~25%
**Status:** CONFIRMED (for L5 rubric scoring)
**Evidence:** Manual review of hybrid L5: auto=50%, manual=75%, underscoring=25%. Manual review record in `manual_reviews/L4_L5_manual_review_sprint2.md`.
**Implication:** L5 scores should be treated as lower bounds. Recommend majority voting (N=3) or manual verification for thesis-grade L5 claims.

### C-EVL-03: L1-L5 taxonomy exposes behaviors invisible to flat benchmarks
**Status:** CONFIRMED
**Evidence:** Five systematic behaviors (F001-F005) only surfaced on abstract questions at specific levels. SUM/AVG confusion (L2), missing ratios (L4), hour prose (L3), judge variance (L5), one-sided comparisons (L4/mini). None would surface on a flat benchmark without level stratification.
**Implication:** The L1-L5 taxonomy is a methodological contribution of the thesis.

---

## Architecture Conclusions

### C-ARC-01: Crowd aggregation in graphs creates a semantic gap
**Status:** CONFIRMED
**Evidence:** Compressing 432k crowd samples/day → 144 CrowdHour nodes causes :Event-based Cypher to miss 98.6% of data. Finding F006. Evidence E020 (pre-fix: 5940 vs 437940), E023 (post-fix: prompt guidance recovered most of the gap).
**Implication:** Time-series data in graphs needs either atomic-node representation OR mandatory query-reformulation guidance. This is a contribution-level finding.

### C-ARC-02: Hybrid does not automatically dominate component approaches
**Status:** CONFIRMED
**Evidence:** B2-hybrid (42.7% pre-fix) < B2-cypher (50.0% pre-fix) on gpt-4o. Community text diluted Cypher precision in the synthesis step. Finding F009.
**Implication:** Naive evidence fusion can be harmful. Weighted or conditional fusion (prefer Cypher when available, fall back to community) is required.

### C-ARC-03: Camera identity conflation across scenarios
**Status:** CONFIRMED
**Evidence:** MERGE by camera_id collapsed base_quiet_day CAM_02 (Platform_1) with ai_hw_summit CAM_02 (Gate_ParkingLot). Finding F007.
**Implication:** Multi-scenario graph deployments need scenario-scoped node keys.

---

## Sprint 4 Updates (2026-04-15) — Final Results

### C-ACC-01 UPDATE: B1 dominates L1-L2 but NOT L3
**Status:** UPDATED — B1 wins L1 (100%), L2 (67%), L4 (100%). But B2 NOW WINS L3 (87% vs 73%) after per-second CrowdEvent fix.
**Evidence:** Sprint 4 manual review. `sprint4_DEFINITIVE_review.md`.

### C-ACC-02 UPDATE: B2 graph-RAG wins L3 and L5
**Status:** CONFIRMED (upgraded from Sprint 3 where B2 won no levels)
**Evidence:** B2-Cypher L3=87%, B2-Hybrid L5=93%. Sprint 4 manual review.
**Implication:** Graph-RAG has genuine advantages on multi-dimensional aggregation (when crowd data is at per-second granularity) and narrative synthesis (community summaries add breadth).

### C-ACC-07: AQR achieves 89.3% — highest of all approaches
**Status:** CONFIRMED
**Evidence:** Routes L1,L2,L4→B1; L3→B2-Cypher; L5→B2-Hybrid. 67/75 cells pass.
**Implication:** Adaptive routing outperforms any single approach by exploiting complementary strengths.

### C-ACC-08: Per-second CrowdEvent nodes are essential for graph-RAG accuracy
**Status:** CONFIRMED
**Evidence:** B2-Cypher jumped from 58.7% (Sprint 3, no CrowdEvent) to 80.0% (Sprint 4, with CrowdEvent).
**Implication:** Graph-RAG on time-series data MUST include atomic-granularity nodes, not just aggregates.

### C-ACC-09: Auto-scorer underestimates L3-L5 by ~15 points
**Status:** CONFIRMED
**Evidence:** 40 cells upgraded from auto-FAIL to manual-PASS. Breakdown: L3 partial listings (14), L4 formatting (9), L5 judge paraphrasing (17).
**Implication:** Manual verification is mandatory for thesis-grade L3-L5 claims. Auto-scorer is a lower bound only.

### C-ARC-03 UPDATE: Scenario conflation FIXED
**Status:** RESOLVED — base_quiet_day removed from logbase, communities rebuilt scenario-scoped.

---

## Template for future conclusions

```
### C-{category}-NN: [One-line conclusion]
**Status:** CONFIRMED / PROVISIONAL / INVALIDATED
**Evidence:** [Specific bench run, evidence entry, or manual review that supports this]
**Implication:** [What this means for the system design or thesis narrative]
```

Add new conclusions after EVERY bench run or significant code change.
Last updated: 2026-04-14
```
