import os
import sys
from logger import log
from game_engine import GameEngine

def main():
    """Main application bootstrap entry point."""
    log.info("=========================================")
    log.info("Starting Fruit Cutter Vision application")
    log.info("Python version: %s", sys.version)
    log.info("Operating System: %s", sys.platform)
    log.info("Current Working Directory: %s", os.getcwd())
    log.info("=========================================")
    
    try:
        # Instantiate and start the game engine
        engine = GameEngine()
        engine.start()
        
    except Exception as e:
        log.critical("Unhandled critical exception in main thread: %s", e, exc_info=True)
        # Show an emergency terminal error if possible
        print(f"\nCRITICAL ERROR: {e}", file=sys.stderr)
        print("Please check 'logs/game.log' for details.", file=sys.stderr)
        sys.exit(1)
        
if __name__ == "__main__":
    main()
