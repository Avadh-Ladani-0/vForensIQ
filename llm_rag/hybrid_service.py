"""B2 Graph-RAG (Hybrid variant).

Runs BOTH cypher and community-summary retrieval in parallel, then synthesizes
a single answer using both evidence streams. The LLM is told to prefer precise
Cypher numbers for factual claims and community summaries for narrative context.
"""
from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any, Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from openai import OpenAI, APIConnectionError, APITimeoutError, RateLimitError

from .cypher_service import (
    generate_cypher, validate_cypher, execute_cypher, repair_cypher, _contextualize,
)
from .community_service import (
    build_community_index, _embed_with_retry,
)
from .common import CHROMA_DIR
import chromadb

from neo4j.exceptions import CypherSyntaxError, ClientError, DatabaseError


HYBRID_SYNTH_PROMPT = """\
You are a CCTV forensic analyst. You have TWO evidence streams:

1. Precise structured rows returned by a Cypher query over the knowledge graph
2. Semantic community summaries retrieved from hierarchical graph clustering

Rules:
- For factual numbers (counts, averages, peaks), trust the Cypher rows — cite them exactly.
- For narrative framing, temporal patterns, and multi-aspect context, use community summaries.
- If the Cypher rows are empty but community summaries cover the question, use the summaries.
- If Cypher rows directly answer the question, prioritize them and use summaries only for flavor.
- Do NOT mention the retrieval method. Just answer.
- Keep it concise: 1-3 sentences for simple questions, up to 6 for narrative briefs.
"""


_TRANSIENT = (APIConnectionError, APITimeoutError, RateLimitError)


def _get_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        env_path = Path(".env")
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith("OPENAI_API_KEY"):
                    _, v = line.split("=", 1)
                    api_key = v.strip().strip('"').strip("'")
                    break
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    return OpenAI(api_key=api_key)


def _chat_with_retry(client: OpenAI, **kwargs: Any) -> Any:
    last: Exception | None = None
    for attempt in range(3):
        try:
            return client.chat.completions.create(**kwargs)
        except _TRANSIENT as exc:
            last = exc
            if attempt < 2:
                time.sleep(1.5 * (attempt + 1))
    assert last is not None
    raise last


def answer_question(
    question: str,
    model: str,
    context: Optional[dict] = None,
    summary_model: str = "gpt-4o-mini",
    top_k_communities: int = 4,
) -> dict:
    t_start = time.time()
    errors: list[str] = []
    llm_calls: list[dict] = []
    cypher = ""
    cypher_cols: list[str] = []
    cypher_rows: list[list[Any]] = []
    retrieved: list[dict] = []
    answer_text: Optional[str] = None

    contextualized = _contextualize(question, context)
    try:
        client = _get_client()

        # --- Stream 1: Cypher ---
        try:
            cypher_raw, u1 = generate_cypher(contextualized, model, client)
            llm_calls.append(u1)
            cypher = validate_cypher(cypher_raw)
            try:
                cypher_cols, cypher_rows = execute_cypher(cypher)
            except (CypherSyntaxError, ClientError, DatabaseError) as exec_err:
                repaired, ur = repair_cypher(contextualized, cypher, str(exec_err), model, client)
                llm_calls.append(ur)
                cypher = validate_cypher(repaired)
                cypher_cols, cypher_rows = execute_cypher(cypher)
        except Exception as e1:
            errors.append(f"cypher_stream: {type(e1).__name__}: {e1}")

        # --- Stream 2: Community retrieval ---
        try:
            build_community_index(model_for_summaries=summary_model, force_rebuild=False)
            q_embed = _embed_with_retry(client, question)
            client_cx = chromadb.PersistentClient(path=str(CHROMA_DIR))
            coll_name = f"vforensiq_community_summaries__{summary_model}"
            coll = client_cx.get_collection(coll_name)
            result = coll.query(query_embeddings=[q_embed], n_results=min(top_k_communities, coll.count()))
            for i in range(len(result["ids"][0])):
                retrieved.append({
                    "community_id": result["ids"][0][i],
                    "summary": result["documents"][0][i],
                    "distance": result["distances"][0][i] if result.get("distances") else None,
                })
        except Exception as e2:
            errors.append(f"community_stream: {type(e2).__name__}: {e2}")

        # --- Dir 3: Weighted fusion with graceful degradation ---
        cypher_available = bool(cypher_cols and cypher_rows)
        community_available = bool(retrieved)

        if cypher_available:
            cypher_block = (
                f"CYPHER EVIDENCE (PRECISE — prefer these numbers for factual claims):\n"
                f"Columns: {cypher_cols}\n"
                f"Row count: {len(cypher_rows)}\n"
                f"Rows (first 50): {cypher_rows[:50]}"
            )
        else:
            cypher_block = "CYPHER EVIDENCE: [unavailable — Cypher query failed; rely on community summaries below]"

        if community_available:
            community_block = "COMMUNITY SUMMARIES (CONTEXTUAL — use for narrative framing and breadth):\n" + "\n\n".join(
                f"[{r['community_id']}] {r['summary']}" for r in retrieved
            )
        else:
            community_block = "COMMUNITY SUMMARIES: [unavailable — retrieval failed; rely on Cypher evidence above]"

        # Fusion weighting instruction based on what's available
        if cypher_available and community_available:
            fusion_note = "Both evidence streams are available. Use Cypher rows for exact numbers; use community summaries for context and narrative framing."
        elif cypher_available:
            fusion_note = "Only Cypher evidence is available. Base your answer entirely on the Cypher rows."
        elif community_available:
            fusion_note = "Only community summaries are available (Cypher failed). Base your answer on the summaries; note that exact numbers may be approximate."
        else:
            fusion_note = "Neither evidence stream produced results. State that you cannot answer based on available data."

        user_msg = (
            f"User question:\n{question}\n\n"
            f"FUSION NOTE: {fusion_note}\n\n"
            f"{cypher_block}\n\n{community_block}"
        )
        resp = _chat_with_retry(
            client, model=model,
            messages=[
                {"role": "system", "content": HYBRID_SYNTH_PROMPT},
                {"role": "user", "content": user_msg},
            ],
        )
        answer_text = (resp.choices[0].message.content or "").strip()
        llm_calls.append({
            "stage": "hybrid_synth", "model": model,
            "prompt_tokens": resp.usage.prompt_tokens if resp.usage else 0,
            "completion_tokens": resp.usage.completion_tokens if resp.usage else 0,
        })
    except Exception as exc:
        errors.append(f"hybrid_top: {type(exc).__name__}: {exc}")

    duration_ms = int((time.time() - t_start) * 1000)
    citations: list[dict] = []
    if cypher:
        citations.append({"type": "cypher_query", "cypher": cypher, "row_count": len(cypher_rows)})
    for r in retrieved:
        citations.append({"type": "community", "community_id": r["community_id"], "distance": r.get("distance")})
    return {
        "answer_text": answer_text,
        "structured_answer": {
            "cypher_columns": cypher_cols,
            "cypher_rows": cypher_rows[:50],
            "cypher_total_rows": len(cypher_rows),
            "retrieved_communities": retrieved,
        },
        "citations": citations,
        "duration_ms": duration_ms,
        "llm_calls": llm_calls,
        "errors": errors,
    }
