# vForensIQ — 8-Week Project Progress Report

**Student:** Avadh Ladani (24MCD009)
**Title:** Intelligent Surveillance Analytics: Driven by LLM and CV
**Department:** CSE, School of Technology, Nirma University
**Duration:** 8 Weeks (February – April 2026)

---

## Weekly Progress

| Week | Dates | Focus Area | Key Deliverables |
|---|---|---|---|
| 1 | Feb 3–9 | Literature Survey | 10-paper survey, problem statement, gap identification |
| 2 | Feb 10–16 | System Design | Data contract (v2), event schema (5 types), SQL logbase DDL, repo structure |
| 3 | Feb 17–23 | Simulator + B1 Implementation | Scenario simulator, L1–L5 taxonomy, eval harness, B1 NL→SQL pipeline, 11 bench questions |
| 4 | Feb 24–Mar 2 | B1 Hardening + Abstract Questions | 41 questions (schema-aware + abstract), session-context injection, 5 LLM behaviour findings |
| 5 | Mar 3–9 | Graph-RAG (B2) Implementation | Neo4j Docker, graph builder, 3 B2 variants (Cypher/Community/Hybrid), first comparison |
| 6 | Mar 10–16 | Analysis + Root Cause Investigation | Crowd-exclusion problem found, latency profiling, 4 optimisation directions researched |
| 7 | Mar 17–23 | Novel Contributions | AQR router (100% classifier), per-second CrowdEvent fix, hierarchical graph, 75 questions |
| 8 | Mar 24–30 | Final Evaluation + Documentation | 375-cell bench, manual verification, thesis chapter, evidence archive, Chat UI |

---

## Final Results

| Level | B1 NL→SQL | B2 Cypher | B2 Hybrid | B3 AQR |
|---|---|---|---|---|
| L1 — Direct Lookup | **100%** | 73% | 60% | **100%** |
| L2 — Single Aggregation | **67%** | 60% | 33% | **67%** |
| L3 — Multi-Dim Aggregation | 73% | **87%** | **87%** | **87%** |
| L4 — Comparative Reasoning | **100%** | 93% | 93% | **100%** |
| L5 — Narrative Synthesis | 87% | 87% | **93%** | **93%** |
| **Overall** | **85.3%** | 80.0% | 73.3% | **89.3%** |

---

## Contributions

| # | Contribution | Status |
|---|---|---|
| C1 | L1–L5 evaluation taxonomy (15 questions per level, 2 question styles) | Complete |
| C2 | Head-to-head TAG vs Graph-RAG comparison on CCTV event data | Complete |
| C3 | 5 systematic LLM querying behaviours documented | Complete |
| C4 | Crowd-inclusion problem in graph-RAG (98.6% data loss finding) | Complete |
| C5 | Schema-aware vs abstract question gap (26 points) | Complete |
| C6 | Adaptive Query Router achieving 89.3% accuracy | Complete |

---

**Submitted by:** Avadh Ladani (24MCD009) | **Date:** April 2026
