"""Token-based cost guard backed by Redis."""
from datetime import datetime, timezone
from fastapi import HTTPException

from app.config import settings
from app.redis_client import r

# Price USD / 1K tokens (reference: gpt-4o-mini)
PRICE_INPUT_PER_1K = 0.00015
PRICE_OUTPUT_PER_1K = 0.0006

_local_spend: float = 0.0


def _cost_key() -> str:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"cost:daily:{today}"


def _effective_budget() -> float:
    return min(settings.daily_budget_usd, settings.monthly_budget_usd)


def check_budget() -> None:
    """Verify spend has not reached configured budget; raise HTTP 402 if exceeded."""
    budget = _effective_budget()
    if r is not None:
        raw = r.get(_cost_key())
        spent = float(raw) if raw is not None else 0.0
    else:
        spent = _local_spend

    if spent >= budget:
        raise HTTPException(status_code=402, detail="Budget limit exceeded")


def record_cost(input_tokens: int, output_tokens: int) -> float:
    """Compute request cost, accumulate into Redis, and return request cost in USD."""
    global _local_spend
    cost = (
        (input_tokens / 1000.0) * PRICE_INPUT_PER_1K
        + (output_tokens / 1000.0) * PRICE_OUTPUT_PER_1K
    )
    if r is not None:
        key = _cost_key()
        r.incrbyfloat(key, cost)
        r.expire(key, 86400 * 2)
    else:
        _local_spend += cost
    return cost
