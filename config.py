import os

# Screen Settings
WIDTH = 1280
HEIGHT = 720
FPS = 60
FULLSCREEN = False

# Camera & Tracking Settings
CAM_WIDTH = 640
CAM_HEIGHT = 480
CAMERA_ID = 0
FLIP_HORIZONTAL = True
COORD_SMOOTHING = 0.25  # Exponential moving average factor (lower = smoother but higher latency)
PINCH_THRESHOLD = 0.05  # Normalized distance between thumb and index tip to trigger pinch gesture
DETECTION_CONFIDENCE = 0.6
TRACKING_CONFIDENCE = 0.6

# Gameplay Physics Settings
GRAVITY = 750.0          # Pixels per second squared
LAUNCH_SPEED_Y_MIN = 700.0
LAUNCH_SPEED_Y_MAX = 950.0
LAUNCH_SPEED_X_MIN = -200.0
LAUNCH_SPEED_X_MAX = 200.0
SPAWN_INTERVAL_MIN = 0.8
SPAWN_INTERVAL_MAX = 2.0
BOMB_CHANCE = 0.2
MIN_SLICE_SPEED = 250.0   # Pixels per second required for a valid slice
COMBO_TIME_WINDOW = 0.4   # Seconds within which multiple slices count as a combo
MAX_LIVES = 3

# Visual Effects
TRAIL_MAX_POINTS = 15
TRAIL_MIN_WIDTH = 2
TRAIL_MAX_WIDTH = 10
PARTICLE_LIMIT = 500      # Soft cap to prevent resource exhaustion
SCREEN_SHAKE_DURATION = 0.3
SCREEN_SHAKE_INTENSITY = 10
SLOW_MOTION_FACTOR = 0.3
SLOW_MOTION_DURATION = 1.0

# Sound Settings
VOLUME = 0.5
SAMPLE_RATE = 44100
CHANNELS = 1              # Mono sound generation

# File Paths
SAVE_DIR = "logs"
SAVE_FILE = os.path.join(SAVE_DIR, "highscore.json")
LOG_FILE = os.path.join(SAVE_DIR, "game.log")

# Developer Options
DEVELOPER_MODE = False
DEBUG_HAND_TRACKING = False

# Premium Color Palette (RGB)
COLOR_BACKGROUND = (10, 15, 29)      # Deep cosmic blue
COLOR_TRAIL_PRIMARY = (0, 240, 255)   # Neon Cyan
COLOR_TRAIL_SECONDARY = (255, 0, 240) # Neon Purple
COLOR_TEXT_PRIMARY = (255, 255, 255)
COLOR_TEXT_ACCENT = (255, 215, 0)     # Gold
COLOR_TEXT_MUTED = (150, 160, 180)
COLOR_BORDER = (40, 50, 80)
COLOR_BUTTON_HOVER_FILL = (0, 240, 255, 60) # RGBA equivalent used in drawing

# Procedural Fruit Colors
FRUIT_COLORS = {
    "watermelon": {
        "outer": (46, 139, 87),    # Sea Green
        "inner": (220, 20, 60),     # Crimson Red
        "seed": (30, 30, 30),       # Dark Charcoal
        "radius": 55
    },
    "apple": {
        "outer": (200, 30, 30),     # Juicy Red
        "inner": (245, 245, 220),   # Creamy white inside
        "stem": (101, 67, 33),      # Brown stem
        "radius": 45
    },
    "banana": {
        "outer": (240, 200, 30),    # Vibrant Yellow
        "inner": (255, 250, 205),   # Lemon chiffon inside
        "tip": (50, 40, 20),        # Dark tip
        "radius": 40
    },
    "orange": {
        "outer": (255, 140, 0),     # Dark Orange
        "inner": (255, 165, 0),     # Orange peel inside
        "center": (255, 255, 240),  # Ivory core
        "radius": 48
    },
    "pineapple": {
        "outer": (184, 134, 11),    # Dark Goldenrod
        "inner": (255, 223, 0),     # Golden yellow pulp
        "crown": (34, 139, 34),     # Forest Green
        "radius": 50
    },
    "strawberry": {
        "outer": (220, 20, 60),     # Crimson
        "inner": (255, 105, 120),   # Soft pink pulp
        "seed": (255, 228, 140),    # Golden yellow seeds
        "leaf": (34, 139, 34),      # Green leaf
        "radius": 38
    },
    "mango": {
        "outer": (255, 165, 0),     # Orange skin
        "inner": (255, 200, 50),    # Rich golden pulp
        "blush": (200, 50, 30),     # Red blush on skin
        "radius": 48
    },
    "kiwi": {
        "outer": (101, 67, 33),     # Brown fuzzy skin
        "inner": (124, 185, 50),    # Bright green flesh
        "seed": (20, 20, 20),       # Black seeds
        "center": (220, 230, 190),  # Pale white core
        "radius": 40
    },
    "peach": {
        "outer": (255, 180, 120),   # Soft peach skin
        "inner": (255, 220, 160),   # Light peach flesh
        "blush": (240, 100, 80),    # Pink blush
        "pit": (139, 90, 43),       # Brown pit
        "radius": 44
    },
    "pear": {
        "outer": (180, 200, 50),    # Yellow-green skin
        "inner": (240, 240, 210),   # Pale cream flesh
        "stem": (101, 67, 33),      # Brown stem
        "radius": 46
    },
    "grapes": {
        "outer": (128, 0, 128),     # Purple
        "inner": (180, 130, 200),   # Light lavender pulp
        "highlight": (200, 160, 230), # Grape shine
        "radius": 42
    },
    "cherry": {
        "outer": (160, 10, 30),     # Deep cherry red
        "inner": (220, 60, 80),     # Bright red pulp
        "stem": (80, 50, 20),       # Dark brown stem
        "highlight": (255, 120, 130), # Glossy highlight
        "radius": 30
    },
    "coconut": {
        "outer": (101, 67, 33),     # Brown shell
        "inner": (255, 255, 245),   # White coconut meat
        "husk": (139, 105, 65),     # Light brown husk
        "radius": 50
    },
    "lemon": {
        "outer": (255, 237, 0),     # Bright yellow rind
        "inner": (255, 255, 180),   # Pale yellow pulp
        "tip": (200, 180, 0),       # Darker tip
        "radius": 40
    },
    "blueberry": {
        "outer": (50, 50, 140),     # Deep indigo blue
        "inner": (100, 80, 160),    # Purple-blue pulp
        "crown": (40, 40, 100),     # Dark blue crown ring
        "highlight": (120, 120, 200), # Blue shine
        "radius": 28
    },
    "bomb": {
        "body": (35, 35, 40),       # Matte Black
        "fuse": (160, 82, 45),      # Brown
        "spark": (255, 69, 0),      # Orange-Red spark
        "radius": 42
    }
}
