"""
Crowd detector: counts persons in-frame at exactly 1 Hz.

Emits a crowd event once per second using wall-clock gating (not frame
count, which would drift with variable FPS). The head_count is the raw
YOLO person-class detection count for that frame.

Publishes: crowd
"""
import logging
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import cv2
from ultralytics import YOLO

from detectors.mqtt_publisher import MQTTPublisher

if TYPE_CHECKING:
    from detectors.frame_provider import FrameServer

logger = logging.getLogger(__name__)

_PERSON_CLASS = 0
_EMIT_INTERVAL_S = 1.0   # exactly 1 Hz


def _utc_now_z() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class CrowdDetector:
    def __init__(self, config: dict, publisher: MQTTPublisher):
        self.camera_id = config["camera_id"]
        self.camera_location = config["camera_location"]
        self.conf_threshold = float(config.get("conf_threshold", 0.5))
        self._model = YOLO(config.get("model_path", "yolov8n.pt"))
        self._publisher = publisher
        self._last_emit = 0.0

    def _count_persons(self, frame) -> tuple[int, float]:
        results = self._model(frame, classes=[_PERSON_CLASS],
                              conf=self.conf_threshold, verbose=False)
        if not results or results[0].boxes is None:
            return 0, 0.0
        boxes = results[0].boxes
        n = len(boxes)
        avg_conf = float(boxes.conf.mean().item()) if n > 0 else 0.0
        return n, avg_conf

    def _publish(self, head_count: int, confidence: float) -> None:
        event = {
            "timestamp": _utc_now_z(),
            "camera_id": self.camera_id,
            "event_type": "crowd",
            "object_id": None,
            "confidence": round(confidence, 4),
            "camera_location": self.camera_location,
            "head_count": head_count,
        }
        self._publisher.publish(self.camera_id, event)
        logger.debug("[%s] crowd  head_count=%d", self.camera_id, head_count)

    def run(self, frame_server: "FrameServer", display: bool = False) -> None:
        logger.info("[%s] CrowdDetector started", self.camera_id)
        last_seen = -1
        last_count = 0
        try:
            while True:
                frame, fno = frame_server.request_frame(last_seen=last_seen)
                if frame is None:   # EOF or timeout
                    break
                last_seen = fno
                now = time.monotonic()
                if now - self._last_emit >= _EMIT_INTERVAL_S:
                    last_count, conf = self._count_persons(frame)
                    self._publish(last_count, conf)
                    self._last_emit = now
                if display:
                    cv2.putText(frame, f"Persons: {last_count}", (10, 30),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                    cv2.imshow(f"[{self.camera_id}] crowd", frame)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
        finally:
            if display:
                cv2.destroyAllWindows()
            logger.info("[%s] CrowdDetector stopped", self.camera_id)
