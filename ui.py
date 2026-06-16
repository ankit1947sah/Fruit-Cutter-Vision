import pygame
import numpy as np
import config
from audio import synth

class UIButton:
    """An interactive UI button supporting hover-to-select progress wheels and pinch clicks."""
    
    def __init__(self, x, y, width, height, text, action_callback, hover_duration=1.2):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.action_callback = action_callback
        
        self.hover_timer = 0.0
        self.hover_duration = float(hover_duration)
        self.is_hovered = False
        
    def update(self, pointer_pos, is_pinching, dt):
        """Updates the button's hover state. Returns True if the action is triggered."""
        if pointer_pos is None:
            self.is_hovered = False
            self.hover_timer = 0.0
            return False
            
        px, py = pointer_pos
        was_hovered = self.is_hovered
        self.is_hovered = self.rect.collidepoint(px, py)
        
        if self.is_hovered:
            if not was_hovered:
                synth.play("click")
                
            # Instant trigger on pinch click
            if is_pinching:
                synth.play("click")
                self.hover_timer = 0.0
                self.action_callback()
                return True
                
            # Increment hover progress timer
            self.hover_timer += dt
            if self.hover_timer >= self.hover_duration:
                synth.play("click")
                self.hover_timer = 0.0
                self.action_callback()
                return True
        else:
            self.hover_timer = max(0.0, self.hover_timer - dt * 2.0) # Decay hover timer faster than it fills
            
        return False
        
    def draw(self, surface, font):
        """Renders the button with custom styles and hover fills."""
        # Determine border color based on hover state
        border_color = config.COLOR_TRAIL_PRIMARY if self.is_hovered else config.COLOR_BORDER
        border_width = 3 if self.is_hovered else 2
        
        # Draw background base
        bg_color = config.COLOR_BACKGROUND
        pygame.draw.rect(surface, bg_color, self.rect, border_radius=8)
        
        # Draw semi-transparent hover overlay
        if self.is_hovered:
            overlay = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
            overlay.fill(config.COLOR_BUTTON_HOVER_FILL)
            surface.blit(overlay, self.rect.topleft)
            
        # Draw border
        pygame.draw.rect(surface, border_color, self.rect, border_width, border_radius=8)
        
        # Render text (centered)
        text_surf = font.render(self.text, True, config.COLOR_TEXT_PRIMARY)
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)

