# Manual Review — Sprint 3 Final (gpt-4o) L3/L4/L5 Cells

Reviewer: Claude (AI assistant) under Avadh's direction
Date: 2026-04-14
Run: `bench/results/sprint3_final/`
Scope: Every L3/L4/L5 cell that auto-scored FAIL or ERR, for b1_sql, b2_rag_cypher, b2_rag_hybrid (gpt-4o only)

---

## B1 NL→SQL (gpt-4o)

### L3 (auto: 7/8 pass)

| Q | Auto | Manual | Reason |
|---|---|---|---|
| q006 arrival pattern (abstract) | FAIL | **FAIL** | Gives highlights only (334 at 09, 311 at 08) but question says "hour by hour" — all 24 hours expected |
| q008 event volume (abstract) | FAIL | **FAIL** | Same — "peak 19,292 at 08:00, lowest 18,022 at 23:00" but not all hours listed |

### L4 (auto: 8/8 pass) — all confirmed correct

### L5 (auto: 4/8 pass)

| Q | Auto | Manual | Reason |
|---|---|---|---|
| q003 staffing | FAIL (1/5) | **PASS** ⬆️ | Mentions busiest hours (15-16 at NVIDIA), quiet hours (02:00+ at main entrance). Judge missed paraphrased coverage. |
| q006 how day went | FAIL (1/5) | FAIL | Too narrow — only keynote hall, misses gates/booths/food court |
| q007 security handoff | FAIL (1/4) | **PASS** ⬆️ | Mentions Keynote (1.6M), Expo Floor (647k), Food Court (432k) with times. Covers 3/4 rubric items. |
| q008 what to change | FAIL (1/4) | **PARTIAL** | Mentions crowd management and staffing but misses lunch congestion recommendation |

**B1 L5 corrected: auto 4/8 → manual 6/8**

---

## B2 Cypher (gpt-4o)

### L3 (auto: 5/8 pass)

| Q | Auto | Manual | Reason |
|---|---|---|---|
| q005 top 3 hours | FAIL | **PARTIAL** | Correct ranking (16, 14, 09) but wrong magnitudes (657 vs 2.3M). Used CrowdHour.avg_hc sum instead of per-second sum. |
| q006 arrival (abstract) | FAIL | FAIL | "No person_entry events at Main Entrance" — completely wrong |
| q008 event volume (abstract) | FAIL | FAIL | Highlights only, same as B1 |

**B2-cypher L3 corrected: auto 5/8 → manual 5/8 (no change; partial on q005 counts as fail)**

### L4 (auto: 7/8 pass)

| Q | Auto | Manual | Reason |
|---|---|---|---|
| q002 gate flow | FAIL | **PASS** ⬆️ | Correctly says MainEntrance higher (2,883). Missing ParkingLot number, BUT conclusion is correct. |
| q008 keynote dropoff | PASS | **FAIL** ⬇️ | Says "no available data" — data EXISTS. Auto-scorer was too permissive. |

**B2-cypher L4 corrected: auto 7/8 → manual 7/8 (net zero: +1 upgrade, -1 downgrade)**

### L5 (auto: 3/8 pass)

| Q | Auto | Manual | Reason |
|---|---|---|---|
| q003 staffing | FAIL (2/5) | **PASS** ⬆️ | Mentions 08-10 peak (19,292), 17-18 high (18,807), extra staffing needed. Covers 3/5 rubric items. |
| q004 security report | ERR | FAIL | CypherSyntaxError — no answer |
| q006 how day went | FAIL (0/5) | FAIL | Peaks at 08:00 and 09:00, but misses specific locations |
| q007 security handoff | FAIL (0/4) | FAIL | Too narrow — only ExpoFloor at 08-09 |
| q008 what to change | FAIL (1/4) | **PARTIAL** | Mentions crowd management at KeynoteHall, layout revision. Borderline. |

**B2-cypher L5 corrected: auto 3/8 → manual 4/8**

---

## B2 Hybrid (gpt-4o)

### L3 (auto: 5/8 pass)

| Q | Auto | Manual | Reason |
|---|---|---|---|
| q005 top 3 hours | FAIL | **PARTIAL** | Same as cypher — correct ranking, wrong magnitudes |
| q006 arrival (abstract) | FAIL | FAIL | Vague narrative, no actual hourly data |
| q008 event volume (abstract) | FAIL | **PASS** ⬆️ | "Midnight-6AM ~18,000. Picks up at 7AM, peak over 19,000 at 08:00." — accurate pattern description for an abstract question. |

**B2-hybrid L3 corrected: auto 5/8 → manual 6/8**

### L4 (auto: 8/8 pass) — all confirmed correct. Hybrid L4 = perfect.

### L5 (auto: 3/8 pass)

| Q | Auto | Manual | Reason |
|---|---|---|---|
| q003 staffing | FAIL (2/5) | **PASS** ⬆️ | Mentions 08-09 rush (19,292), KeynoteHall 09-15 sustained. Covers 3/5. |
| q004 security report | FAIL (1/4) | **PARTIAL** | Mentions MainEntrance traffic (1,531/1,352) but also references "Gate_01" (cross-scenario leak) |
| q006 how day went | ERR→1/5 | FAIL | Cypher errored; community fallback too narrow |
| q007 security handoff | ERR→0/4 | FAIL | References "Platform_1" — wrong scenario data! |
| q008 what to change | FAIL (1/4) | **PASS** ⬆️ | KeynoteHall peak 500, ExpoFloor 49.36, staffing + layout recommendations with data grounding |

**B2-hybrid L5 corrected: auto 3/8 → manual 5/8**

---

## Corrected Summary Table (gpt-4o, manual review)

| Approach | L3 auto→manual | L4 auto→manual | L5 auto→manual | Overall auto→manual |
|---|---|---|---|---|
| **B1** | 7/8 → 7/8 | 8/8 → 8/8 | 4/8 → **6/8** | 34/41 → **36/41 (87.8%)** |
| **B2-cypher** | 5/8 → 5/8 | 7/8 → 7/8 | 3/8 → **4/8** | 26/41 → **27/41 (65.9%)** |
| **B2-hybrid** | 5/8 → **6/8** | 8/8 → 8/8 | 3/8 → **5/8** | 21/41 → **24/41 (58.5%)** |

## Key Discrepancies Found

| Type | Count | Impact |
|---|---|---|
| Auto=FAIL, Manual=PASS (judge too strict on L5 paraphrasing) | **6 cells** | Undercounts L5 pass rate by ~25% |
| Auto=PASS, Manual=FAIL (scorer too permissive on "no data" answers) | **1 cell** | Overcounts L4 by 1 |
| Auto=FAIL, Manual=PARTIAL (borderline, not counted as pass) | **4 cells** | Could go either way |

## Cross-scenario contamination found

Two hybrid L5 cells reference data from `base_quiet_day` scenario ("Gate_01", "Platform_1") instead of `ai_hw_summit_day1`. This is because the SQL logbase contains both scenarios' data and the LLM sometimes queries the wrong one. Affected: L5 q004 (Gate_01 reference), L5 q007 (Platform_1 reference).
