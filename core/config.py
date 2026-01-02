from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Sport Challenge Bot"
    
    # Telegram
    TELEGRAM_BOT_TOKEN: str
    
    # Supabase
    SUPABASE_URL: str
    SUPABASE_KEY: str
    
    # Strava
    STRAVA_CLIENT_ID: str
    STRAVA_CLIENT_SECRET: str
    STRAVA_REDIRECT_URI: str = "https://unubiquitous-porky-tesha.ngrok-free.dev/strava/auth"
    
    # Webhook
    # The token you define for Strava to verify the webhook
    WEBHOOK_VERIFY_TOKEN: str = "STRAVA_DEFAULT_TOKEN"
    
    # Sync Configuration
    # Format: YYYY-MM-DD
    STRAVA_SYNC_START_DATE: str | None = None
    STRAVA_SYNC_END_DATE: str | None = None

    class Config:
        env_file = ".env"

settings = Settings()
