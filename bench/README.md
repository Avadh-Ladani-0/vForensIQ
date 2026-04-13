# vForensIQ Evaluation Bench

L1–L5 benchmark for the two LLM approaches. Every bench item is
`(simulator scenario, question, gold answer)`; the harness runs both LLM
approaches against each question and scores their answers.

## Layout

```
bench/
  questions/
    L1/  q001_*.json, q002_*.json, ...     # shared scenarios, auto-gold
    L2/
    L3/
    L4/                                      # per-question scenarios
    L5/
  results/     # gitignored; one folder per harness run
```

Simulator scenarios live in `simulator/scenarios/` and are referenced by
name from question files. The harness guarantees the named scenario has
been materialized into the logbase before running the question (scoped
wipe + re-insert is idempotent, per `simulator/core.py`).

## Question file shape

```json
{
  "question_id": "L1_q001_car_entry_count_at_gate01",
  "level": "L1",
  "scenario": "base_quiet_day",
  "question_text": "How many car_entry events were recorded at Gate_01 on 2025-12-01?",
  "gold": { "type": "sql", "sql": "SELECT ...", "scoring": "exact_numeric" },
  "metadata": { "note": "free-form human notes" }
}
```

| field | notes |
|---|---|
| `question_id` | Unique, filename-safe; convention `{level}_q{nnn}_{slug}` |
| `level` | One of `L1` `L2` `L3` `L4` `L5`. Must match containing subdir |
| `scenario` | Name of a scenario in `simulator/scenarios/{name}.json` |
| `question_text` | Exact text posed to each LLM approach |
| `gold` | Gold-answer block; shape depends on `gold.type` (see below) |
| `metadata` | Free-form; harness ignores it |

## `gold` block — one of three shapes

### `gold.type = "sql"` — L1, L2, L3
Gold is computed at eval time by running `gold.sql` against the current
logbase. Keeps gold in lockstep with the scenario; no stale cached values.

```json
"gold": {
  "type": "sql",
  "sql": "SELECT COUNT(*) AS count FROM events WHERE ...",
  "scoring": "exact_numeric"
}
```

Allowed `scoring` values for SQL-gold:

| scoring | level | rule |
|---|---|---|
| `exact_numeric` | L1 | LLM's numeric answer = gold exactly |
| `numeric_tolerance_1pct` | L2 | within ±1% of gold |
| `set_match_with_tolerance` | L3 | group-by row set equal; each aggregate within ±1% |

### `gold.type = "structured_facts"` — L4
Gold is inline JSON facts; no SQL execution. Authored per-question
alongside a bespoke scenario that injects the comparative facts into
`ground_truth.json`.

```json
"gold": {
  "type": "structured_facts",
  "facts": {
    "busier_location": "Platform_1",
    "dominance_ratio": { "value": 2.3, "tolerance": 0.15 },
    "busiest_hour_utc": "18:00"
  },
  "scoring": "structured_facts"
}
```

### `gold.type = "rubric_coverage"` — L5
Gold is a list of atomic facts the narrative should mention, plus a
coverage threshold and a grounding hard gate.

```json
"gold": {
  "type": "rubric_coverage",
  "rubric": [
    "Gate_01 car traffic peaked at 08-10 UTC with ~80 car_entry/hr",
    "An anomaly spike of 400 persons occurred at 19:00 UTC on Wednesday",
    "Overnight hours 23-05 UTC had near-zero activity"
  ],
  "coverage_threshold": 0.7,
  "grounding_required": true,
  "scoring": "rubric_coverage"
}
```

## Scoring dimensions (harness-wide)

| dimension | L1 | L2 | L3 | L4 | L5 |
|---|---|---|---|---|---|
| numeric / set match | ✓ | ✓ (±1%) | ✓ | — | — |
| structured-fact match | — | — | — | ✓ | — |
| rubric coverage | — | — | — | — | ✓ (≥0.7) |
| grounding (citations valid) | — | — | — | ✓ | ✓ (hard gate) |
| prose quality (LLM-judge) | — | — | — | rubric | ✓ |
| latency p50, p95 | ✓ | ✓ | ✓ | ✓ | ✓ |

## Time-filter convention in gold SQL

Gold SQL uses `timestamp_utc` (TEXT ISO 8601 Z) for readability:

```sql
WHERE timestamp_utc >= '2025-12-01T00:00:00Z'
  AND timestamp_utc <  '2025-12-02T00:00:00Z'
```

ISO-8601 Z lexicographic order equals chronological order, so TEXT
comparison is correct. SQLite will still use the `idx_events_cam_ts` /
`idx_events_type_ts` indexes when the other filter is on `camera_id` /
`event_type`, which it almost always is at L1–L3.

## Running the harness

See task 0.5 (coming next). Planned CLI:

```bash
python -m bench.run_eval --approach sql --level L1
python -m bench.run_eval --approach rag --level L1,L2,L3
python -m bench.run_eval --approach both --level all
```
