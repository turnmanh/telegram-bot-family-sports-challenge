from fastapi import APIRouter, BackgroundTasks
from stravalib.client import Client
from core.config import settings
from db.supabase import supabase
from app.sync import sync_user_activities

router = APIRouter()

@router.get("/strava/auth")
async def strava_auth(code: str, state: str, background_tasks: BackgroundTasks):
    """
    Callback endpoint for Strava OAuth.
    Exchanges code for token and saves it with Telegram ID (state).
    """
    client = Client()
    try:
        # Exchange code for tokens
        token_response = client.exchange_code_for_token(
            client_id=settings.STRAVA_CLIENT_ID,
            client_secret=settings.STRAVA_CLIENT_SECRET,
            code=code
        )
        
        # Prepare data for Supabase
        user_data = {
            "telegram_id": int(state),
            "access_token": token_response["access_token"],
            # stravalib might return refresh_token in response or we need to extract it
            "refresh_token": token_response.get("refresh_token"),
            "expires_at": token_response.get("expires_at"),
            "athlete_id": token_response.get("athlete", {}).get("id"),
            "first_name": token_response.get("athlete", {}).get("firstname"),
            "last_name": token_response.get("athlete", {}).get("lastname")
        }
        
        # Save to Supabase (upsert)
        # Using execute() to run the query
        data, count = supabase.table("users").upsert(user_data).execute()
        
        # Trigger background sync
        background_tasks.add_task(sync_user_activities, user_data)
        
        return {"message": "Authorization successful! Syncing your activities... You can close this window and return to Telegram."}
        
    except Exception as e:
        return {"error": f"Authorization failed: {str(e)}"}

from pydantic import BaseModel
from telegram.error import TelegramError
from app.bot import create_bot_application
from core.scoring import calculate_weighted_distance
import time

class WebhookEvent(BaseModel):
    object_type: str
    object_id: int
    aspect_type: str
    owner_id: int
    subscription_id: int
    event_time: int
    updates: dict = {}


from fastapi import Query

@router.get("/strava/webhook")
async def strava_webhook_verify_endpoint(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token")
):
    if hub_mode == "subscribe" and hub_verify_token == settings.WEBHOOK_VERIFY_TOKEN:
        return {"hub.challenge": hub_challenge}
    return {"error": "Invalid token"}

@router.post("/strava/webhook")
async def strava_webhook_event(event: WebhookEvent):
    # Process only activity creation
    if event.object_type == "activity" and event.aspect_type == "create":
        # 1. Get user from DB
        response = supabase.table("users").select("*").eq("athlete_id", event.owner_id).execute()
        if not response.data:
            print(f"User not found for athlete_id: {event.owner_id}")
            return {"status": "User not found"}
        
        user = response.data[0]
        telegram_id = user["telegram_id"]
        
        # 2. Fetch Activity Details (Need valid token)
        # TODO: Implement token refresh logic if expired (omitted for brevity, assume valid or simple refresh)
        client = Client(access_token=user["access_token"])
        
        # Check expiry
        if time.time() > user["expires_at"]:
            try:
                refresh_response = client.refresh_access_token(
                    client_id=settings.STRAVA_CLIENT_ID,
                    client_secret=settings.STRAVA_CLIENT_SECRET,
                    refresh_token=user["refresh_token"]
                )
                # Update DB
                supabase.table("users").update({
                    "access_token": refresh_response["access_token"],
                    "refresh_token": refresh_response["refresh_token"],
                    "expires_at": refresh_response["expires_at"]
                }).eq("telegram_id", telegram_id).execute()
                client.access_token = refresh_response["access_token"]
            except Exception as e:
                print(f"Failed to refresh token: {e}")
                return {"status": "Token refresh failed"}

        try:
            activity = client.get_activity(event.object_id)
            
            # Safe handling for Stravalib versions
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
            
            # 3. Calculate Score
            weighted_km = calculate_weighted_distance(activity_type_str, distance_meters) 

            activity_data = {
                "activity_id": event.object_id,
                "user_id": telegram_id,
                "type": activity_type_str,
                "distance": float(distance_km),
                "weighted_distance": weighted_km,
                "name": activity.name,
                "start_date": activity.start_date.isoformat()
            }
            supabase.table("activities").upsert(activity_data).execute()
            
            # 5. Notify User
            bot = create_bot_application().bot
            msg = (
                f"🏃 New Activity Processed!\n"
                f"Type: {activity_type_str}\n"
                f"Dist: {distance_km:.2f} km\n"
                f"Weighted: {weighted_km:.2f} km"
            )
            # Need to await bot message
            # Since this is a FastAPI route, we can await
            await bot.send_message(chat_id=telegram_id, text=msg)
            
        except Exception as e:
            print(f"Error processing activity: {e}")
            return {"status": "Error processing"}

    return {"status": "ok"}
