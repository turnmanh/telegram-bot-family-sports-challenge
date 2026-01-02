import time
from stravalib.client import Client
from core.config import settings
from db.supabase import supabase

def get_strava_client(user: dict) -> Client:
    """
    Returns a valid Strava Client for the given user.
    Refreshes the token if it's expired.
    'user' is a dict containing at least: telegram_id, access_token, refresh_token, expires_at.
    """
    client = Client(access_token=user["access_token"])
    
    # Check if token is expired (or close to expiring, e.g. 5 mins buffer)
    # user["expires_at"] is expected to be a timestamp (int)
    expires_at = user.get("expires_at")
    
    if expires_at and time.time() > expires_at - 300:
        print(f"Token expired or expiring soon for user {user.get('telegram_id')}. Refreshing...")
        try:
            refresh_response = client.refresh_access_token(
                client_id=settings.STRAVA_CLIENT_ID,
                client_secret=settings.STRAVA_CLIENT_SECRET,
                refresh_token=user["refresh_token"]
            )
            
            # Update user dict for the caller so they have the fresh tokens
            user["access_token"] = refresh_response["access_token"]
            user["refresh_token"] = refresh_response["refresh_token"]
            user["expires_at"] = refresh_response["expires_at"]
            
            # Update DB
            supabase.table("users").update({
                "access_token": user["access_token"],
                "refresh_token": user["refresh_token"],
                "expires_at": user["expires_at"]
            }).eq("telegram_id", user["telegram_id"]).execute()
            
            client.access_token = user["access_token"]
            print(f"Token refreshed successfully for user {user.get('telegram_id')}.")
        except Exception as e:
            print(f"Failed to refresh token for user {user.get('telegram_id')}: {e}")
            # We still return the client, but it might fail on the next request if the token is truly dead
            
    return client
