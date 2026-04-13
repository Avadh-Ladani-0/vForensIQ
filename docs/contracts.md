# vForensIQ Data & Message Contracts

**Version: v2 (2026-04-13)**

This document is the **authoritative source** for the event schema, MQTT
transport, simulator output, and SQL logbase shape. Every workstream
(WS-A pipeline, WS-B1 LLM-SQL, WS-B2 LLM-RAG, WS-C evaluation) builds
against this contract. Any change requires the process described in §6.

### Change log
- **v2 (2026-04-13)** — Simulator writes directly to the SQL logbase
  (§3, §4.4, §5). MQTT is now exclusively the edge/CV ingestion path.
  Eval/LLM workstreams do not depend on MQTT. No schema fields changed —
  both ingestion paths still produce identical `events` rows.
- **v1 (2026-04-13)** — Initial contract.

---

## 1. Event JSON schema (wire format)

Every event — whether produced by a CV detector, the simulator, or the
CSV-replay publisher — is a single JSON object with exactly this shape:

```json
{
  "timestamp": "2025-12-01T13:32:32Z",
  "camera_id": "CAM_08",
  "event_type": "car_entry",
  "object_id": "660",
  "confidence": 0.98,
  "camera_location": "Gate_01",
  "head_count": 0
}
```

### 1.1 Field reference

| field | type | required | notes |
|---|---|---|---|
| `timestamp` | string | yes | ISO 8601 UTC, second-precision, trailing `Z` mandatory. Example: `2025-12-01T13:32:32Z`. Naive or timezone-offset datetimes are rejected. |
| `camera_id` | string | yes | Stable identifier, matches `^CAM_\d{2,3}$` by convention. |
| `event_type` | string | yes | One of the 5 values in §1.2. |
| `object_id` | string \| null | yes | Tracker ID for entry/exit events; `null` for `crowd`. |
| `confidence` | number | yes | Range `[0.0, 1.0]`. Detection confidence for entry/exit; averaged detection confidence over the frame for `crowd`. |
| `camera_location` | string | yes | Free-form label such as `Gate_01`, `Platform_1`, `Main_hall`. Used for GROUP BY. |
| `head_count` | integer | yes | Persons in-frame for `crowd`. `0` for all other event types. |

### 1.2 Event vocabulary (frozen, 5 values)

| event_type | emission pattern | object_id | head_count |
|---|---|---|---|
| `person_entry` | event-driven, on entry-line crossing | tracker ID | 0 |
| `person_exit` | event-driven, on exit-line crossing | tracker ID | 0 |
| `car_entry` | event-driven, on vehicle entry-line crossing | tracker ID | 0 |
| `car_exit` | event-driven, on vehicle exit-line crossing | tracker ID | 0 |
| `crowd` | **periodic, 1 Hz** sampling on crowd-mode cameras | `null` | integer ≥ 0 |

"Per-second data" in project scope refers primarily to `crowd` sampling —
entry/exit events are sparse by nature. Steady-state back-of-envelope:
10 crowd cameras × 86 400 s/day = ~864 k `crowd` rows/day, so a 7-day
logbase is in the low millions of rows.

---

## 2. MQTT transport

| aspect | value |
|---|---|
| broker | Eclipse Mosquitto, local instance |
| publish topic | `vforensiq/events/{camera_id}` |
| subscribe pattern (logbase ingest) | `vforensiq/events/#` |
| payload | UTF-8 JSON, one event per message |
| QoS | 1 (at-least-once) |
| retained flag | `false` — events are not state |
| will message | none |
| auth | none (prototype, localhost only) |

### 2.1 Minimal broker config (`docs/mosquitto.conf`)

```
listener 1883 127.0.0.1
allow_anonymous true
persistence false
log_dest stderr
```

### 2.2 At-least-once implications

Subscribers must be idempotent. Deduplication happens at SQL ingest time
via `INSERT ... ON CONFLICT(event_id) DO NOTHING`, where `event_id` is
computed deterministically per §4.2.

---

## 3. Simulator output contract

The simulator has **two outputs**, one operational and one for eval:

1. **Direct write to the SQL logbase** (§4.1) — identical rows to what
   the MQTT subscriber writes. This is how LLM workstreams see simulated
   data. Simulator ingestion does **not** use MQTT; it connects to the
   SQLite file directly, computes `event_id` per §4.2, and inserts via
   the same `INSERT ... ON CONFLICT DO NOTHING` as the subscriber.
2. **`ground_truth.json`** written to `simulator/out/{scenario_name}/`.
   Structured known facts about the scenario, consumed by the eval
   harness (L4 structured-fact match, L5 rubric coverage). The eval
   harness is the only reader of this file.

Optionally, a scenario may also dump `events.jsonl` (wire-shape events,
one per line) into the same output directory for debugging — this file
is not consumed by any production code path.

### 3.1 `ground_truth.json` top-level shape

