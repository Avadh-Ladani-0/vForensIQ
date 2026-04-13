---
name: LLM approach design (B1 and B2)
description: B1 NL→SQL two-step pipeline and B2 three Graph-RAG sub-variants; 4×2 eval matrix; sprint schedule.
type: project
---

B1 (NL→SQL): question + schema → LLM #1 → SQL → executor → rows → LLM #2 → answer + SQL citations. Models: gpt-4o-mini and gpt-4o.

B2 (Graph-RAG on Neo4j): three sub-variants all compared:
- b2_rag_cypher: NL→Cypher execute→synthesize
- b2_rag_community: Louvain/Leiden community detection on graph → hierarchical summaries → embedding retrieval (Chroma + text-embedding-3-small) → synthesize
- b2_rag_hybrid: Cypher + community summaries merged by router

Eval matrix: 4 approaches × 2 models × 5 levels = 40 cells per scenario.

Sprint schedule: Sprint 1–2 = B1; Sprint 3 = Neo4j + b2_rag_cypher; Sprint 4 = community + hybrid; Sprint 5 = scale test.

**Why:** Three B2 sub-variants allow comparison of retrieval strategies (precise lookup vs. semantic summary vs. hybrid), which is the research contribution. This is defensible and not padding.

**How to apply:** Do not conflate B2 sub-variants — each is a distinct retrieval strategy. Cite NL→Cypher, Microsoft GraphRAG, and community detection papers for each variant respectively.
