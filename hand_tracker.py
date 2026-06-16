import cv2
import numpy as np
import threading
import time
import os
import queue
from logger import log
import config

# New MediaPipe Tasks Vision API (replaces deprecated mp.solutions.hands)
try:
    import mediapipe as mp
    from mediapipe.tasks.python import BaseOptions
    from mediapipe.tasks.python.vision import (
        HandLandmarker,
        HandLandmarkerOptions,
        RunningMode,
    )
    _MP_AVAILABLE = True
except Exception as e:
    _MP_AVAILABLE = False
    log.error(
        "MediaPipe failed to load (%s). Hand tracking will be unavailable; falling back to mouse input.", e
    )

# Landmark indices (same across old and new API)
_INDEX_FINGER_TIP = 8
_THUMB_TIP = 4

# Default model path relative to project root
_MODEL_FILENAME = "hand_landmarker.task"


class OneEuroFilter:
    """First-order low-pass filter with an adaptive cutoff frequency for jitter reduction."""
    
    def __init__(self, t0, x0, dx0=0.0, mincutoff=1.0, beta=0.0, dcutoff=1.0):
        self.mincutoff = float(mincutoff)
        self.beta = float(beta)
        self.dcutoff = float(dcutoff)
        self.x_prev = float(x0)
        self.dx_prev = float(dx0)
        self.t_prev = float(t0)
        
    def __call__(self, t, x):
        t_e = t - self.t_prev
        if t_e <= 0:
            return self.x_prev
            
        # Filter the derivative to get velocity
        a_d = self._alpha(t_e, self.dcutoff)
        dx = (x - self.x_prev) / t_e
        dx_hat = a_d * dx + (1.0 - a_d) * self.dx_prev
        
        # Cutoff frequency changes with velocity (dynamic tracking)
        cutoff = self.mincutoff + self.beta * abs(dx_hat)
        a = self._alpha(t_e, cutoff)
        x_hat = a * x + (1.0 - a) * self.x_prev
        
        # Store values for next call
        self.x_prev = x_hat
        self.dx_prev = dx_hat
        self.t_prev = t
        
        return x_hat
        
    def _alpha(self, t_e, cutoff):
        r = 2 * np.pi * cutoff * t_e
        return r / (r + 1.0)


