# Motion Grid Control

Turn your webcam into a body-controlled game controller: step left/right to
change lanes, jump to jump, duck to duck — built to teach real-time
computer vision, coordinate mapping, and event-driven systems along the way.

## How it works (the concept)

```
Webcam frame
    │
    ▼
MediaPipe Pose  ──►  torso center point (x, y), smoothed
    │
    ├── x  ──► LaneMapper        ──► LEFT / CENTER / RIGHT
    └── y  ──► VerticalStateTracker ──► NEUTRAL / JUMP / DUCK
                    (relative to auto-calibrated baseline)
    │
    ▼
EventManager (edge-triggered: fires only on STATE CHANGE, with cooldown)
    │
    ▼
KeyController ──► presses the real arrow/space keys your game listens for
    │
    ▼
Overlay ──► draws grid, active lane, baseline lines, and an event log
```

The key design decision: **the grid tells you where you are, the event
manager tells you when that changed.** Every frame recomputes state, but a
key is only pressed the instant you cross from one cell into another —
that's what keeps "holding a lane" from spamming input 30 times a second.

## Project layout

| File | Responsibility |
|---|---|
| `config.yaml` | every tunable value — grid size, thresholds, key bindings |
| `pose_detector.py` | webcam frame → single (x, y) tracked point |
| `grid_mapper.py` | pixel coordinate → lane / vertical state (pure logic, no I/O) |
| `event_manager.py` | state → edge-triggered transition events + log |
| `key_controller.py` | event → real OS key press |
| `overlay.py` | drawing the grid, landmark, baseline, log on the frame |
| `main.py` | wires it all together into the live loop |

## Setup

```bash
cd motion_grid_control
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

You need a working webcam and, ideally, a few feet of open space in front
of it so your full torso is visible when you step, jump, or duck.

### Pose model download (first run only)

MediaPipe's pose tracking now goes through its newer "Tasks" API instead
of the older `mp.solutions.pose` API you may see in tutorials (that one
has been removed in current MediaPipe releases). This means pose
detection needs a small model file, which `pose_detector.py` downloads
automatically the first time you run `main.py` — you'll see "Downloading
pose model..." printed once, then never again.

If your machine has no internet access at runtime (offline lab machine,
restricted network, etc.), download it manually ahead of time and place
it next to `main.py`:

```bash
# any of lite / full / heavy — lite is fastest, heavy is most accurate
curl -o pose_landmarker_lite.task \
  https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task
```

## Running it

1. Test the tracking on its own first, with no keys sent to any game:
   ```bash
   python main.py --no-keys
   ```
   You should see the camera feed with 3 lane columns, your torso landmark
   as a red dot, and 3 horizontal calibration lines once baseline
   calibration finishes ("Calibrating baseline... stand neutrally" appears
   for the first ~1.5 seconds — stand still and centered during that time).

2. Move left/right and confirm the highlighted lane follows you. Jump and
   duck and confirm the log (top-right) prints `LANE CHANGE`, `JUMP
   triggered`, `DUCK triggered` at the right moments — and *only once* per
   jump/duck, not repeatedly while airborne or crouched.

3. Press `c` any time to force re-calibration if you moved the camera or
   your standing position drifted. Press `q` to quit.

4. Once tracking looks right, open your game (Temple Run or similar),
   click on the game window so it's focused, then run:
   ```bash
   python main.py
   ```
   Keep the tracker window open too — it's your feedback loop while
   playing, and lets you re-calibrate with `c` if needed.

## Tuning it for your setup

All in `config.yaml`, no code changes needed:

- **Game not responding to key presses** → set `keys.backend` to
  `pydirectinput` (Windows only). Many games built on DirectInput ignore
  the synthetic events pyautogui sends.
- **Jump/duck too sensitive or not sensitive enough** → adjust
  `vertical.jump_threshold_ratio` / `duck_threshold_ratio` (fraction of
  frame height). Smaller = more sensitive.
- **Jumps/ducks re-firing while you're still in the air** → increase
  `vertical.cooldown_seconds`.
- **Lane changes feel laggy or too twitchy** → adjust
  `tracking.smoothing_window` (higher = smoother but slower to react) and
  `controller.lane_cooldown_seconds`.
- **Wrong key mapped** → edit `keys.jump`, `keys.duck`, `keys.left`,
  `keys.right` directly (e.g. many endless runners use `space` for jump
  instead of `up`).

## Roadmap — from here to a solid, everyday tool

**Phase 1 — Get it working reliably for you (today)**
- Run `--no-keys` mode, confirm lane detection and jump/duck are accurate
  for your camera angle, lighting, and distance from the camera.
- Tune thresholds in `config.yaml` until false triggers are rare.

**Phase 2 — Connect it to a real game**
- Pick your game, identify its actual key bindings (some use WASD, some
  arrow keys, some space for jump).
- Update `keys:` in `config.yaml` to match.
- If key presses don't register, switch `keys.backend` to
  `pydirectinput`.

**Phase 3 — Make it robust for actual play sessions**
- Add a countdown/ready screen before calibration starts, so you're not
  scrambling to stand still.
- Add a "pause tracking" hotkey (e.g. `p`) so accidental hand movements
  near the keyboard don't trigger events between game rounds.
- Log events to a file (`events.log`) if you want to review/tune after a
  session instead of only watching the on-screen log.

**Phase 4 — Extend the grid concept**
- This teaches you the pattern generally, not just for a runner game.
  Once comfortable, try:
  - A 3×3 grid (9 cells) for a game needing diagonal moves too.
  - Hand tracking instead of torso (swap `pose_detector.py` for
    MediaPipe Hands) for gesture-based control.
  - Swap the webcam source for `mss`/`pyautogui.screenshot()` screen
    capture if you ever do want to track an object *inside* a video/game
    window rather than your own body — the `grid_mapper.py` and
    `event_manager.py` logic is identical either way, only
    `pose_detector.py`'s input source changes.

**Phase 5 (optional) — polish**
- Package as a single executable with `pyinstaller` so you don't need to
  launch it from a terminal each time.
- Add a small settings UI instead of hand-editing `config.yaml`.

## Notes on accuracy

- Good, even lighting and a camera at roughly chest height give the most
  stable torso tracking.
- Keep your full torso (both shoulders and both hips) in frame — MediaPipe
  Pose needs those four points for the tracked center.
- Re-calibrate (`c`) whenever you change position relative to the camera;
  the jump/duck thresholds are relative to *your* standing baseline, not
  absolute screen positions.
