# Individual Impact Analysis — Four Candidate Novel Directions

Each direction is analyzed against ACTUAL failure root causes from bench runs.
Data sources: `sprint2_full` (gpt-4o pre-fix) + `sprint2_gpt5_fix` (gpt-5 post-fix).

---

## Current Failure Root Cause Distribution

### B1 (NL→SQL) — 12 failures across both runs
| Root Cause | Count | Levels Affected |
|---|---|---|
| RUBRIC_COVERAGE_LOW (L5 judge) | 6 | L5 only |
| NUMERIC_TOLERANCE_EXCEEDED | 2 | L2 |
| FACT_NUMERIC_MISMATCH | 2 | L4 |
| SET_MATCH_KEYS_MISSING | 1 | L3 |
| VALIDATION_ERROR | 1 | L5 |

**B1 is already strong (85.4%). Its failures are concentrated in L5 (judge variance) and a few L2-L4 edge cases.**

### B2-Cypher — 69 failures across both runs
| Root Cause | Count | Which Direction Fixes It |
|---|---|---|
| QUOTA_EXHAUSTION | 18 | None (infra) |
| NUMERIC_TOLERANCE_EXCEEDED | 16 | Dir 2 (verifier), Dir 4 (granularity) |
| CYPHER_SYNTAX_ERROR | 9 | Dir 2 (multi-agent repair) |
| SET_MATCH_KEYS_MISSING | 5 | Dir 4 (hour-level crowd data) |
| Crowd-exclusion undercounts (got 0/5940 vs expected) | 10 | **Dir 4 (hierarchical graph)** |
| SET_MATCH_VALUES_WRONG | 3 | Dir 4 (correct granularity) |
| RUBRIC_COVERAGE_LOW | 4 | Dir 3 (dual-channel), Dir 1 (route to B1) |
| Other | 4 | Various |

### B2-Hybrid — 73 failures across both runs
| Root Cause | Count | Which Direction Fixes It |
|---|---|---|
| NUMERIC_TOLERANCE_EXCEEDED | 20 | Dir 4 (granularity) |
| QUOTA_EXHAUSTION | 17 | None (infra) |
| CYPHER_SYNTAX_ERROR | 8 | Dir 2 (repair taxonomy) |
| Crowd-exclusion undercounts | 10 | **Dir 4 (hierarchical graph)** |
| SET_MATCH_KEYS/VALUES | 8 | Dir 4 + Dir 3 |
| FACT_NUMERIC_MISMATCH | 3 | Dir 2 (verifier) |
| RUBRIC_COVERAGE_LOW | 3 | Dir 3, or Dir 1 (route away) |
| Other | 4 | Various |

### B2-Community — 143 failures across both runs
| Root Cause | Count | Which Direction Fixes It |
|---|---|---|
| NUMERIC_TOLERANCE_EXCEEDED | 32 | **NONE — fundamental design flaw** |
| QUOTA_EXHAUSTION | 22 | None (infra) |
| SET_MATCH_KEYS_MISSING | 21 | NONE — summaries don't carry keys |
| FACT_NUMERIC_MISMATCH | 14 | NONE — summaries lose precision |
| SET_MATCH_VALUES_WRONG | 11 | NONE |
| Wrong entity counts (got 8, expected 437940) | 20+ | **NONE — can't fix with any direction** |
| RUBRIC_COVERAGE_LOW | 13 | Dir 3 (dual channel adds precision) |

**Community-only is fundamentally broken for L1-L3. No direction can fix it.**

---

## Direction 1: Adaptive Query Router (AQR) — Impact Analysis

### Mechanism
Routes each question to the approach that empirically performs best at that level.

### Cells it would fix (from current data)
The router DOESN'T fix any individual approach — it AVOIDS the weaker approach per level.

**Projected B3-AQR results (picking per-level winner from existing data):**

| Level | Routed to | Source Pass Rate | Current Best Static |
|---|---|---|---|
| L1 (9 Q) | B1 SQL | 100% (18/18) | B1: 100% |
| L2 (8 Q) | B1 SQL | 94% (15/16) | B1: 94% |
| L3 (8 Q) | B2 Cypher (gpt-5 post-fix) | 94% (15/16) | Tie B1/B2: 94% |
| L4 (8 Q) | B2 Cypher | 100% (14/14 manually verified) | B2: 100% |
| L5 (8 Q) | B2 Hybrid | 75% (6/8 manually verified) | B2-hybrid: 75% |

