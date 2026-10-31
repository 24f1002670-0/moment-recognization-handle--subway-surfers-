"""
pose_detector.py
----------------
Wraps MediaPipe's PoseLandmarker (the current "Tasks" API) so the rest of
the app only deals with a single (x, y) tracked point per frame instead
of 33 raw landmarks.

IMPORTANT — API note: older MediaPipe tutorials use `mp.solutions.pose`.
That legacy API has been removed in current MediaPipe releases (it's gone
even in the latest PyPI package, and fully gone in the 1.0 line). Pose
detection now goes through `mediapipe.tasks`, which requires a
separately-downloaded `.task` model file — `ensure_model()` below
downloads it automatically on first run (needs internet once).

Why torso center instead of a hand or the nose?
- Nose/head is easy to knock out of frame when you duck.
- A single hand is easy to lose (occlusion, fast motion).
- The average of both shoulders + both hips is stable through jumps,
  ducks, and side steps, which is exactly what a "player position"
  detector needs.
"""

import os
import time
import collections
import urllib.request

import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision

# Standard BlazePose landmark indices — these indices are stable across
# API versions, only how you access the model changed.
LEFT_SHOULDER, RIGHT_SHOULDER = 11, 12
LEFT_HIP, RIGHT_HIP = 23, 24

# "lite" variant: smallest/fastest, plenty accurate for lane/jump/duck
# tracking. Swap to pose_landmarker_full or _heavy for higher accuracy
# at the cost of speed.
MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
    "pose_landmarker_lite/float16/1/pose_landmarker_lite.task"
)
MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "pose_landmarker_lite.task")


def ensure_model():
    """Downloads the pose landmark model once (~5-9MB), on first run only."""
    if not os.path.exists(MODEL_PATH):
        print(f"Downloading pose model to {MODEL_PATH} (one-time)...")
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
        print("Model downloaded.")
    return MODEL_PATH


class PoseDetector:
    def __init__(self, min_detection_confidence=0.6, min_tracking_confidence=0.6,
                 smoothing_window=5, model_path=None):
        model_path = model_path or ensure_model()

        base_options = mp_python.BaseOptions(model_asset_path=model_path)
        options = mp_vision.PoseLandmarkerOptions(
            base_options=base_options,
            running_mode=mp_vision.RunningMode.VIDEO,
            num_poses=1,
            min_pose_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )
        self._landmarker = mp_vision.PoseLandmarker.create_from_options(options)

        # rolling buffer for a simple moving-average smoother
        self._buffer = collections.deque(maxlen=max(1, smoothing_window))

        # VIDEO mode requires strictly increasing timestamps per frame
        self._start_time = time.time()
        self._last_timestamp_ms = -1

    def _next_timestamp_ms(self):
        ts = int((time.time() - self._start_time) * 1000)
        if ts <= self._last_timestamp_ms:
            ts = self._last_timestamp_ms + 1
        self._last_timestamp_ms = ts
        return ts

    def process(self, frame_bgr):
        """
        Returns (point_px, landmarks_or_none)
        point_px: (x, y) in pixel coordinates, smoothed. None if no person found.
        landmarks_or_none: list of 33 landmark points (x,y normalized 0-1),
                            usable directly with draw_landmarks().
        """
        import cv2
        h, w = frame_bgr.shape[:2]
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

        result = self._landmarker.detect_for_video(mp_image, self._next_timestamp_ms())

        if not result.pose_landmarks:
            return None, None

        lm = result.pose_landmarks[0]  # first/only detected person

        def pt(idx):
            p = lm[idx]
            return p.x * w, p.y * h

        ls, rs = pt(LEFT_SHOULDER), pt(RIGHT_SHOULDER)
        lh, rh = pt(LEFT_HIP), pt(RIGHT_HIP)

        cx = (ls[0] + rs[0] + lh[0] + rh[0]) / 4.0
        cy = (ls[1] + rs[1] + lh[1] + rh[1]) / 4.0

        self._buffer.append((cx, cy))
        avg_x = sum(p[0] for p in self._buffer) / len(self._buffer)
        avg_y = sum(p[1] for p in self._buffer) / len(self._buffer)

        return (avg_x, avg_y), lm

    def draw_landmarks(self, frame_bgr, landmarks):
        """landmarks: the list returned as the second value of process()."""
        import cv2
        h, w = frame_bgr.shape[:2]
        for p in landmarks:
            x, y = int(p.x * w), int(p.y * h)
            cv2.circle(frame_bgr, (x, y), 2, (0, 255, 0), -1)

    def close(self):
        self._landmarker.close()
