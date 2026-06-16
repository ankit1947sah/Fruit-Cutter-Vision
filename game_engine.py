import pygame
import random
import time
import os
import sys
import queue
import numpy as np
import config
from logger import log
from audio import synth
from camera import Camera
from hand_tracker import HandTracker
from object_pool import ObjectPool
from fruit import Fruit, initialize_procedural_fruits
from particles import Particle, ParticleManager
from effects import TrailSegment, BladeTrail, ScreenShake, SlowMotion, Shockwave
from collision import calculate_slice_details
from score_system import ScoreSystem
from state_manager import StateManager, GameState
from ui import UIButton, UIRenderer

# Try to import psutil for accurate memory diagnostics
try:
    import psutil
    _process = psutil.Process(os.getpid())
except ImportError:
    _process = None

class GameEngine:
    """The central hub coordinating updates, input capture, rendering, and thread management."""
    
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Antigravity Fruit Ninja Vision")
        
        # Setup display (Support fullscreen toggling via settings)
        self.screen_flags = pygame.FULLSCREEN if config.FULLSCREEN else 0
        self.screen = pygame.display.set_mode((config.WIDTH, config.HEIGHT), self.screen_flags)
        self.clock = pygame.time.Clock()
        self.running = False
        
        # Virtual canvas for screen shake implementation
        self.canvas = pygame.Surface((config.WIDTH, config.HEIGHT))
        
        # Initialize Subsystems
        self.state_mgr = StateManager()
        self.score_sys = ScoreSystem()
        self.ui_renderer = UIRenderer()
        
        # Init Camera & Hand Tracking
        self.camera = Camera()
        self.tracker = HandTracker(self.camera)
        
        # Initialize Object Pools
        self.fruit_pool = ObjectPool(lambda: Fruit(), initial_size=20, name="FruitPool")
        self.particle_pool = ObjectPool(lambda: Particle(), initial_size=150, name="ParticlePool")
        self.trail_pool = ObjectPool(lambda: TrailSegment(), initial_size=40, name="TrailPool")
        
        # Initialize Managers
        self.particle_mgr = ParticleManager(self.particle_pool)
        self.blade_trail = BladeTrail(self.trail_pool)
        self.screen_shake = ScreenShake()
        self.slow_motion = SlowMotion()
        
        # Lists for active gameplay elements
        self.active_fruits = []
        self.active_shockwaves = []
        
        # Spawn timers
        self.spawn_timer = 0.0
        self.next_spawn_interval = 1.5
        
        # Pointer tracking variables
        self.prev_pointer_pos = None
        self.curr_pointer_pos = None
        self.hand_detected = False
        self.is_pinching = False
        
        # Performance logging metrics
        self.frame_time = 0.0
        self.tracking_latency = 0.0
        
        # UI Buttons list (for menus)
        self.menu_buttons = []
        
        # Keyboard entry buffer for Game Over leaderboard
        self.player_name_entry = ""
        self.entering_name = False
        
        # Load audio mixer
        synth.init_mixer()
        
    def start(self):
        """Launches background threads and runs the main engine loop."""
        self.running = True
        self.camera.start()
        self.tracker.start()
        
        # Load high scores
        self.score_sys.load_high_scores()
        
        log.info("Game Engine started.")
        
        while self.running:
            # Calculate delta time (in seconds)
            raw_dt = self.clock.tick(config.FPS) / 1000.0
            
            # Avoid huge jumps on window drag
            raw_dt = min(raw_dt, 0.1)
            
            # Measure frame time
            start_frame_time = time.perf_counter()
            
            # Handle Pygame events (events are processed in all states)
            self._handle_events()
            
            # Update inputs and read background threads
            self._update_inputs(raw_dt)
            
            # Apply slow motion scale to update delta-time
            self.slow_motion.update(raw_dt)
            dt = raw_dt * self.slow_motion.get_dt_modifier()
            
            # Update state-specific logic
            self._update_state(dt)
            
            # Draw game according to current state
            self._draw_state()
            
            # Update frame metric
            self.frame_time = (time.perf_counter() - start_frame_time) * 1000.0
            
        # Clean up
        self._shutdown()
        
    def _shutdown(self):
        """Gracefully stops camera and tracking threads, and exits Pygame."""
        log.info("Shutting down game engine...")
        self.tracker.stop()
        self.camera.stop()
        pygame.quit()
        sys.exit(0)
        
    def _handle_events(self):
        """Processes keyboard/system events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.state_mgr.current_state == GameState.PLAYING:
                        self.state_mgr.transition_to(GameState.PAUSED)
                    elif self.state_mgr.current_state == GameState.PAUSED:
                        self.state_mgr.transition_to(GameState.PLAYING)
                    elif self.state_mgr.current_state != GameState.MAIN_MENU:
                        self.state_mgr.transition_to(GameState.MAIN_MENU)
                        
                elif event.key == pygame.K_F1:
                    # Toggle developer metrics
                    config.DEVELOPER_MODE = not config.DEVELOPER_MODE
                    log.info("Developer Mode toggled: %s", config.DEVELOPER_MODE)

                elif event.key == pygame.K_F3:
                    # Toggle hand tracking debug overlay
                    config.DEBUG_HAND_TRACKING = not config.DEBUG_HAND_TRACKING
                    log.info("Debug Hand Tracking toggled: %s", config.DEBUG_HAND_TRACKING)
                    
                # Handle typing in Leaderboard entry mode
                if self.entering_name and self.state_mgr.current_state == GameState.GAME_OVER:
                    if event.key == pygame.K_BACKSPACE:
                        self.player_name_entry = self.player_name_entry[:-1]
                    elif event.key == pygame.K_RETURN:
                        if self.player_name_entry:
                            self.score_sys.add_score_to_leaderboard(self.player_name_entry, self.score_sys.score)
                            self.entering_name = False
                            self._setup_game_over_buttons()
                    else:
                        if len(self.player_name_entry) < 8 and event.unicode.isalnum():
                            self.player_name_entry += event.unicode.upper()

    def _update_inputs(self, dt):
        """Fetches the latest coordinates from the tracker using a thread-safe queue, falling back to mouse."""
        # Age the blade trail first
        self.blade_trail.update(dt)
        
        # Retrieve all queued coordinate updates from the hand tracker thread
        coord_events = []
        if self.tracker.running:
            while not self.tracker.coord_queue.empty():
                try:
                    ev = self.tracker.coord_queue.get_nowait()
                    coord_events.append(ev)
                except queue.Empty:
                    break
                    
        # Check if we should process webcam coordinates or fallback to mouse
        if coord_events:
            # We have tracking updates!
            for tx, ty, detected, pinching, ts in coord_events:
                # Update current state
                self.hand_detected = detected
                self.is_pinching = pinching
                
                # Check latency
                if detected:
                    self.tracking_latency = (time.perf_counter() - ts) * 1000.0
                    # If latency calculation is negative or tiny due to timer discrepancies, clamp it
                    self.tracking_latency = max(1.0, min(100.0, self.tracking_latency))
                else:
                    self.tracking_latency = 0.0
                
                if detected and tx is not None and ty is not None:
                    # Save previous pointer pos for slice segment calculation
                    self.prev_pointer_pos = self.curr_pointer_pos
                    self.curr_pointer_pos = (tx, ty)
                    
                    # Add to trail if we are in active game/menu states
                    if self.state_mgr.current_state in (GameState.PLAYING, GameState.MAIN_MENU, GameState.SETTINGS, GameState.HIGH_SCORES, GameState.GAME_OVER):
                        self.blade_trail.add_point(tx, ty)
                        
                    # If playing, run collision checks immediately on this segment!
                    if self.state_mgr.current_state == GameState.PLAYING:
                        self._check_slice_collisions(dt)
                else:
                    # Tracking lost or hand not detected in this event
                    self.hand_detected = False
                    self._fallback_to_mouse(dt)
        else:
            # No new queue events in this frame (either thread has not ticked yet, or tracker is disabled)
            if not self.hand_detected:
                # Fall back to mouse input
                self._fallback_to_mouse(dt)
            else:
                # We are tracking hand, but did not receive a new frame in this exact frame tick.
                # To prevent speed dropping to 0, we do not update prev_pointer_pos or run collisions.
                # Just keep the current pos.
                pass

    def _fallback_to_mouse(self, dt):
        """Standard mouse fallback control logic."""
        mx, my = pygame.mouse.get_pos()
        pinching = pygame.mouse.get_pressed()[0]
        
        self.prev_pointer_pos = self.curr_pointer_pos
        self.curr_pointer_pos = (mx, my)
        self.is_pinching = pinching
        self.tracking_latency = 0.0
        
        # Add to trail if in active game/menu states
        if self.state_mgr.current_state in (GameState.PLAYING, GameState.MAIN_MENU, GameState.SETTINGS, GameState.HIGH_SCORES, GameState.GAME_OVER):
            self.blade_trail.add_point(mx, my)
            
        # If playing, run collision checks immediately on mouse stroke segment
        if self.state_mgr.current_state == GameState.PLAYING:
            self._check_slice_collisions(dt)

    def _check_slice_collisions(self, dt):
        """Verifies if the current blade segment intersects with any active whole fruits."""
        if self.prev_pointer_pos is None or self.curr_pointer_pos is None:
            return
            
        for fruit in list(self.active_fruits):  # Use list copy to avoid mutation errors
            if fruit.state == "whole" and fruit.active:
                details = calculate_slice_details(
                    self.prev_pointer_pos, self.curr_pointer_pos,
                    (fruit.physics.x, fruit.physics.y), fruit.radius, dt
                )
                
                if details:
                    # Slice achieved!
                    fruit.slice(details)
                    alive = self.score_sys.register_slice(fruit.fruit_type)
                    
                    # Visual effects
                    if fruit.fruit_type == "bomb":
                        self.screen_shake.trigger(0.6, 20)
                        self.particle_mgr.spawn_bomb_explosion(fruit.physics.x, fruit.physics.y)
                        self.slow_motion.trigger(1.2, 0.25)
                        
                        # Clear other whole fruits
                        for other in self.active_fruits:
                            if other != fruit and other.state == "whole":
                                other.active = False
                                self.fruit_pool.release(other)
                        self.active_fruits.clear()
                        
                        if not alive:
                            self._trigger_game_over()
                            break
                    else:
                        self.screen_shake.trigger(0.18, 6)
                        inner_color = config.FRUIT_COLORS[fruit.fruit_type]["inner"]
                        self.particle_mgr.spawn_juice_splash(
                            fruit.physics.x, fruit.physics.y, inner_color, details["angle"]
                        )
                        self.particle_mgr.spawn_seeds(fruit.physics.x, fruit.physics.y, count=3)
                        
                        wave = Shockwave(fruit.physics.x, fruit.physics.y, max_radius=80, color=inner_color)
                        wave.active = True
                        self.active_shockwaves.append(wave)
                
    def _update_state(self, dt):
        """Directs updates to corresponding state handlers."""
        state = self.state_mgr.current_state
        
        if state == GameState.LOADING:
            self._update_loading(dt)
        elif state == GameState.MAIN_MENU:
            self._update_menu(dt)
        elif state == GameState.PLAYING:
            self._update_playing(dt)
        elif state == GameState.PAUSED:
            self._update_paused(dt)
        elif state == GameState.SETTINGS:
            self._update_settings(dt)
        elif state == GameState.HIGH_SCORES:
            self._update_high_scores(dt)
        elif state == GameState.GAME_OVER:
            self._update_game_over(dt)
            
    def _draw_state(self):
        """Directs rendering calls based on state, applying screen shake."""
        # 1. Clear virtual canvas
        self.canvas.fill(config.COLOR_BACKGROUND)
        
        state = self.state_mgr.current_state
        
        # 2. Render state content to virtual canvas
        if state == GameState.LOADING:
            self._draw_loading()
        elif state == GameState.MAIN_MENU:
            self._draw_menu()
        elif state == GameState.PLAYING:
            self._draw_playing()
        elif state == GameState.PAUSED:
            self._draw_paused()
        elif state == GameState.SETTINGS:
            self._draw_settings()
        elif state == GameState.HIGH_SCORES:
            self._draw_high_scores()
        elif state == GameState.GAME_OVER:
            self._draw_game_over()
            
        # Draw blade trail on top of everything (except loading screen)
        if state != GameState.LOADING:
            self.blade_trail.draw(self.canvas)
            
            # Render hover-to-select progress wheel at cursor
            if self.curr_pointer_pos is not None:
                max_progress = 0.0
                for btn in self.menu_buttons:
                    if btn.is_hovered:
                        max_progress = max(max_progress, btn.hover_timer / btn.hover_duration)
                if max_progress > 0.0:
                    self.ui_renderer.draw_progress_wheel(self.canvas, self.curr_pointer_pos, max_progress)
                    
        # 3. Draw developer performance overlay if enabled
        if config.DEVELOPER_MODE:
            self._draw_developer_overlay()
            
        # Draw hand tracking debug overlay if enabled
        if config.DEBUG_HAND_TRACKING:
            self._draw_hand_tracking_debug()
            
        # 4. Resolve screen shake offsets
        self.screen_shake.update(self.clock.get_time() / 1000.0) # Clock delta
        dx, dy = self.screen_shake.get_offset()
        
        # 5. Clear main window and blit the virtual canvas with screen shake offsets
        self.screen.fill((0, 0, 0))
        self.screen.blit(self.canvas, (dx, dy))
        pygame.display.flip()

    def _draw_hand_tracking_debug(self):
        """Renders the comprehensive hand tracking debug overlay (F3)."""
        # 1. Semi-transparent backdrop over game
        backdrop = pygame.Surface((config.WIDTH, config.HEIGHT), pygame.SRCALPHA)
        backdrop.fill((10, 15, 30, 200))  # Slate dark blue overlay
        self.canvas.blit(backdrop, (0, 0))
        
        # 2. Retrieve camera frame
        frame = self.camera.get_frame()
        cw, ch = 640, 480
        ox = (config.WIDTH - cw) // 2 + 100 # Shift slightly right to make room for text panel on left
        oy = (config.HEIGHT - ch) // 2
        
        if frame is not None:
            try:
                # opencv image is BGR, convert to RGB for pygame
                rgb_frame = frame[:, :, ::-1]
                frame_surf = pygame.surfarray.make_surface(rgb_frame.swapaxes(0, 1))
                scaled_surf = pygame.transform.scale(frame_surf, (cw, ch))
                
                # Draw webcam feed centered-right
                self.canvas.blit(scaled_surf, (ox, oy))
                pygame.draw.rect(self.canvas, config.COLOR_BORDER, (ox - 4, oy - 4, cw + 8, ch + 8), 4, border_radius=8)
                
                # 3. Draw Hand Skeleton if detected
                landmarks = self.tracker.get_landmarks()
                if landmarks is not None:
                    # Map all 21 landmarks into absolute coordinates on the scaled surface
                    pts = []
                    for lm in landmarks:
                        lx = ox + int(lm.x * cw)
                        ly = oy + int(lm.y * ch)
                        pts.append((lx, ly))
                        
                    # Connections
                    connections = [
                        (0, 1), (1, 2), (2, 3), (3, 4),        # Thumb
                        (0, 5), (5, 6), (6, 7), (7, 8),        # Index
                        (5, 9), (9, 10), (10, 11), (11, 12),    # Middle
                        (9, 13), (13, 14), (14, 15), (15, 16),  # Ring
                        (13, 17), (0, 17), (17, 18), (18, 19), (19, 20) # Pinky
                    ]
                    
                    # Draw connection lines
                    for p1_idx, p2_idx in connections:
                        pygame.draw.line(self.canvas, config.COLOR_TRAIL_SECONDARY, pts[p1_idx], pts[p2_idx], 3)
                        
                    # Draw joint points
                    for idx, pt in enumerate(pts):
                        color = config.COLOR_TEXT_PRIMARY
                        radius = 4
                        if idx == 8:  # Index finger tip
                            color = config.COLOR_TRAIL_PRIMARY
                            radius = 8
                            # Draw an index finger target marker (crosshair + outer circle)
                            pygame.draw.circle(self.canvas, config.COLOR_TRAIL_PRIMARY, pt, 16, 2)
                            pygame.draw.line(self.canvas, config.COLOR_TRAIL_PRIMARY, (pt[0] - 22, pt[1]), (pt[0] + 22, pt[1]), 2)
                            pygame.draw.line(self.canvas, config.COLOR_TRAIL_PRIMARY, (pt[0], pt[1] - 22), (pt[0], pt[1] + 22), 2)
                        elif idx == 4:  # Thumb tip
                            color = config.COLOR_TEXT_ACCENT
                            radius = 6
                        pygame.draw.circle(self.canvas, color, pt, radius)
            except Exception as e:
                log.exception("Exception drawing hand landmarks debug view: %s", e)
        else:
            # Draw camera placeholder frame
            pygame.draw.rect(self.canvas, config.COLOR_BORDER, (ox, oy, cw, ch), 2, border_radius=8)
            placeholder_text = self.ui_renderer.font_hud.render("WEBCAM FEED UNAVAILABLE", True, (200, 50, 50))
            pr = placeholder_text.get_rect(center=(ox + cw // 2, oy + ch // 2))
            self.canvas.blit(placeholder_text, pr)
            
        # 4. Render diagnostics text box on the left side of the screen
        game_fps = self.clock.get_fps()
        camera_fps = self.camera.fps
        finger_x, finger_y = self.curr_pointer_pos if self.curr_pointer_pos else (0, 0)
        
        telemetry_lines = [
            "=== WEBCAM TRACKING DIAGNOSTICS ===",
            f"Hand Status: {'DETECTED' if self.hand_detected else 'NO HAND'}",
            f"Index Tip Pygame: ({int(finger_x)}, {int(finger_y)})",
            f"Pinch Gesture: {'ACTIVE' if self.is_pinching else 'INACTIVE'}",
            f"MediaPipe Model: hand_landmarker.task",
            f"Detection Confidence Threshold: {config.DETECTION_CONFIDENCE}",
            f"Tracking Confidence Threshold: {config.TRACKING_CONFIDENCE}",
            f"Game Refresh Rate: {game_fps:.1f} FPS",
            f"Webcam Hardware: {camera_fps:.1f} FPS",
            f"Tracking Latency: {self.tracking_latency:.1f} ms",
            "",
            "Safe Zone bounds: [0.15, 0.85]",
            "Coordinate Filter: One Euro Filter",
            "",
            "[F3] Close Hand Diagnostics Overlay"
        ]
        
        panel_w = 360
        panel_h = len(telemetry_lines) * 24 + 30
        panel_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel_surf.fill((10, 15, 30, 230))
        
        px = 40
        py = (config.HEIGHT - panel_h) // 2
        self.canvas.blit(panel_surf, (px, py))
        pygame.draw.rect(self.canvas, config.COLOR_TRAIL_PRIMARY, (px, py, panel_w, panel_h), 2, border_radius=8)
        
        for idx, line in enumerate(telemetry_lines):
            color = config.COLOR_TRAIL_PRIMARY if idx == 0 else config.COLOR_TEXT_PRIMARY
            if "NO HAND" in line:
                color = (255, 60, 60)
            elif "DETECTED" in line:
                color = (60, 255, 60)
            elif "ACTIVE" in line:
                color = config.COLOR_TEXT_ACCENT
                
            text_surf = self.ui_renderer.font_body.render(line, True, color)
            self.canvas.blit(text_surf, (px + 15, py + 15 + idx * 24))

    # =========================================================================
    # STATE: LOADING
    # =========================================================================
    
    def _update_loading(self, dt):
        """Warmup frame to render procedural assets."""
        # Initialize assets immediately on the first frame
        initialize_procedural_fruits()
        synth.generate_all_sounds()
        
        # Brief pause to show loading is complete
        time.sleep(0.5)
        
        # Transition to menu
        self._setup_menu_buttons()
        self.state_mgr.transition_to(GameState.MAIN_MENU)
        
    def _draw_loading(self):
        """Draws loading screen text and spinner."""
        self.ui_renderer.draw_title(self.canvas, "LOADING SYSTEMS...", y_offset=config.HEIGHT // 2 - 40)
        
        # Simple progress bar frame
        w, h = 300, 20
        x = (config.WIDTH - w) // 2
        y = config.HEIGHT // 2 + 20
        pygame.draw.rect(self.canvas, config.COLOR_BORDER, (x, y, w, h), 2, border_radius=4)
        
        # Draw fully loaded bar
        pygame.draw.rect(self.canvas, config.COLOR_TRAIL_PRIMARY, (x + 3, y + 3, w - 6, h - 6), border_radius=2)
        
        # Hint text
        hint_surf = self.ui_renderer.font_body.render(
            "COMPILING PROCEDURAL WAVEFORMS & COLOR GRADIENTS", True, config.COLOR_TEXT_MUTED
        )
        hr = hint_surf.get_rect(center=(config.WIDTH // 2, y + 50))
        self.canvas.blit(hint_surf, hr)

    # =========================================================================
    # STATE: MAIN MENU
    # =========================================================================
    
    def _setup_menu_buttons(self):
        self.menu_buttons = [
            UIButton(config.WIDTH//2 - 150, 240, 300, 50, "PLAY GAME", self._btn_play),
            UIButton(config.WIDTH//2 - 150, 310, 300, 50, "HIGH SCORES", self._btn_high_scores),
            UIButton(config.WIDTH//2 - 150, 380, 300, 50, "SETTINGS", self._btn_settings),
            UIButton(config.WIDTH//2 - 150, 450, 300, 50, "EXIT GAME", self._btn_exit)
        ]
        
    def _update_menu(self, dt):
        # Update buttons
        for btn in self.menu_buttons:
            if btn.update(self.curr_pointer_pos, self.is_pinching, dt):
                break # Stop updates to prevent index shifts during transition
                
    def _draw_menu(self):
        # Title
        self.ui_renderer.draw_title(self.canvas, "FRUIT CUTTER VISION")
        
        sub = self.ui_renderer.font_body.render("HOVER CURSOR OR PINCH TO SELECT", True, config.COLOR_TEXT_MUTED)
        sr = sub.get_rect(center=(config.WIDTH//2, 160))
        self.canvas.blit(sub, sr)
        
        # Draw buttons
        for btn in self.menu_buttons:
            btn.draw(self.canvas, self.ui_renderer.font_header)
            
        # Draw instructions logo
        instr_lbl = self.ui_renderer.font_body.render("INDEX FINGER ACTS AS BLADE. GOAL: SLICE FRUITS, AVOID BOMBS!", True, config.COLOR_TEXT_ACCENT)
        ir = instr_lbl.get_rect(center=(config.WIDTH//2, config.HEIGHT - 50))
        self.canvas.blit(instr_lbl, ir)

    def _btn_play(self):
        # Clear entities and start game
        self.active_fruits.clear()
        self.active_shockwaves.clear()
        self.particle_mgr.clear()
        self.blade_trail.clear()
        self.score_sys.reset()
        
        self.spawn_timer = 0.0
        self.next_spawn_interval = 1.0
        
        self.state_mgr.transition_to(GameState.PLAYING)
        
    def _btn_high_scores(self):
        self._setup_highscore_buttons()
        self.state_mgr.transition_to(GameState.HIGH_SCORES)
        
    def _btn_settings(self):
        self._setup_settings_buttons()
        self.state_mgr.transition_to(GameState.SETTINGS)
        
    def _btn_exit(self):
        self.running = False

    # =========================================================================
    # STATE: PLAYING (Gameplay)
    # =========================================================================
    
    def _update_playing(self, dt):
        # 1. Spawn logic
        self.spawn_timer += dt
        if self.spawn_timer >= self.next_spawn_interval:
            self.spawn_timer = 0.0
            self._spawn_wave()
            
        # 2. Update scoring combo times
        self.score_sys.update(dt)
        
        # Resolve any triggered combos
        combo = self.score_sys.consume_combo_trigger()
        if combo:
            # Trigger effects: shake screen and spawn combo popup
            self.screen_shake.trigger(0.3, 8)
            # Find approximate average slice location or just place at pointer
            cx, cy = config.WIDTH // 2, config.HEIGHT // 3
            if self.curr_pointer_pos:
                cx, cy = self.curr_pointer_pos
            # Add to active shockwaves for visual impact
            wave = Shockwave(cx, cy, max_radius=120, color=config.COLOR_TEXT_ACCENT)
            wave.active = True
            self.active_shockwaves.append(wave)
            
            # Capture the combo details to draw it
            # We keep it as a floating notification
            self.floating_combo = (combo, cx, cy, 1.2) # (details, x, y, duration)
            
        # Handle floating combo timers
        if hasattr(self, "floating_combo") and self.floating_combo:
            details, cx, cy, duration = self.floating_combo
            duration -= dt
            if duration <= 0:
                self.floating_combo = None
            else:
                self.floating_combo = (details, cx, cy, duration)
                
        # 3. Update Fruits
        still_active_fruits = []
        for fruit in self.active_fruits:
            fruit.update(dt)
            
            if fruit.active:
                still_active_fruits.append(fruit)
                
                # Check for missed whole fruits falling past bottom
                if fruit.state == "whole" and fruit.fruit_type != "bomb":
                    # Check if descending below boundary
                    if fruit.physics.y > config.HEIGHT + 80 and fruit.physics.vy > 0:
                        fruit.active = False
                        alive = self.score_sys.register_miss()
                        if not alive:
                            self._trigger_game_over()
                            return
            else:
                # Release to pool
                self.fruit_pool.release(fruit)
                
        self.active_fruits = still_active_fruits
        
        # 5. Update Particles
        self.particle_mgr.update(dt)
        
        # 6. Update Shockwaves
        still_active_waves = []
        for wave in self.active_shockwaves:
            wave.update(dt)
            if wave.active:
                still_active_waves.append(wave)
        self.active_shockwaves = still_active_waves
        
    def _draw_playing(self):
        # Draw background elements (procedural gradient lines or grid could be here, keep deep dark clean)
        
        # Draw Shockwaves first (underlay)
        for wave in self.active_shockwaves:
            wave.draw(self.canvas)
            
        # Draw Fruits
        for fruit in self.active_fruits:
            fruit.draw(self.canvas)
            
        # Draw Particles
        self.particle_mgr.draw(self.canvas)
        
        # Draw floating combo messages
        if hasattr(self, "floating_combo") and self.floating_combo:
            details, cx, cy, duration = self.floating_combo
            self.ui_renderer.draw_combo_popup(self.canvas, details, cx, cy)
            
        # Draw HUD overlays
        # Retrieve latest camera frame for calibration viewport
        cam_frame = self.camera.get_frame()
        self.ui_renderer.draw_hud(
            self.canvas, self.score_sys.score, self.score_sys.lives,
            cam_frame, self.hand_detected, 
            self.curr_pointer_pos[0] if self.curr_pointer_pos else None,
            self.curr_pointer_pos[1] if self.curr_pointer_pos else None,
            self.is_pinching
        )
        
    def _spawn_wave(self):
        """Calculates dynamic difficulty scaling and launches fruit waves."""
        score = self.score_sys.score
        
        # 1. Scale variables dynamically
        # Increase wave size based on score: starting at 1, max 4 fruits at once
        max_wave_size = min(4, 1 + score // 15)
        wave_size = random.randint(1, max_wave_size)
        
        # Speed scaling: increase velocities
        speed_multiplier = 1.0 + min(0.35, (score / 60.0) * 0.15)
        
        # Bomb chance scaling: up to 35%
        bomb_prob = min(0.35, config.BOMB_CHANCE + (score // 25) * 0.05)
        
        # Spawn interval scaling: faster spawns at higher score
        self.next_spawn_interval = max(config.SPAWN_INTERVAL_MIN, 
                                        config.SPAWN_INTERVAL_MAX - (score // 10) * 0.18)
        
        # 2. Launch fruits in wave
        log.info("Spawning wave of size %d. Next interval: %.2fs, Bomb prob: %.2f", 
                 wave_size, self.next_spawn_interval, bomb_prob)
                 
        fruit_types = ["watermelon", "apple", "banana", "orange", "pineapple"]
        
        # Keep track of x coordinates of spawned fruits in this wave to avoid overlapping launch collisions
        spawned_xs = []
        
        for _ in range(wave_size):
            # Select x offset
            x_found = False
            for _ in range(5): # try 5 times to find a unique X coordinate
                tx = random.randint(150, config.WIDTH - 150)
                if not spawned_xs or all(abs(tx - ex) > 100 for ex in spawned_xs):
                    x_found = True
                    break
            if not x_found:
                tx = random.randint(150, config.WIDTH - 150)
            spawned_xs.append(tx)
            
            # Start position below screen
            ty = config.HEIGHT + 50
            
            # Y speed: launch upward arc
            vy = -random.uniform(config.LAUNCH_SPEED_Y_MIN, config.LAUNCH_SPEED_Y_MAX) * speed_multiplier
            
            # X speed: push towards screen center
            center_x = config.WIDTH // 2
            if tx < center_x:
                vx = random.uniform(50.0, 200.0)
            else:
                vx = random.uniform(-200.0, -50.0)
            vx *= speed_multiplier
            
            # Spin rate
            rot = random.uniform(-160.0, 160.0)
            
            # Select item type
            if random.random() < bomb_prob:
                f_type = "bomb"
            else:
                f_type = random.choice(fruit_types)
                
            # Acquire fruit and launch
            fruit = self.fruit_pool.acquire(f_type, tx, ty, vx, vy, rot)
            self.active_fruits.append(fruit)

    def _trigger_game_over(self):
        """Initiates Game Over sequences."""
        log.info("Game Over triggered! Final score: %d", self.score_sys.score)
        
        # Clear entities
        self.active_fruits.clear()
        self.active_shockwaves.clear()
        self.particle_mgr.clear()
        self.blade_trail.clear()
        
        # Play crash or click sound
        synth.play("explosion")
        
        # Check if score qualifies for high scores list
        qualifies = self.score_sys.qualifies_for_leaderboard(self.score_sys.score)
        if qualifies:
            self.score_sys.add_score_to_leaderboard("PLAYER", self.score_sys.score)
        
        self.entering_name = False
        self._setup_game_over_buttons()
            
        self.state_mgr.transition_to(GameState.GAME_OVER)
        
    # =========================================================================
    # STATE: PAUSED
    # =========================================================================
    
    def _setup_paused_buttons(self):
        self.menu_buttons = [
            UIButton(config.WIDTH//2 - 150, 280, 300, 50, "RESUME GAME", self._btn_resume),
            UIButton(config.WIDTH//2 - 150, 350, 300, 50, "RESTART GAME", self._btn_play),
            UIButton(config.WIDTH//2 - 150, 420, 300, 50, "QUIT TO MENU", self._btn_quit)
        ]
        
    def _update_paused(self, dt):
        for btn in self.menu_buttons:
            if btn.update(self.curr_pointer_pos, self.is_pinching, dt):
                break
                
    def _draw_paused(self):
        # Draw current gameplay frame behind a dark semi-transparent dim overlay
        self._draw_playing()
        
        dim = pygame.Surface((config.WIDTH, config.HEIGHT), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 150))
        self.canvas.blit(dim, (0, 0))
        
        self.ui_renderer.draw_title(self.canvas, "GAME PAUSED")
        
        # Draw buttons
        for btn in self.menu_buttons:
            btn.draw(self.canvas, self.ui_renderer.font_header)
            
    def _btn_resume(self):
        self.state_mgr.transition_to(GameState.PLAYING)
        
    def _btn_quit(self):
        self._setup_menu_buttons()
        self.state_mgr.transition_to(GameState.MAIN_MENU)

    # =========================================================================
    # STATE: SETTINGS
    # =========================================================================
    
    def _setup_settings_buttons(self):
        # Dynamic button texts based on configurations
        self.menu_buttons = [
            UIButton(config.WIDTH//2 - 150, 240, 300, 50, f"VOL: {int(config.VOLUME * 100)}%", self._btn_toggle_volume),
            UIButton(config.WIDTH//2 - 150, 310, 300, 50, f"SCREEN: {'FULL' if config.FULLSCREEN else 'WINDOW'}", self._btn_toggle_screen),
            UIButton(config.WIDTH//2 - 150, 380, 300, 50, f"METRICS: {'ON' if config.DEVELOPER_MODE else 'OFF'}", self._btn_toggle_metrics),
            UIButton(config.WIDTH//2 - 150, 460, 300, 50, "BACK TO MENU", self._btn_quit)
        ]
        
    def _update_settings(self, dt):
        for btn in self.menu_buttons:
            if btn.update(self.curr_pointer_pos, self.is_pinching, dt):
                break
                
    def _draw_settings(self):
        self.ui_renderer.draw_title(self.canvas, "SETTINGS")
        
        # Draw buttons
        for btn in self.menu_buttons:
            btn.draw(self.canvas, self.ui_renderer.font_header)
            
    def _btn_toggle_volume(self):
        new_vol = config.VOLUME + 0.25
        if new_vol > 1.0:
            new_vol = 0.0
        synth.set_volume(new_vol)
        log.info("Volume changed: %.2f", config.VOLUME)
        self._setup_settings_buttons() # refresh texts
        
    def _btn_toggle_screen(self):
        config.FULLSCREEN = not config.FULLSCREEN
        self.screen_flags = pygame.FULLSCREEN if config.FULLSCREEN else 0
        self.screen = pygame.display.set_mode((config.WIDTH, config.HEIGHT), self.screen_flags)
        log.info("Fullscreen toggled: %s", config.FULLSCREEN)
        self._setup_settings_buttons()
        
    def _btn_toggle_metrics(self):
        config.DEVELOPER_MODE = not config.DEVELOPER_MODE
        self._setup_settings_buttons()

    # =========================================================================
    # STATE: HIGH SCORES (Leaderboard)
    # =========================================================================
    
    def _setup_highscore_buttons(self):
        self.menu_buttons = [
            UIButton(config.WIDTH//2 - 150, config.HEIGHT - 100, 300, 50, "BACK TO MENU", self._btn_quit)
        ]
        
    def _update_high_scores(self, dt):
        for btn in self.menu_buttons:
            if btn.update(self.curr_pointer_pos, self.is_pinching, dt):
                break
                
    def _draw_high_scores(self):
        self.ui_renderer.draw_title(self.canvas, "LOCAL LEADERBOARD")
        
        # Draw table headers
        headers_y = 180
        lbl_rank = self.ui_renderer.font_hud.render("RANK", True, config.COLOR_TRAIL_PRIMARY)
        lbl_name = self.ui_renderer.font_hud.render("PLAYER", True, config.COLOR_TRAIL_PRIMARY)
        lbl_score = self.ui_renderer.font_hud.render("SCORE", True, config.COLOR_TRAIL_PRIMARY)
        lbl_date = self.ui_renderer.font_hud.render("DATE", True, config.COLOR_TRAIL_PRIMARY)
        
        self.canvas.blit(lbl_rank, (config.WIDTH//2 - 250, headers_y))
        self.canvas.blit(lbl_name, (config.WIDTH//2 - 120, headers_y))
        self.canvas.blit(lbl_score, (config.WIDTH//2 + 50, headers_y))
        self.canvas.blit(lbl_date, (config.WIDTH//2 + 180, headers_y))
        
        # Draw horizontal dividing line
        pygame.draw.line(self.canvas, config.COLOR_BORDER, (config.WIDTH//2 - 250, headers_y + 35), (config.WIDTH//2 + 300, headers_y + 35), 2)
        
        # Render high scores
        scores = self.score_sys.leaderboard
        for idx, entry in enumerate(scores):
            row_y = headers_y + 55 + idx * 45
            
            txt_rank = self.ui_renderer.font_body.render(f"#{idx+1}", True, config.COLOR_TEXT_MUTED)
            txt_name = self.ui_renderer.font_body.render(entry["name"], True, config.COLOR_TEXT_PRIMARY)
            txt_score = self.ui_renderer.font_body.render(str(entry["score"]), True, config.COLOR_TEXT_ACCENT)
            txt_date = self.ui_renderer.font_body.render(entry["date"], True, config.COLOR_TEXT_MUTED)
            
            self.canvas.blit(txt_rank, (config.WIDTH//2 - 240, row_y))
            self.canvas.blit(txt_name, (config.WIDTH//2 - 120, row_y))
            self.canvas.blit(txt_score, (config.WIDTH//2 + 50, row_y))
            self.canvas.blit(txt_date, (config.WIDTH//2 + 180, row_y))
            
        # Draw button
        for btn in self.menu_buttons:
            btn.draw(self.canvas, self.ui_renderer.font_header)

    # =========================================================================
    # STATE: GAME OVER
    # =========================================================================
    
    def _setup_game_over_buttons(self):
        self.menu_buttons = [
            UIButton(config.WIDTH//2 - 150, 420, 300, 50, "PLAY AGAIN", self._btn_play),
            UIButton(config.WIDTH//2 - 150, 490, 300, 50, "QUIT TO MENU", self._btn_quit)
        ]
        
    def _update_game_over(self, dt):
        if not self.entering_name:
            for btn in self.menu_buttons:
                if btn.update(self.curr_pointer_pos, self.is_pinching, dt):
                    break
                    
    def _draw_game_over(self):
        self.ui_renderer.draw_title(self.canvas, "GAME OVER")
        
        # Display Stats
        stats_y = 160
        score_lbl = self.ui_renderer.font_header.render(f"FINAL SCORE: {self.score_sys.score}", True, config.COLOR_TEXT_ACCENT)
        fruits_lbl = self.ui_renderer.font_body.render(f"Fruits Sliced: {self.score_sys.fruits_sliced}", True, config.COLOR_TEXT_PRIMARY)
        combos_lbl = self.ui_renderer.font_body.render(f"Combos Hit: {self.score_sys.combos_sliced}", True, config.COLOR_TEXT_PRIMARY)
        
        sr = score_lbl.get_rect(center=(config.WIDTH//2, stats_y))
        fr = fruits_lbl.get_rect(center=(config.WIDTH//2, stats_y + 40))
        cr = combos_lbl.get_rect(center=(config.WIDTH//2, stats_y + 70))
        
        self.canvas.blit(score_lbl, sr)
        self.canvas.blit(fruits_lbl, fr)
        self.canvas.blit(combos_lbl, cr)
        
        # If qualifying for leaderboard, display text input field
        if self.entering_name:
            prompt_lbl = self.ui_renderer.font_header.render("NEW HIGH SCORE!", True, config.COLOR_TRAIL_PRIMARY)
            pr = prompt_lbl.get_rect(center=(config.WIDTH//2, stats_y + 130))
            self.canvas.blit(prompt_lbl, pr)
            
            sub_prompt = self.ui_renderer.font_body.render("TYPE YOUR INITIALS (KEYBOARD) AND PRESS ENTER:", True, config.COLOR_TEXT_MUTED)
            s_pr = sub_prompt.get_rect(center=(config.WIDTH//2, stats_y + 175))
            self.canvas.blit(sub_prompt, s_pr)
            
            # Input field border
            field_rect = pygame.Rect(config.WIDTH//2 - 150, stats_y + 205, 300, 45)
            pygame.draw.rect(self.canvas, config.COLOR_TRAIL_PRIMARY, field_rect, 2, border_radius=6)
            
            # Cursor blink
            cursor = "|" if int(time.time() * 2) % 2 == 0 else ""
            txt_entry = self.ui_renderer.font_header.render(self.player_name_entry + cursor, True, config.COLOR_TEXT_PRIMARY)
            t_er = txt_entry.get_rect(center=field_rect.center)
            self.canvas.blit(txt_entry, t_er)
        else:
            # Draw buttons
            for btn in self.menu_buttons:
                btn.draw(self.canvas, self.ui_renderer.font_header)

    # =========================================================================
    # TELEMETRY OVERLAY (DEVELOPER MODE)
    # =========================================================================
    
    def _draw_developer_overlay(self):
        """Renders real-time telemetry metrics in the top left corner."""
        # Retrieve memory footprint
        mem_text = "Memory: N/A"
        if _process:
            try:
                mem_mb = _process.memory_info().rss / (1024 * 1024)
                mem_text = f"Memory: {mem_mb:.1f} MB"
            except Exception:
                pass
                
        fps = self.clock.get_fps()
        
        telemetry_lines = [
            "--- METRICS TELEMETRY (F1 to toggle) ---",
            f"FPS: {fps:.1f}",
            f"Frame Time: {self.frame_time:.2f} ms",
            f"Hand Latency: {self.tracking_latency:.1f} ms",
            mem_text,
            f"Active Fruits: {len(self.active_fruits)}",
            f"Active Particles: {len(self.particle_mgr.active_particles)}",
            f"Active Waves: {len(self.active_shockwaves)}",
            f"Fruit Pool Size: {self.fruit_pool.get_free_count()}",
            f"Particle Pool Size: {self.particle_pool.get_free_count()}",
            f"Input Mode: {'Webcam (MediaPipe)' if self.hand_detected else 'Mouse (Fallback)'}"
        ]
        
        overlay_w = 320
        overlay_h = len(telemetry_lines) * 20 + 20
        
        # Transparent background panel
        panel = pygame.Surface((overlay_w, overlay_h), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 180))
        self.canvas.blit(panel, (15, 60))
        
        # Draw text lines
        for idx, line in enumerate(telemetry_lines):
            color = config.COLOR_TRAIL_PRIMARY if idx == 0 else config.COLOR_TEXT_PRIMARY
            if "NO HAND" in line or "Mouse" in line:
                color = (255, 140, 0)
                
            text_surf = self.ui_renderer.font_body.render(line, True, color)
            self.canvas.blit(text_surf, (25, 70 + idx * 20))
