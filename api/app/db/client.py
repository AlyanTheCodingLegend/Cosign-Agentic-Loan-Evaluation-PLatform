"""Supabase client built from settings."""

from supabase import Client, create_client

from app.config import get_settings


def get_client() -> Client:
    """Return a Supabase client configured from SUPABASE_URL and SUPABASE_KEY."""
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_key.get_secret_value())
