import os
import secrets

from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-KEY", auto_error=False)


def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    """
    Validate the X-API-KEY header against EXTENSION_API_KEY.

    This is an abuse-prevention gate, not a strong secret: the key ships
    inside the public extension bundle and can be read by anyone who
    unpacks it. It stops casual scraping and other installed extensions
    from riding on this backend for free — it does not replace per-user
    billing/quota enforcement.
    """
    expected = os.getenv("EXTENSION_API_KEY", "")
    if not expected or not api_key or not secrets.compare_digest(api_key, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid API key.",
        )
    return api_key
