"""B2 Graph-RAG (Community-Summary variant).

Louvain community detection over the Neo4j graph (exported to NetworkX).
Each community is summarized by an LLM at two granularities (location-level,
hour-level). Summaries are embedded into Chroma and retrieved by semantic
similarity to the user question. LLM then synthesizes an answer grounded in the
retrieved summaries.

Pattern: Microsoft GraphRAG-style community summaries (Edge et al. 2024),
applied to a structured CCTV event graph.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import chromadb
import community as community_louvain  # python-louvain
import networkx as nx
from neo4j import GraphDatabase
from openai import OpenAI, APIConnectionError, APITimeoutError, RateLimitError

from .common import CHROMA_DIR, NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER, OPENAI_EMBED_MODEL


CHROMA_COLLECTION = "vforensiq_community_summaries"

COMMUNITY_SUMMARY_PROMPT = """\
You are summarizing a cluster of CCTV activity into 2-4 sentences.

Given the raw events, per-camera event counts, and per-hour aggregates below,
produce a concise factual summary. Mention:
- Which camera_locations are involved
- Which event_types dominate (person/car entry/exit or crowd)
- The time range covered
- Any notable numbers (peak head_count, peak event count per hour, total volume)

Be factual, specific, and concise. No speculation. No markdown.
"""

ANSWER_SYNTH_PROMPT = """\
You are a CCTV forensic analyst. Based ONLY on the retrieved community summaries below,
answer the user's question in plain language. Cite specific locations, times, and numbers
from the summaries. If the summaries don't cover what the user asked, say so briefly.

Rules:
- Quote numbers exactly from the summaries.
- Reference camera_locations by name.
- Keep answers to 1-4 sentences for simple questions, up to 6 for narrative briefs.
- Do not speculate beyond the retrieved summaries.
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


def _embed_with_retry(client: OpenAI, text: str) -> list[float]:
    last: Exception | None = None
    for attempt in range(3):
        try:
            r = client.embeddings.create(model=OPENAI_EMBED_MODEL, input=text)
            return r.data[0].embedding
        except _TRANSIENT as exc:
            last = exc
            if attempt < 2:
                time.sleep(1.5 * (attempt + 1))
    assert last is not None
    raise last


# ---------------------------------------------------------------------------
# Graph export -> NetworkX
# ---------------------------------------------------------------------------

def _export_graph_to_networkx() -> tuple[nx.Graph, dict[str, dict]]:
    """Build an undirected NetworkX graph from Neo4j for Louvain.

    Nodes = Camera, Event, CrowdHour, Hour.
    Edges from DETECTED_BY, OCCURRED_IN, AT_CAMERA, DURING relationships.
    Returns (graph, node_attrs_by_id).
    """
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    g = nx.Graph()
    attrs: dict[str, dict] = {}
    try:
        with driver.session() as session:
            # Cameras
            for r in session.run("MATCH (c:Camera) RETURN c.camera_id AS cid, c.camera_location AS loc, c.mode AS mode"):
                nid = f"cam:{r['cid']}"
                g.add_node(nid, kind="Camera", camera_id=r["cid"], camera_location=r["loc"], mode=r["mode"])
                attrs[nid] = {"kind": "Camera", "camera_id": r["cid"], "camera_location": r["loc"], "mode": r["mode"]}
            # Events
            for r in session.run("MATCH (e:Event) RETURN e.event_id AS eid, e.event_type AS et, e.timestamp_utc AS ts"):
                nid = f"evt:{r['eid']}"
                g.add_node(nid, kind="Event", event_type=r["et"], timestamp_utc=r["ts"])
                attrs[nid] = {"kind": "Event", "event_type": r["et"], "timestamp_utc": r["ts"]}
            # CrowdHours
            for r in session.run(
                "MATCH (ch:CrowdHour) RETURN ch.crowd_hour_id AS chid, ch.camera_location AS loc, "
                "ch.hour_utc AS hr, ch.avg_hc AS avg_hc, ch.peak_hc AS peak_hc"
            ):
                nid = f"ch:{r['chid']}"
                g.add_node(nid, kind="CrowdHour", camera_location=r["loc"], hour_utc=r["hr"],
                           avg_hc=r["avg_hc"], peak_hc=r["peak_hc"])
                attrs[nid] = {"kind": "CrowdHour", "camera_location": r["loc"], "hour_utc": r["hr"],
                              "avg_hc": r["avg_hc"], "peak_hc": r["peak_hc"]}
            # Hours
            for r in session.run("MATCH (h:Hour) RETURN h.hour_utc AS hr"):
                nid = f"hr:{r['hr']}"
                g.add_node(nid, kind="Hour", hour_utc=r["hr"])
                attrs[nid] = {"kind": "Hour", "hour_utc": r["hr"]}
            # Edges
            for r in session.run("MATCH (e:Event)-[:DETECTED_BY]->(c:Camera) RETURN e.event_id AS e, c.camera_id AS c"):
                g.add_edge(f"evt:{r['e']}", f"cam:{r['c']}")
            for r in session.run("MATCH (e:Event)-[:OCCURRED_IN]->(h:Hour) RETURN e.event_id AS e, h.hour_utc AS h"):
                g.add_edge(f"evt:{r['e']}", f"hr:{r['h']}")
            for r in session.run("MATCH (ch:CrowdHour)-[:AT_CAMERA]->(c:Camera) RETURN ch.crowd_hour_id AS ch, c.camera_id AS c"):
                g.add_edge(f"ch:{r['ch']}", f"cam:{r['c']}")
            for r in session.run("MATCH (ch:CrowdHour)-[:DURING]->(h:Hour) RETURN ch.crowd_hour_id AS ch, h.hour_utc AS h"):
                g.add_edge(f"ch:{r['ch']}", f"hr:{r['h']}")
    finally:
        driver.close()
    return g, attrs


