from logger import log
from audio import synth

class GameState:
    """Enumeration of all supported application screens and game loops."""
    LOADING = "LOADING"
    MAIN_MENU = "MAIN_MENU"
    PLAYING = "PLAYING"
    PAUSED = "PAUSED"
    SETTINGS = "SETTINGS"
    HIGH_SCORES = "HIGH_SCORES"
    GAME_OVER = "GAME_OVER"

class StateManager:
    """Manages the current active screen state, transitions, and shared state context."""
    
    def __init__(self, initial_state=GameState.LOADING):
        self.current_state = initial_state
        self.previous_state = None
        self.context = {} # Shared dictionary to pass details (e.g. final scores) between states
        
        log.info("StateManager initialized. Starting state: %s", self.current_state)
        
    def transition_to(self, next_state, context_updates=None):
        """Switches the current active game state.
        
        Args:
            next_state (str): One of the GameState values.
            context_updates (dict, optional): Context key-value pairs to set/update.
        """
        if next_state == self.current_state:
            return
            
        log.info("Transitioning from state '%s' to '%s'", self.current_state, next_state)
        
        # Save previous state
        self.previous_state = self.current_state
        self.current_state = next_state
        
        # Update shared context
        if context_updates:
            self.context.update(context_updates)
            
        # Play level/menu transition synth chime
        if next_state in (GameState.PLAYING, GameState.GAME_OVER):
            synth.play("click")
            
    def go_back(self):
        """Transitions back to the previous state, if possible."""
        if self.previous_state:
            self.transition_to(self.previous_state)
        else:
            self.transition_to(GameState.MAIN_MENU)
            
    def get_context_value(self, key, default=None):
        """Retrieves data passed between states."""
        return self.context.get(key, default)
        
    def clear_context(self):
        """Clears all shared state variables."""
        self.context.clear()
