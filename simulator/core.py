"""Scenario-driven simulator. Writes directly to the SQL logbase per docs/contracts.md."""
from __future__ import annotations

import hashlib
import json
import random
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Union

# Resolve paths relative to the project root, not the simulator package dir,
# so running `python -m simulator <name>` from the repo root does what users expect.
_PKG_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _PKG_DIR.parent

DEFAULT_LOGBASE_PATH = _REPO_ROOT / "runtime" / "vforensiq_logbase.db"
SCENARIOS_DIR = _PKG_DIR / "scenarios"
OUT_DIR = _PKG_DIR / "out"

EVENT_TYPES = ["person_entry", "person_exit", "car_entry", "car_exit", "crowd"]

# Must match docs/contracts.md §4.1 exactly.
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS events (
    event_id          TEXT PRIMARY KEY,
    timestamp_utc     TEXT    NOT NULL,
    timestamp_epoch_s INTEGER NOT NULL,
    camera_id         TEXT    NOT NULL,
    event_type        TEXT    NOT NULL,
    object_id         TEXT,
    confidence        REAL    NOT NULL,
    camera_location   TEXT    NOT NULL,
    head_count        INTEGER NOT NULL DEFAULT 0,
    ingested_at_utc   TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_events_ts          ON events(timestamp_epoch_s);
CREATE INDEX IF NOT EXISTS idx_events_cam_ts      ON events(camera_id, timestamp_epoch_s);
CREATE INDEX IF NOT EXISTS idx_events_type_ts     ON events(event_type, timestamp_epoch_s);
CREATE INDEX IF NOT EXISTS idx_events_location_ts ON events(camera_location, timestamp_epoch_s);
"""

INSERT_SQL = """
INSERT INTO events (
    event_id, timestamp_utc, timestamp_epoch_s, camera_id, event_type,
    object_id, confidence, camera_location, head_count, ingested_at_utc
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(event_id) DO NOTHING
"""


# ---------------------------------------------------------------------------
# Helpers (§4.2 event_id, ISO-8601 Z handling).
# ---------------------------------------------------------------------------

def compute_event_id(camera_id: str, timestamp_utc: str, event_type: str, object_id: str | None) -> str:
    raw = f"{camera_id}|{timestamp_utc}|{event_type}|{object_id or ''}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def utc_now_iso_z() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def iso_z_from_epoch(epoch_s: int) -> str:
    return datetime.fromtimestamp(epoch_s, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def epoch_from_iso_z(iso_z: str) -> int:
    if not iso_z.endswith("Z"):
        raise ValueError(f"timestamp must end in Z (UTC): {iso_z}")
    return int(datetime.fromisoformat(iso_z.replace("Z", "+00:00")).timestamp())


# ---------------------------------------------------------------------------
# Scenario data model.
# ---------------------------------------------------------------------------

@dataclass
class HourlyRate:
    """Per-hour event rate with optional peak-hour overrides. Ranges are half-open UTC hours."""
    default: float
    peak_hours: dict[str, float] = field(default_factory=dict)  # e.g. "08-10" -> 200.0

    def rate_at(self, hour_utc: int) -> float:
        for hour_range, peak_rate in self.peak_hours.items():
            start, end = (int(x) for x in hour_range.split("-"))
            if start <= hour_utc < end:
                return float(peak_rate)
        return float(self.default)


@dataclass
class EntryExitTraffic:
    person_rate_per_hour: HourlyRate
    car_rate_per_hour: HourlyRate
    exit_ratio: float
    confidence_range: tuple[float, float]


@dataclass
class CrowdTraffic:
    head_count_baseline: float
    peak_hours: dict[str, float]
    noise_stddev: float
    confidence_range: tuple[float, float]

    def expected_count_at(self, hour_utc: int) -> float:
        for hour_range, peak in self.peak_hours.items():
            start, end = (int(x) for x in hour_range.split("-"))
            if start <= hour_utc < end:
                return float(peak)
        return float(self.head_count_baseline)


@dataclass
class CameraSpec:
    camera_id: str
    camera_location: str
    mode: str  # "entry_exit" | "crowd"
    traffic: Union[EntryExitTraffic, CrowdTraffic]


@dataclass
class Scenario:
    scenario_name: str
    scenario_version: int
    seed: int
    window_start_epoch: int
    window_end_epoch: int
    cameras: list[CameraSpec]

    @property
    def window_start_iso(self) -> str:
        return iso_z_from_epoch(self.window_start_epoch)

    @property
    def window_end_iso(self) -> str:
        return iso_z_from_epoch(self.window_end_epoch)


def load_scenario(path: Path) -> Scenario:
    data = json.loads(path.read_text(encoding="utf-8"))
    window = data["window_utc"]
    cameras: list[CameraSpec] = []
    for cam in data["cameras"]:
        mode = cam["mode"]
        t = cam["traffic"]
        traffic: Union[EntryExitTraffic, CrowdTraffic]
        if mode == "entry_exit":
            traffic = EntryExitTraffic(
                person_rate_per_hour=HourlyRate(**t["person_rate_per_hour"]),
                car_rate_per_hour=HourlyRate(**t["car_rate_per_hour"]),
                exit_ratio=float(t["exit_ratio"]),
                confidence_range=(float(t["confidence_range"][0]), float(t["confidence_range"][1])),
            )
        elif mode == "crowd":
            traffic = CrowdTraffic(
                head_count_baseline=float(t["head_count_baseline"]),
                peak_hours={str(k): float(v) for k, v in t.get("peak_hours", {}).items()},
                noise_stddev=float(t["noise_stddev"]),
                confidence_range=(float(t["confidence_range"][0]), float(t["confidence_range"][1])),
            )
        else:
            raise ValueError(f"Unknown camera mode: {mode!r}")
        cameras.append(CameraSpec(
            camera_id=str(cam["camera_id"]),
            camera_location=str(cam["camera_location"]),
            mode=mode,
            traffic=traffic,
        ))
    return Scenario(
        scenario_name=str(data["scenario_name"]),
        scenario_version=int(data["scenario_version"]),
        seed=int(data["seed"]),
        window_start_epoch=epoch_from_iso_z(window["start"]),
        window_end_epoch=epoch_from_iso_z(window["end"]),
        cameras=cameras,
    )


# ---------------------------------------------------------------------------
# Event generators.
# ---------------------------------------------------------------------------

def generate_entry_exit_events(
    rng: random.Random,
    camera: CameraSpec,
    window_start: int,
    window_end: int,
) -> list[dict[str, Any]]:
    """Event-driven arrivals (homogeneous Poisson per hour)."""
    assert isinstance(camera.traffic, EntryExitTraffic)
    traffic = camera.traffic
    events: list[dict[str, Any]] = []
    object_counter = 0

    current = window_start
    while current < window_end:
        hour_utc = datetime.fromtimestamp(current, tz=timezone.utc).hour
        hour_end = min(current + 3600, window_end)

        for class_name, rate_hourly in (
            ("person", traffic.person_rate_per_hour.rate_at(hour_utc)),
            ("car",    traffic.car_rate_per_hour.rate_at(hour_utc)),
        ):
            if rate_hourly <= 0:
                continue
            per_second = rate_hourly / 3600.0
            t = float(current)
            while True:
                t += rng.expovariate(per_second)
                if t >= hour_end:
                    break
                ts = int(t)
                is_exit = rng.random() < traffic.exit_ratio
                event_type = f"{class_name}_{'exit' if is_exit else 'entry'}"
                object_counter += 1
                confidence = round(rng.uniform(*traffic.confidence_range), 2)
                events.append({
                    "timestamp_utc": iso_z_from_epoch(ts),
                    "timestamp_epoch_s": ts,
                    "camera_id": camera.camera_id,
                    "event_type": event_type,
                    "object_id": str(object_counter),
                    "confidence": confidence,
                    "camera_location": camera.camera_location,
                    "head_count": 0,
                })
        current = hour_end
    return events


def generate_crowd_events(
    rng: random.Random,
    camera: CameraSpec,
    window_start: int,
    window_end: int,
) -> list[dict[str, Any]]:
    """Periodic 1 Hz sampling with Gaussian noise around the expected count."""
    assert isinstance(camera.traffic, CrowdTraffic)
    traffic = camera.traffic
    events: list[dict[str, Any]] = []

    for ts in range(window_start, window_end):
        hour_utc = datetime.fromtimestamp(ts, tz=timezone.utc).hour
        expected = traffic.expected_count_at(hour_utc)
        noisy = rng.gauss(expected, traffic.noise_stddev)
        head_count = max(0, int(round(noisy)))
        confidence = round(rng.uniform(*traffic.confidence_range), 2)
        events.append({
            "timestamp_utc": iso_z_from_epoch(ts),
            "timestamp_epoch_s": ts,
            "camera_id": camera.camera_id,
            "event_type": "crowd",
            "object_id": None,
            "confidence": confidence,
            "camera_location": camera.camera_location,
            "head_count": head_count,
        })
    return events


# ---------------------------------------------------------------------------
# SQL sink.
# ---------------------------------------------------------------------------

def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_SQL)


def reset_scenario_rows(conn: sqlite3.Connection, scenario: Scenario) -> int:
    """Remove prior rows that fall under this scenario's (cameras × window) before re-running."""
    if not scenario.cameras:
        return 0
    camera_ids = [c.camera_id for c in scenario.cameras]
    placeholders = ",".join("?" for _ in camera_ids)
    cursor = conn.execute(
        f"DELETE FROM events WHERE camera_id IN ({placeholders}) "
        "AND timestamp_epoch_s >= ? AND timestamp_epoch_s < ?",
        (*camera_ids, scenario.window_start_epoch, scenario.window_end_epoch),
    )
    return cursor.rowcount or 0


def write_events(conn: sqlite3.Connection, events: list[dict[str, Any]]) -> None:
    ingested_at = utc_now_iso_z()
    rows = []
    for e in events:
        event_id = compute_event_id(
            e["camera_id"], e["timestamp_utc"], e["event_type"], e["object_id"],
        )
        rows.append((
            event_id,
            e["timestamp_utc"],
            e["timestamp_epoch_s"],
            e["camera_id"],
            e["event_type"],
            e["object_id"],
            e["confidence"],
            e["camera_location"],
            e["head_count"],
            ingested_at,
        ))
    conn.executemany(INSERT_SQL, rows)


# ---------------------------------------------------------------------------
# Ground truth.
# ---------------------------------------------------------------------------

def compute_ground_truth(scenario: Scenario, events: list[dict[str, Any]]) -> dict[str, Any]:
    counts_by_type = {et: 0 for et in EVENT_TYPES}
    for e in events:
        counts_by_type[e["event_type"]] = counts_by_type.get(e["event_type"], 0) + 1

    return {
        "scenario_name": scenario.scenario_name,
        "scenario_version": scenario.scenario_version,
        "seed": scenario.seed,
        "window_utc": {
            "start": scenario.window_start_iso,
            "end":   scenario.window_end_iso,
        },
        "cameras": [
            {
                "camera_id": c.camera_id,
                "camera_location": c.camera_location,
                "mode": c.mode,
            }
            for c in scenario.cameras
        ],
        "known_facts": {
            "total_events": len(events),
            "counts_by_event_type": counts_by_type,
            # L4/L5 scenarios will add structured peaks/anomalies here.
            "peaks": [],
            "anomalies": [],
        },
    }


# ---------------------------------------------------------------------------
# Orchestrator.
# ---------------------------------------------------------------------------

def run_scenario(
    scenario_name: str,
    logbase_path: Path = DEFAULT_LOGBASE_PATH,
    scenarios_dir: Path = SCENARIOS_DIR,
    out_dir: Path = OUT_DIR,
) -> dict[str, Any]:
    scenario_path = scenarios_dir / f"{scenario_name}.json"
    if not scenario_path.exists():
        raise FileNotFoundError(f"Scenario not found: {scenario_path}")
    scenario = load_scenario(scenario_path)

    rng = random.Random(scenario.seed)
    all_events: list[dict[str, Any]] = []
    for cam in scenario.cameras:
        if cam.mode == "entry_exit":
            all_events.extend(generate_entry_exit_events(
                rng, cam, scenario.window_start_epoch, scenario.window_end_epoch,
            ))
        elif cam.mode == "crowd":
            all_events.extend(generate_crowd_events(
                rng, cam, scenario.window_start_epoch, scenario.window_end_epoch,
            ))
    all_events.sort(key=lambda e: (e["timestamp_epoch_s"], e["camera_id"]))

    logbase_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(logbase_path, timeout=30)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        init_schema(conn)
        deleted = reset_scenario_rows(conn, scenario)
        write_events(conn, all_events)
        conn.commit()
    finally:
        conn.close()

    ground_truth = compute_ground_truth(scenario, all_events)
    scenario_out = out_dir / scenario.scenario_name
    scenario_out.mkdir(parents=True, exist_ok=True)
    gt_path = scenario_out / "ground_truth.json"
    gt_path.write_text(json.dumps(ground_truth, indent=2) + "\n", encoding="utf-8")

    return {
        "scenario_name": scenario.scenario_name,
        "seed": scenario.seed,
        "window_utc": {"start": scenario.window_start_iso, "end": scenario.window_end_iso},
        "generated_events": len(all_events),
        "deleted_prior_rows": deleted,
        "logbase_path": str(logbase_path),
        "ground_truth_path": str(gt_path),
    }
