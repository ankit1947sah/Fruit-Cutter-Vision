import config

class PhysicsState:
    """Manages kinematic state (position, velocity, acceleration, rotation) for 2D arcade physics."""
    
    def __init__(self, x=0.0, y=0.0, vx=0.0, vy=0.0, ax=0.0, ay=config.GRAVITY, angle=0.0, angular_velocity=0.0):
        self.x = float(x)
        self.y = float(y)
        self.vx = float(vx)
        self.vy = float(vy)
        self.ax = float(ax)
        self.ay = float(ay)
        self.angle = float(angle)
        self.angular_velocity = float(angular_velocity)
        
    def reset(self, x=0.0, y=0.0, vx=0.0, vy=0.0, ax=0.0, ay=config.GRAVITY, angle=0.0, angular_velocity=0.0):
        """Resets the state, useful for object pooling."""
        self.x = float(x)
        self.y = float(y)
        self.vx = float(vx)
        self.vy = float(vy)
        self.ax = float(ax)
        self.ay = float(ay)
        self.angle = float(angle)
        self.angular_velocity = float(angular_velocity)
        
    def update(self, dt):
        """Updates position, velocity, and rotation using semi-implicit Euler integration."""
        # Update velocities
        self.vx += self.ax * dt
        self.vy += self.ay * dt
        
        # Update positions
        self.x += self.vx * dt
        self.y += self.vy * dt
        
        # Update rotation
        self.angle += self.angular_velocity * dt
        
        # Keep angle within [0, 360) range
        self.angle = self.angle % 360.0
        
    def apply_force(self, fx, fy):
        """Applies an instantaneous impulse force by modifying velocity."""
        self.vx += float(fx)
        self.vy += float(fy)
        
    def get_pos(self):
        """Returns the position as an (x, y) tuple."""
        return self.x, self.y
        
    def get_velocity(self):
        """Returns the velocity as a (vx, vy) tuple."""
        return self.vx, self.vy
