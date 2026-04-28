"""
Calibration tool for vForensIQ camera line setup.

Works with both live cameras (webcam index / RTSP URL) and video files.

  - Live cameras  : shows the live feed continuously so you always see the
                    current scene. Press SPACE to freeze a frame before clicking.
  - Video files   : plays the video on a loop so you can pick the right moment.
                    Press SPACE to pause, SPACE again to resume.

For entry_exit cameras:
  Click 3 times to calibrate:
    Click 1 — LINE START  (point A on the crossing line)
    Click 2 — LINE END    (point B on the crossing line)
    Click 3 — ENTRY SIDE  (click anywhere on the side people come FROM when entering)

  Entry vs exit is determined by which side of the line the tracked object
  was on before it crossed. Clicking the entry side stores the sign of the
  cross-product so the detector knows the direction at runtime.

For crowd cameras:
  No line needed — just confirm the source looks correct and press S to save.

Config saved to: detectors/camera_configs/{camera_id}.json

Usage:
    python -m detectors.calibrate \\
        --source 0 \\
        --camera-id CAM_01 \\
        --location "Gate_MainEntrance" \\
        --mode entry_exit

    python -m detectors.calibrate \\
        --source /path/to/video.mp4 \\
        --camera-id CAM_02 \\
        --location "ExpoFloor_Aisle" \\
        --mode crowd

Controls:
    SPACE          pause / resume  (freeze a frame to click precisely)
    Left-click     place calibration point (entry_exit mode only)
    R              reset all clicks
    S              save config and exit
    Q / ESC        quit without saving
"""
import argparse
import json
import sys
from pathlib import Path

import cv2

_CONFIGS_DIR = Path(__file__).parent / "camera_configs"
_CONFIGS_DIR.mkdir(exist_ok=True)


def _cross(px, py, x1, y1, x2, y2) -> int:
    """Sign of cross product — which side of directed line (x1,y1)→(x2,y2) the point is on."""
    val = (x2 - x1) * (py - y1) - (y2 - y1) * (px - x1)
    return 1 if val > 0 else (-1 if val < 0 else 0)


class _State:
    def __init__(self, mode: str):
        self.mode = mode
        self.step = 0
        self.pt1 = None
        self.pt2 = None
        self.entry_sign = None  # +1 or -1

    def reset(self):
        self.step = 0
        self.pt1 = self.pt2 = self.entry_sign = None

    def click(self, x: int, y: int):
        if self.mode == "crowd":
            return
        if self.step == 0:
            self.pt1 = (x, y)
            self.step = 1
        elif self.step == 1:
            if (x, y) == self.pt1:
                return
            self.pt2 = (x, y)
            self.step = 2
        elif self.step == 2:
            s = _cross(x, y, *self.pt1, *self.pt2)
            if s == 0:
                print("[calibrate] Clicked exactly on the line — click clearly to one side.")
                return
            self.entry_sign = s
            self.step = 3

    @property
    def ready(self) -> bool:
        return self.mode == "crowd" or self.step == 3


# ---------------------------------------------------------------------------
# Overlay drawing
# ---------------------------------------------------------------------------

_STEP_HINTS = {
    0: "Click 1/3  LINE START (point A)",
    1: "Click 2/3  LINE END   (point B)",
    2: "Click 3/3  ENTRY SIDE (where people come FROM when entering)",
    3: "S=Save   R=Reset   Q=Quit",
}


