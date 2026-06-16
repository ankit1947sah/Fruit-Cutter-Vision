import unittest
import config
from score_system import ScoreSystem

class TestScoreSystem(unittest.TestCase):
    
    def setUp(self):
        self.score_sys = ScoreSystem()
        self.score_sys.reset()
        
    def test_initial_state(self):
        self.assertEqual(self.score_sys.score, 0)
        self.assertEqual(self.score_sys.lives, config.MAX_LIVES)
        self.assertEqual(self.score_sys.fruits_sliced, 0)
        self.assertEqual(self.score_sys.bombs_hit, 0)
        
    def test_single_fruit_slice(self):
        alive = self.score_sys.register_slice("apple")
        self.assertTrue(alive)
        self.assertEqual(self.score_sys.score, 1)
        self.assertEqual(self.score_sys.fruits_sliced, 1)
        
    def test_missed_fruit(self):
        alive = self.score_sys.register_miss()
        self.assertTrue(alive)
        self.assertEqual(self.score_sys.lives, config.MAX_LIVES - 1)
        
    def test_bomb_hit(self):
        # Give some initial score
        self.score_sys.score = 25
        alive = self.score_sys.register_slice("bomb")
        self.assertTrue(alive)
        self.assertEqual(self.score_sys.lives, config.MAX_LIVES - 1)
        self.assertEqual(self.score_sys.score, 15) # -10 points
        self.assertEqual(self.score_sys.bombs_hit, 1)
        
    def test_lives_exhaustion(self):
        # Lose 3 lives
        self.score_sys.register_miss()
        self.score_sys.register_miss()
        still_alive = self.score_sys.register_miss()
        self.assertFalse(still_alive)
        self.assertEqual(self.score_sys.lives, 0)
        
    def test_combo_accumulation(self):
        # Slice 3 fruits in the same combo window
        # Slice 1: starts the timer (config.COMBO_TIME_WINDOW = 0.4s)
        self.score_sys.register_slice("watermelon")
        self.assertEqual(self.score_sys.score, 1)
        self.assertTrue(self.score_sys.combo_timer > 0.0)
        
        # Slice 2
        self.score_sys.register_slice("apple")
        self.assertEqual(self.score_sys.score, 2)
        
        # Slice 3
        self.score_sys.register_slice("orange")
        self.assertEqual(self.score_sys.score, 3)
        
        # Let's advance time by 0.5s to trigger the combo
        self.score_sys.update(0.5)
        
        # Combo timer should have run out and checked the combo
        self.assertEqual(self.score_sys.combo_timer, 0.0)
        # 3 fruits combo should give 3 bonus points
        # Total score = 3 (base) + 3 (bonus) = 6 points
        self.assertEqual(self.score_sys.score, 6)
        self.assertEqual(self.score_sys.combos_sliced, 1)
        
        # Retrieve pending combo trigger
        trigger = self.score_sys.consume_combo_trigger()
        self.assertIsNotNone(trigger)
        self.assertEqual(trigger["count"], 3)
        self.assertEqual(trigger["bonus"], 3)
        
    def test_no_combo_if_only_two_fruits(self):
        self.score_sys.register_slice("watermelon")
        self.score_sys.register_slice("apple")
        self.score_sys.update(0.5)
        # 2 fruits do not make a combo (requires >= 3)
        # Score remains 2 points
        self.assertEqual(self.score_sys.score, 2)
        self.assertEqual(self.score_sys.combos_sliced, 0)
        self.assertIsNone(self.score_sys.consume_combo_trigger())
        
if __name__ == '__main__':
    unittest.main()
