"""
main.py
-------
Run this file. It opens your webcam, tracks your body position, maps it
to a LEFT/CENTER/RIGHT grid + JUMP/DUCK vertical state, fires key presses
on transitions only, and draws a live overlay so you can see exactly what
the system is doing.

Usage:
    python main.py [--config config.yaml] [--no-keys]

Controls while running:
    q            quit
    c            force baseline re-calibration (stand still for a moment)
"""

import argparse
import time
import cv2
import yaml

from pose_detector import PoseDetector
from grid_mapper import LaneMapper, VerticalStateTracker
from event_manager import EventManager
from key_controller import KeyController
import overlay as ov


def load_config(path):
    with open(path, "r") as f:
        return yaml.safe_load(f)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--no-keys", action="store_true",
                         help="Disable key presses; overlay-only test mode.")
    args = parser.parse_args()

    cfg = load_config(args.config)

    cam_cfg = cfg["camera"]
    cap = cv2.VideoCapture(cam_cfg["index"])
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, cam_cfg["width"])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cam_cfg["height"])

    if not cap.isOpened():
        raise RuntimeError(
            f"Could not open camera index {cam_cfg['index']}. "
            "Try a different index in config.yaml (0, 1, 2...)."
        )

    detector = PoseDetector(
        min_detection_confidence=cfg["tracking"]["min_detection_confidence"],
        min_tracking_confidence=cfg["tracking"]["min_tracking_confidence"],
        smoothing_window=cfg["tracking"]["smoothing_window"],
    )

    lane_mapper = None       # built once we know actual frame size
    vtracker = None

    events = EventManager(
        lane_cooldown=cfg["controller"]["lane_cooldown_seconds"],
        vertical_cooldown=cfg["vertical"]["cooldown_seconds"],
        log_max_lines=cfg["overlay"]["log_max_lines"],
    )

    controller = KeyController(
        key_map=cfg["keys"],
        backend=cfg["keys"]["backend"],
        enabled=cfg["controller"]["enabled"] and not args.no_keys,
        press_seconds=cfg["controller"]["key_press_seconds"],
        between_steps_seconds=cfg["controller"].get("between_step_seconds", 0.12),
    )

    win_name = cfg["overlay"]["window_name"]
    prev_t = time.time()
    fps = 0.0

    print("Starting. Stand in a neutral pose for baseline calibration...")

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("Frame grab failed, stopping.")
                break

            if cam_cfg.get("mirror", True):
                frame = cv2.flip(frame, 1)

            h, w = frame.shape[:2]
            if lane_mapper is None:
                lane_mapper = LaneMapper(w, cfg["grid"]["columns"], cfg["grid"]["labels"])
                vtracker = VerticalStateTracker(
                    h,
                    jump_ratio=cfg["vertical"]["jump_threshold_ratio"],
                    duck_ratio=cfg["vertical"]["duck_threshold_ratio"],
                    auto_baseline_frames=cfg["vertical"]["auto_baseline_frames"],
                )

            point, landmarks = detector.process(frame)

            lane_idx, lane_label = (1, lane_mapper.labels[1] if lane_mapper.columns > 1 else "CENTER")
            vstate = "NEUTRAL"

            if point is not None:
                if landmarks is not None:
                    detector.draw_landmarks(frame, landmarks)

                x, y = point
                lane_idx, lane_label = lane_mapper.cell_for_x(x)

                if vtracker.calibrating():
                    vtracker.feed_calibration_sample(y)
                else:
                    vstate = vtracker.state_for_y(y)

                # --- fire events on transitions only ---
                lane_event = events.update_lane(lane_idx, lane_label)
                if lane_event:
                    controller.fire_steps(lane_event["direction"], lane_event["steps"])

                vertical_event = events.update_vertical(vstate)
                if vertical_event:
                    controller.fire(vertical_event.lower())

            # --- overlay ---
            if cfg["overlay"]["show_grid"]:
                ov.draw_grid(frame, lane_mapper, lane_idx)
            if vtracker is not None:
                ov.draw_vertical_baseline(frame, vtracker)
            if cfg["overlay"]["show_landmark"]:
                ov.draw_landmark(frame, point)
            if cfg["overlay"]["show_log"]:
                ov.draw_log(frame, events.log)

            now = time.time()
            fps = 0.9 * fps + 0.1 * (1.0 / max(1e-6, now - prev_t))
            prev_t = now
            ov.draw_status(frame, lane_label, vstate, fps)

            cv2.imshow(win_name, frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            if key == ord(cfg["vertical"]["recalibrate_key"]):
                vtracker.reset_calibration()
                print("Re-calibrating baseline...")

    finally:
        cap.release()
        cv2.destroyAllWindows()
        detector.close()


if __name__ == "__main__":
    main()