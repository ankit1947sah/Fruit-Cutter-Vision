import pygame
import random
import numpy as np
import config

class Particle:
    """Represents a single visual particle (juice drop, spark, or wood seed)."""
    
    def __init__(self):
        self.x = 0.0
        self.y = 0.0
        self.vx = 0.0
        self.vy = 0.0
        self.color = (255, 255, 255)
        self.radius = 4.0
        self.life = 0.0
        self.max_life = 1.0
        self.gravity = config.GRAVITY
        self.particle_type = "juice"
        self.active = False
        
    def reset(self, x, y, vx, vy, color, radius, life, gravity, particle_type):
        """Re-initializes the particle state for recycling in the object pool."""
        self.x = float(x)
        self.y = float(y)
        self.vx = float(vx)
        self.vy = float(vy)
        self.color = color
        self.radius = float(radius)
        self.life = float(life)
        self.max_life = float(life)
        self.gravity = float(gravity)
        self.particle_type = particle_type
        self.active = True
        
    def update(self, dt):
        """Updates particle coordinates and lifetime."""
        if not self.active:
            return
            
        # Apply gravity (except for sparks which can float or drift randomly)
        if self.particle_type != "spark":
            self.vy += self.gravity * dt
            
        # Update positions
        self.x += self.vx * dt
        self.y += self.vy * dt
        
        # Diminish lifetime
        self.life -= dt
        if self.life <= 0.0:
            self.active = False
            
    def draw(self, surface):
        """Draws the particle with a fading alpha channel based on remaining life."""
        if not self.active:
            return
            
        # Calculate fade out alpha (0 to 255)
        pct = max(0.0, min(1.0, self.life / self.max_life))
        alpha = int(pct * 255)
        
        # Color with alpha
        rgba_color = (self.color[0], self.color[1], self.color[2], alpha)
        
        # In Pygame CE, we can draw transparent circles directly onto surfaces
        # We handle boundary clipping to avoid drawing out of bounds
        try:
            # Drawing a small circle
            pygame.draw.circle(surface, rgba_color, (int(self.x), int(self.y)), int(self.radius))
        except Exception:
            # Fallback to drawing a simple non-alpha rectangle or circle if Pygame fails
            pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), int(self.radius))

class ParticleManager:
    """Manages active particles, spawns groups of particles, and handles pooling."""
    
    def __init__(self, particle_pool):
        self.pool = particle_pool
        self.active_particles = []
        
    def update(self, dt):
        """Updates all active particles and releases dead ones back to the pool."""
        still_active = []
        for p in self.active_particles:
            p.update(dt)
            if p.active:
                still_active.append(p)
            else:
                self.pool.release(p)
        self.active_particles = still_active
        
    def draw(self, surface):
        """Draws all active particles on the screen."""
        for p in self.active_particles:
            p.draw(surface)
            
    def spawn_juice_splash(self, x, y, color, slice_angle, count=15):
        """Spawns juice splatter particles sprayed along perpendicular cut axes."""
        if len(self.active_particles) >= config.PARTICLE_LIMIT:
            return
            
        # Calculate perpendicular directions
        angles = [slice_angle - np.pi/2, slice_angle + np.pi/2]
        
        for _ in range(count):
            # Select randomly between the two perpendicular directions
            base_angle = random.choice(angles)
            # Add some variance to direction
            angle = base_angle + random.uniform(-0.4, 0.4)
            
            # Velocity and life parameters
            speed = random.uniform(150.0, 450.0)
            vx = np.cos(angle) * speed
            vy = np.sin(angle) * speed - random.uniform(50.0, 150.0) # Upward bias
            
            life = random.uniform(0.3, 0.8)
            radius = random.uniform(2.5, 6.0)
            
            # Vary juice colors slightly for visual depth
            c_var = random.randint(-15, 15)
            r = max(0, min(255, color[0] + c_var))
            g = max(0, min(255, color[1] + c_var))
            b = max(0, min(255, color[2] + c_var))
            
            # Acquire from pool
            p = self.pool.acquire(
                x, y, vx, vy, (r, g, b), radius, life, config.GRAVITY * 0.8, "juice"
            )
            self.active_particles.append(p)
            
    def spawn_seeds(self, x, y, count=4):
        """Spawns dark seeds that drop downward from sliced fruits."""
        for _ in range(count):
            angle = random.uniform(0, 2.0 * np.pi)
            speed = random.uniform(80.0, 200.0)
            vx = np.cos(angle) * speed
            vy = np.sin(angle) * speed - 50.0 # Some upward arc
            
            life = random.uniform(0.5, 1.0)
            radius = random.uniform(2.0, 3.0)
            color = (30, 30, 30) # Dark seed color
            
            p = self.pool.acquire(x, y, vx, vy, color, radius, life, config.GRAVITY, "seed")
            self.active_particles.append(p)
            
    def spawn_bomb_explosion(self, x, y, count=60):
        """Spawns massive fire, spark, and dark smoke cloud particles on bomb explosion."""
        for _ in range(count):
            angle = random.uniform(0, 2.0 * np.pi)
            speed = random.uniform(100.0, 600.0)
            vx = np.cos(angle) * speed
            vy = np.sin(angle) * speed
            
            # Mix sparks (orange-red) and smoke (dark grey)
            is_spark = random.random() > 0.4
            if is_spark:
                color = (255, random.randint(50, 180), 0)
                radius = random.uniform(3.0, 8.0)
                life = random.uniform(0.2, 0.6)
                gravity = 0.0 # Sparks float or experience low friction
                p_type = "spark"
            else:
                gray = random.randint(30, 70)
                color = (gray, gray, gray)
                radius = random.uniform(10.0, 25.0)
                life = random.uniform(0.5, 1.2)
                gravity = -100.0 # Smoke drifts slightly upwards
                p_type = "fume"
                # Slow down smoke velocity
                vx *= 0.5
                vy *= 0.5
                
            p = self.pool.acquire(x, y, vx, vy, color, radius, life, gravity, p_type)
            self.active_particles.append(p)
            
    def clear(self):
        """Releases all active particles back to the pool."""
        for p in self.active_particles:
            self.pool.release(p)
        self.active_particles.clear()
