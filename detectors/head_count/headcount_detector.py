import cv2
import json
import time
from datetime import datetime
from ultralytics import YOLO
import threading

class HeadCountDetector:
    """
    Head Count Detector using YOLO.
    Stores detections in JSON log (no video writing).
    """

    def __init__(self, 
                 model_path="yolov8n.pt",
                 camera_id="CAM_01",
                 area_spot="Train Station Entrance",
                 log_path="logs/headcount_events.jsonl"):

        self.model = YOLO(model_path)
        self.camera_id = camera_id
        self.area_spot = area_spot
        self.log_path = log_path

        # person class -> YOLO class 0
        self.PERSON_CLASS_ID = 0

        print(f"[INFO] HeadCountDetector initialized for camera {camera_id}")

    def log_event(self, headcount):
        """Write a JSONL entry for each detection."""
        event = {
            "cv_event_type": "head_count",
            "headcount": headcount,
            "timestamp": datetime.utcnow().isoformat(),
            "camera_id": self.camera_id,
            "area_spot": self.area_spot
        }

        with open(self.log_path, "a") as f:
            f.write(json.dumps(event) + "\n")

        return event

    def process_frame(self, frame):
        """Runs YOLO on a single frame and returns headcount."""
        results = self.model(frame, conf=0.15)[0]

        person_boxes = [
            box for box in results.boxes
            if int(box.cls) == self.PERSON_CLASS_ID
        ]

        headcount = len(person_boxes)
        return headcount

    def run(self, video_path, show_live=False, sleep_ms=1):
        """
        Main loop: Reads frames, performs headcount,
        logs JSON events.
        """

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"❌ ERROR: Cannot open video: {video_path}")
            return

        print(f"[INFO] Processing started for {self.camera_id}")

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            headcount = self.process_frame(frame)
            event = self.log_event(headcount)

            if show_live:
                display = frame.copy()
                cv2.putText(display, f"Headcount: {headcount}", (20, 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
                cv2.imshow(f"Headcount - {self.camera_id}", display)
                if cv2.waitKey(1) & 0xFF == 27:
                    break

            # optional sleep for CPU relief
            time.sleep(sleep_ms / 1000)

        cap.release()
        cv2.destroyAllWindows()
        print(f"[INFO] Finished processing for {self.camera_id}")


# --------------------------------------------------------
# THREAD STARTER FUNCTION (to be called from main program)
# --------------------------------------------------------

def run_headcount_thread(video_path="Data/entry_exit/train_station.mp4",
                         model_path="yolov8s.pt",
                         camera_id="CAM_01",
                         area_spot="train_station_entrance",
                         log_path="logs/headcount_events.jsonl",
                         show_live=False,
                         daemon=False):

    detector = HeadCountDetector(
        model_path=model_path,
        camera_id=camera_id,
        area_spot=area_spot,
        log_path=log_path
    )

    thread = threading.Thread(
        target=detector.run,
        args=(video_path, show_live),
        daemon=daemon
    )
    thread.start()
    return thread


thread=run_headcount_thread() 