# vForensIQ — Deployment Guide

Two machines, two roles:

```
┌─────────────────────────────┐          ┌──────────────────────────────────────┐
│        EDGE DEVICE          │          │           CENTRAL SERVER             │
│  (camera-side machine)      │          │  (broker + logbase + LLM queries)    │
│                             │  MQTT    │                                      │
│  FrameServer                │ ───────► │  Mosquitto broker  (Docker)          │
│  EntryExitDetector          │  1883    │  logbase/subscriber.py  → SQLite     │
│  CrowdDetector              │          │  LLM query pipeline (B1 / B2 / AQR)  │
│                             │          │  Streamlit UI                        │
└─────────────────────────────┘          └──────────────────────────────────────┘
```

The central server must be reachable from the edge device on port 1883 (MQTT).
No connection is needed in the other direction.

---

## Part 1 — Central Server Setup

### 1.1  Prerequisites

- Docker and Docker Compose v2
- Python 3.10+
- Git

### 1.2  Clone the repo

```bash
git clone <repo-url> vForensIQ
cd vForensIQ
```

### 1.3  Start Mosquitto broker

```bash
docker compose up -d mosquitto
```

Verify it is listening:

```bash
docker compose logs mosquitto
# expect: "mosquitto version X.Y.Z running"
```

The broker binds to `0.0.0.0:1883` (all interfaces) so the edge device can
reach it. If your server has a firewall, open TCP port 1883:

```bash
# Ubuntu / Debian (ufw)
sudo ufw allow 1883/tcp
```

### 1.4  Create the Python environment

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 1.5  Configure environment

```bash
cp .env.server.example .env
```

Edit `.env`:

```ini
MQTT_BROKER_HOST=127.0.0.1   # broker runs locally
MQTT_BROKER_PORT=1883
LOGBASE_PATH=/opt/vforensiq/runtime/vforensiq_logbase.db   # or any writable path
OPENAI_API_KEY=sk-...
```

Load it before running any Python commands:

```bash
set -a && source .env && set +a
```

Or prefix each command: `env $(cat .env | grep -v ^#) <command>`.

### 1.6  Start the subscriber

The subscriber listens to MQTT and writes every incoming event into SQLite.
Run it in its own terminal (or as a systemd service — see section 1.7):

```bash
python -m logbase.subscriber
```

Expected output:

```
2026-04-18 10:00:00 INFO Broker: 127.0.0.1:1883  (will retry until reachable)
2026-04-18 10:00:00 INFO Logbase: /opt/vforensiq/runtime/vforensiq_logbase.db
2026-04-18 10:00:01 INFO Connected to broker 127.0.0.1:1883  subscribed to vforensiq/events/#
```

The subscriber starts before the edge device connects — that is fine. It will
wait indefinitely. If the broker goes down mid-run it reconnects automatically
(1 s → 30 s exponential backoff).

### 1.7  (Optional) Run subscriber as a systemd service

```ini
# /etc/systemd/system/vforensiq-subscriber.service
[Unit]
Description=vForensIQ MQTT subscriber
After=docker.service

[Service]
User=<your-user>
WorkingDirectory=/path/to/vForensIQ
EnvironmentFile=/path/to/vForensIQ/.env
ExecStart=/path/to/vForensIQ/.venv/bin/python -m logbase.subscriber
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now vforensiq-subscriber
sudo systemctl status vforensiq-subscriber
```

### 1.8  Start the Streamlit UI (optional)

```bash
streamlit run chat_ui.py
```

Open `http://<server-ip>:8501` in a browser.

---

## Part 2 — Edge Device Setup

The edge device only needs the lightweight CV stack — no Neo4j, no LLM.

### 2.1  Prerequisites

- Python 3.10+
- A display (for calibration) — headless pipeline run is fine without one
- Camera: USB webcam (`/dev/video0`), RTSP stream, or a video file for testing
- Network access to the central server on port 1883

### 2.2  Clone the repo

```bash
git clone <repo-url> vForensIQ
cd vForensIQ
```

### 2.3  Create the Python environment

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-edge.txt
```

> **GPU note**: if the edge device has an NVIDIA GPU, install the matching
> CUDA-enabled torch *before* the requirements file:
>
> ```bash
> pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
> pip install -r requirements-edge.txt
> ```

### 2.4  Download YOLO weights

If `yolov8n.pt` is not present in the repo root, ultralytics downloads it
automatically on first run. To pre-download:

```bash
python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"
```

### 2.5  Configure environment

```bash
cp .env.edge.example .env
```

Edit `.env` — set `MQTT_BROKER_HOST` to the central server's IP:

```ini
MQTT_BROKER_HOST=192.168.1.100   # replace with your server's IP
MQTT_BROKER_PORT=1883
```

Load it:

```bash
set -a && source .env && set +a
```

### 2.6  Calibrate cameras

Run the calibration tool once per camera. It opens a window on the feed so
you can draw the entry/exit line interactively.

**Entry / exit camera** (persons and vehicles crossing a line):

```bash
python -m detectors.calibrate \
    --source 0 \
    --camera-id CAM_01 \
    --location "Gate_MainEntrance" \
    --mode entry_exit
```

In the window:

1. **Click 1** — line start (point A)
2. **Click 2** — line end (point B)
3. **Click 3** — click anywhere on the **entry side** (the side people come FROM when entering)
4. Press **S** to save

Other controls: `SPACE` freezes/resumes the feed, `R` resets clicks, `Q`/`ESC` quits without saving.

**Crowd / density camera** (person count only, no line needed):

```bash
python -m detectors.calibrate \
    --source /path/to/video.mp4 \
    --camera-id CAM_02 \
    --location "ExpoFloor_Aisle" \
    --mode crowd
