import pygame
import numpy as np
import config
from physics import PhysicsState
from logger import log
from audio import synth

# Global dictionary to store pre-rendered fruit surfaces
# Structure: { fruit_type: { "whole": Surface, "left": Surface, "right": Surface } }
FRUIT_SURFACES = {}

def initialize_procedural_fruits():
    """Generates and caches all procedural fruit surfaces.
    
    This is called during the Loading state to avoid runtime allocations.
    """
    global FRUIT_SURFACES
    FRUIT_SURFACES.clear()
    
    log.info("Generating procedural fruit surfaces...")
    
    for name, data in config.FRUIT_COLORS.items():
        radius = data["radius"]
        size = 120 # Standard size for all fruit canvas surfaces
        center = (size // 2, size // 2)
        
        # Create transparent canvas for the whole fruit
        whole_surf = pygame.Surface((size, size), pygame.SRCALPHA)
        
        # Draw specific fruit graphics
        if name == "watermelon":
            # Outer rind (dark green)
            pygame.draw.circle(whole_surf, data["outer"], center, radius)
            # Inner rind (light green)
            pygame.draw.circle(whole_surf, (144, 238, 144), center, radius - 3)
            pygame.draw.circle(whole_surf, data["outer"], center, radius - 6)
            # Pulp (crimson red)
            pygame.draw.circle(whole_surf, data["inner"], center, radius - 8)
            # Seeds
            seed_color = data["seed"]
            seed_offsets = [
                (12, 10), (-15, -12), (18, -15), (-10, 18), 
                (0, -20), (22, 5), (-20, 2), (5, 20)
            ]
            for dx, dy in seed_offsets:
                # Scale offsets relative to radius
                sx = int(center[0] + dx * (radius / 55))
                sy = int(center[1] + dy * (radius / 55))
                pygame.draw.circle(whole_surf, seed_color, (sx, sy), 3)
                
        elif name == "apple":
            # Draw apple body (two overlapping red circles for organic heart shape)
            r_body = radius - 4
            pygame.draw.circle(whole_surf, data["outer"], (center[0] - 6, center[1] + 2), r_body)
            pygame.draw.circle(whole_surf, data["outer"], (center[0] + 6, center[1] + 2), r_body)
            # Indent cover
            pygame.draw.circle(whole_surf, data["outer"], (center[0], center[1] + 12), r_body - 4)
            # Interior flesh (drawn so cross section shows creamy white)
            pygame.draw.circle(whole_surf, data["inner"], center, r_body - 12)
            # Core/Seed area
            pygame.draw.circle(whole_surf, (139, 69, 19), center, 4)
            # Leaf and Stem
            stem_color = data["stem"]
            pygame.draw.line(whole_surf, stem_color, center, (center[0] + 2, center[1] - r_body - 4), 3)
            # Leaf
            leaf_surf = pygame.Surface((20, 12), pygame.SRCALPHA)
            pygame.draw.ellipse(leaf_surf, (34, 139, 34), (0, 0, 20, 12))
            leaf_rotated = pygame.transform.rotate(leaf_surf, 35)
            whole_surf.blit(leaf_rotated, (center[0] + 2, center[1] - r_body - 12))
            
        elif name == "banana":
            # Draw curved yellow banana using overlapping circles
            num_circles = 8
            for i in range(num_circles):
                # Calculate coordinates along an arc
                theta = -np.pi/3.5 + (i / (num_circles - 1)) * (2.0 * np.pi/3.5)
                bx = int(center[0] + 20 * np.cos(theta))
                by = int(center[1] + 20 * np.sin(theta))
                
                # Outer peel
                r_step = radius - 15 - abs(i - num_circles/2) * 1.5
                pygame.draw.circle(whole_surf, data["outer"], (bx, by), int(r_step))
                # Inner pulp
                pygame.draw.circle(whole_surf, data["inner"], (bx, by), int(r_step - 3))
                
            # Tips
            t1_x = int(center[0] + 20 * np.cos(-np.pi/3.5))
            t1_y = int(center[1] + 20 * np.sin(-np.pi/3.5))
            pygame.draw.circle(whole_surf, data["tip"], (t1_x, t1_y), 4)
            
            t2_x = int(center[0] + 20 * np.cos(np.pi/3.5))
            t2_y = int(center[1] + 20 * np.sin(np.pi/3.5))
            pygame.draw.circle(whole_surf, data["tip"], (t2_x, t2_y), 4)
            
        elif name == "orange":
            # Outer skin
            pygame.draw.circle(whole_surf, data["outer"], center, radius)
            # White rind
            pygame.draw.circle(whole_surf, data["center"], center, radius - 4)
            # Pulp outer
            pygame.draw.circle(whole_surf, data["inner"], center, radius - 6)
            # Core
            pygame.draw.circle(whole_surf, data["center"], center, 5)
            # Radial wedges
            for i in range(8):
                angle = i * (np.pi / 4)
                ex = int(center[0] + (radius - 7) * np.cos(angle))
                ey = int(center[1] + (radius - 7) * np.sin(angle))
                pygame.draw.line(whole_surf, data["center"], center, (ex, ey), 2)
                
        elif name == "pineapple":
            # Leafy crown first (drawn behind the body)
            crown_color = data["crown"]
            for i in range(5):
                angle_offset = (i - 2) * 20 # degrees
                crown_leaf = pygame.Surface((18, 40), pygame.SRCALPHA)
                pygame.draw.polygon(crown_leaf, crown_color, [(9, 0), (0, 40), (18, 40)])
                crown_rotated = pygame.transform.rotate(crown_leaf, angle_offset)
                whole_surf.blit(crown_rotated, (center[0] - crown_rotated.get_width()//2, center[1] - radius - 15))
                
            # Golden brown body (ellipse)
            body_w = int(radius * 1.6)
            body_h = int(radius * 2.0)
            body_rect = (center[0] - body_w//2, center[1] - body_h//2 + 5, body_w, body_h)
            pygame.draw.ellipse(whole_surf, data["outer"], body_rect)
            # Inner yellow body
            pygame.draw.ellipse(whole_surf, data["inner"], (body_rect[0] + 5, body_rect[1] + 5, body_w - 10, body_h - 10))
            
            # Cross hatching pattern
            hatch_surf = pygame.Surface((size, size), pygame.SRCALPHA)
            hatch_color = (139, 90, 0, 100) # Semi-transparent dark gold
            # We draw diagonal lines and clip them to the body
            for d in range(-60, 60, 12):
                pygame.draw.line(hatch_surf, hatch_color, (0, 60 + d), (120, 60 + d + 60), 2)
                pygame.draw.line(hatch_surf, hatch_color, (0, 60 + d), (120, 60 + d - 60), 2)
            # Blit with masking
            whole_surf.blit(hatch_surf, (0, 0))
            
        elif name == "strawberry":
            # Draw strawberry body (teardrop/heart shape using overlapping circles)
            pygame.draw.circle(whole_surf, data["outer"], (center[0], center[1] + 5), radius)
            pygame.draw.circle(whole_surf, data["outer"], (center[0] - 8, center[1] - 5), radius - 8)
            pygame.draw.circle(whole_surf, data["outer"], (center[0] + 8, center[1] - 5), radius - 8)
            # Inner flesh visible as cross-section
            pygame.draw.circle(whole_surf, data["inner"], center, radius - 10)
            # Seeds scattered on the surface
            seed_offsets = [
                (-12, -8), (10, -10), (-8, 10), (14, 6), (0, -16),
                (-15, 3), (12, -3), (-5, 15), (8, 14), (0, 5)
            ]
            for dx, dy in seed_offsets:
                sx = int(center[0] + dx * (radius / 38))
                sy = int(center[1] + dy * (radius / 38))
                pygame.draw.circle(whole_surf, data["seed"], (sx, sy), 2)
            # Green leaf crown at top
            leaf_color = data["leaf"]
            leaf_pts = [
                (center[0] - 15, center[1] - radius + 5),
                (center[0], center[1] - radius - 10),
                (center[0] + 15, center[1] - radius + 5)
            ]
            pygame.draw.polygon(whole_surf, leaf_color, leaf_pts)
            # Small stem
            pygame.draw.line(whole_surf, (80, 50, 20), (center[0], center[1] - radius - 10), (center[0], center[1] - radius - 16), 3)

        elif name == "mango":
            # Mango body (oval/kidney shape)
            body_w = int(radius * 1.8)
            body_h = int(radius * 1.4)
            body_rect = (center[0] - body_w // 2, center[1] - body_h // 2, body_w, body_h)
            pygame.draw.ellipse(whole_surf, data["outer"], body_rect)
            # Red blush on upper-left
            blush_surf = pygame.Surface((size, size), pygame.SRCALPHA)
            pygame.draw.circle(blush_surf, (*data["blush"], 120), (center[0] - 10, center[1] - 10), radius // 2)
            whole_surf.blit(blush_surf, (0, 0))
            # Inner pulp cross-section
            pygame.draw.ellipse(whole_surf, data["inner"], (body_rect[0] + 10, body_rect[1] + 10, body_w - 20, body_h - 20))
            # Large flat seed/pit in center
            pygame.draw.ellipse(whole_surf, (200, 180, 120), (center[0] - 12, center[1] - 6, 24, 12))

        elif name == "kiwi":
            # Brown fuzzy outer skin
            pygame.draw.circle(whole_surf, data["outer"], center, radius)
            # Bright green flesh
            pygame.draw.circle(whole_surf, data["inner"], center, radius - 4)
            # Pale white core center
            pygame.draw.circle(whole_surf, data["center"], center, 6)
            # Radiating seed lines from core
            num_seeds = 12
            for i in range(num_seeds):
                angle = i * (2.0 * np.pi / num_seeds)
                # Draw a line of tiny seeds along each radial
                for d in range(8, radius - 6, 5):
                    sx = int(center[0] + d * np.cos(angle))
                    sy = int(center[1] + d * np.sin(angle))
                    pygame.draw.circle(whole_surf, data["seed"], (sx, sy), 1)

        elif name == "peach":
            # Peach body (round with a slight cleft)
            pygame.draw.circle(whole_surf, data["outer"], center, radius)
            # Pink blush on upper area
            blush_surf = pygame.Surface((size, size), pygame.SRCALPHA)
            pygame.draw.circle(blush_surf, (*data["blush"], 100), (center[0] + 5, center[1] - 10), radius // 2)
            whole_surf.blit(blush_surf, (0, 0))
            # Inner flesh
            pygame.draw.circle(whole_surf, data["inner"], center, radius - 8)
            # Brown pit at center
            pygame.draw.circle(whole_surf, data["pit"], center, 10)
            # Cleft line (vertical crease)
            pygame.draw.line(whole_surf, data["blush"], (center[0], center[1] - radius + 2), (center[0], center[1] + radius - 2), 2)

        elif name == "pear":
            # Pear body (gourd shape: smaller circle on top, larger on bottom)
            # Bottom bulge
            pygame.draw.circle(whole_surf, data["outer"], (center[0], center[1] + 10), radius - 5)
            # Upper narrower section
            pygame.draw.circle(whole_surf, data["outer"], (center[0], center[1] - 12), radius - 16)
            # Smooth transition fill
            pygame.draw.rect(whole_surf, data["outer"], (center[0] - (radius - 16), center[1] - 12, (radius - 16) * 2, 22))
            # Inner flesh
            pygame.draw.circle(whole_surf, data["inner"], (center[0], center[1] + 8), radius - 14)
            # Small seed
            pygame.draw.circle(whole_surf, (80, 50, 20), (center[0], center[1] + 5), 3)
            # Stem
            stem_color = data["stem"]
            pygame.draw.line(whole_surf, stem_color, (center[0], center[1] - radius + 8), (center[0] + 3, center[1] - radius - 6), 3)

        elif name == "grapes":
            # Draw a cluster of overlapping grape spheres
            grape_r = radius // 3
            offsets = [
                (0, -grape_r * 2), (-grape_r, -grape_r), (grape_r, -grape_r),
                (-grape_r * 2, 0), (0, 0), (grape_r * 2, 0),
                (-grape_r, grape_r), (grape_r, grape_r), (0, grape_r * 2)
            ]
            for ox, oy in offsets:
                gx = center[0] + ox
                gy = center[1] + oy
                pygame.draw.circle(whole_surf, data["outer"], (gx, gy), grape_r + 2)
                # Glossy highlight on each grape
                pygame.draw.circle(whole_surf, data["highlight"], (gx - 3, gy - 3), grape_r // 2)
            # Stem at top
            pygame.draw.line(whole_surf, (80, 50, 20), (center[0], center[1] - grape_r * 2), (center[0] + 5, center[1] - grape_r * 3), 3)
            # Small leaf
            leaf_surf = pygame.Surface((16, 10), pygame.SRCALPHA)
            pygame.draw.ellipse(leaf_surf, (34, 139, 34), (0, 0, 16, 10))
            whole_surf.blit(leaf_surf, (center[0] + 4, center[1] - grape_r * 3 - 4))

        elif name == "cherry":
            # Draw two cherries side by side
            cherry_r = radius
            c1 = (center[0] - cherry_r // 2 - 2, center[1] + 4)
            c2 = (center[0] + cherry_r // 2 + 2, center[1] + 4)
            # Cherry bodies
            pygame.draw.circle(whole_surf, data["outer"], c1, cherry_r)
            pygame.draw.circle(whole_surf, data["outer"], c2, cherry_r)
            # Glossy highlights
            pygame.draw.circle(whole_surf, data["highlight"], (c1[0] - 4, c1[1] - 5), cherry_r // 3)
            pygame.draw.circle(whole_surf, data["highlight"], (c2[0] - 4, c2[1] - 5), cherry_r // 3)
            # Inner flesh
            pygame.draw.circle(whole_surf, data["inner"], c1, cherry_r - 6)
            pygame.draw.circle(whole_surf, data["inner"], c2, cherry_r - 6)
            # Stems meeting at top
            stem_top = (center[0], center[1] - cherry_r - 10)
            stem_color = data["stem"]
            pygame.draw.line(whole_surf, stem_color, c1, stem_top, 2)
            pygame.draw.line(whole_surf, stem_color, c2, stem_top, 2)

        elif name == "coconut":
            # Brown hairy outer shell
            pygame.draw.circle(whole_surf, data["outer"], center, radius)
            # Lighter husk ring
            pygame.draw.circle(whole_surf, data["husk"], center, radius - 3)
            pygame.draw.circle(whole_surf, data["outer"], center, radius - 6)
            # White coconut meat (cross-section)
            pygame.draw.circle(whole_surf, data["inner"], center, radius - 10)
            # Hollow water center
            pygame.draw.circle(whole_surf, (220, 235, 245), center, radius - 20)
            # Three characteristic "eyes" on outer shell
            eye_offsets = [(-12, -radius + 18), (12, -radius + 18), (0, -radius + 26)]
            for ex, ey in eye_offsets:
                pygame.draw.circle(whole_surf, (60, 40, 20), (center[0] + ex, center[1] + ey), 5)
                pygame.draw.circle(whole_surf, (40, 25, 10), (center[0] + ex, center[1] + ey), 3)

        elif name == "lemon":
            # Lemon body (elongated ellipse with pointed tips)
            body_w = int(radius * 2.0)
            body_h = int(radius * 1.4)
            body_rect = (center[0] - body_w // 2, center[1] - body_h // 2, body_w, body_h)
            pygame.draw.ellipse(whole_surf, data["outer"], body_rect)
            # Inner pale pulp
            pygame.draw.ellipse(whole_surf, data["inner"], (body_rect[0] + 6, body_rect[1] + 6, body_w - 12, body_h - 12))
            # Pointed tips
            tip_color = data["tip"]
            # Left tip
            pygame.draw.polygon(whole_surf, tip_color, [
                (center[0] - body_w // 2 - 6, center[1]),
                (center[0] - body_w // 2 + 6, center[1] - 6),
                (center[0] - body_w // 2 + 6, center[1] + 6)
            ])
            # Right tip
            pygame.draw.polygon(whole_surf, tip_color, [
                (center[0] + body_w // 2 + 6, center[1]),
                (center[0] + body_w // 2 - 6, center[1] - 6),
                (center[0] + body_w // 2 - 6, center[1] + 6)
            ])
            # Radial wedge segments
            for i in range(6):
                angle = i * (np.pi / 3)
                ex = int(center[0] + (radius - 8) * np.cos(angle))
                ey = int(center[1] + (radius - 12) * np.sin(angle))
                pygame.draw.line(whole_surf, data["outer"], center, (ex, ey), 1)

        elif name == "blueberry":
            # Small round blueberry
            pygame.draw.circle(whole_surf, data["outer"], center, radius)
            # Subtle highlight
            pygame.draw.circle(whole_surf, data["highlight"], (center[0] - 4, center[1] - 5), radius // 2)
            # Inner pulp
            pygame.draw.circle(whole_surf, data["inner"], center, radius - 5)
            # Crown ring (calyx) at top
            crown_color = data["crown"]
            crown_y = center[1] - radius + 4
            pygame.draw.circle(whole_surf, crown_color, (center[0], crown_y), 8, 2)
            # Small star pattern inside crown
            for i in range(5):
                angle = i * (2 * np.pi / 5) - np.pi / 2
                px = int(center[0] + 5 * np.cos(angle))
                py = int(crown_y + 5 * np.sin(angle))
                pygame.draw.line(whole_surf, crown_color, (center[0], crown_y), (px, py), 1)

        elif name == "bomb":
            # Bomb body
            pygame.draw.circle(whole_surf, data["body"], center, radius)
            # 3D Highlight reflection
            pygame.draw.circle(whole_surf, (80, 80, 90), (center[0] - radius//3, center[1] - radius//3), radius//3)
            # Fuse connector
            pygame.draw.rect(whole_surf, (60, 60, 60), (center[0] - 6, center[1] - radius - 3, 12, 6))
            # Fuse thread (curved brown line)
            fuse_pts = [
                (center[0], center[1] - radius),
                (center[0] + 10, center[1] - radius - 15),
                (center[0] + 25, center[1] - radius - 20)
            ]
            pygame.draw.lines(whole_surf, data["fuse"], False, fuse_pts, 3)
            
        # Create Left and Right Halves by splitting the whole surface
        # Left half has the right side cleared; Right half has the left side cleared
        left_surf = whole_surf.copy()
        right_surf = whole_surf.copy()
        
        # Clear right side of left surface (setting to transparent)
        # Using a rect filling with (0,0,0,0) and special blend mode
        clear_rect_l = pygame.Rect(size // 2, 0, size // 2, size)
        left_surf.fill((0, 0, 0, 0), clear_rect_l, pygame.BLEND_RGBA_MIN)
        
        # Clear left side of right surface
        clear_rect_r = pygame.Rect(0, 0, size // 2, size)
        right_surf.fill((0, 0, 0, 0), clear_rect_r, pygame.BLEND_RGBA_MIN)
        
        # Store in cached dictionary
        FRUIT_SURFACES[name] = {
            "whole": whole_surf,
            "left": left_surf,
            "right": right_surf
        }
        
    log.info("Cached %d procedural fruit surfaces successfully.", len(FRUIT_SURFACES))

class FruitHalf:
    """Represents one of the halves of a sliced fruit flying apart."""
    
    def __init__(self):
        self.physics = PhysicsState()
        self.active = False
        self.side = "left" # "left" or "right"
        self.fruit_type = "watermelon"
        
    def reset(self, fruit_type, side, x, y, vx, vy, angular_velocity):
        """Initializes a half-fruit's kinematic state."""
        self.fruit_type = fruit_type
        self.side = side
        self.physics.reset(x, y, vx, vy, angular_velocity=angular_velocity)
        self.active = True
        
    def update(self, dt):
        """Updates physics and checks if offscreen."""
        if not self.active:
            return
        self.physics.update(dt)
        # Deactivate if it falls below the screen height
        if self.physics.y > config.HEIGHT + 80:
            self.active = False
            
    def draw(self, surface):
        """Draws the pre-rendered half-fruit rotated dynamically."""
        if not self.active:
            return
            
        # Fetch the static half surface
        half_img = FRUIT_SURFACES[self.fruit_type][self.side]
        
        # Rotate around the center pivot
        rotated_img = pygame.transform.rotate(half_img, self.physics.angle)
        rect = rotated_img.get_rect(center=(int(self.physics.x), int(self.physics.y)))
        
        # Draw onto the target screen surface
        surface.blit(rotated_img, rect.topleft)

class Fruit:
    """Represents a whole fruit or bomb object launched onto the screen."""
    
    def __init__(self):
        self.physics = PhysicsState()
        self.active = False
        self.fruit_type = "watermelon"
        self.radius = 50
        self.state = "whole" # "whole" or "sliced"
        
        # Pre-allocate two sub-halves to avoid allocations at slice time
        self.half_left = FruitHalf()
        self.half_right = FruitHalf()
        
        # Slice metadata
        self.slice_angle = 0.0
        self.sliced_time = 0.0
        
    def reset(self, fruit_type, x, y, vx, vy, angular_velocity):
        """Re-initializes the object, allowing reuse in object pools."""
        self.fruit_type = fruit_type
        self.radius = config.FRUIT_COLORS[fruit_type]["radius"]
        self.physics.reset(x, y, vx, vy, angular_velocity=angular_velocity)
        self.state = "whole"
        self.active = True
        self.half_left.active = False
        self.half_right.active = False
        self.slice_angle = 0.0
        self.sliced_time = 0.0
        
    def update(self, dt):
        """Updates whole physics or child half-fruit physics."""
        if not self.active:
            return
            
        if self.state == "whole":
            self.physics.update(dt)
            # Deactivate if falls off screen (below bottom, or too far left/right)
            if self.physics.y > config.HEIGHT + 100:
                self.active = False
        else:
            # Update both halves
            self.half_left.update(dt)
            self.half_right.update(dt)
            
            # Deactivate root fruit when both halves have fallen offscreen
            if not self.half_left.active and not self.half_right.active:
                self.active = False
                
    def slice(self, slice_details):
        """Transitions whole fruit to sliced halves, applying push impulses."""
        if self.state != "whole" or not self.active:
            return
            
        self.state = "sliced"
        self.slice_angle = slice_details["angle"]
        
        # Determine push forces
        pv1 = slice_details["push_vector_1"]
        pv2 = slice_details["push_vector_2"]
        
        # Inherit base velocities and add perpendicular slice impulses
        v1x = self.physics.vx + pv1[0]
        v1y = self.physics.vy + pv1[1]
        v2x = self.physics.vx + pv2[0]
        v2y = self.physics.vy + pv2[1]
        
        # Set opposing rotational rates for dramatic split animation
        rot_rate_1 = -self.physics.angular_velocity * 1.5 - 90.0
        rot_rate_2 = self.physics.angular_velocity * 1.5 + 90.0
        
        # Initialize the pooled halves
        # Left half inherits the left visual surface, right half inherits right
        self.half_left.reset(self.fruit_type, "left", self.physics.x, self.physics.y, v1x, v1y, rot_rate_1)
        self.half_right.reset(self.fruit_type, "right", self.physics.x, self.physics.y, v2x, v2y, rot_rate_2)
        
        # Play procedural audio
        if self.fruit_type == "bomb":
            synth.play("explosion")
        else:
            synth.play("splat")
            
    def draw(self, surface):
        """Draws the whole fruit or delegates drawing to active halves."""
        if not self.active:
            return
            
        if self.state == "whole":
            # Draw whole fruit pre-rendered surface
            whole_img = FRUIT_SURFACES[self.fruit_type]["whole"]
            
            # Rotate dynamically
            rotated_img = pygame.transform.rotate(whole_img, self.physics.angle)
            rect = rotated_img.get_rect(center=(int(self.physics.x), int(self.physics.y)))
            surface.blit(rotated_img, rect.topleft)
            
            # Draw bomb spark if it is a bomb
            if self.fruit_type == "bomb":
                self._draw_bomb_spark(surface)
        else:
            # Draw halves
            self.half_left.draw(surface)
            self.half_right.draw(surface)
            
    def _draw_bomb_spark(self, surface):
        """Draws a flickering spark animation at the end of the fuse."""
        # The end of the fuse is hardcoded relative to the center in the 120x120 texture
        # Base offset (rotated by the bomb's angle)
        # Offset in unrotated space is (25, -radius - 20) -> (25, -62) relative to center
        theta = np.radians(-self.physics.angle) # Rotate opposite direction because pygame.transform.rotate goes CCW
        ox = 25
        oy = -self.radius - 20
        
        # Rotated offset
        rx = ox * np.cos(theta) - oy * np.sin(theta)
        ry = ox * np.sin(theta) + oy * np.cos(theta)
        
        spark_x = int(self.physics.x + rx)
        spark_y = int(self.physics.y + ry)
        
        # Draw flickering spark particles
        import random
        r_spark = random.randint(4, 9)
        color = config.FRUIT_COLORS["bomb"]["spark"]
        # Core yellow
        pygame.draw.circle(surface, (255, 255, 0), (spark_x, spark_y), r_spark // 2)
        # Outer red-orange halo
        pygame.draw.circle(surface, color, (spark_x, spark_y), r_spark, 2)
