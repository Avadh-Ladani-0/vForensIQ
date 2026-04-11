from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

from .common import LOG_DIR_PATH, PIPELINE_LOG_PATH


_CONFIGURED = False


def _log_level_from_env() -> int:
    raw_level = os.getenv("NL_SQL_LOG_LEVEL", "INFO").upper().strip()
    return getattr(logging, raw_level, logging.INFO)


def setup_nl_sql_logging() -> Path:
    global _CONFIGURED
    if _CONFIGURED:
        return PIPELINE_LOG_PATH

    LOG_DIR_PATH.mkdir(parents=True, exist_ok=True)

    max_bytes = int(os.getenv("NL_SQL_LOG_MAX_BYTES", str(5 * 1024 * 1024)))
    backup_count = int(os.getenv("NL_SQL_LOG_BACKUP_COUNT", "3"))
    level = _log_level_from_env()

    root_logger = logging.getLogger("nl_sql")
    root_logger.setLevel(level)
    root_logger.propagate = False

    target_file = str(PIPELINE_LOG_PATH.resolve())
    for handler in root_logger.handlers:
        if isinstance(handler, RotatingFileHandler) and getattr(handler, "baseFilename", "") == target_file:
            _CONFIGURED = True
            return PIPELINE_LOG_PATH

    file_handler = RotatingFileHandler(
        filename=PIPELINE_LOG_PATH,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    )
    root_logger.addHandler(file_handler)
    _CONFIGURED = True
    return PIPELINE_LOG_PATH


def get_logger(module_name: str) -> logging.Logger:
    setup_nl_sql_logging()
    if module_name.startswith("nl_sql"):
        return logging.getLogger(module_name)
    return logging.getLogger(f"nl_sql.{module_name}")