```

Confirm the feed looks correct, then press **S** to save.

Config is written to `detectors/camera_configs/<camera-id>.json`. Run once
per camera; re-run any time to update the line.

**Calibrate from a video file** (useful for testing without a live camera):

```bash
python -m detectors.calibrate \
    --source /path/to/scene.mp4 \
    --camera-id CAM_TEST \
    --location "TestZone" \
    --mode entry_exit
```

The video loops automatically so you can pick a good frame.

### 2.7  Run the detector pipeline

```bash
python -m detectors.pipeline
```

This starts one detector thread per camera config found in
`detectors/camera_configs/`. Events are published to the broker immediately
on detection.

Useful flags:

```bash
# Show live video windows (requires a display / X11)
python -m detectors.pipeline --display

# Run only one specific camera
python -m detectors.pipeline --camera CAM_01

# Override broker address without editing .env
python -m detectors.pipeline --broker-host 192.168.1.100 --broker-port 1883
```

Expected startup output:

```
2026-04-18 10:05:00 INFO Loaded config: CAM_01  mode=entry_exit  source=0
2026-04-18 10:05:00 INFO Loaded config: CAM_02  mode=crowd  source=/path/to/video.mp4
2026-04-18 10:05:00 INFO Started entry_exit detector: CAM_01
2026-04-18 10:05:00 INFO Started crowd detector: CAM_02
2026-04-18 10:05:00 INFO FrameServer: connected  source=0  live=True
2026-04-18 10:05:00 INFO MQTT publisher targeting broker 192.168.1.100:1883
2026-04-18 10:05:01 INFO MQTT connected to broker 192.168.1.100:1883
```

On the central server you should see the subscriber logging incoming events:

```
2026-04-18 10:05:15 INFO event_id=a3f2c91b4e78d021  type=person_entry  cam=CAM_01
2026-04-18 10:05:16 INFO event_id=8b6e3a220c14f9d7  type=crowd         cam=CAM_02
```

---

## Part 3 — Camera Config Reference

Each file in `detectors/camera_configs/` looks like this:

**Entry / exit camera:**

```json
{
  "camera_id": "CAM_01",
  "camera_location": "Gate_MainEntrance",
  "mode": "entry_exit",
  "video_source": "0",
  "model_path": "yolov8n.pt",
  "conf_threshold": 0.5,
  "entry_line": {
    "x1": 320, "y1": 100,
    "x2": 320, "y2": 400
  },
  "entry_side_sign": 1
}
```

**Crowd camera:**

```json
{
  "camera_id": "CAM_02",
  "camera_location": "ExpoFloor_Aisle",
  "mode": "crowd",
  "video_source": "/data/videos/floor.mp4",
  "model_path": "yolov8n.pt",
  "conf_threshold": 0.5
}
```

| Field | Description |
|---|---|
| `camera_id` | Unique string; also used as the MQTT sub-topic |
| `camera_location` | Free-text label stored in every event |
| `mode` | `entry_exit` or `crowd` |
| `video_source` | Webcam index, RTSP URL, or file path |
| `model_path` | YOLO weights file (relative to working dir) |
| `conf_threshold` | Minimum detection confidence (0–1) |
| `entry_line` | Line coordinates set by calibration (entry_exit only) |
| `entry_side_sign` | +1 or -1, set by calibration (entry_exit only) |

---

## Part 4 — Events Published

All five event types share the same JSON envelope:

```json
{
  "timestamp":       "2026-04-18T10:05:15Z",
  "camera_id":       "CAM_01",
  "event_type":      "person_entry",
  "object_id":       "42",
  "confidence":      0.8731,
  "camera_location": "Gate_MainEntrance",
  "head_count":      0
}
```

| `event_type` | Trigger | `object_id` | `head_count` |
|---|---|---|---|
| `person_entry` | Person crosses line inbound | ByteTrack track ID | 0 |
| `person_exit` | Person crosses line outbound | ByteTrack track ID | 0 |
| `car_entry` | Vehicle crosses line inbound | ByteTrack track ID | 0 |
| `car_exit` | Vehicle crosses line outbound | ByteTrack track ID | 0 |
| `crowd` | Once per second (1 Hz) | null | Person count |

**Entry/exit detection rules:**

1. Track must be seen for ≥ 3 frames (prevents spurious detections)
2. Object centroid must be clearly on one side of the line before and after crossing
3. Sign of cross-product must flip (true crossing, not jitter)
4. 3-second cooldown per track ID (prevents duplicate events)
5. Confidence must be ≥ `conf_threshold`

**MQTT topic:** `vforensiq/events/{camera_id}`  
**QoS:** 1 (at-least-once). Events published while the broker is unreachable
are buffered by paho and delivered once the connection is restored.

---

## Part 5 — Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Publisher logs "will retry" but never connects | Edge device cannot reach server port 1883 | Check firewall (`ufw`, `iptables`, security groups); verify broker is running (`docker ps`) |
| Subscriber logs events but DB is empty | Wrong `LOGBASE_PATH` | Check path exists and is writable; check `LOGBASE_PATH` env var |
| 0 entry/exit events, crowd events only | `lap` not installed | `pip install lap==0.5.13`; ByteTrack requires it |
| Calibration window is frozen / static | Normal for live cam — press SPACE to unfreeze | SPACE toggles pause |
| `No camera configs found` | Calibration not done | Run `python -m detectors.calibrate ...` first |
| Duplicate events after reconnect | Expected — QoS 1 delivers at-least-once | DB has `ON CONFLICT DO NOTHING` dedup on `event_id` |
