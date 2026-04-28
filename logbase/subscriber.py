"""
MQTT → SQLite ingestor.  Runs on the CENTRAL SERVER.

Subscribes to vforensiq/events/# on the MQTT broker and writes every
incoming event into the local SQLite logbase.

Deployment model
----------------
Edge device  →  MQTT broker  →  [this process]  →  SQLite logbase
(CV pipeline)   (Mosquitto)      (central server)

The edge device and this process can be on completely different machines.
Only the broker host/port needs to be reachable from both sides.

Startup resilience
------------------
If the broker is not yet reachable when this process starts (e.g., the
edge device boots before the server), paho will keep retrying with
exponential backoff (1 s → 30 s) instead of crashing.  The same backoff
applies if the connection drops while running.

Configuration — three equivalent ways (highest priority first):
    1. CLI args          --broker-host  --broker-port  --logbase
    2. Environment vars  MQTT_BROKER_HOST  MQTT_BROKER_PORT  LOGBASE_PATH
    3. Defaults          127.0.0.1  1883  runtime/vforensiq_logbase.db

Usage:
    # Same machine as broker:
    python -m logbase.subscriber

    # Remote broker:
    python -m logbase.subscriber --broker-host 192.168.1.100

    # Or via env:
    MQTT_BROKER_HOST=192.168.1.100 python -m logbase.subscriber
"""
import argparse
import hashlib
import json
import logging
import os
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

import paho.mqtt.client as mqtt
from paho.mqtt.client import CallbackAPIVersion

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[1]

# Defaults — overridden by env vars or CLI args.
_DEFAULT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "127.0.0.1")
_DEFAULT_BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))
_DEFAULT_LOGBASE = Path(os.getenv("LOGBASE_PATH",
                                   str(_REPO_ROOT / "runtime" / "vforensiq_logbase.db")))

_SUBSCRIBE_TOPIC = "vforensiq/events/#"
_REQUIRED_FIELDS = {"timestamp", "camera_id", "event_type", "object_id",
                    "confidence", "camera_location", "head_count"}
_VALID_EVENT_TYPES = {"person_entry", "person_exit", "car_entry", "car_exit", "crowd"}

