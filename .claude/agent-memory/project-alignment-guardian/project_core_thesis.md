---
name: Project core thesis
description: LLM is the primary contribution; CV event detection is proof-of-concept only — confirmed from both the MTech report and frozen plan.
type: project
---

The authoritative statement is in the report conclusion: "CV is not the core focus of the system; rather, it acts as an enabling mechanism that supplies the LLM with reliable event-level information. The true value of the system emerges from the LLM's ability to reason over these structured logs."

**Why:** The project's novel contribution is two LLM approaches (B1 NL→SQL, B2 Graph-RAG) evaluated across L1–L5 complexity tiers. CV provides the event log schema as a data source; it is not evaluated or improved as a research artifact.

**How to apply:** Flag any proposed CV work beyond what is needed for D1 (one real video, one working pipeline). All sprint time should prioritize B1→B2→eval (D2, D3). CV scope boundary: 5 event types, one real video demo, no fine-tuning, no novel detector architecture.
