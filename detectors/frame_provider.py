"""
FrameServer — pull-based shared camera access for edge detectors.

Architecture
------------
One FrameServer per physical camera source runs a single reader thread
that continuously decodes frames.  All event detectors call
request_frame() to pull the next frame when they are ready to process it.

Why pull, not push
------------------
Push (queue-based): the reader blindly fills queues.  A slow detector
falls behind; with small queues frames are dropped; with large queues
memory grows.  The reader drives the pace.

Pull (this module): each detector calls request_frame(last_seen=N) and
blocks until a frame newer than N is available.  The reader calls
notify_all() so every waiting detector wakes up and reads the same frame
simultaneously.  No queues, no drops, no wasted copies.

Live vs file behaviour
----------------------
Live camera (webcam index / RTSP)
  Detectors that fall behind naturally "catch up" to the latest frame on
  their next request_frame() call — they skip the frames they missed
  (fine for real-time analytics).

Video file
  The reader produces frames as fast as the detector threads consume them
  (it blocks on notify_all → re-read only after consumers are done).
  Every frame is processed; no frames are dropped.

Usage
-----
    server = FrameServer("/dev/video0")
    server.start()

    # in detector thread:
    last = -1
    while True:
        frame, fno = server.request_frame(last_seen=last)
        if frame is None:
            break           # EOF or timeout
        last = fno
        # … process frame …

Multiple detectors sharing one camera:
    server = FrameServer("rtsp://cam1/stream")
    server.start()
    # each detector thread calls server.request_frame() independently
    # VideoCapture is opened exactly once
"""
import cv2
import logging
import threading
import time
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

_RECONNECT_DELAY_S = 2.0


def _is_live(source) -> bool:
    s = str(source)
    return s.isdigit() or s.startswith("rtsp://") or s.startswith("rtmp://")


class FrameServer:
    """
    Single-reader, multi-consumer camera frame server.

    The reader thread writes each decoded frame into a shared slot and
    calls notify_all() on the condition variable.  Any number of detector
    threads can call request_frame() concurrently; they all wake up and
    receive the same frame without any copying overhead until they
    actually need to modify it.
    """

    def __init__(self, source):
        self.source   = source
        self._src     = int(source) if str(source).isdigit() else source
        self._live    = _is_live(source)

        self._frame:    Optional[np.ndarray] = None
        self._frame_no: int  = 0       # increments on every decoded frame
        self._eof:      bool = False   # set when a video file is exhausted
        self._cond  = threading.Condition()

        self._running = False
        self._thread: Optional[threading.Thread] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        self._running = True
        self._thread  = threading.Thread(
            target=self._reader,
            daemon=True,
            name=f"FrameServer:{self.source}",
        )
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        with self._cond:
            self._eof = True          # unblock detectors waiting on first frame
            self._cond.notify_all()   # unblock any waiting detectors

    def request_frame(
        self,
        last_seen: int = -1,
        timeout:   float = 10.0,
    ) -> tuple[Optional[np.ndarray], int]:
        """
        Block until a frame newer than `last_seen` is available, then
        return (frame_copy, frame_no).

        Args:
            last_seen : frame_no of the last frame this detector processed.
                        Pass -1 (default) to receive the very first frame.
            timeout   : maximum seconds to wait before returning (None, -1).

        Returns:
            (frame, frame_no)  –  frame is None on EOF or timeout.
        """
        with self._cond:
            deadline = time.monotonic() + timeout
            # Wait while there is no new frame AND the server is not done.
            # Includes self._frame is None so we block until the reader has
            # decoded at least one frame (covers the startup race where
            # detectors call request_frame before start() has run).
            while (
                (self._frame is None or self._frame_no <= last_seen)
                and not self._eof
            ):
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return None, -1
                self._cond.wait(timeout=remaining)

            if self._eof and (self._frame is None or self._frame_no <= last_seen):
                return None, -1   # video file ended, nothing new

            if self._frame is None:
                return None, -1

            # Return a copy so detectors can draw overlays without
            # corrupting the shared slot for other detectors.
            return self._frame.copy(), self._frame_no

    # ------------------------------------------------------------------
    # Reader thread
    # ------------------------------------------------------------------

    def _reader(self) -> None:
        while self._running:
            cap = cv2.VideoCapture(self._src)
            if not cap.isOpened():
                logger.error("FrameServer: cannot open %s — retry in %ds",
                             self.source, _RECONNECT_DELAY_S)
                time.sleep(_RECONNECT_DELAY_S)
                continue

            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            # Throttle file sources to their native FPS so ByteTrack sees
            # realistic inter-frame timing and the 1 Hz crowd gate fires
            # proportionally to the video duration.
            frame_interval = (1.0 / fps) if not self._live else 0.0

            logger.info("FrameServer: connected  source=%s  live=%s  fps=%.1f",
                        self.source, self._live, fps)

            last_frame_t = time.monotonic()
            while self._running:
                if frame_interval > 0:
                    elapsed = time.monotonic() - last_frame_t
                    if elapsed < frame_interval:
                        time.sleep(frame_interval - elapsed)
                    last_frame_t = time.monotonic()

                ok, frame = cap.read()
                if not ok:
                    if self._live:
                        logger.warning("FrameServer: lost %s — reconnecting",
                                       self.source)
                    else:
                        logger.info("FrameServer: %s finished", self.source)
                    break

                with self._cond:
                    self._frame    = frame
                    self._frame_no += 1
                    self._cond.notify_all()   # wake ALL waiting detectors

            cap.release()

            if not self._live:
                with self._cond:
                    self._eof = True
                    self._cond.notify_all()   # unblock any remaining waiters
                return

            if self._running:
                time.sleep(_RECONNECT_DELAY_S)

        logger.info("FrameServer: stopped  source=%s", self.source)


# ---------------------------------------------------------------------------
# Registry — one FrameServer per unique source
# ---------------------------------------------------------------------------

class FrameServerRegistry:
    """Returns the same FrameServer for any source that's already registered."""

    def __init__(self):
        self._servers: dict[str, FrameServer] = {}

    def get_or_create(self, source) -> FrameServer:
        key = str(source)
        if key not in self._servers:
            self._servers[key] = FrameServer(source)
        return self._servers[key]

    def start_all(self) -> None:
        for s in self._servers.values():
            s.start()

    def stop_all(self) -> None:
        for s in self._servers.values():
            s.stop()


# ---------------------------------------------------------------------------
# Backwards-compat alias (pipeline.py imported FrameProviderRegistry)
# ---------------------------------------------------------------------------
FrameProviderRegistry = FrameServerRegistry
