from ultralytics import YOLO
import cv2
import numpy as np
from deep_sort_realtime.deepsort_tracker import DeepSort
from datetime import datetime
import json, os

# 1. Load YOLO model
model = YOLO('yolov8n.pt')  # or 'yolov8s.pt' for better accuracy

# 2. Initialize tracker
tracker = DeepSort(max_age=30)

# 3. Define entry/exit line (x1,y1,x2,y2)
ENTRY_LINE = ((100, 300), (500, 300))  # adjust to your frame
LINE_ORIENTATION = 'horizontal'

# 4. Prepare log directory
LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "entry_exit_log.json")
os.makedirs(LOG_DIR, exist_ok=True)

def log_event(event_type, object_id):
    """Store each event in JSON file and print to console"""
    log = {
        "timestamp": datetime.now().isoformat(),
        "camera_id": "CAM_01",
        "event_type": event_type,
        "object_id": object_id,
        "confidence": 0.95
    }
    # ✅ print for quick debugging
    print(json.dumps(log, indent=2))

    # ✅ append to JSON file
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r+", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = []
            data.append(log)
            f.seek(0)
            json.dump(data, f, indent=2)
    else:
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            json.dump([log], f, indent=2)


# 5. Process video
cap = cv2.VideoCapture(r"Data\entry_exit\train_station.mp4")
prev_positions = {}

while True:
    ret, frame = cap.read()
    if not ret:
        break

    results = model.predict(frame, verbose=False)[0]
    detections = []
    for box in results.boxes:
        cls = int(box.cls)
        if model.names[cls] == 'person':
            x1, y1, x2, y2 = box.xyxy[0]
            conf = float(box.conf)
            detections.append(([x1, y1, x2 - x1, y2 - y1], conf, 'person'))

    tracks = tracker.update_tracks(detections, frame=frame)
    for track in tracks:
        if not track.is_confirmed():
            continue
        tid = track.track_id
        x1, y1, x2, y2 = track.to_ltrb()
        center_y = (y1 + y2) / 2
        center_x = (x1 + x2) / 2

        prev = prev_positions.get(tid)
        if prev:
            if LINE_ORIENTATION == 'horizontal':
                if prev[1] < ENTRY_LINE[0][1] <= center_y:
                    log_event("ENTRY", tid)
                elif prev[1] > ENTRY_LINE[0][1] >= center_y:
                    log_event("EXIT", tid)
        prev_positions[tid] = (center_x, center_y)

    # Visualization
    cv2.line(frame, ENTRY_LINE[0], ENTRY_LINE[1], (0, 255, 0), 2)
    cv2.imshow("EntryExit Detection", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()