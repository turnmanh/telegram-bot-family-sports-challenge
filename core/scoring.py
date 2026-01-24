from decimal import Decimal
from typing import Dict, Optional

# Default activity weights - ONLY allowing Run, Ride, and Swim as requested
# Run is the baseline (1.0)
DEFAULT_ACTIVITY_WEIGHTS = {
    "Run": Decimal("1.0"),
    "Ride": Decimal("0.25"),
    "Swim": Decimal("4.0"),
}

def calculate_weighted_distance(
    activity_type: str, 
    distance_meters: float, 
    custom_weights: Optional[Dict[str, Decimal]] = None
) -> float:
    """
    Calculates the weighted distance in Kilometers.
    
    Args:
        activity_type: The Strava activity type.
        distance_meters: The distance in meters.
        custom_weights: Optional dictionary of weights to override defaults.
        
    Returns:
        float: The weighted distance in KM.
    """
    weights = custom_weights if custom_weights is not None else DEFAULT_ACTIVITY_WEIGHTS
    weight = weights.get(activity_type, DEFAULT_ACTIVITY_WEIGHTS.get(activity_type, Decimal("0.0")))
    
    # Convert meters to km (meters / 1000) * weight
    weighted_km = (Decimal(str(distance_meters)) / Decimal("1000")) * weight
    return float(weighted_km)

async def refresh_activity_weights() -> Dict[str, Decimal]:
    """
    Fetches the latest activity weights from the database.
    """
    from db.supabase import supabase
    try:
        res = supabase.table("activity_weights").select("sport_type, weight").execute()
        if res.data:
            return {item["sport_type"]: Decimal(str(item["weight"])) for item in res.data}
    except Exception as e:
        print(f"Error fetching weights from DB: {e}")
    
    return DEFAULT_ACTIVITY_WEIGHTS
