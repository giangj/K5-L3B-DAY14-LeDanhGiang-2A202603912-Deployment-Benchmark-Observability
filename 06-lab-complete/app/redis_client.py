"""Shared Redis connection for rate limiter and cost guard."""
import redis

from app.config import settings

r = (
    redis.from_url(
        settings.redis_url,
        decode_responses=True,
        socket_connect_timeout=1.0,
        socket_timeout=1.0,
    )
    if settings.redis_url
    else None
)


def redis_healthy() -> bool:
    """Return True if Redis responds to PING, False otherwise."""
    if r is None:
        return False
    try:
        return bool(r.ping())
    except Exception:
        return False
