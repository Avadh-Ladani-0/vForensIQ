"""Shared config for B2 graph-RAG approaches."""
from __future__ import annotations

import os
from pathlib import Path

_PKG_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _PKG_DIR.parent

DEFAULT_LOGBASE_PATH = _REPO_ROOT / "runtime" / "vforensiq_logbase.db"
CHROMA_DIR = _REPO_ROOT / "runtime" / "chroma_communities"

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "vforensiq_dev")

OPENAI_EMBED_MODEL = "text-embedding-3-small"
