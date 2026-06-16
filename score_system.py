import json
import os
import time
from logger import log
import config
from audio import synth

class ScoreSystem:
    """Manages the player's score, lives, combo tracking, statistics, and high score saving/loading."""
    
    def __init__(self):
        self.score = 0
        self.lives = config.MAX_LIVES
        self.combos_sliced = 0
        self.fruits_sliced = 0
        self.bombs_hit = 0
        
        # Combo tracking
        self.combo_fruits = []      # List of fruit types sliced in the current window
        self.combo_timer = 0.0
        self.pending_combo_trigger = None # Stores combo details to be displayed by the engine
        
        # High scores leaderboard
        self.leaderboard = []
        self.load_high_scores()
        
    def reset(self):
        """Resets the state for a new game session."""
        self.score = 0
        self.lives = config.MAX_LIVES
        self.combos_sliced = 0
        self.fruits_sliced = 0
        self.bombs_hit = 0
        self.combo_fruits.clear()
        self.combo_timer = 0.0
        self.pending_combo_trigger = None
        log.info("Score system reset. New game started.")
        
    def register_slice(self, fruit_type):
        """Registers a sliced object. Updates score, lives, and starts/extends combo window.
        
        Args:
            fruit_type (str): Type of fruit or 'bomb'.
            
        Returns:
            bool: True if the player is still alive, False if they ran out of lives.
        """
        if fruit_type == "bomb":
            self.bombs_hit += 1
            # In our arcade rules, hitting a bomb deducts a life and 10 points
            self.lives -= 1
            self.score = max(0, self.score - 10)
            log.info("Bomb hit! Lives remaining: %d. Score: %d", self.lives, self.score)
            
            # Reset current combo
            self.combo_fruits.clear()
            self.combo_timer = 0.0
            
            return self.lives > 0
            
        # Standard fruit slice
        self.score += 1
        self.fruits_sliced += 1
        
        # Track combo
        if self.combo_timer <= 0.0:
            self.combo_timer = config.COMBO_TIME_WINDOW
        self.combo_fruits.append(fruit_type)
        
        return True
        
    def register_miss(self):
        """Registers a whole fruit falling offscreen without being sliced."""
        # Lose 1 life in classic mode
        self.lives -= 1
        log.info("Fruit missed! Lives remaining: %d", self.lives)
        return self.lives > 0
        
    def update(self, dt):
        """Updates the combo window timer."""
        if self.combo_timer > 0.0:
            self.combo_timer -= dt
            if self.combo_timer <= 0.0:
                self.combo_timer = 0.0
                self._check_combo()
                
    def _check_combo(self):
        """Evaluates whether the accumulated slices constitute a combo and awards bonus points."""
        num_fruits = len(self.combo_fruits)
        if num_fruits >= 3:
            # Combo achieved!
            self.combos_sliced += 1
            
            # Award combo bonuses
            if num_fruits == 3:
                bonus = 3
            elif num_fruits == 4:
                bonus = 8
            else:
                bonus = 15
                
            self.score += bonus
            
            # Cache the combo trigger metadata so the engine can spawn text/flashes
            self.pending_combo_trigger = {
                "count": num_fruits,
                "bonus": bonus,
                "fruits": list(self.combo_fruits)
            }
            
            log.info("COMBO! Sliced %d fruits. Bonus +%d points. New score: %d", 
                     num_fruits, bonus, self.score)
            synth.play("combo")
            
        self.combo_fruits.clear()
        
    def consume_combo_trigger(self):
        """Retrieves and clears the pending combo details."""
        trigger = self.pending_combo_trigger
        self.pending_combo_trigger = None
        return trigger
        
    def load_high_scores(self):
        """Loads the high score leaderboard from the persistent JSON file."""
        os.makedirs(config.SAVE_DIR, exist_ok=True)
        if not os.path.exists(config.SAVE_FILE):
            log.info("No high score file found. Populating default leaderboard.")
            self.leaderboard = [
                {"name": "NINJA", "score": 250, "date": time.strftime("%Y-%m-%d")},
                {"name": "SENSEI", "score": 150, "date": time.strftime("%Y-%m-%d")},
                {"name": "RECRUIT", "score": 50, "date": time.strftime("%Y-%m-%d")}
            ]
            self.save_high_scores()
            return
            
        try:
            with open(config.SAVE_FILE, 'r') as f:
                data = json.load(f)
                self.leaderboard = data.get("leaderboard", [])
                log.info("High scores loaded successfully. %d records.", len(self.leaderboard))
        except Exception as e:
            log.error("Failed to load high scores: %s. Using empty list.", e)
            self.leaderboard = []
            
    def save_high_scores(self):
        """Saves the leaderboard to highscore.json."""
        os.makedirs(config.SAVE_DIR, exist_ok=True)
        try:
            # Sort leaderboard by score descending
            self.leaderboard.sort(key=lambda x: x["score"], reverse=True)
            self.leaderboard = self.leaderboard[:5] # Keep only top 5
            
            with open(config.SAVE_FILE, 'w') as f:
                json.dump({"leaderboard": self.leaderboard}, f, indent=4)
            log.info("High scores saved successfully.")
        except Exception as e:
            log.error("Failed to save high scores: %s", e)
            
    def qualifies_for_leaderboard(self, score):
        """Checks if a score fits into the top 5 spots."""
        if len(self.leaderboard) < 5:
            return True
        return score > self.leaderboard[-1]["score"]
        
    def add_score_to_leaderboard(self, name, score):
        """Adds a score entry to the leaderboard and saves it."""
        if not name:
            name = "AAA"
        entry = {
            "name": name.upper()[:8],
            "score": score,
            "date": time.strftime("%Y-%m-%d")
        }
        self.leaderboard.append(entry)
        self.save_high_scores()
