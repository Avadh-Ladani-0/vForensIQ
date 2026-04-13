"""CLI entrypoint: `python -m simulator <scenario_name>`."""
from __future__ import annotations

import sys

from simulator.core import run_scenario


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python -m simulator <scenario_name>", file=sys.stderr)
        return 2
    scenario_name = sys.argv[1]
    result = run_scenario(scenario_name)
    print(f"Scenario:         {result['scenario_name']} (seed={result['seed']})")
    print(f"Window UTC:       {result['window_utc']['start']} -> {result['window_utc']['end']}")
    print(f"Generated events: {result['generated_events']}")
    print(f"Prior rows wiped: {result['deleted_prior_rows']} (scoped to cameras x window)")
    print(f"Logbase:          {result['logbase_path']}")
    print(f"Ground truth:     {result['ground_truth_path']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