```json
{
  "scenario_name": "base_quiet_day",
  "scenario_version": 1,
  "seed": 42,
  "window_utc": {
    "start": "2025-12-01T00:00:00Z",
    "end":   "2025-12-02T00:00:00Z"
  },
  "cameras": [
    { "camera_id": "CAM_01", "camera_location": "Gate_01", "mode": "entry_exit" },
    { "camera_id": "CAM_02", "camera_location": "Platform_1", "mode": "crowd" }
  ],
  "known_facts": {
    "total_events": 12345,
    "counts_by_event_type": {
      "person_entry": 100, "person_exit": 98,
      "car_entry": 40, "car_exit": 39,
      "crowd": 86400
    },
    "peaks": [ /* scenario-specific */ ],
    "anomalies": [ /* scenario-specific */ ]
  }
}
```

`known_facts` contents are scenario-specific; the eval harness reads only
the fields referenced by its scorers. Scenarios authored for L4/L5 are
expected to inject purposeful facts (dominance ratios, peak hours, quiet
hours, injected spikes) into `known_facts` so scoring is unambiguous.

---

## 4. SQL logbase schema (SQLite)

Single database file at `runtime/vforensiq_logbase.db`. One base table
lands in Sprint 0; minute/hour/day rollups arrive in Sprint 2.

### 4.1 Base table DDL

```sql
CREATE TABLE IF NOT EXISTS events (
    event_id          TEXT PRIMARY KEY,
    timestamp_utc     TEXT    NOT NULL,   -- ISO 8601 Z, exactly as on the wire
    timestamp_epoch_s INTEGER NOT NULL,   -- derived; fast range filters
    camera_id         TEXT    NOT NULL,
    event_type        TEXT    NOT NULL,
    object_id         TEXT,                -- null for crowd
    confidence        REAL    NOT NULL,
    camera_location   TEXT    NOT NULL,
    head_count        INTEGER NOT NULL DEFAULT 0,
    ingested_at_utc   TEXT    NOT NULL     -- set by subscriber on insert
);

CREATE INDEX IF NOT EXISTS idx_events_ts          ON events(timestamp_epoch_s);
CREATE INDEX IF NOT EXISTS idx_events_cam_ts      ON events(camera_id, timestamp_epoch_s);
CREATE INDEX IF NOT EXISTS idx_events_type_ts     ON events(event_type, timestamp_epoch_s);
CREATE INDEX IF NOT EXISTS idx_events_location_ts ON events(camera_location, timestamp_epoch_s);
```

### 4.2 `event_id` derivation

```
event_id = sha1(f"{camera_id}|{timestamp_utc}|{event_type}|{object_id or ''}").hexdigest()[:16]
```

Deterministic, so:
- MQTT QoS-1 redelivery is safe (UPSERT no-ops the duplicate).
- The same simulator run with the same seed produces the same `event_id`s,
  which makes eval runs reproducible across machines.

### 4.3 Column semantics vs wire

All seven wire fields land 1:1 as columns with the same names, except:
- `timestamp` → `timestamp_utc` (kept for clarity alongside the derived
  `timestamp_epoch_s`).
- `event_id` and `ingested_at_utc` are **logbase-only** — not part of the
  wire contract. LLM approaches may read them for citations and audit.

### 4.4 Two writers, one schema

The `events` table has exactly two writers; they must produce
indistinguishable rows:

| writer | path | `ingested_at_utc` meaning |
|---|---|---|
| MQTT subscriber (WS-A) | edge CV → MQTT → SQLite | wall-clock when the subscriber ingested the message |
| Simulator (WS-C support) | scenario JSON → SQLite (direct) | wall-clock when the simulator run inserted the row |

Both use the §4.2 `event_id` formula, the §1 field semantics, and the
same `INSERT ... ON CONFLICT(event_id) DO NOTHING` statement. An LLM
querying the logbase cannot and should not tell which writer produced a
given row.

---

## 5. Allowed usage per workstream

Every workstream must treat the following as the only inputs they can
depend on:

| workstream | reads | writes |
|---|---|---|
| WS-A (pipeline) | raw video, detector config | §1 events on MQTT |
| logbase ingest (WS-A) | §1 events on MQTT | §4.1 SQL rows |
| simulator (WS-C support) | scenario JSON | §4.1 SQL rows + `ground_truth.json` |
| WS-B1 (LLM-SQL) | §4.1 SQL rows, rollup tables (Sprint 2+) | answer envelope + SQL citations |
| WS-B2 (LLM-RAG) | §4.1 SQL rows + derived episode summaries | answer envelope + event_id citations |
| WS-C (eval) | `ground_truth.json` (§3), both LLM envelopes | bench results JSON |

LLM approaches **must not** read `ground_truth.json` or any simulator
artifact directly — they only see `events` rows, identical to what real
edge/MQTT ingestion would produce.

---

## 6. Change control

Any change to this document requires, in order:

1. A one-line rationale in the Git commit message.
2. Bumping the **Version** marker at the top of this file (v1 → v2).
3. A compatibility note at the end of the changed section describing
   what breaks for each workstream.
4. Updating `memory/project_plan_and_scope.md` if the change affects
   scope or contract surface.

Contracts are locked between changes — do not introduce ad-hoc fields,
topic patterns, or column names in code without amending this document
first.
