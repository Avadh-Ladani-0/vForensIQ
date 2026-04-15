# Latency, Token Usage, and Cost Profile — All Approaches

Raw data: `docs/evidence/approach_profiles/latency_raw.csv`

---

## 1. Overall Latency (gpt-4o series)

| Approach | p50 latency | p95 latency | Avg tokens/cell | LLM calls/cell |
|---|---|---|---|---|
| **B1 NL→SQL** | **3.9s** | 11.6s | 1,759 | 2.0 |
| B2 Cypher | 3.5s | 14.1s | 2,384 | 2.2 |
| B2 Community | **2.3s** | 4.8s | 886 | 1.0 |
| B2 Hybrid | 4.3s | 15.7s | 2,408 | 2.2 |

### Key observations:
- **B2-Community is fastest** (2.3s p50) because it makes only 1 LLM call (retrieval is embedding-based, not LLM-based)
- **B1 and B2-Cypher are comparable** (~3.5-3.9s p50) — both make 2 LLM calls (generate + synthesize)
- **B2-Hybrid is slowest** (4.3s p50) — runs Cypher + Community + synthesis (effectively 2.2 calls with Neo4j + Chroma overhead)
- **P95 spread is large** for Cypher/Hybrid (14-16s) due to repair loops on complex queries

## 2. GPT-5 vs GPT-4o Latency Impact

| Approach | gpt-4o p50 | gpt-5 p50 | Slowdown |
|---|---|---|---|
| B2 Cypher | 3.5s | **24.2s** | **6.9×** |
| B2 Hybrid | 4.3s | **35.4s** | **8.2×** |
| B2 Community | 2.3s | **13.0s** | **5.7×** |

**GPT-5 is 6-8× slower than GPT-4o per cell.** This is why the gpt-5 bench took 2.5 hours vs 30 min for gpt-4o. For production deployment, the latency vs accuracy tradeoff is significant.

## 3. Per-Level Latency (gpt-4o, median ms)

| Level | B1 SQL | B2 Cypher | B2 Community | B2 Hybrid |
|---|---|---|---|---|
| L1 (simple lookup) | 2.7s | 2.6s | 2.2s | 3.0s |
| L2 (aggregation) | 2.9s | 2.7s | 1.8s | 3.7s |
| L3 (GROUP BY) | 4.4s | 3.5s | 3.2s | 4.2s |
| L4 (comparative) | 4.5s | 5.1s | 2.8s | 5.4s |
| L5 (narrative) | **7.9s** | **12.0s** | 3.7s | **15.3s** |

### Level-latency findings:
- **L1-L2 are fast across all approaches** (~2-3s) — simple queries, short answers
- **L5 is the latency bottleneck** — B2-Cypher takes 12s, Hybrid takes 15.3s (complex multi-aspect Cypher + large synthesis prompt)
- **Community is consistently fast** at every level (~2-4s) because retrieval is constant-time (embedding lookup), regardless of question complexity
- **B1 L5 at 7.9s is 2× cheaper than B2-Hybrid L5 at 15.3s** — but B2-Hybrid produces better narratives

## 4. Token Usage Per Cell (gpt-4o, average)

| Level | B1 SQL | B2 Cypher | B2 Community | B2 Hybrid |
|---|---|---|---|---|
| L1 | 1,326 | 1,341 | 850 | 1,700 |
| L2 | 1,425 | 1,367 | 830 | 1,709 |
| L3 | 1,621 | 1,814 | 878 | 1,929 |
| L4 | 1,694 | 1,906 | 891 | 2,146 |
| L5 | **2,782** | **5,621** | 984 | **4,643** |

### Token findings:
- **B2-Cypher L5 uses 2× the tokens of B1 L5** (5,621 vs 2,782) — the Cypher schema prompt is larger than the SQL schema prompt
- **Community is token-cheap** (~850-984 per cell regardless of level) — retrieval is non-LLM
- **Hybrid L5 = 4,643 tokens** — less than Cypher alone because community retrieval replaces some LLM work

## 5. Cost Estimation (per 41-question bench run at OpenAI pricing)

Approximate pricing (gpt-4o, April 2026):
- Input: $2.50/1M tokens, Output: $10.00/1M tokens
- Assuming 70% input / 30% output split