def _community_profile(nodes: list[str], attrs: dict[str, dict]) -> dict[str, Any]:
    """Summarize a community into a structured profile fed to the LLM."""
    cam_ids = set()
    locations = set()
    event_type_counts: dict[str, int] = {}
    hours = set()
    ts_list: list[str] = []
    avg_hc_list: list[float] = []
    peak_hc: float = 0
    for nid in nodes:
        a = attrs.get(nid, {})
        kind = a.get("kind")
        if kind == "Camera":
            cam_ids.add(a["camera_id"])
            locations.add(a["camera_location"])
        elif kind == "Event":
            et = a.get("event_type", "")
            event_type_counts[et] = event_type_counts.get(et, 0) + 1
            ts = a.get("timestamp_utc")
            if ts:
                ts_list.append(ts)
        elif kind == "CrowdHour":
            locations.add(a["camera_location"])
            hours.add(a["hour_utc"])
            if a.get("avg_hc") is not None:
                avg_hc_list.append(float(a["avg_hc"]))
            if a.get("peak_hc") is not None:
                peak_hc = max(peak_hc, float(a["peak_hc"]))
        elif kind == "Hour":
            hours.add(a["hour_utc"])
    return {
        "camera_ids": sorted(cam_ids),
        "camera_locations": sorted(locations),
        "hour_range_utc": [min(hours), max(hours)] if hours else None,
        "event_range_utc": [min(ts_list), max(ts_list)] if ts_list else None,
        "event_type_counts": event_type_counts,
        "total_events": sum(event_type_counts.values()),
        "avg_head_count_mean_of_means": (sum(avg_hc_list) / len(avg_hc_list)) if avg_hc_list else None,
        "peak_head_count": peak_hc if peak_hc else None,
        "node_count": len(nodes),
    }


def _summarize_community(client: OpenAI, profile: dict, model: str) -> str:
    user = "Community profile (structured):\n" + json.dumps(profile, indent=2)
    resp = _chat_with_retry(
        client, model=model, temperature=0,
        messages=[
            {"role": "system", "content": COMMUNITY_SUMMARY_PROMPT},
            {"role": "user", "content": user},
        ],
    )
    return (resp.choices[0].message.content or "").strip()


# ---------------------------------------------------------------------------
# Index (build once per model+graph; cache in Chroma)
# ---------------------------------------------------------------------------

