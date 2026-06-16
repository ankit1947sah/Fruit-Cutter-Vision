import unittest
from state_manager import StateManager, GameState

class TestStateManager(unittest.TestCase):
    
    def test_initial_state(self):
        mgr = StateManager(initial_state=GameState.LOADING)
        self.assertEqual(mgr.current_state, GameState.LOADING)
        self.assertIsNone(mgr.previous_state)
        
    def test_transitions(self):
        mgr = StateManager(initial_state=GameState.MAIN_MENU)
        mgr.transition_to(GameState.PLAYING, context_updates={"diff": "hard"})
        
        self.assertEqual(mgr.current_state, GameState.PLAYING)
        self.assertEqual(mgr.previous_state, GameState.MAIN_MENU)
        self.assertEqual(mgr.get_context_value("diff"), "hard")
        
    def test_go_back(self):
        mgr = StateManager(initial_state=GameState.MAIN_MENU)
        mgr.transition_to(GameState.SETTINGS)
        self.assertEqual(mgr.current_state, GameState.SETTINGS)
        
        mgr.go_back()
        self.assertEqual(mgr.current_state, GameState.MAIN_MENU)
        
    def test_prevent_duplicate_transitions(self):
        mgr = StateManager(initial_state=GameState.PLAYING)
        mgr.transition_to(GameState.PLAYING) # No-op
        self.assertIsNone(mgr.previous_state)
        
if __name__ == '__main__':
    unittest.main()
