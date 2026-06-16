import pygame
import random
import numpy as np
import config

class TrailSegment:
    """A single segment point along the blade's sweeping path."""
    
    def __init__(self, x=0.0, y=0.0):
        self.x = float(x)
        self.y = float(y)
        self.age = 0.0
        
    def reset(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.age = 0.0

class BladeTrail:
    """Manages index finger trailing lines and renders a glowing, tapered ribbon."""
    
    def __init__(self, trail_pool):
        self.pool = trail_pool
        self.points = []
        self.max_age = 0.25 # seconds before trail segments fade completely
        
    def add_point(self, x, y):
        """Adds a new coordinate to the trail. Reuses from pool."""
        # Avoid duplication if the coordinate hasn't moved
        if self.points and self.points[-1].x == x and self.points[-1].y == y:
            return
            
        segment = self.pool.acquire(x, y)
        self.points.append(segment)
        
        # Limit size
        if len(self.points) > config.TRAIL_MAX_POINTS:
            removed = self.points.pop(0)
            self.pool.release(removed)
            
    def update(self, dt):
        """Ages existing points and removes expired segments."""
        still_active = []
        for pt in self.points:
            pt.age += dt
            if pt.age < self.max_age:
                still_active.append(pt)
            else:
                self.pool.release(pt)
        self.points = still_active
        
    def draw(self, surface):
        """Draws a smooth glowing tapered trail on the surface."""
        n = len(self.points)
        if n < 2:
            return
            
        # Draw a glowing neon trail by drawing connected lines with varying widths
        for i in range(n - 1):
            p1 = (int(self.points[i].x), int(self.points[i].y))
            p2 = (int(self.points[i+1].x), int(self.points[i+1].y))
            
            # Progress factor from 0.0 (oldest) to 1.0 (newest)
            t_factor = i / (n - 1)
            
            # Taper width
            width = int(config.TRAIL_MIN_WIDTH + (config.TRAIL_MAX_WIDTH - config.TRAIL_MIN_WIDTH) * t_factor)
            width = max(1, width)
            
            # Fade alpha
            alpha = int(t_factor * 255)
            
            # Interpolate color from primary (cyan) to secondary (magenta/purple)
            # Older points are purple, newer are cyan
            c_cyan = config.COLOR_TRAIL_PRIMARY
            c_purple = config.COLOR_TRAIL_SECONDARY
            
            r = int(c_purple[0] + (c_cyan[0] - c_purple[0]) * t_factor)
            g = int(c_purple[1] + (c_cyan[1] - c_purple[1]) * t_factor)
            b = int(c_purple[2] + (c_cyan[2] - c_purple[2]) * t_factor)
            
            # Draw thin outer glow line and thick inner core line
            glow_rgba = (r, g, b, alpha)
            core_rgba = (255, 255, 255, alpha) # White hot core
            
            try:
                # Outer glowing envelope line
                pygame.draw.line(surface, glow_rgba, p1, p2, width + 4)
                # Inner hot core line
                pygame.draw.line(surface, core_rgba, p1, p2, max(1, width // 2))
            except Exception:
                # Fallback to simple RGB line if alpha blend fails
                pygame.draw.line(surface, (r, g, b), p1, p2, width)
                
    def clear(self):
        """Resets the trail and returns all points to the pool."""
        for pt in self.points:
            self.pool.release(pt)
        self.points.clear()

class ScreenShake:
    """Generates random viewport offsets to simulate impact shakes."""
    
    def __init__(self):
        self.timer = 0.0
        self.intensity = 0
        
    def trigger(self, duration=config.SCREEN_SHAKE_DURATION, intensity=config.SCREEN_SHAKE_INTENSITY):
        """Starts a screen shake event."""
        self.timer = duration
        self.intensity = intensity
        
    def update(self, dt):
        """Decrements the timer."""
        if self.timer > 0.0:
            self.timer -= dt
            if self.timer <= 0.0:
                self.timer = 0.0
                
    def get_offset(self):
        """Returns the current frame translation offset as (dx, dy)."""
        if self.timer > 0.0:
            dx = random.randint(-self.intensity, self.intensity)
            dy = random.randint(-self.intensity, self.intensity)
            return dx, dy
        return 0, 0

class SlowMotion:
    """Manages slow-motion timing modifiers applied to game update steps."""
    
    def __init__(self):
        self.timer = 0.0
        self.factor = 1.0
        
    def trigger(self, duration=config.SLOW_MOTION_DURATION, factor=config.SLOW_MOTION_FACTOR):
        """Starts a slow-motion period."""
        self.timer = duration
        self.factor = factor
        
    def update(self, dt):
        """Updates remaining duration. Note: updates are done in real-time dt."""
        if self.timer > 0.0:
            # We decrement the timer using the real delta time, not the scaled one
            self.timer -= dt
            if self.timer <= 0.0:
                self.timer = 0.0
                self.factor = 1.0
                
    def get_dt_modifier(self):
        """Returns the speed modifier to scale dt."""
        if self.timer > 0.0:
            return self.factor
        return 1.0

class Shockwave:
    """An expanding ring ripple centered on slice events."""
    
    def __init__(self, x=0.0, y=0.0, max_radius=80.0, color=(255, 255, 255)):
        self.x = float(x)
        self.y = float(y)
        self.radius = 5.0
        self.max_radius = max_radius
        self.color = color
        self.life = 0.25 # seconds duration
        self.max_life = 0.25
        self.active = False
        
    def reset(self, x, y, max_radius, color):
        self.x = float(x)
        self.y = float(y)
        self.radius = 5.0
        self.max_radius = max_radius
        self.color = color
        self.life = 0.25
        self.max_life = 0.25
        self.active = True
        
    def update(self, dt):
        """Expands radius and ages lifetime."""
        if not self.active:
            return
            
        self.life -= dt
        if self.life <= 0.0:
            self.active = False
            return
            
        pct = 1.0 - (self.life / self.max_life) # 0.0 to 1.0
        self.radius = 5.0 + (self.max_radius - 5.0) * pct
        
    def draw(self, surface):
        """Draws the ring with expanding fade."""
        if not self.active:
            return
            
        pct_life = max(0.0, min(1.0, self.life / self.max_life))
        alpha = int(pct_life * 200)
        
        rgba = (self.color[0], self.color[1], self.color[2], alpha)
        width = max(1, int(4 * pct_life))
        
        try:
            pygame.draw.circle(surface, rgba, (int(self.x), int(self.y)), int(self.radius), width)
        except Exception:
            pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), int(self.radius), width)
