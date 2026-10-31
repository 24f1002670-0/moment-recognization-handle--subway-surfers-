"""
overlay.py
----------
All the "make it visible" drawing code lives here, separate from tracking
logic, so you can change how things look without touching detection math.
"""

import cv2


def draw_grid(frame, lane_mapper, active_lane_idx):
    h, w = frame.shape[:2]
    overlay = frame.copy()

    # highlight the active lane
    x0, x1 = lane_mapper.cell_bounds(active_lane_idx)
    cv2.rectangle(overlay, (x0, 0), (x1, h), (0, 200, 0), -1)
    cv2.addWeighted(overlay, 0.15, frame, 0.85, 0, frame)

    # column divider lines
    for i in range(1, lane_mapper.columns):
        x = int(i * lane_mapper.cell_width)
        cv2.line(frame, (x, 0), (x, h), (80, 80, 80), 1)

    # labels
    for i, label in enumerate(lane_mapper.labels):
        x0, x1 = lane_mapper.cell_bounds(i)
        cx = (x0 + x1) // 2
        color = (0, 255, 0) if i == active_lane_idx else (150, 150, 150)
        cv2.putText(frame, label, (cx - 30, 30), cv2.FONT_HERSHEY_SIMPLEX,
                    0.7, color, 2, cv2.LINE_AA)


def draw_vertical_baseline(frame, vtracker):
    h, w = frame.shape[:2]
    if vtracker.baseline is None:
        cv2.putText(frame, "Calibrating baseline... stand neutrally",
                    (w // 2 - 220, h - 20), cv2.FONT_HERSHEY_SIMPLEX,
                    0.6, (0, 165, 255), 2, cv2.LINE_AA)
        return
    y = int(vtracker.baseline)
    cv2.line(frame, (0, y), (w, y), (255, 200, 0), 1)
    y_jump = int(vtracker.baseline - vtracker.jump_px)
    y_duck = int(vtracker.baseline + vtracker.duck_px)
    cv2.line(frame, (0, y_jump), (w, y_jump), (0, 255, 255), 1)
    cv2.line(frame, (0, y_duck), (w, y_duck), (0, 128, 255), 1)


def draw_landmark(frame, point_px):
    if point_px is None:
        return
    x, y = int(point_px[0]), int(point_px[1])
    cv2.circle(frame, (x, y), 8, (0, 0, 255), -1)


def draw_status(frame, lane_label, vstate, fps):
    cv2.putText(frame, f"Lane: {lane_label}  Vertical: {vstate}  FPS: {fps:.0f}",
                (10, frame.shape[0] - 45), cv2.FONT_HERSHEY_SIMPLEX,
                0.55, (255, 255, 255), 1, cv2.LINE_AA)


def draw_log(frame, log_lines):
    h, w = frame.shape[:2]
    y = 55
    for line in log_lines[-6:]:
        cv2.putText(frame, line, (w - 340, y), cv2.FONT_HERSHEY_SIMPLEX,
                    0.42, (200, 200, 200), 1, cv2.LINE_AA)
        y += 18
