---
name: References file status
description: mybib.bib has 10 entries covering CV and LLM survey topics; no docs/references.txt exists; several citations for adopted techniques are missing.
type: project
---

mybib.bib (10 entries) covers: YOLOv8, YOLOv7, YOLO-FaceV2, FLAME fire detection, LLM-for-video-surveillance survey, structured DB retrieval via LLM, HyST hybrid retrieval, StructuredRAG JSON formatting, LLM log analysis survey, surveillance event detection review.

Missing citations (as of Sprint 0 close):
- NL→SQL / Text-to-SQL benchmark: BIRD, Spider, WikiSQL, and survey papers
- NL→Cypher for graph querying
- Microsoft GraphRAG (community summaries)
- Louvain/Leiden community detection algorithms
- BGE-M3 embedding model
- Chroma vector store (no academic paper needed, but should note it)
- DeepSORT / ByteTrack (already used in prototype)

**Why:** Every adopted technique must have a citation in the report bib. Missing citations are a thesis defense risk.

**How to apply:** Before Sprint 1 kickoff, add missing citations to mybib.bib. Do NOT maintain a separate docs/references.txt — consolidate into mybib.bib to keep a single authoritative source for the report.