| Approach | Avg tokens/cell | Cells (41Q × 1 model) | Total tokens | Estimated cost |
|---|---|---|---|---|
| B1 SQL | 1,759 | 41 | 72,119 | **$0.32** |
| B2 Cypher | 2,384 | 41 | 97,744 | $0.43 |
| B2 Community | 886 | 41 | 36,326 | **$0.16** |
| B2 Hybrid | 2,408 | 41 | 98,728 | $0.44 |
| **Full 4-approach run** | — | 164 | 304,917 | **$1.35** |

**Community is cheapest** ($0.16/run) but least accurate (2-13%).
**B1 is best cost-performance** ($0.32/run at 85% accuracy).
**Full matrix (328 cells, 2 models)** costs ~$2.70 per run.

## 6. Latency Impact of Each Novel Direction

### Direction 1: AQR (Adaptive Query Router)

| Component | Added latency | Notes |
|---|---|---|
| Query classifier | +50-100ms | Zero-shot LLM classification OR rule-based (no LLM) |
| Backend selection | +0ms | Routing logic is in-memory |
| **Net impact** | **+50-100ms per cell** | Negligible vs 2-15s backend latency |

**Token impact:** +200-400 tokens for the classification call (if LLM-based), OR 0 tokens (if rule-based). Saves tokens on average because L1-L3 questions avoid the expensive B2-Hybrid path (saves ~700 tokens/cell for 60% of questions).

**Net cost:** AQR is CHEAPER than always running Hybrid, and faster.

### Direction 2: Multi-Agent B1

| Component | Added latency | Notes |
|---|---|---|
| Schema Linker agent | +1-2s | Extra LLM call |
| Query Planner agent | +1-2s | Extra LLM call |
| Execution Verifier | +0.5-1s | SQL re-execution + LLM check |
| Taxonomy Repairer | +0-2s | Only fires on error (~15% of cells) |
| **Net impact** | **+2-5s per cell (B1 goes from 3.9s to 6-9s)** | ~2× slower |

**Token impact:** ~3-5× more tokens per B1 cell (currently 1,759 → ~5,000-8,000). Three extra LLM calls.

**Cost impact:** B1 cost triples ($0.32 → ~$1.00/run). Significant for production; acceptable for eval.

### Direction 3: Dual-Channel B2

| Component | Added latency | Notes |
|---|---|---|
| Fusion scoring | +0.3-0.5s | Compare Cypher row count vs community similarity |
| **Net impact** | **+0.3-0.5s** | Negligible; already parallel |

**Token impact:** +200-400 tokens for fusion scoring prompt. Minimal.

### Direction 4: Hierarchical Graph

| Component | Added latency | Notes |
|---|---|---|
| Granularity selector | +0.5-1s | LLM or rule-based temporal-scope classification |
| Graph query at selected level | +0 to -2s | Simpler queries at right granularity are FASTER |
| Graph BUILD time | +5-30min | Per-second level adds 432k nodes; one-time cost |
| **Net per-query impact** | **~0s (wash)** | Selector adds time; simpler queries save time |

**Token impact:** +200-400 tokens for granularity selection. Same tokens for the actual query.

**Build cost:** Graph build goes from 7s → ~5-30 min (per-second nodes are 100× more). But this is one-time, not per-query.

## 7. Latency-Accuracy Tradeoff Table (the thesis visualization)

| Approach | Accuracy | p50 Latency | Cost/run | Pareto optimal? |
|---|---|---|---|---|
| B2-Community | 13% | 2.3s | $0.16 | No (too low accuracy) |
| B1 SQL | **85%** | 3.9s | $0.32 | **Yes** (best accuracy/cost) |
| B2-Cypher | 66% | 3.5s | $0.43 | No (lower accuracy than B1 at similar latency) |
| B2-Hybrid | 66% | 4.3s | $0.44 | No (same accuracy as Cypher, slower) |
| **B3-AQR (projected)** | **~93%** | **~3.5s** | **~$0.30** | **Yes** (best accuracy AND saves cost) |

**AQR is projected to be Pareto-optimal** — it matches or beats B1's latency (by routing simple queries to fast B1 and only using slow B2-Hybrid for L5), while achieving higher accuracy, at lower total token cost.
