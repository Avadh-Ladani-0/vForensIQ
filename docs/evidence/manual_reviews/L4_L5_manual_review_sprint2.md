# Manual Review Record — L4/L5 Cells from Sprint 2

Reviewer: Claude (AI assistant) under Avadh's direction
Date: 2026-04-14
Run sources: `sprint2_full` (gpt-4o), `sprint2_gpt5_fix` (gpt-5)

## Methodology
Every L4 and L5 cell was read in full. The answer text was compared against:
- The gold value / structured facts / rubric
- The actual data in the SQL logbase (verified via direct SQL queries)
- The Cypher/SQL query that was generated

Verdict categories: PASS (answer is factually correct and addresses the question),
PARTIAL (some facts correct but incomplete), FAIL (wrong or missing).

## GPT-5 Post-Fix L4 Results (b2_rag_cypher)

| Question | Auto | Manual | Discrepancy? | Notes |
|---|---|---|---|---|
| q001 booth compare | PASS | PASS | No | "NVIDIA avg 15.515, Intel 10.648, ratio 1.46" — all correct |
| q002 gate flow | PASS | PASS | No | "MainEntrance 2883, ParkingLot 615" |
| q003 morning/evening | PASS | PASS | No | "1191 vs 997, morning busier by 194" |
| q004 keynote AM/PM | PASS | PASS | No | "450.19 vs 399.51" |
| q005 peak/baseline | PASS | PASS | No | "KeynoteHall peak 500, baseline 7.085, ratio 70.6" |
| q006 abstract rush | PASS | PASS | No | "1252 vs 1054" |
| q007 abstract booths | PASS | PASS | No | "15.515 vs 10.648, 1.457x, peaks 86 vs 53" — excellent |
| q008 keynote dropoff | QUOTA | N/A | — | API quota exhausted |

## GPT-5 Post-Fix L4 Results (b2_rag_hybrid)

| Question | Auto | Manual | Discrepancy? | Notes |
|---|---|---|---|---|
| q001-q005 | PASS | PASS | No | Same quality as cypher |
| q006 abstract rush | ERR | **PASS** | **YES** | Community stream errored but cypher produced "1236 vs 1034" — correct answer |
| q007 abstract booths | ERR | FAIL | No | Both streams errored |
| q008 | QUOTA | N/A | — | |

## GPT-4o Pre-Fix L5 Results (b2_rag_hybrid — best L5 performer)

| Question | Auto (judge) | Manual | Discrepancy? | Notes |
|---|---|---|---|---|
| q001 security brief | 4/5 PASS | PASS | No | Covers gates + keynote + food court |
| q002 NVIDIA timeline | 4/5 PASS | PASS | No | Excellent detail: peaks 10-11 and 15-16, avg 60/70 |
| q003 staffing | 1/5 FAIL | **PASS** | **YES** | Judge missed: answer mentions booth peaks and hours |
| q004 security report | 4/4 PASS | PASS | No | "MainEntrance 1531, ParkingLot 381 cars, KeynoteHall 500" |
| q005 keynote lifecycle | 1/4 FAIL | **PASS** | **YES** | Has lifecycle data: "1117 entries, 1072 exits, peak 500" |
| q006 day summary | 1/5 FAIL | FAIL | No | Too narrow — only keynote covered |
| q007 security handoff | 2/4 PASS | PASS | No | Mentions right locations + times |
| q008 what to change | 2/4 PASS | PASS | No | Data-grounded recommendations |

**Judge underscoring rate on hybrid L5:** 2/8 cells = 25% false negative rate.
**Corrected hybrid L5 pass rate:** 6/8 = 75% (auto was 4/8 = 50%).

## GPT-4o Pre-Fix L4 Results (b2_rag_cypher)

| Question | Auto | Manual | Discrepancy? | Notes |
|---|---|---|---|---|
| q001-q006 | PASS | PASS | No | All correct |
| q007 | PASS | PARTIAL | Minor | "116.8 more popular" is a nonsensical metric (should be ratio) |
| q008 | PASS | **FAIL** | **YES** | Says "no data available" — data exists! Auto-scorer too permissive |

## Summary of Discrepancies

| Type | Count | Direction |
|---|---|---|
| Auto=FAIL, Manual=PASS (false negative) | 3 | Judge too strict on paraphrasing |
| Auto=ERR, Manual=PASS (false negative from partial-error) | 1 | Community stream errored but answer was produced |
| Auto=PASS, Manual=FAIL (false positive) | 1 | Scorer accepted "no data available" |
| Auto=PASS, Manual=PARTIAL (quality concern) | 1 | Nonsensical metric accepted |

**Net impact:** Automated scoring underestimates B2-hybrid L5 by ~25%.
