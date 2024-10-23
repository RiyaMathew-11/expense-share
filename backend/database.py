from supabase import create_client
from config import get_settings

settings = get_settings()

# Error handling while connecting to Supabase
try:
    supabase = create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_KEY
    )
    print("Successfully connected to Supabase")
except Exception as e:
    print(f"Error connecting to Supabase: {str(e)}")
    raise e