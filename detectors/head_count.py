import importlib.util
from pathlib import Path

base = Path(__file__).resolve().parent
module_path = base / "head_count" / "headcount_detector.py"
spec = importlib.util.spec_from_file_location("headcount_detector", str(module_path))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
HeadCountDetector = getattr(module, "HeadCountDetector")
run_headcount_thread = getattr(module, "run_headcount_thread")


if __name__ == "__main__":
	run_headcount_thread()