class UIRenderer:
    """Handles rendering of HUD, menus, leaderboards, and the webcam calibrator."""
    
    def __init__(self):
        # Cache fonts to avoid reloading
        pygame.font.init()
        self.font_title = pygame.font.SysFont("Outfit, Arial, Helvetica", 56, bold=True)
        self.font_header = pygame.font.SysFont("Outfit, Arial, Helvetica", 36, bold=True)
        self.font_body = pygame.font.SysFont("Outfit, Arial, Helvetica", 24)
        self.font_score = pygame.font.SysFont("monospace", 42, bold=True)
        self.font_hud = pygame.font.SysFont("Outfit, Arial, Helvetica", 30, bold=True)
        self.font_combo = pygame.font.SysFont("Outfit, Arial, Helvetica", 40, bold=True, italic=True)
        
    def draw_hud(self, surface, score, lives, camera_frame, hand_detected, px, py, is_pinching):
        """Renders the player HUD during gameplay."""
        # 1. Draw Score (top left)
        score_label = self.font_hud.render("SCORE:", True, config.COLOR_TEXT_MUTED)
        surface.blit(score_label, (25, 20))
        
        score_val = self.font_score.render(f"{score:04d}", True, config.COLOR_TEXT_ACCENT)
        surface.blit(score_val, (125, 12))
        
        # 2. Draw Lives (three 'X' marks in top right)
        # Red X for lost life, Muted outline for remaining
        start_x = config.WIDTH - 150
        for i in range(config.MAX_LIVES):
            x_pos = start_x + i * 40
            y_pos = 20
            
            # Draw empty box slot first
            pygame.draw.rect(surface, config.COLOR_BORDER, (x_pos, y_pos, 30, 30), 2, border_radius=4)
            
            # Fill with red 'X' if lost
            if i >= lives:
                # Classic Fruit Ninja Red X
                color_x = (220, 20, 60)
                # Left-to-right diagonal
                pygame.draw.line(surface, color_x, (x_pos + 6, y_pos + 6), (x_pos + 24, y_pos + 24), 4)
                # Right-to-left diagonal
                pygame.draw.line(surface, color_x, (x_pos + 24, y_pos + 6), (x_pos + 6, y_pos + 24), 4)
            else:
                # Active life indicator (Green checkmark or small green circle)
                pygame.draw.circle(surface, (46, 139, 87), (x_pos + 15, y_pos + 15), 6)
                
        # 3. Draw Camera mini-calibrator in bottom-right corner
        if camera_frame is not None:
            self._draw_camera_overlay(surface, camera_frame, hand_detected, px, py)
            
    def _draw_camera_overlay(self, surface, frame, hand_detected, px, py):
        """Renders a small webcam view in the bottom right corner with hand indicator."""
        cw, ch = 160, 120
        margin = 15
        ox = config.WIDTH - cw - margin
        oy = config.HEIGHT - ch - margin
        
        try:
            # OpenCV frame is BGR; convert to RGB and swap axes for Pygame surface
            rgb_frame = cv2 = frame.copy() # OpenCV library frame check
            rgb_frame = rgb_frame[:, :, ::-1] # Quick BGR to RGB channel reversal using slicing
            
            # Make pygame surface
            frame_surf = pygame.surfarray.make_surface(rgb_frame.swapaxes(0, 1))
            scaled_surf = pygame.transform.scale(frame_surf, (cw, ch))
            
            # Draw frame
            surface.blit(scaled_surf, (ox, oy))
            
            # Draw thin border around calibrator
            pygame.draw.rect(surface, config.COLOR_BORDER, (ox, oy, cw, ch), 2)
            
            # Draw green/red tracking status label
            status_color = (0, 255, 0) if hand_detected else (255, 0, 0)
            status_text = "TRACKED" if hand_detected else "NO HAND"
            lbl = self.font_body.render(status_text, True, status_color)
            surface.blit(lbl, (ox + 5, oy + ch - 22))
            
            # Draw miniature fingertip dot if detected
            if hand_detected and px is not None and py is not None:
                # Map coordinates from game screen to mini webcam coordinates
                # We need to map X from [0, WIDTH] to [ox, ox + cw]
                # We need to map Y from [0, HEIGHT] to [oy, oy + ch]
                mx = ox + int((px / config.WIDTH) * cw)
                my = oy + int((py / config.HEIGHT) * ch)
                pygame.draw.circle(surface, config.COLOR_TRAIL_PRIMARY, (mx, my), 5)
        except Exception as e:
            # Don't let webcam overlay crash rendering if frame conversions fail
            pass
            
    def draw_progress_wheel(self, surface, pos, progress_factor):
        """Draws a circular progress meter around the fingertip cursor."""
        if pos is None or progress_factor <= 0.0:
            return
            
        x, y = int(pos[0]), int(pos[1])
        radius = 24
        
        # Draw background ring outline
        pygame.draw.circle(surface, (100, 100, 100, 100), (x, y), radius, 2)
        
        # Calculate bounding rect for arc drawing
        rect = pygame.Rect(x - radius, y - radius, radius * 2, radius * 2)
        
        # Draw arc representing selection fill
        start_angle = -np.pi / 2 # Start from top
        end_angle = start_angle + (2.0 * np.pi * progress_factor)
        
        # Draw thick progress arc
        pygame.draw.arc(surface, config.COLOR_TRAIL_PRIMARY, rect, -end_angle, -start_angle, 4)
        
        # Draw small inner reticle dot
        pygame.draw.circle(surface, config.COLOR_TEXT_PRIMARY, (x, y), 3)
        
    def draw_combo_popup(self, surface, combo_details, x, y):
        """Draws a floating combo notification text at the sliced coordinate."""
        count = combo_details["count"]
        bonus = combo_details["bonus"]
        
        txt = f"{count} FRUIT COMBO! +{bonus}"
        
        # Glow effect: draw offset text in cyan, and core text in white
        glow_surf = self.font_combo.render(txt, True, config.COLOR_TRAIL_PRIMARY)
        core_surf = self.font_combo.render(txt, True, config.COLOR_TEXT_ACCENT)
        
        # Draw centered at (x, y)
        gr = glow_surf.get_rect(center=(x, y))
        cr = core_surf.get_rect(center=(x - 2, y - 2))
        
        surface.blit(glow_surf, gr.topleft)
        surface.blit(core_surf, cr.topleft)
        
    def draw_title(self, surface, text, y_offset=80):
        """Helper to draw a styled glowing screen title."""
        glow = self.font_title.render(text, True, config.COLOR_TRAIL_PRIMARY)
        core = self.font_title.render(text, True, config.COLOR_TEXT_PRIMARY)
        
        gr = glow.get_rect(center=(config.WIDTH // 2, y_offset))
        cr = core.get_rect(center=(config.WIDTH // 2 - 2, y_offset - 2))
        
        surface.blit(glow, gr.topleft)
        surface.blit(core, cr.topleft)
