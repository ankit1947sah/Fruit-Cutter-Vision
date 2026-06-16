import unittest
import config
from collision import check_line_circle_intersection, calculate_slice_details

class TestCollision(unittest.TestCase):
    
    def test_line_circle_intersection_hit(self):
        # Circle at (100, 100), radius 20
        # Segment from (50, 100) to (150, 100) -> cuts straight through center
        center = (100.0, 100.0)
        radius = 20.0
        p1 = (50.0, 100.0)
        p2 = (150.0, 100.0)
        
        intersects, t, closest_pt = check_line_circle_intersection(p1, p2, center, radius)
        self.assertTrue(intersects)
        self.assertAlmostEqual(t, 0.5) # closest point is exactly halfway
        self.assertEqual(closest_pt, (100.0, 100.0))
        
    def test_line_circle_intersection_tangent(self):
        # Circle at (100, 100), radius 20
        # Segment from (50, 80) to (150, 80) -> touches top edge of circle
        center = (100.0, 100.0)
        radius = 20.0
        p1 = (50.0, 80.0)
        p2 = (150.0, 80.0)
        
        intersects, t, closest_pt = check_line_circle_intersection(p1, p2, center, radius)
        self.assertTrue(intersects)
        self.assertAlmostEqual(t, 0.5)
        self.assertEqual(closest_pt, (100.0, 80.0))
        
    def test_line_circle_intersection_miss(self):
        # Segment from (50, 70) to (150, 70) -> misses circle
        center = (100.0, 100.0)
        radius = 20.0
        p1 = (50.0, 70.0)
        p2 = (150.0, 70.0)
        
        intersects, t, closest_pt = check_line_circle_intersection(p1, p2, center, radius)
        self.assertFalse(intersects)
        
    def test_slice_speed_threshold(self):
        # Segment cutting through, but speed too low
        # Speed threshold is config.MIN_SLICE_SPEED = 250 px/sec
        # Stroke of length 10 over dt = 1.0 sec -> speed = 10 px/sec (too slow)
        center = (100.0, 100.0)
        radius = 20.0
        p1 = (95.0, 100.0)
        p2 = (105.0, 100.0)
        dt = 1.0 # 1 second
        
        details = calculate_slice_details(p1, p2, center, radius, dt)
        self.assertIsNone(details) # Speed is too slow, should return None
        
        # Stroke of length 100 over dt = 0.1 sec -> speed = 1000 px/sec (valid)
        p1 = (50.0, 100.0)
        p2 = (150.0, 100.0)
        dt = 0.1
        details = calculate_slice_details(p1, p2, center, radius, dt)
        self.assertIsNotNone(details)
        
        # Check slice direction: moving right -> angle should be 0 radians
        self.assertAlmostEqual(details["angle"], 0.0)
        # Push vector 1 should be straight up (0 - pi/2 = -pi/2), push vector 2 straight down
        pv1 = details["push_vector_1"]
        pv2 = details["push_vector_2"]
        self.assertAlmostEqual(pv1[0], 0.0) # no x push
        self.assertTrue(pv1[1] < 0.0)      # negative y push (upward)
        self.assertAlmostEqual(pv2[0], 0.0) # no x push
        self.assertTrue(pv2[1] > 0.0)      # positive y push (downward)
        
if __name__ == '__main__':
    unittest.main()