# Must match docs/contracts.md §4.1 exactly (mirrors simulator/core.py SCHEMA_SQL).
_SCHEMA_SQL = """
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

_INSERT_SQL = """
INSERT INTO events (
    event_id, timestamp_utc, timestamp_epoch_s, camera_id, event_type,
    object_id, confidence, camera_location, head_count, ingested_at_utc
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(event_id) DO NOTHING
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _event_id(camera_id: str, ts_utc: str, event_type: str, object_id) -> str:
    raw = f"{camera_id}|{ts_utc}|{event_type}|{object_id or ''}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def _epoch_from_iso_z(ts: str) -> int:
    return int(datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ")
               .replace(tzinfo=timezone.utc).timestamp())


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Subscriber
# ---------------------------------------------------------------------------

class Subscriber:
    def __init__(self, broker_host: str = _DEFAULT_BROKER_HOST,
                 broker_port: int = _DEFAULT_BROKER_PORT,
                 logbase_path: Path = _DEFAULT_LOGBASE):

        # --- DB setup -------------------------------------------------------
        logbase_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(logbase_path), check_same_thread=False)
        self._conn.executescript("PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;")
        self._conn.executescript(_SCHEMA_SQL)
        self._conn.commit()
        logger.info("Logbase: %s", logbase_path)

        # --- MQTT setup -----------------------------------------------------
        self._broker_host = broker_host
        self._broker_port = broker_port

        self._client = mqtt.Client(CallbackAPIVersion.VERSION2,
                                   client_id="vforensiq-subscriber",
                                   clean_session=True)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message

        # Exponential backoff: 1 s → 30 s.  Applied both to the initial
        # connection attempt and to any later reconnects, so this process
        # survives broker restarts without crashing.
        self._client.reconnect_delay_set(min_delay=1, max_delay=30)

        logger.info("Broker: %s:%d  (will retry until reachable)", broker_host, broker_port)
        # Store connect params for the retry loop in run_forever().
        # Do NOT connect here — run_forever() drives the retry + loop_forever.

    # ------------------------------------------------------------------
    # MQTT callbacks
    # ------------------------------------------------------------------

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            client.subscribe(_SUBSCRIBE_TOPIC, qos=1)
            logger.info("Connected to broker %s:%d  subscribed to %s",
                        self._broker_host, self._broker_port, _SUBSCRIBE_TOPIC)
        else:
            # Log but do NOT exit — paho will retry with backoff automatically.
            logger.warning("Broker connect refused (rc=%s) — will retry", reason_code)

    def _on_disconnect(self, client, userdata, flags, reason_code, properties):
        if reason_code != 0:
            logger.warning("Broker disconnected (rc=%s) — reconnecting with backoff", reason_code)

    def _on_message(self, client, userdata, msg):
        try:
            event = json.loads(msg.payload.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            logger.warning("Bad payload on %s: %s", msg.topic, exc)
            return

        missing = _REQUIRED_FIELDS - set(event.keys())
        if missing:
            logger.warning("Dropping event — missing fields %s", missing)
            return
        if event["event_type"] not in _VALID_EVENT_TYPES:
            logger.warning("Unknown event_type: %s", event["event_type"])
            return

        ts = event["timestamp"]
        try:
            epoch = _epoch_from_iso_z(ts)
        except ValueError:
            logger.warning("Bad timestamp (must be YYYY-MM-DDTHH:MM:SSZ): %s", ts)
            return

        oid = event["object_id"]
        eid = _event_id(event["camera_id"], ts, event["event_type"], oid)
        row = (
            eid, ts, epoch,
            event["camera_id"], event["event_type"],
            str(oid) if oid is not None else None,
            float(event["confidence"]),
            event["camera_location"],
            int(event["head_count"]),
            _now_utc(),
        )
        try:
            self._conn.execute(_INSERT_SQL, row)
            self._conn.commit()
            logger.info("event_id=%-16s  type=%-15s  cam=%s",
                        eid, event["event_type"], event["camera_id"])
        except sqlite3.Error as exc:
            logger.error("DB write error: %s", exc)

    # ------------------------------------------------------------------
    # Run
    # ------------------------------------------------------------------

    def run_forever(self) -> None:
        # Retry initial connect so the subscriber survives broker-not-up at startup.
        # loop_forever() re-connects automatically after any mid-run drop.
        while True:
            try:
                self._client.connect(self._broker_host, self._broker_port, keepalive=60)
                break
            except OSError as exc:
                logger.warning("Cannot reach broker (%s) — retrying in 5 s", exc)
                time.sleep(5)
        try:
            self._client.loop_forever()
        except KeyboardInterrupt:
            logger.info("Subscriber stopped.")
        finally:
            self._conn.close()


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(
        description="vForensIQ MQTT→SQLite subscriber (central server side)"
    )
    ap.add_argument("--broker-host", default=_DEFAULT_BROKER_HOST,
                    help="MQTT broker hostname or IP  (default: %(default)s, "
                         "override with MQTT_BROKER_HOST env var)")
    ap.add_argument("--broker-port", type=int, default=_DEFAULT_BROKER_PORT,
                    help="MQTT broker port  (default: %(default)s)")
    ap.add_argument("--logbase", type=Path, default=_DEFAULT_LOGBASE,
                    help="SQLite logbase path  (default: %(default)s)")
    ap.add_argument("--verbose", action="store_true",
                    help="Show DEBUG-level log lines (individual event inserts)")
    args = ap.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    Subscriber(
        broker_host=args.broker_host,
        broker_port=args.broker_port,
        logbase_path=args.logbase,
    ).run_forever()


if __name__ == "__main__":
    main()
