"""Supabase client built from settings."""

from supabase import Client


def get_client() -> Client:
    """Return a Supabase client configured from SUPABASE_URL and SUPABASE_KEY."""
    raise NotImplementedError
