"""Config — 12-Factor: read all runtime configuration from environment variables."""
from dataclasses import dataclass
import os

from dotenv import load_dotenv

load_dotenv(override=False)


def _env_int(name: str, default: int) -> int:
    val = os.getenv(name)
    if val is None or val == "":
        return default
    return int(val)


def _env_float(name: str, default: float) -> float:
    val = os.getenv(name)
    if val is None or val == "":
        return default
    return float(val)


@dataclass
class Settings:
    port: int = _env_int("PORT", 8000)
    environment: str = os.getenv("ENVIRONMENT", "development")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    agent_api_key: str = os.getenv("AGENT_API_KEY", "")
    redis_url: str = os.getenv("REDIS_URL", "")
    rate_limit_per_minute: int = _env_int("RATE_LIMIT_PER_MINUTE", 10)
    daily_budget_usd: float = _env_float("DAILY_BUDGET_USD", 1.0)
    monthly_budget_usd: float = _env_float("MONTHLY_BUDGET_USD", 10.0)


settings = Settings()
