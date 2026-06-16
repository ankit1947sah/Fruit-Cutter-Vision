import unittest
import queue
import time
import numpy as np
import config
from hand_tracker import OneEuroFilter, HandTracker
from collision import calculate_slice_details


class MockCamera:
    """Mock Camera class that returns dummy frames."""
    def __init__(self):
        self.latest_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        self.fps = 30.0

    def get_frame(self):
        return self.latest_frame.copy()


class TestHandTracking(unittest.TestCase):

    def test_one_euro_filter_smoothing(self):
        """Verifies that One Euro Filter stabilizes values and reduces variance."""
        t0 = time.perf_counter()
        # Create a filter starting at 100.0
        filt = OneEuroFilter(t0=t0, x0=100.0, mincutoff=1.0, beta=0.007)
        
        # Sequentially feed coordinates with minor high-frequency jitter
        t = t0
        raw_values = [100.0, 102.0, 98.0, 101.0, 99.0, 100.0]
        smoothed_values = []
        
        for val in raw_values:
            t += 0.033 # ~30 FPS frame rate interval
            smoothed_values.append(filt(t, val))
            
        # The first output should be smoothed (less extreme than the raw values)
        # Verify that all outputs are numerical floats and stay relatively stable
        for val in smoothed_values:
            self.assertIsInstance(val, float)
            # The filter output should stay in a tighter bounding box than raw values [98, 102]
            self.assertTrue(98.5 <= val <= 101.5)

    def test_hand_tracker_queue_communication(self):
        """Verifies coordinates queue has correct capacity and drops old frames."""
        camera = MockCamera()
        tracker = HandTracker(camera, screen_width=1280, screen_height=720)
        
        # Initially, the queue should be empty
        self.assertTrue(tracker.coord_queue.empty())
        
        # Put dummy events onto the queue
        for i in range(15):
            try:
                if tracker.coord_queue.full():
                    tracker.coord_queue.get_nowait()
                tracker.coord_queue.put_nowait((100.0 + i, 200.0 + i, True, False, time.perf_counter()))
            except Exception:
                pass
                
        # Queue should contain exactly 10 items (maximum capacity)
        self.assertEqual(tracker.coord_queue.qsize(), 10)
        
        # Read the first item from the queue - it should be the 6th item placed (i=5)
        # because the first 5 items were dropped due to capacity overflow
        x, y, detected, pinching, ts = tracker.coord_queue.get()
        self.assertEqual(x, 105.0)
        self.assertEqual(y, 205.0)
        self.assertTrue(detected)

    def test_slice_speed_velocity_thresholds(self):
        """Verifies that slice triggers ONLY when velocity exceeds configuration limits."""
        # Config threshold is MIN_SLICE_SPEED = 250 px/sec
        p_start = (100.0, 100.0)
        
        # Slow movement: 20 pixels in 0.2 seconds -> speed = 100 px/sec (below threshold)
        p_slow = (120.0, 100.0)
        dt_slow = 0.2
        details_slow = calculate_slice_details(p_start, p_slow, center=(110.0, 100.0), radius=20, dt=dt_slow)
        self.assertIsNone(details_slow)
        
        # Fast movement: 100 pixels in 0.05 seconds -> speed = 2000 px/sec (above threshold)
        p_fast = (200.0, 100.0)
        dt_fast = 0.05
        details_fast = calculate_slice_details(p_start, p_fast, center=(150.0, 100.0), radius=20, dt=dt_fast)
        self.assertIsNotNone(details_fast)
        self.assertEqual(details_fast["angle"], 0.0)
        self.assertTrue(details_fast["speed"] >= 2000.0)


if __name__ == '__main__':
    unittest.main()
