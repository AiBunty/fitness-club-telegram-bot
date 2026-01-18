"""
Geofence validation using Haversine formula
Server-side only distance calculation
"""

import logging
import math

logger = logging.getLogger(__name__)


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate distance between two GPS coordinates using Haversine formula
    
    Args:
        lat1, lon1: User's coordinates (from browser GPS)
        lat2, lon2: Gym's coordinates
    
    Returns:
        Distance in meters
    """
    try:
        R = 6371000  # Earth radius in meters
        
        # Convert to radians
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        
        # Haversine formula
        a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        distance = R * c
        return distance
    except Exception as e:
        logger.error(f"Error calculating distance: {e}")
        return float('inf')  # Return infinity on error (fails geofence check)


def is_within_geofence(user_lat: float, user_lon: float, gym_lat: float, gym_lon: float, 
                       radius_meters: int = 10) -> tuple[bool, float]:
    """
    Check if user is within geofence radius of gym
    
    Args:
        user_lat, user_lon: User's GPS coordinates
        gym_lat, gym_lon: Gym's GPS coordinates
        radius_meters: Allowed radius (default 10m, range 5-20m)
    
    Returns:
        tuple[bool, float]: (is_within_geofence, distance_in_meters)
    """
    try:
        distance = haversine_distance(user_lat, user_lon, gym_lat, gym_lon)
        is_within = distance <= radius_meters
        
        logger.debug(f"Geofence check: distance={distance:.1f}m, radius={radius_meters}m, within={is_within}")
        return is_within, distance
    except Exception as e:
        logger.error(f"Error checking geofence: {e}")
        return False, float('inf')
