"""Settings read from environment variables, and router threshold constants."""

from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# Values marked PLACEHOLDER are not tuned yet; set them before the demo.
# Currency is unspecified in the source data, so prefer ratios and percentiles.

# --- Router thresholds ---
# Max income_mismatch_pct (a fraction) before needs_info. Agreed policy value.
INCOME_MISMATCH_TOLERANCE: float = 0.10
# 90th percentile of AMT_CREDIT in a 4,000-row stratified sample of application_train.csv
# (seed/prepare_home_credit.py). Currency is unspecified, so this is a percentile, not a price.
HIGH_LOAN_AMOUNT_CUTOFF: float = 1_129_500.0
# PLACEHOLDER: reasoner confidence below which a human reviews.
MIN_AUTO_CLEAR_CONFIDENCE: float = 0.80

# --- Risk policy (see POLICY.md) ---
# Frozen from percentiles of a 4,000-row stratified sample of application_train.csv, so the
# training labels, the prompted model and the app all use the same numbers. Ratios and scores,
# never currency amounts. The sample's percentile is noted beside each value.
# Payment-to-income = AMT_ANNUITY / (AMT_INCOME_TOTAL / 12).
POLICY_DECLINE_PAYMENT_TO_INCOME: float = 3.65  # p90
POLICY_REFER_PAYMENT_TO_INCOME: float = 2.77  # p75
# Loan-to-income only ever refers; it never declines on its own.
POLICY_REFER_LOAN_TO_INCOME: float = 5.23  # p75
# Average of the available EXT_SOURCE_1/2/3 scores. A case with none is always referred.
POLICY_DECLINE_SCORE_AVERAGE: float = 0.35  # p15
POLICY_REFER_SCORE_AVERAGE: float = 0.44  # p30

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
    # Origins allowed to call the API from a browser, comma separated.
    cors_origins: str = "http://localhost:3000"


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings, read once on first use."""
    return Settings()