**Projected AQR overall: ~93%** (68/73 verifiable cells)
**Best single approach overall: 85.4% (B1)**
**AQR improvement: +8 points**

### Evidence needed to prove this works
- [ ] Classification accuracy of the router itself (must be >90%)
- [ ] End-to-end bench run with `b3_aqr` as a real approach in the harness
- [ ] Latency comparison (AQR adds classification overhead — how much?)
- [ ] Ablation: what happens if router misclassifies? (route L1 to B2 by mistake)
- [ ] Token cost comparison (AQR should save tokens by avoiding heavy B2 for simple queries)

### Data to collect during Sprint 3
- Router classification confusion matrix (predicted level vs gold level)
- Per-cell routing decision + actual approach selected
- Latency breakdown: router time + backend time vs direct-backend time
- Token usage per cell (already in envelope's `llm_calls`)
- Misclassification impact: accuracy when router is wrong

---

## Direction 2: Multi-Agent SQL-of-Thought (B1 upgrade) — Impact Analysis

### Mechanism
Decompose B1 into sub-agents: Schema Linker → Query Planner → SQL Generator → Execution Verifier → Taxonomy-Guided Repairer.

### Cells it would fix
From B1's 12 failures:

| Failure | Count | Would Dir 2 fix it? | How? |
|---|---|---|---|
| RUBRIC_COVERAGE_LOW (L5) | 6 | MAYBE 2-3 | Query planner decomposes L5 into sub-queries; verifier checks each sub-answer covers a rubric item |
| NUMERIC_TOLERANCE_EXCEEDED (L2) | 2 | MAYBE 1 | Verifier checks result plausibility (e.g., "is 81.87 reasonable for food court lunch?") |
| FACT_NUMERIC_MISMATCH (L4) | 2 | YES 1-2 | Query planner explicitly plans both entities in comparisons; verifier demands ratio |
| SET_MATCH_KEYS_MISSING (L3) | 1 | YES 1 | Verifier checks GROUP BY result has all expected keys |
| VALIDATION_ERROR (L5) | 1 | YES 1 | Taxonomy repairer handles the specific error type |

**Projected fix: 4-7 of 12 B1 failures → B1 from 85.4% → 88-90%**

### Evidence needed
- [ ] Before/after on the same 41 questions (old B1 vs multi-agent B1)
- [ ] Per-agent latency breakdown (schema linker time, planner time, etc.)
- [ ] Which specific agent catches which error type (to prove the taxonomy works)
- [ ] Token overhead (5 LLM calls vs 2 — how much more expensive?)
- [ ] Ablation: remove one agent at a time, measure degradation

### Data to collect
- Per-question agent trace: what each agent produced
- Error categorization before/after the taxonomy repairer
- Sub-query decomposition for L4/L5 questions
- Verification check results (what did the verifier flag?)

---

## Direction 3: Dual-Channel Retrieval (B2 upgrade) — Impact Analysis

### Mechanism
Fuse Cypher precision with community semantic breadth via weighted combination.

### Cells it would fix
From B2-Hybrid's failures (already IS dual-channel, but naively):

| Failure | Count | Would Dir 3 fix it? | How? |
|---|---|---|---|
| NUMERIC_TOLERANCE_EXCEEDED | 20 | MAYBE 5-8 | Weighted fusion prefers Cypher numbers when available; falls back to community only when Cypher errors |
| CYPHER_SYNTAX_ERROR | 8 | YES 5-6 | If Cypher fails, fusion automatically weights community 100%; currently hybrid errors when cypher errors |
| RUBRIC_COVERAGE_LOW | 3 | MAYBE 1-2 | Community adds breadth; fusion strategy explicitly merges coverage |
| Crowd-exclusion undercounts | 10 | NO | Fundamental graph schema issue, not fusion issue |

**Projected fix: 10-16 of hybrid's 73 failures → Hybrid from 42.7% → 55-60%**
*Note: subsumed by Direction 4 which fixes the crowd issue directly.*

### Evidence needed
- [ ] Fusion weight sensitivity analysis (α=0.0 pure community → α=1.0 pure Cypher)
- [ ] Per-cell: which channel contributed the correct answer?
- [ ] Failure mode when both channels are wrong vs when one saves the other

---

## Direction 4: Query-Adaptive Hierarchical Graph — Impact Analysis

### Mechanism
4-level graph (per-second → per-minute → per-hour → per-day). Temporal scope selector picks the right granularity.

### Cells it would fix
This is the HIGHEST IMPACT direction for B2 because it fixes the crowd-exclusion problem at the root.

From B2-Cypher's failures (gpt-4o pre-fix):

| Failure | Count | Would Dir 4 fix it? | How? |
|---|---|---|---|
| Crowd-exclusion (got 0/5940 for counts) | 10 | **YES ALL 10** | Per-second :Event nodes for crowd exist; COUNT works natively |
| NUMERIC_TOLERANCE_EXCEEDED | 16 | YES 8-10 | Correct granularity → correct AVG/MAX |
| SET_MATCH_KEYS_MISSING (hour format) | 5 | YES 3-4 | Per-minute level provides finer bucketing |
| SET_MATCH_VALUES_WRONG | 3 | YES 2-3 | Correct base data → correct aggregates |
| CYPHER_SYNTAX_ERROR | 9 | MAYBE 2-3 | Simpler queries needed when graph has right level |

**Projected fix for B2-Cypher: 25-30 of 69 failures → Cypher from 50% → 68-75%**

From B2-Hybrid: similar improvement → **Hybrid from 42.7% → 60-70%**

The crowd-inclusion prompt fix (Sprint 2) already recovered SOME of this (50% → 66% on gpt-5). Direction 4 goes further by making the graph schema correct rather than patching via prompt.

### Evidence needed
- [ ] Before/after per-level pass rates (old graph vs hierarchical graph)
- [ ] Granularity selection accuracy (did the selector pick the right level?)
- [ ] Graph build time at each granularity (per-second = 6M nodes; is it tractable?)
- [ ] Community detection quality at each granularity level
- [ ] Memory/disk usage comparison (small graph vs full graph)
- [ ] The specific Sprint 2 failure cases as motivating examples

### Data to collect
- Per-question: which granularity was selected and why
- Node/edge counts at each granularity level
- Graph build time per level
- Louvain community count and quality per level
- Before/after comparison on the exact same questions that failed in Sprint 2

---

## Comparative Impact Summary

| Direction | B1 impact | B2-Cypher impact | B2-Hybrid impact | New "B3" impact | Implementation effort |
|---|---|---|---|---|---|
| **Dir 1: AQR** | none (uses B1 as-is) | none (uses B2 as-is) | none (uses as-is) | **+8 pts (85→93%)** | 1 sprint |
| **Dir 2: Multi-Agent B1** | **+3-5 pts (85→90%)** | none | none | +1-3 pts (via improved B1 backend) | 1 sprint |
| **Dir 3: Dual-Channel B2** | none | +5-8 pts | **+12-17 pts (43→60%)** | +2-5 pts (via improved B2 backend) | 0.5 sprint |
| **Dir 4: Hierarchical Graph** | none | **+18-25 pts (50→75%)** | **+17-27 pts (43→70%)** | +5-10 pts (via improved B2 backends) | 1.5 sprints |

---

## Recommended Priority Stack

### If you have 1 sprint: **Direction 1 (AQR) alone**
- +8 pts to headline number
- Novel contribution
- Doesn't require fixing B2 first
- Produces the "B3-routed at 93%" result

### If you have 2 sprints: **Direction 1 + Direction 4**
- AQR gives the headline; Hierarchical Graph strengthens the B2 backends
- Combined: B3 routes to improved-B2 for L3-L5, giving ~95%+ projected

### If you have 3 sprints: **Direction 1 + Direction 4 + Direction 2**
- Full system: routed to multi-agent B1 (for L1-L2) or hierarchical-graph B2 (for L3-L5)
- Projected ~97%+
- Strongest thesis but highest implementation risk

### NOT recommended: Direction 3 alone
- Subsumed by Direction 4; low standalone novelty
