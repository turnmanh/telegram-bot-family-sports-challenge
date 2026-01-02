from decimal import Decimal

ACTIVITY_WEIGHTS = {
    "Run": Decimal("1.0"),
    "Ride": Decimal("0.1"),
    "Swim": Decimal("2.0"),
}

def calculate_weighted_distance(activity_type: str, distance_meters: float) -> float:
    """
    Calculates the weighted distance in Kilometers.
    
    Args:
        activity_type: The Strava activity type (e.g., 'Run', 'Ride').
        distance_meters: The distance in meters.
        
    Returns:
        float: The weighted distance in KM.
    """
    weight = ACTIVITY_WEIGHTS.get(activity_type, Decimal("0.0"))
    # Convert meters to km (meters / 1000) * weight
    weighted_km = (Decimal(str(distance_meters)) / Decimal("1000")) * weight
    return float(weighted_km)
