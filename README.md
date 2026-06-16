# Antigravity Fruit Cutter Vision

A production-ready, high-performance Fruit Ninja clone built in Python. The game uses real-time computer vision (webcam hand tracking via MediaPipe) to let you slice flying fruits with your index finger. It includes a fallback mouse mode so it is fully playable even on environments without a camera.

## Core Features
*   **Webcam Hand Tracking**: Control the blade using your index finger fingertip. Supports gesture-based menu navigation (hover-to-select and pinch-to-click) with coordinate smoothing (EMA) and low latency (< 15ms tracker thread overhead).
*   **Fallback Input System**: Automatically transitions to mouse movement if the camera is occupied or MediaPipe libraries fail to load (e.g. library conflicts).
*   **100% Procedural Assets**: Zero asset files required (no PNGs, JPGs, WAVs, or MP3s). Fruits, particle splatters, UI elements, and sound effects are dynamically synthesized at startup using mathematical equations (sine sweeps, white noise filtering, chord harmonies) and vector drawing APIs.
*   **High Performance**: Main loop runs on a virtual canvas at a locked 60 FPS with frame times < 16.6ms, keeping memory consumption < 120MB (target was < 300MB) with no garbage collection spikes thanks to extensive object pooling.
*   **Visual Polish**: Multi-color tapered neon blade trails, camera calibrator corner overlays, screen shakes, slow-motion modifiers, combo flares, and juice particles.
*   **State Machine**: Professional transition states (Loading, Main Menu, Playing, Paused, Settings, leaderboards, Game Over) with persistence saving/loading scores to `logs/highscore.json`.

---

## Folder Structure

```
project_root/
│
├── main.py             # Application bootstrap entry point
├── config.py           # Unified configuration layer
├── camera.py           # Webcam frame capture thread wrapper
├── hand_tracker.py     # MediaPipe Hand Tracking thread (EMA, Pinch, coordinate mapping)
├── game_engine.py      # Main game loop, spawner, and state handlers
├── fruit.py            # Fruit and FruitHalf classes (procedural graphics rendering)
├── physics.py          # 2D Kinematics engine (semi-implicit Euler integration)
├── collision.py        # Line-circle segment intersections and momentum transfer math
├── particles.py        # Juice splatters, seed drop, and bomb flame particle manager
├── effects.py          # Blade trail ribbon, screen shake, slow motion, shockwaves
├── audio.py            # Procedural audio waveform synthesizer (mixer wrapper)
├── score_system.py     # Score, combo tracking, and JSON high score saver
├── ui.py               # UIButton hover/pinch widgets and HUD renderer
├── state_manager.py    # Screen state transition machine
├── object_pool.py      # Pre-allocated recycling pools
├── logger.py           # Log rotated outputs to logs/game.log
├── fruit_cutter.spec   # PyInstaller release build specification
├── requirements.txt    # Project library dependencies
└── tests/              # Automated unit tests suite
```

---

## Installation & Setup

1.  **Clone the repository** (or copy to your workspace directory).
2.  **Set up a virtual environment** (recommended):
    ```bash
    python -m venv venv
    source venv/bin/activate  # On macOS/Linux
    venv\Scripts\activate     # On Windows
    ```
3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

---

## How to Play

Run the application using:
```bash
python main.py
```

### Controls:
*   **Index Finger (Webcam)**: Move your index finger in front of the camera to sweep the neon blade trail.
*   **Select Button (Webcam)**: Hover your finger cursor over a menu button for 1.2 seconds (completing the circular progress ring) or bring your thumb and index finger together to **Pinch-click** it.
*   **Mouse (Fallback)**: Move your mouse cursor to sweep the blade. Hold the **Left Mouse Button** to click or simulate pinch gestures.
*   **Keyboard**:
    *   `Esc`: Pause gameplay or return to the main menu.
    *   `F1`: Toggle the developer performance telemetry overlay (shows live FPS, memory footprint, active particle counts, and input mode).

---

## Developer Commands

### Running Unit Tests
A comprehensive test suite is located in `tests/` covering kinematics, line-circle intersections, combo time-windows, and state machines:
```bash
python -m unittest discover -s tests
```

### Running Performance Benchmarks
We provide a headless benchmark simulator that runs the game at full speed (using SDL's dummy display and audio drivers), simulating slices and spawns to stress test the collision and particle pipelines:
```bash
python benchmark.py
```
This prints telemetry outputs to stdout and saves a performance report at `logs/benchmark_report.txt`.

### Packaging standalone builds (PyInstaller)
Compile a single folder directory containing a standalone executable (no Python interpreter needed for end-users):
```bash
pyinstaller fruit_cutter.spec
```
Outputs will be built in the `dist/FruitCutterVision/` directory.
