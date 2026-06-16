import numpy as np
import config

def get_distance(p1, p2):
    """Calculates Euclidean distance between two 2D points."""
    return np.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

def check_line_circle_intersection(p1, p2, center, radius):
    """Checks if a line segment (p1 -> p2) intersects a circle.
    
    Args:
        p1 (tuple): Start point of segment (x1, y1)
        p2 (tuple): End point of segment (x2, y2)
        center (tuple): Center of circle (cx, cy)
        radius (float): Radius of circle
        
    Returns:
        bool: True if intersection occurs, False otherwise.
        float: The parameter t (0 to 1) of the closest point on segment.
        tuple: The closest point (x, y) on the segment.
    """
    x1, y1 = p1
    x2, y2 = p2
    cx, cy = center
    
    # Vector of the segment
    dx = x2 - x1
    dy = y2 - y1
    
    # Segment length squared
    len_sq = dx*dx + dy*dy
    if len_sq == 0:
        # Segment is just a point
        dist = get_distance(p1, center)
        return dist <= radius, 0.0, p1
        
    # Projection factor t, clamped to [0, 1]
    # t = [(cx - x1)*dx + (cy - y1)*dy] / len_sq
    t = ((cx - x1) * dx + (cy - y1) * dy) / len_sq
    t = max(0.0, min(1.0, t))
    
    # Coordinates of projection point
    px = x1 + t * dx
    py = y1 + t * dy
    
    # Distance to projection point
    dist_sq = (px - cx)**2 + (py - cy)**2
    
    return dist_sq <= radius*radius, t, (px, py)

def calculate_slice_details(p1, p2, center, radius, dt):
    """Computes full mathematical details of a slice intersection.
    
    Args:
        p1 (tuple): Start point of segment (x1, y1)
        p2 (tuple): End point of segment (x2, y2)
        center (tuple): Center of circle (cx, cy)
        radius (float): Radius of circle
        dt (float): Frame delta time
        
    Returns:
        dict: Details of slice if valid, None otherwise.
    """
    if dt <= 0:
        dt = 0.016
        
    # Calculate blade speed
    blade_dist = get_distance(p1, p2)
    blade_speed = blade_dist / dt
    
    # Verify speed exceeds threshold
    if blade_speed < config.MIN_SLICE_SPEED:
        return None
        
    intersects, t, closest_pt = check_line_circle_intersection(p1, p2, center, radius)
    if not intersects:
        return None
        
    # Slice vector and angle
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    slice_angle = np.arctan2(dy, dx) # in radians
    
    # Calculate approximate entry/exit points
    # For a perfect line-circle intersection:
    # (P1 + t*D - C)^2 = R^2
    # a*t^2 + 2*b*t + c = 0
    # where a = D.D, b = (P1 - C).D, c = (P1 - C).(P1 - C) - R^2
    cx, cy = center
    x1, y1 = p1
    
    a = dx*dx + dy*dy
    b = (x1 - cx)*dx + (y1 - cy)*dy
    c = (x1 - cx)**2 + (y1 - cy)**2 - radius*radius
    
    discriminant = b*b - a*c
    
    entry_pt = p1
    exit_pt = p2
    
    if discriminant >= 0 and a > 0:
        sqrt_disc = np.sqrt(discriminant)
        t1 = (-b - sqrt_disc) / a
        t2 = (-b + sqrt_disc) / a
        
        # Clamp roots to segment boundaries
        t1_clamped = max(0.0, min(1.0, t1))
        t2_clamped = max(0.0, min(1.0, t2))
        
        entry_pt = (x1 + t1_clamped * dx, y1 + t1_clamped * dy)
        exit_pt = (x1 + t2_clamped * dx, y1 + t2_clamped * dy)
        
    # Perpendicular vector to push the halves apart
    push_angle_1 = slice_angle - np.pi/2
    push_angle_2 = slice_angle + np.pi/2
    
    # Push velocity magnitude scaled by blade speed (plus baseline speed)
    push_speed = 100.0 + min(blade_speed * 0.15, 300.0)
    
    return {
        "angle": slice_angle,
        "speed": blade_speed,
        "entry": entry_pt,
        "exit": exit_pt,
        "closest_point": closest_pt,
        "push_vector_1": (np.cos(push_angle_1) * push_speed, np.sin(push_angle_1) * push_speed),
        "push_vector_2": (np.cos(push_angle_2) * push_speed, np.sin(push_angle_2) * push_speed),
        "blade_velocity": (dx / dt, dy / dt)
    }
