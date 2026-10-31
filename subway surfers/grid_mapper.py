"""
grid_mapper.py
--------------
Pure coordinate-mapping logic. No OpenCV, no keyboard, no I/O — this is the
"teach the concept" module: pixel coordinate -> grid cell / motion state.

Two independent mappings live here because they answer two different
questions:
  1. Horizontal: which lane is the player standing in? (LEFT/CENTER/RIGHT)
  2. Vertical: is the player jumping, ducking, or neutral, relative to a
     calibrated baseline height (not a fixed grid row, since standing
     height varies per person/camera setup).
"""


class LaneMapper:
    """Maps an x pixel coordinate to one of N equal-width columns."""

    def __init__(self, frame_width, columns=3, labels=None):
        self.frame_width = frame_width
        self.columns = columns
        self.labels = labels or [str(i) for i in range(columns)]
        self.cell_width = frame_width / columns

    def cell_for_x(self, x):
        idx = int(x // self.cell_width)
        idx = max(0, min(self.columns - 1, idx))
        return idx, self.labels[idx]

    def cell_bounds(self, idx):
        x0 = int(idx * self.cell_width)
        x1 = int((idx + 1) * self.cell_width)
        return x0, x1


class VerticalStateTracker:
    """
    Determines NEUTRAL / JUMP / DUCK relative to an auto-calibrated
    baseline y-position (the player's standing torso height).

    Image y grows downward, so:
      current_y < baseline - jump_threshold  -> JUMP (torso moved up)
      current_y > baseline + duck_threshold  -> DUCK (torso moved down)
    """

    NEUTRAL, JUMP, DUCK = "NEUTRAL", "JUMP", "DUCK"

    def __init__(self, frame_height, jump_ratio=0.12, duck_ratio=0.10,
                 auto_baseline_frames=45):
        self.frame_height = frame_height
        self.jump_px = jump_ratio * frame_height
        self.duck_px = duck_ratio * frame_height
        self.auto_baseline_frames = auto_baseline_frames
        self.baseline = None
        self._calib_buffer = []

    def calibrating(self):
        return self.baseline is None

    def feed_calibration_sample(self, y):
        self._calib_buffer.append(y)
        if len(self._calib_buffer) >= self.auto_baseline_frames:
            self.baseline = sum(self._calib_buffer) / len(self._calib_buffer)
            self._calib_buffer.clear()

    def reset_calibration(self):
        self.baseline = None
        self._calib_buffer.clear()

    def state_for_y(self, y):
        if self.baseline is None:
            return self.NEUTRAL
        if y < self.baseline - self.jump_px:
            return self.JUMP
        if y > self.baseline + self.duck_px:
            return self.DUCK
        return self.NEUTRAL
