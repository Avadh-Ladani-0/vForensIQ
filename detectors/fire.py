import cv2
from ultralytics import YOLO

# -----------------------------
# CONFIG
# -----------------------------
MODEL_PATH = "CV-Event\yolov8n-fire.pt"     # change to yolov8s.pt / yolov8m.pt etc.
VIDEO_PATH = "Data\Siberian mall fire_ CCTV shows fire erupting.mp4"      # CCTV video file
CONF_THRESH = 0.35            # confidence threshold
SAVE_OUTPUT = True            # save output? True/False
OUTPUT_PATH = "output.mp4"    # output video file

# -----------------------------
# LOAD MODEL
# -----------------------------
print("[INFO] Loading YOLOv8 model...")
model = YOLO(MODEL_PATH)

# -----------------------------
# VIDEO SETUP
# -----------------------------
cap = cv2.VideoCapture(VIDEO_PATH)

width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fps    = cap.get(cv2.CAP_PROP_FPS)

if SAVE_OUTPUT:
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(OUTPUT_PATH, fourcc, fps, (width, height))

print("[INFO] Running inference...")

# -----------------------------
# MAIN LOOP
# -----------------------------
while True:

    ret, frame = cap.read()
    if not ret:
        break
    

    # YOLO inference
    results = model(frame, conf=CONF_THRESH)

    # Parse detection results
    annotated_frame = results[0].plot()  # draws boxes

    # Save output
    if SAVE_OUTPUT:
        writer.write(annotated_frame)

    # Show live view
    cv2.imshow("YOLOv8 CCTV Inference", annotated_frame)

    # Exit on 'q'
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# -----------------------------
# CLEANUP
# -----------------------------
cap.release()
if SAVE_OUTPUT:
    writer.release()

cv2.destroyAllWindows()
print("[INFO] Done!")
