"""Redis-backed sliding window rate limiter (60s window per API key)."""
import time
import uuid
from fastapi import HTTPException

from app.config import settings
from app.redis_client import r

_local_windows: dict[str, list[float]] = {}


def check_rate_limit(key: str) -> None:
    """Enforce RATE_LIMIT_PER_MINUTE requests per 60 seconds; raise HTTP 429 when exceeded."""
    limit = settings.rate_limit_per_minute
    now = time.time()
    window_start = now - 60.0

    if r is not None:
        redis_key = f"ratelimit:{key}"
        pipe = r.pipeline()
        pipe.zremrangebyscore(redis_key, 0, window_start)
        pipe.zcard(redis_key)
        _, current_count = pipe.execute()

        if int(current_count) >= limit:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded",
                headers={"Retry-After": "60"},
            )

        member = f"{now}:{uuid.uuid4().hex}"
        pipe = r.pipeline()
        pipe.zadd(redis_key, {member: now})
        pipe.expire(redis_key, 120)
        pipe.execute()
        return

    # Local fallback only when REDIS_URL is unset
    timestamps = [t for t in _local_windows.get(key, []) if t > window_start]
    if len(timestamps) >= limit:
        _local_windows[key] = timestamps
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={"Retry-After": "60"},
        )
    timestamps.append(now)
    _local_windows[key] = timestamps
