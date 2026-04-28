"""
Multi-camera parallel detector pipeline.

Architecture
------------
For every unique video source a single FrameServer thread opens
VideoCapture once and shares frames with all detectors via a pull model.
Detectors call request_frame(last_seen=N) and block until a new frame
is available — no queues, no frame drops.

  - A live webcam (e.g. source=0) or RTSP stream is decoded exactly once,
    even if two detectors (entry_exit + crowd) share the same camera.
  - File-based sources set an EOF flag when the video ends so detector
    threads exit cleanly.
  - RTSP / webcam sources reconnect automatically on drop.

Each detector runs in its own daemon thread.

Usage:
    python -m detectors.pipeline                   # headless, all cameras
    python -m detectors.pipeline --display          # show live windows
    python -m detectors.pipeline --camera CAM_01   # single camera only

Camera configs are loaded from detectors/camera_configs/*.json.
Create them with:  python -m detectors.calibrate ...
"""
import argparse
import json
import logging
import signal
import sys
import threading
from pathlib import Path

from detectors.frame_provider import FrameProviderRegistry
from detectors.mqtt_publisher import MQTTPublisher
from detectors.entry_exit_detector import EntryExitDetector
from detectors.crowd_detector import CrowdDetector

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

_CONFIGS_DIR = Path(__file__).parent / "camera_configs"


def _load_configs(camera_filter: str | None = None) -> list[dict]:
    configs = []
    for path in sorted(_CONFIGS_DIR.glob("*.json")):
        if path.name.startswith("."):
            continue
        try:
            cfg = json.loads(path.read_text())
        except Exception as exc:
            logger.warning("Skipping %s: %s", path.name, exc)
            continue
        if camera_filter and cfg.get("camera_id") != camera_filter:
            continue
        configs.append(cfg)
        logger.info("Loaded config: %s  mode=%s  source=%s",
                    cfg["camera_id"], cfg.get("mode"), cfg.get("video_source"))
    return configs


def run_pipeline(display: bool = False, camera_filter: str | None = None,
                 broker_host: str | None = None, broker_port: int | None = None) -> None:
    configs = _load_configs(camera_filter)
    if not configs:
        logger.error(
            "No camera configs found in %s — run detectors/calibrate.py first.", _CONFIGS_DIR
        )
        sys.exit(1)

    pub_kwargs = {}
    if broker_host:
        pub_kwargs["host"] = broker_host
    if broker_port:
        pub_kwargs["port"] = broker_port
    publisher = MQTTPublisher(**pub_kwargs)
    registry = FrameProviderRegistry()
    threads: list[threading.Thread] = []

    for cfg in configs:
        mode = cfg.get("mode", "entry_exit")
        source = cfg.get("video_source")

        # Each camera pulls frames from its source's shared FrameServer.
        # If two configs share the same source, VideoCapture is opened only once.
        server = registry.get_or_create(source)

        if mode == "entry_exit":
            detector = EntryExitDetector(cfg, publisher)
        elif mode == "crowd":
            detector = CrowdDetector(cfg, publisher)
        else:
            logger.warning("Unknown mode '%s' for %s — skipping", mode, cfg["camera_id"])
            continue

        t = threading.Thread(
            target=detector.run,
            args=(server, display),
            daemon=True,
            name=cfg["camera_id"],
        )
        t.start()
        threads.append(t)
        logger.info("Started %s detector: %s", mode, cfg["camera_id"])

    registry.start_all()
    logger.info("%d detector(s) running across %d source(s).  Ctrl+C to stop.",
                len(threads), len(registry._servers))

    def _shutdown(sig, frame):
        logger.info("Shutdown signal — stopping.")
        registry.stop_all()
        publisher.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    for t in threads:
        t.join()

    registry.stop_all()
    publisher.stop()
    logger.info("All detector threads finished.")


def main() -> None:
    ap = argparse.ArgumentParser(
        description="vForensIQ multi-camera CV detector pipeline (edge device side)"
    )
    ap.add_argument("--display", action="store_true",
                    help="Show live video window per camera (requires a display)")
    ap.add_argument("--camera", metavar="CAMERA_ID", default=None,
                    help="Run only this camera ID (default: all configs)")
    ap.add_argument("--broker-host", default=None,
                    help="MQTT broker hostname or IP  (default: MQTT_BROKER_HOST env var "
                         "or 127.0.0.1)")
    ap.add_argument("--broker-port", type=int, default=None,
                    help="MQTT broker port  (default: MQTT_BROKER_PORT env var or 1883)")
    args = ap.parse_args()
    run_pipeline(args.display, args.camera, args.broker_host, args.broker_port)


if __name__ == "__main__":
    main()
