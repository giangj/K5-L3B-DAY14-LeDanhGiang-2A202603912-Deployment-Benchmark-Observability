"""API Key authentication via X-API-Key header."""
import hmac
from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

from app.config import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_key(api_key: str | None = Security(api_key_header)) -> str:
    """Validate X-API-Key against AGENT_API_KEY; raise HTTP 401 on missing or invalid key."""
    expected = settings.agent_api_key
    if not expected or not api_key or not hmac.compare_digest(api_key, expected):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return api_key
