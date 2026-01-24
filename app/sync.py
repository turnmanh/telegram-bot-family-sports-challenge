from datetime import datetime
from core.config import settings
from db.supabase import supabase
from core.scoring import calculate_weighted_distance, refresh_activity_weights
import logging

logger = logging.getLogger(__name__)

async def sync_user_activities(user_data: dict):
    """
    Syncs activities for a user within the configured date range.
    Uses bulk upsert for efficiency.
    """
    if not settings.STRAVA_SYNC_START_DATE:
        logger.info("No sync start date configured. Skipping sync.")
        return

    logger.info(f"Starting sync for user {user_data['telegram_id']}...")
    from app.strava_utils import get_strava_client
    client = get_strava_client(user_data)
    
    # Fetch current weights from DB
    weights = await refresh_activity_weights()
    
    start_date = datetime.strptime(settings.STRAVA_SYNC_START_DATE, "%Y-%m-%d")
    end_date = None
    if settings.STRAVA_SYNC_END_DATE:
        end_date = datetime.strptime(settings.STRAVA_SYNC_END_DATE, "%Y-%m-%d")

    try:
        # get_activities returns an iterator
        activities = client.get_activities(after=start_date, before=end_date, limit=None)
        
        u_activities = []
        for activity in activities:
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
            
            distance_km = distance_meters / 1000.0
            weighted_km = calculate_weighted_distance(activity_type_str, distance_meters, custom_weights=weights)
            
            # ONLY allow Ride, Run, and Swim (activities with weight > 0)
            if weighted_km <= 0:
                logger.info(f"Skipping activity {activity.id} (type: {activity_type_str}) as it is not an allowed type.")
                continue

            u_activities.append({
                "activity_id": activity.id,
                "user_id": user_data['telegram_id'],
                "type": activity_type_str,
                "distance": distance_km,
                "weighted_distance": weighted_km,
                "name": activity.name,
                "start_date": activity.start_date.isoformat()
            })
            
        if u_activities:
            # Chunking bulk upsert if necessary (Supabase handled well up to ~1000)
            supabase.table("activities").upsert(u_activities).execute()
        
        # Also ensure all OLD activities for this user are updated if weights changed
        await refresh_all_weighted_distances(user_data['telegram_id'])
            
        logger.info(f"Sync complete for user {user_data['telegram_id']}: {len(u_activities)} activities synced.")
        
    except Exception as e:
        logger.error(f"Error syncing activities for user {user_data['telegram_id']}: {e}")

async def refresh_all_weighted_distances(telegram_id: int):
    """
    Refresh all weighted_distance values in the DB for a specific user.
    """
    try:
        # Fetch weights
        weights = await refresh_activity_weights()
        
        # Fetch user activities
        res = supabase.table("activities").select("*").eq("user_id", telegram_id).execute()
        if not res.data:
            return
            
        updates = []
        for activity in res.data:
            dist_meters = float(activity["distance"]) * 1000.0
            new_weighted = calculate_weighted_distance(activity["type"], dist_meters, custom_weights=weights)
            
            if abs(new_weighted - float(activity["weighted_distance"])) > 0.001:
                updates.append({
                    "activity_id": activity["activity_id"],
                    "weighted_distance": new_weighted
                })
        
        if updates:
            # Upsert acts as "update" when activity_id matches
            supabase.table("activities").upsert(updates).execute()
            logger.info(f"Updated weights for {len(updates)} existing activities for user {telegram_id}")
            
    except Exception as e:
        logger.warn(f"Failed to refresh all weighted distances for {telegram_id}: {e}")

async def sync_for_user(telegram_id: int):
    """
    Fetches user data from DB and runs sync.
    """
    try:
        res = supabase.table("users").select("*").eq("telegram_id", telegram_id).execute()
        if res.data:
            user_data = res.data[0]
            if user_data.get("access_token"):
                await sync_user_activities(user_data)
    except Exception as e:
        logger.error(f"Error in sync_for_user for {telegram_id}: {e}")

async def sync_all_users():
    """
    Syncs activities for all users that have a Strava connection.
    """
    try:
        res = supabase.table("users").select("*").not_.is_("access_token", "null").execute()
        for user_data in res.data:
            await sync_user_activities(user_data)
    except Exception as e:
        logger.error(f"Error in sync_all_users: {e}")
