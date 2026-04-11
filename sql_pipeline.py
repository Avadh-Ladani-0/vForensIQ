from __future__ import annotations

import sys
from pathlib import Path

_PKG_ROOT = Path(__file__).resolve().parent
if str(_PKG_ROOT) not in sys.path:
    sys.path.insert(0, str(_PKG_ROOT))

from nl_sql import CANONICAL_SOURCE_CSV, run_nl_sql_pipeline

__all__ = ["CANONICAL_SOURCE_CSV", "run_nl_sql_pipeline"]