class HandTracker:
    """Processes webcam frames using MediaPipe HandLandmarker (Tasks API) in a background thread."""

    def __init__(self, camera, screen_width=config.WIDTH, screen_height=config.HEIGHT):
        self.camera = camera
        self.screen_width = screen_width
        self.screen_height = screen_height

        self.lock = threading.Lock()
        self.running = False
        self.thread = None

        # Thread-safe output states
        self.finger_x = None
        self.finger_y = None
        self.is_pinching = False
        self.hand_detected = False
        self.latest_landmarks = None  # Holds the full 21 normalized landmarks list

        # Thread-safe event queue for coordinates
        self.coord_queue = queue.Queue(maxsize=10)

        # One Euro Filters for x and y
        self.filter_x = None
        self.filter_y = None

        # Legacy smoothing backup variables
        self.raw_x = None
        self.raw_y = None
        self.smooth_alpha = config.COORD_SMOOTHING

    def start(self):
        """Starts the tracking thread."""
        if not _MP_AVAILABLE:
            log.warning("Cannot start HandTracker thread: MediaPipe is missing.")
            return

        # Check that model file exists
        model_path = self._resolve_model_path()
        if model_path is None:
            log.error(
                "HandLandmarker model file '%s' not found. "
                "Download it from https://storage.googleapis.com/mediapipe-models/"
                "hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task "
                "and place it in the project root.",
                _MODEL_FILENAME,
            )
            return

        if self.running:
            log.warning("HandTracker thread is already running.")
            return

        self.running = True
        self.thread = threading.Thread(
            target=self._tracking_loop,
            args=(model_path,),
            name="TrackerThread",
            daemon=True,
        )
        self.thread.start()
        log.info("HandTracker thread started.")

    @staticmethod
    def _resolve_model_path():
        """Locate the hand_landmarker.task model file."""
        # Check project root (working directory)
        if os.path.isfile(_MODEL_FILENAME):
            return os.path.abspath(_MODEL_FILENAME)
        # Check next to this source file
        here = os.path.dirname(os.path.abspath(__file__))
        alt = os.path.join(here, _MODEL_FILENAME)
        if os.path.isfile(alt):
            return alt
        return None

    def _tracking_loop(self, model_path):
        """Background loop running hand tracking updates using the Tasks API."""
        landmarker = None
        try:
            # Build HandLandmarker with VIDEO running mode
            # Note: Parameter name is min_tracking_confidence (NOT min_hand_tracking_confidence)
            options = HandLandmarkerOptions(
                base_options=BaseOptions(model_asset_path=model_path),
                running_mode=RunningMode.VIDEO,
                num_hands=1,
                min_hand_detection_confidence=config.DETECTION_CONFIDENCE,
                min_tracking_confidence=config.TRACKING_CONFIDENCE,
            )
            landmarker = HandLandmarker.create_from_options(options)
            log.info("MediaPipe HandLandmarker (Tasks API) initialized successfully.")

            frame_timestamp_ms = 0
            last_timestamp = time.perf_counter()

            while self.running:
                # Get the latest frame from the camera
                frame = self.camera.get_frame()
                if frame is None:
                    time.sleep(0.005)  # Wait for camera to produce a frame
                    continue

                # Convert BGR frame to RGB for MediaPipe
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                # Wrap as MediaPipe Image
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)

                # Advance timestamp monotonically (milliseconds)
                now_time = time.perf_counter()
                time_delta_ms = int((now_time - last_timestamp) * 1000.0)
                if time_delta_ms <= 0:
                    time_delta_ms = 1
                frame_timestamp_ms += time_delta_ms
                last_timestamp = now_time

                # Detect hand landmarks
                result = landmarker.detect_for_video(mp_image, frame_timestamp_ms)

                if result.hand_landmarks and len(result.hand_landmarks) > 0:
                    hand = result.hand_landmarks[0]

                    # Index finger tip (landmark 8)
                    index_tip = hand[_INDEX_FINGER_TIP]
                    # Thumb tip (landmark 4)
                    thumb_tip = hand[_THUMB_TIP]

                    # Safe-zone boundary padding (15% padding on each side)
                    # Maps [0.15, 0.85] range of camera to [0.0, 1.0] of screen
                    padding = 0.15
                    scale = 1.0 - 2.0 * padding
                    
                    x_mapped = (index_tip.x - padding) / scale
                    x_mapped = max(0.0, min(1.0, x_mapped))
                    raw_x = x_mapped * self.screen_width
                    
                    y_mapped = (index_tip.y - padding) / scale
                    y_mapped = max(0.0, min(1.0, y_mapped))
                    raw_y = y_mapped * self.screen_height

                    # Calculate pinch distance (normalised 2D Euclidean distance)
                    dx = index_tip.x - thumb_tip.x
                    dy = index_tip.y - thumb_tip.y
                    pinch_dist = np.sqrt(dx * dx + dy * dy)
                    is_pinching = pinch_dist < config.PINCH_THRESHOLD

                    # Apply One Euro Filter to reduce jitter and maintain low latency
                    now_ts = time.perf_counter()
                    if self.filter_x is None or self.filter_y is None:
                        self.filter_x = OneEuroFilter(now_ts, raw_x, mincutoff=1.0, beta=0.007)
                        self.filter_y = OneEuroFilter(now_ts, raw_y, mincutoff=1.0, beta=0.007)
                        smooth_x = raw_x
                        smooth_y = raw_y
                    else:
                        smooth_x = self.filter_x(now_ts, raw_x)
                        smooth_y = self.filter_y(now_ts, raw_y)

                    with self.lock:
                        self.raw_x = raw_x
                        self.raw_y = raw_y
                        self.finger_x = smooth_x
                        self.finger_y = smooth_y
                        self.is_pinching = is_pinching
                        self.hand_detected = True
                        self.latest_landmarks = hand

                    # Push coordinate update to thread-safe queue
                    try:
                        if self.coord_queue.full():
                            self.coord_queue.get_nowait()  # Drop oldest to prevent latency buildup
                        self.coord_queue.put_nowait((smooth_x, smooth_y, True, is_pinching, now_ts))
                    except Exception:
                        pass
                else:
                    with self.lock:
                        self.hand_detected = False
                        self.latest_landmarks = None

                    # Push "no hand" event to the queue
                    try:
                        if self.coord_queue.full():
                            self.coord_queue.get_nowait()
                        self.coord_queue.put_nowait((None, None, False, False, time.perf_counter()))
                    except Exception:
                        pass

                # Yield thread execution time
                time.sleep(0.002)

        except Exception as e:
            log.exception("Exception in HandTracker thread: %s", e)
            with self.lock:
                self.hand_detected = False
        finally:
            if landmarker:
                landmarker.close()
                log.info("MediaPipe HandLandmarker resource closed.")

    def get_pointer(self):
        """Thread-safe acquisition of the current tracked pointer.

        Returns:
            tuple: (x, y, hand_detected, is_pinching)
        """
        with self.lock:
            return self.finger_x, self.finger_y, self.hand_detected, self.is_pinching

    def get_landmarks(self):
        """Thread-safe acquisition of the latest hand landmarks.

        Returns:
            list: List of 21 NormalizedLandmark objects, or None
        """
        with self.lock:
            return self.latest_landmarks

    def stop(self):
        """Stops the hand tracker thread."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
            log.info("HandTracker thread stopped.")
