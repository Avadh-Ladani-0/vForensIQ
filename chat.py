import argparse
import json
import sys
from pathlib import Path
from typing import Any

_PKG_ROOT = Path(__file__).resolve().parent
if str(_PKG_ROOT) not in sys.path:
    sys.path.insert(0, str(_PKG_ROOT))

from nl_sql import run_nl_sql_pipeline
from nl_sql.common import PIPELINE_LOG_PATH


def _print_envelope(label: str, envelope: dict[str, Any]) -> None:
    print(f"\n========== {label} ==========")
    print(f"Provider: {envelope.get('provider', 'unknown')}")
    print(f"Model: {envelope.get('provider_model', 'unknown')}")
    print(f"Duration: {envelope.get('duration_ms', 0)} ms")
    print(f"Event context: {', '.join(envelope.get('event_context', [])) or 'N/A'}")
    print(f"Context source: {envelope.get('event_context_source', 'N/A')}")
    print("\nAnswer:")
    print(envelope.get("answer_text") or envelope.get("summary_text", "No answer"))

    processed_rows = envelope.get("processed_rows", [])
    if processed_rows:
        print(f"\nProcessed evidence rows: {len(processed_rows)}")
        print(json.dumps(processed_rows[:5], indent=2))

    citations = envelope.get("citation_queries", [])
    if citations:
        print("\nSQL citations:")
        for citation in citations:
            print(f"- [{citation.get('id')}] {citation.get('purpose')}")
            print(citation.get("sql", ""))
            print("")

    print("\nEvent chunk stats:")
    print(json.dumps(envelope.get("event_chunk_stats", {}), indent=2))

    errors = envelope.get("errors", [])
    if errors:
        print("\nErrors:")
        for err in errors:
            print(f"- {err}")


def run_cli(chunk_size: int) -> None:
    print("vForensIQ Event-Context NL->SQL CLI")
    print("Primary source: Data/Augmented_Data/out/data.csv")
    print(f"Pipeline log: {PIPELINE_LOG_PATH}")
    print("Provider: openai")
    question = input("\nEnter your question:\n> ").strip()
    if not question:
        print("No question provided.")
        return

    result = run_nl_sql_pipeline(
        question=question,
        provider_mode="openai",
        compare=False,
        chunk_size=chunk_size,
    )

    _print_envelope("OpenAI Result", result.get("result", {}))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="vForensIQ NL->SQL CLI")
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=5000,
        help="Rows per chunk for event-context summarization",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_cli(chunk_size=args.chunk_size)
