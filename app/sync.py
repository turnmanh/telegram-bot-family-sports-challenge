from datetime import datetime
from core.config import settings
from db.supabase import supabase
from core.scoring import calculate_weighted_distance
import logging

logger = logging.getLogger(__name__)

async def sync_user_activities(user_data: dict):
    """
    Syncs activities for a user within the configured date range.
    """
    if not settings.STRAVA_SYNC_START_DATE:
        logger.info("No sync start date configured. Skipping sync.")
        return

    logger.info(f"Starting sync for user {user_data['telegram_id']}...")
    from app.strava_utils import get_strava_client
    client = get_strava_client(user_data)
    
    start_date = datetime.strptime(settings.STRAVA_SYNC_START_DATE, "%Y-%m-%d")
    end_date = None
    if settings.STRAVA_SYNC_END_DATE:
        end_date = datetime.strptime(settings.STRAVA_SYNC_END_DATE, "%Y-%m-%d")

    try:
        # get_activities returns an iterator
        # limit=None ensures we fetch ALL activities in the range
        activities = client.get_activities(after=start_date, before=end_date, limit=None)
        
        count = 0
        for activity in activities:
            # Safe handling for Stravalib versions (Quantity vs float, Enum vs str)
            distance_val = activity.distance
            if hasattr(distance_val, 'num'): 
                distance_meters = distance_val.num
            elif hasattr(distance_val, 'magnitude'):
                distance_meters = distance_val.magnitude
            else:
                distance_meters = float(distance_val)
                
            activity_type = activity.type
            if hasattr(activity_type, 'root'):
                activity_type_str = str(activity_type.root)
            else:
                activity_type_str = str(activity_type)
            
            # We only care about activities with distance
            # Filter logic if desired
            
            distance_km = distance_meters / 1000.0
            weighted_km = calculate_weighted_distance(activity_type_str, distance_meters)
            
            activity_data = {
                "activity_id": activity.id,
                "user_id": user_data['telegram_id'],
                "type": activity_type_str,
                "distance": distance_km,
                "weighted_distance": weighted_km,
                "name": activity.name,
                "start_date": activity.start_date.isoformat()
            }
            
            supabase.table("activities").upsert(activity_data).execute()
            count += 1
            
        logger.info(f"Sync complete for user {user_data['telegram_id']}: {count} activities processed.")
        
    except Exception as e:
        logger.error(f"Error syncing activities for user {user_data['telegram_id']}: {e}")
