"""Settings read from environment variables, and router threshold constants."""

from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# Values marked PLACEHOLDER are not tuned yet; set them before the demo.
# Currency is unspecified in the source data, so prefer ratios and percentiles.

# --- Router thresholds ---
# PLACEHOLDER: max income_mismatch_pct (a fraction) before needs_info.
INCOME_MISMATCH_TOLERANCE: float = 0.10
# PLACEHOLDER: loan amount above which a human always reviews. Derive from a percentile of
# AMT_CREDIT in the seed data, not a fixed currency amount.
HIGH_LOAN_AMOUNT_CUTOFF: float = 1_000_000.0
# PLACEHOLDER: reasoner confidence below which a human reviews.
MIN_AUTO_CLEAR_CONFIDENCE: float = 0.80

# --- Model calls ---
# PLACEHOLDER: per-call timeout for the model, in seconds.
MODEL_TIMEOUT_SECONDS: float = 30.0
# Fixed by hard rule 7: retry once, then fall back to refer.
MODEL_MAX_RETRIES: int = 1

_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    """Runtime settings. Every field comes from an environment variable of the same name."""

    model_config = SettingsConfigDict(env_file=_ENV_FILE, extra="ignore")

    # True runs on the in-memory store and the rule-based fake model, with no credentials.
    use_fakes: bool = False
    model_base_url: str = ""
    model_name: str = ""
    model_api_key: SecretStr = SecretStr("")
    supabase_url: str = ""
    supabase_key: SecretStr = SecretStr("")


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings, read once on first use."""
    return Settings()
