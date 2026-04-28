"""
Entry / exit event detector for persons and vehicles.

Uses YOLOv8 + ByteTrack to track objects frame-by-frame and fires
line-crossing events according to these rules:

  1. Minimum track age  — a track must be seen for MIN_TRACK_AGE frames
                          before any line-crossing event is considered.
                          Prevents spurious events from noisy new detections.

  2. Both-sides sign    — the object's centroid must be clearly on one side
                          (sign ≠ 0) both before and after the crossing.
                          Skips objects sitting exactly on the line.

  3. Sign flip          — only when the sign changes (crossed the line).

  4. Per-track cooldown — after an event fires for a track_id, that same
                          track_id cannot fire again for COOLDOWN_S seconds.
                          Prevents duplicate events from jittery tracks.

  5. Confidence gate    — detections below conf_threshold are ignored.

  6. Entered vs. exited — determined by which side the object came FROM:
       prev_sign == entry_side_sign → object was on entry side → fired "entry"
       prev_sign != entry_side_sign → object was on exit side  → fired "exit"

Publishes: person_entry, person_exit, car_entry, car_exit
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
_VEHICLE_CLASSES = {2, 5, 7}   # car, bus, truck (COCO)
MIN_TRACK_AGE = 3               # frames
COOLDOWN_S = 3.0                # seconds


def _utc_now_z() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _cross_sign(px: float, py: float, x1: int, y1: int, x2: int, y2: int) -> int:
    val = (x2 - x1) * (py - y1) - (y2 - y1) * (px - x1)
    return 1 if val > 0 else (-1 if val < 0 else 0)


def _event_type(cls: int, entered: bool) -> str:
    if cls == _PERSON_CLASS:
        return "person_entry" if entered else "person_exit"
    return "car_entry" if entered else "car_exit"


class EntryExitDetector:
    def __init__(self, config: dict, publisher: MQTTPublisher):
        self.camera_id = config["camera_id"]
        self.camera_location = config["camera_location"]
        self.conf_threshold = float(config.get("conf_threshold", 0.5))

        line = config["entry_line"]
        self._lx1, self._ly1 = int(line["x1"]), int(line["y1"])
        self._lx2, self._ly2 = int(line["x2"]), int(line["y2"])
        self._entry_sign: int = int(config["entry_side_sign"])  # +1 or -1

        self._model = YOLO(config.get("model_path", "yolov8n.pt"))
        self._publisher = publisher

        # track_id -> {prev_sign, age, last_event_ts, cls}
        self._states: dict[int, dict] = {}

    # ------------------------------------------------------------------
    # Frame processing
    # ------------------------------------------------------------------

    def _process(self, frame) -> None:
        track_classes = [_PERSON_CLASS, *_VEHICLE_CLASSES]
        results = self._model.track(
            frame,
            persist=True,
            classes=track_classes,
            conf=self.conf_threshold,
            iou=0.5,
            tracker="bytetrack.yaml",
            verbose=False,
        )
        if not results or results[0].boxes is None:
            return

        now = time.monotonic()
        active: set[int] = set()

        for box in results[0].boxes:
            if box.id is None:
                continue
            tid = int(box.id[0])
            cls = int(box.cls[0])
            conf = float(box.conf[0])
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
            active.add(tid)

            curr_sign = _cross_sign(cx, cy, self._lx1, self._ly1, self._lx2, self._ly2)
            st = self._states.get(tid)

            if st is None:
                self._states[tid] = {"prev_sign": curr_sign, "age": 1,
                                     "last_event_ts": 0.0, "cls": cls}
                continue

            st["age"] += 1
            prev_sign = st["prev_sign"]

            if (
                st["age"] >= MIN_TRACK_AGE
                and curr_sign != 0
                and prev_sign != 0
                and curr_sign != prev_sign
                and (now - st["last_event_ts"]) >= COOLDOWN_S
            ):
                entered = (prev_sign == self._entry_sign)
                etype = _event_type(cls, entered)
                self._publish(etype, str(tid), conf)
                st["last_event_ts"] = now

            st["prev_sign"] = curr_sign
            st["cls"] = cls

        # Prune tracks no longer visible
        for tid in [k for k in self._states if k not in active]:
            del self._states[tid]

    def _publish(self, event_type: str, object_id: str, confidence: float) -> None:
        event = {
            "timestamp": _utc_now_z(),
            "camera_id": self.camera_id,
            "event_type": event_type,
            "object_id": object_id,
            "confidence": round(confidence, 4),
            "camera_location": self.camera_location,
            "head_count": 0,
        }
        self._publisher.publish(self.camera_id, event)
        logger.info("[%s] %s  track=%s  conf=%.2f", self.camera_id, event_type, object_id, confidence)

    # ------------------------------------------------------------------
    # Debug overlay
    # ------------------------------------------------------------------

    def _overlay(self, frame) -> None:
        cv2.line(frame, (self._lx1, self._ly1), (self._lx2, self._ly2), (0, 60, 255), 2)
        mid = ((self._lx1 + self._lx2) // 2, (self._ly1 + self._ly2) // 2)
        cv2.putText(frame, "ENTRY", (mid[0] + 6, mid[1] - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 220, 0), 2)

    # ------------------------------------------------------------------
    # Run loop  — pull frames from FrameServer on demand
    # ------------------------------------------------------------------

    def run(self, frame_server: "FrameServer", display: bool = False) -> None:
        logger.info("[%s] EntryExitDetector started", self.camera_id)
        last_seen = -1
        try:
            while True:
                frame, fno = frame_server.request_frame(last_seen=last_seen)
                if frame is None:   # EOF or timeout
                    break
                last_seen = fno
                self._process(frame)
                if display:
                    self._overlay(frame)
                    cv2.imshow(f"[{self.camera_id}] entry/exit", frame)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
        finally:
            if display:
                cv2.destroyAllWindows()
            logger.info("[%s] EntryExitDetector stopped", self.camera_id)
