from supabase import create_client, Client
from core.config import settings

def create_supabase_client() -> Client:
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

supabase: Client = create_supabase_client()
