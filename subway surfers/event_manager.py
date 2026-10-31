"""
event_manager.py
-----------------
This is the piece that makes the system "event-driven" instead of
"continuous". Grid/vertical state is recomputed every frame, but a key
should only be pressed the moment the state CHANGES (an edge), not on
every frame the player happens to be in that state. Without this,
holding a lane would spam the "left" key 30 times a second.

Two independent state machines:
  - LaneEvents:     LEFT <-> CENTER <-> RIGHT transitions, debounced.
  - VerticalEvents: NEUTRAL -> JUMP / NEUTRAL -> DUCK, edge-triggered
                     with a cooldown so a single jump doesn't refire
                     while you're still in the air.
"""

import time


class EventManager:
    def __init__(self, lane_cooldown=0.25, vertical_cooldown=0.5, log_max_lines=6):
        self.lane_cooldown = lane_cooldown
        self.vertical_cooldown = vertical_cooldown
        self.log_max_lines = log_max_lines

        self._current_lane = None
        self._last_lane_event_t = 0.0

        self._current_vstate = "NEUTRAL"
        self._last_vertical_event_t = 0.0

        self.log = []

    def _push_log(self, text):
        ts = time.strftime("%H:%M:%S")
        self.log.append(f"[{ts}] {text}")
        if len(self.log) > self.log_max_lines:
            self.log.pop(0)

    def update_lane(self, lane_idx, lane_label):
        """
        Returns None, or a dict {"direction": "left"|"right", "steps": n}
        describing how many lane-shift key presses are needed to move the
        in-game character from the OLD lane to the NEW lane.

        This fires on every real lane change, including a return to
        CENTER — because in a relative-shift game (most runners), "return
        to center" IS a left/right press, not a separate action. If you
        skip a lane entirely (LEFT -> RIGHT in one frame), steps=2, so the
        game's lane position stays in sync with your physical position.
        """
        now = time.time()
        if self._current_lane is None:
            # first detection: just record it, no key press (nothing to shift from)
            self._current_lane = lane_idx
            return None
        if lane_idx == self._current_lane:
            return None
        if now - self._last_lane_event_t < self.lane_cooldown:
            return None

        delta = lane_idx - self._current_lane   # e.g. LEFT(0)->RIGHT(2) => +2
        direction = "right" if delta > 0 else "left"
        steps = abs(delta)

        self._current_lane = lane_idx
        self._last_lane_event_t = now
        self._push_log(f"LANE CHANGE -> {lane_label} ({direction} x{steps})")
        return {"direction": direction, "steps": steps}

    def update_vertical(self, vstate):
        """Returns 'JUMP' or 'DUCK' the instant we enter that state, else None."""
        now = time.time()
        if vstate == self._current_vstate:
            return None
        if vstate in ("JUMP", "DUCK") and now - self._last_vertical_event_t < self.vertical_cooldown:
            # still update current state so we don't refire on the way back down
            self._current_vstate = vstate
            return None

        prev = self._current_vstate
        self._current_vstate = vstate
        if vstate in ("JUMP", "DUCK"):
            self._last_vertical_event_t = now
            self._push_log(f"{vstate} triggered")
            return vstate
        return None