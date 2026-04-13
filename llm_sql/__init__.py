"""LLM-SQL approaches.

B1 two-step NL->SQL lives in `llm_sql.b1_service`.
Import directly:   from llm_sql.b1_service import answer_question

The legacy prototype modules (service.py, planner.py, aggregation.py,
event_context.py, summarizer.py, db.py) were removed at end of Sprint 1 —
they were retargeted to the report's schema via the cleaner two-step
design, and the old event-context / chunked-aggregation / QueryPlan
scaffolding is no longer needed.
"""

__all__: list[str] = []