def _draw(frame, state: _State, camera_id: str, location: str, paused: bool):
    h, _ = frame.shape[:2]

    # Header
    cv2.putText(frame, f"{camera_id}  |  {location}  |  {state.mode}",
                (10, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2)

    # Step hint
    if state.mode == "crowd":
        hint = "S=Save   Q=Quit"
    else:
        hint = _STEP_HINTS.get(min(state.step, 3), "")
    cv2.putText(frame, hint, (10, h - 38), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)

    # SPACE hint (always visible)
    space_hint = "PAUSED — SPACE to resume" if paused else "SPACE = freeze frame"
    color = (0, 200, 255) if paused else (180, 180, 180)
    cv2.putText(frame, space_hint, (10, h - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

    # Calibration geometry
    if state.pt1:
        cv2.circle(frame, state.pt1, 7, (0, 255, 0), -1)
        cv2.putText(frame, "A", (state.pt1[0] + 9, state.pt1[1] - 7),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2)

    if state.pt1 and state.pt2:
        cv2.line(frame, state.pt1, state.pt2, (0, 60, 255), 2)
        cv2.circle(frame, state.pt2, 7, (0, 60, 255), -1)
        cv2.putText(frame, "B", (state.pt2[0] + 9, state.pt2[1] - 7),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 60, 255), 2)

    if state.step == 3:
        mid = ((state.pt1[0] + state.pt2[0]) // 2, (state.pt1[1] + state.pt2[1]) // 2)
        cv2.putText(frame, "ENTRY ZONE", (mid[0] + 10, mid[1] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 220, 0), 2)


# ---------------------------------------------------------------------------
# Main calibration loop
# ---------------------------------------------------------------------------

def calibrate(source, camera_id: str, location: str, mode: str,
              model_path: str = "yolov8n.pt", conf: float = 0.5) -> None:
    src = int(source) if str(source).isdigit() else str(source)
    is_live = isinstance(src, int) or str(source).startswith(("rtsp://", "rtmp://"))

    cap = cv2.VideoCapture(src)
    if not cap.isOpened():
        sys.exit(f"[calibrate] Cannot open source: {source}")

    # Read the first frame to confirm source works
    ok, current_frame = cap.read()
    if not ok:
        cap.release()
        sys.exit("[calibrate] Cannot read a frame — check path or index.")

    state = _State(mode)
    paused = False

    win = f"vForensIQ Calibrate — {camera_id}"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)
    cv2.setMouseCallback(win, lambda event, x, y, flags, param:
                         state.click(x, y) if event == cv2.EVENT_LBUTTONDOWN else None)

    saved = False
    while True:
        # ---- advance frame ------------------------------------------------
        if not paused:
            ok, frame = cap.read()
            if not ok:
                if is_live:
                    # Live source: wait briefly for the next frame
                    if cv2.waitKey(30) & 0xFF in (ord('q'), ord('Q'), 27):
                        break
                    continue
                else:
                    # Video file ended: loop back to frame 0
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ok, frame = cap.read()
                    if not ok:
                        break
            current_frame = frame

        # ---- render -------------------------------------------------------
        display = current_frame.copy()
        _draw(display, state, camera_id, location, paused)
        cv2.imshow(win, display)

        # ---- keys ---------------------------------------------------------
        key = cv2.waitKey(30) & 0xFF

        if key in (ord('q'), ord('Q'), 27):
            print("[calibrate] Exited without saving.")
            break

        elif key == ord(' '):
            paused = not paused

        elif key in (ord('r'), ord('R')):
            state.reset()

        elif key in (ord('s'), ord('S')):
            if not state.ready:
                remaining = 3 - state.step if mode == "entry_exit" else 0
                print(f"[calibrate] Cannot save — {remaining} click(s) still needed.")
                continue

            cfg = {
                "camera_id": camera_id,
                "camera_location": location,
                "mode": mode,
                "video_source": str(source),
                "model_path": model_path,
                "conf_threshold": conf,
            }
            if mode == "entry_exit":
                cfg["entry_line"] = {
                    "x1": state.pt1[0], "y1": state.pt1[1],
                    "x2": state.pt2[0], "y2": state.pt2[1],
                }
                cfg["entry_side_sign"] = state.entry_sign
            dest = _CONFIGS_DIR / f"{camera_id}.json"
            dest.write_text(json.dumps(cfg, indent=2))
            print(f"[calibrate] Saved: {dest}")
            saved = True
            break

    cap.release()
    cv2.destroyAllWindows()
    return saved


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="vForensIQ camera calibration tool")
    ap.add_argument("--source", required=True,
                    help="Webcam index (0, 1 …), RTSP URL, or video file path")
    ap.add_argument("--camera-id", required=True, dest="camera_id")
    ap.add_argument("--location", required=True, help="Camera location label used in events")
    ap.add_argument("--mode", choices=["entry_exit", "crowd"], required=True)
    ap.add_argument("--model", default="yolov8n.pt", help="YOLO model weights (default: yolov8n.pt)")
    ap.add_argument("--conf", type=float, default=0.5, help="Detection confidence threshold")
    args = ap.parse_args()
    calibrate(args.source, args.camera_id, args.location, args.mode, args.model, args.conf)


if __name__ == "__main__":
    main()