def build_community_index(
    model_for_summaries: str = "gpt-4o-mini",
    force_rebuild: bool = False,
) -> dict:
    """Build the community summary index. Idempotent — reuses Chroma collection if present."""
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client_cx = chromadb.PersistentClient(path=str(CHROMA_DIR))

    coll_name = f"{CHROMA_COLLECTION}__{model_for_summaries}"
    if not force_rebuild:
        try:
            existing = client_cx.get_collection(coll_name)
            if existing.count() > 0:
                return {"reused": True, "collection": coll_name, "count": existing.count()}
        except Exception:
            pass

    # (Re)create
    try:
        client_cx.delete_collection(coll_name)
    except Exception:
        pass
    coll = client_cx.create_collection(name=coll_name, metadata={"hnsw:space": "cosine"})

    g, attrs = _export_graph_to_networkx()
    partition = community_louvain.best_partition(g, random_state=42)

    communities: dict[int, list[str]] = {}
    for node, cid in partition.items():
        communities.setdefault(cid, []).append(node)

    llm = _get_client()
    summaries_written = 0
    for cid, nodes in communities.items():
        if len(nodes) < 3:  # skip trivial singletons
            continue
        profile = _community_profile(nodes, attrs)
        summary_text = _summarize_community(llm, profile, model_for_summaries)
        embed = _embed_with_retry(llm, summary_text)
        doc_id = f"community_{cid}"
        metadata = {
            "community_id": cid,
            "node_count": len(nodes),
            "camera_locations": ",".join(profile["camera_locations"][:10]),
            "total_events": profile["total_events"],
        }
        coll.add(
            ids=[doc_id],
            documents=[summary_text],
            embeddings=[embed],
            metadatas=[metadata],
        )
        summaries_written += 1
    return {
        "reused": False, "collection": coll_name,
        "communities_found": len(communities),
        "summaries_written": summaries_written,
    }


# ---------------------------------------------------------------------------
# Retrieval + answer synthesis
# ---------------------------------------------------------------------------

def _contextualize(question: str, context: Optional[dict]) -> str:
    if not context:
        return question
    win = context.get("scenario_window") or {}
    s, e = win.get("start"), win.get("end")
    label = context.get("scenario_label", "the dataset")
    if not (s and e):
        return question
    return (
        f"[SESSION CONTEXT: viewing '{label}', window {s} to {e} UTC. "
        f"'today'/'yesterday'/'the day' = this window.]\n\nUSER QUESTION: {question}"
    )


def answer_question(
    question: str,
    model: str,
    context: Optional[dict] = None,
    summary_model: str = "gpt-4o-mini",
    top_k: int = 6,
) -> dict:
    t_start = time.time()
    errors: list[str] = []
    llm_calls: list[dict] = []
    answer_text: Optional[str] = None
    retrieved: list[dict] = []

    contextualized = _contextualize(question, context)
    try:
        # Ensure index exists (cheap no-op if already built)
        build_community_index(model_for_summaries=summary_model, force_rebuild=False)

        llm = _get_client()
        q_embed = _embed_with_retry(llm, question)

        client_cx = chromadb.PersistentClient(path=str(CHROMA_DIR))
        coll_name = f"{CHROMA_COLLECTION}__{summary_model}"
        coll = client_cx.get_collection(coll_name)
        result = coll.query(query_embeddings=[q_embed], n_results=min(top_k, coll.count()))

        for i in range(len(result["ids"][0])):
            retrieved.append({
                "community_id": result["ids"][0][i],
                "summary": result["documents"][0][i],
                "distance": result["distances"][0][i] if result.get("distances") else None,
                "metadata": result["metadatas"][0][i] if result.get("metadatas") else {},
            })

        evidence = "\n\n".join(
            f"[Community {r['community_id']}]\n{r['summary']}" for r in retrieved
        )
        user_msg = (
            f"User question:\n{contextualized}\n\n"
            f"Retrieved community summaries:\n{evidence}\n\n"
            f"Answer the user's question using ONLY the summaries above."
        )
        resp = _chat_with_retry(
            llm, model=model,
            messages=[
                {"role": "system", "content": ANSWER_SYNTH_PROMPT},
                {"role": "user", "content": user_msg},
            ],
        )
        answer_text = (resp.choices[0].message.content or "").strip()
        llm_calls.append({
            "stage": "answer_synth", "model": model,
            "prompt_tokens": resp.usage.prompt_tokens if resp.usage else 0,
            "completion_tokens": resp.usage.completion_tokens if resp.usage else 0,
        })
    except Exception as exc:
        errors.append(f"{type(exc).__name__}: {exc}")

    duration_ms = int((time.time() - t_start) * 1000)
    return {
        "answer_text": answer_text,
        "structured_answer": {
            "retrieved_communities": retrieved,
            "top_k": top_k,
        },
        "citations": [
            {"type": "community", "community_id": r["community_id"], "distance": r.get("distance")}
            for r in retrieved
        ],
        "duration_ms": duration_ms,
        "llm_calls": llm_calls,
        "errors": errors,
    }
