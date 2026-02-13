"""
API Dependencies

FastAPI dependency injection for authentication and common services.

Security: JWT tokens are verified cryptographically using Supabase JWKS (ES256)
with HS256 fallback via the JWT secret. Never decode without verification.
"""

import logging
from typing import Optional

import jwt
from jwt import PyJWKClient
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.config.settings import get_settings


logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)

# Cached JWKS client — avoids re-fetching keys on every request.
# PyJWKClient caches keys internally and refreshes ~every 10 min.
_jwks_client: Optional[PyJWKClient] = None


def _get_jwks_client() -> PyJWKClient:
    """Return a singleton PyJWKClient for the Supabase JWKS endpoint."""
    global _jwks_client
    if _jwks_client is None:
        settings = get_settings()
        jwks_url = f"{settings.supabase_url}/auth/v1/.well-known/jwks.json"
        _jwks_client = PyJWKClient(jwks_url, cache_keys=True)
    return _jwks_client


def _decode_with_jwks(token: str, issuer: str) -> dict:
    """Verify JWT using Supabase JWKS endpoint (ES256 asymmetric keys)."""
    client = _get_jwks_client()
    signing_key = client.get_signing_key_from_jwt(token)
    return jwt.decode(
        token,
        signing_key.key,
        algorithms=["ES256"],
        issuer=issuer,
        audience="authenticated",
        options={"require": ["exp", "sub", "iss"]},
    )


def _decode_with_secret(token: str, secret: str, issuer: str) -> dict:
    """Verify JWT using HS256 symmetric secret (legacy Supabase signing)."""
    return jwt.decode(
        token,
        secret,
        algorithms=["HS256"],
        issuer=issuer,
        audience="authenticated",
        options={"require": ["exp", "sub", "iss"]},
    )


async def get_current_user_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> str:
    """
    Extract and verify user ID from a Supabase JWT.

    Verification strategy (in order):
      1. JWKS (ES256) — preferred, supports key rotation automatically.
      2. HS256 with ``SUPABASE_JWT_SECRET`` — fallback for legacy signing.

    Returns:
        Authenticated user ID (``sub`` claim).

    Raises:
        HTTPException 401: token missing, expired, or invalid.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    settings = get_settings()
    issuer = f"{settings.supabase_url}/auth/v1"

    payload: Optional[dict] = None

    # --- Strategy 1: JWKS (ES256) ---
    try:
        payload = _decode_with_jwks(token, issuer)
    except (jwt.exceptions.PyJWKClientError, jwt.InvalidTokenError) as jwks_err:
        logger.debug("JWKS verification failed, trying HS256 fallback: %s", jwks_err)

    # --- Strategy 2: HS256 fallback ---
    if payload is None and settings.supabase_jwt_secret:
        try:
            payload = _decode_with_secret(
                token, settings.supabase_jwt_secret, issuer
            )
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
            )
        except jwt.InvalidTokenError as e:
            logger.warning("HS256 JWT verification also failed: %s", e)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or unverifiable token",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing user ID",
        )

    return user_id


async def get_optional_user_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[str]:
    """
    Optionally extract user ID from JWT token.

    Returns ``None`` if no token is provided (for public endpoints).
    """
    if not credentials:
        return None

    try:
        return await get_current_user_id(credentials)
    except HTTPException:
        return None


# =============================================================================
# Re-export DB dependencies for a single import source
# Routers should import from api.dependencies, not db.dependencies directly.
# =============================================================================
from app.infrastructure.db.dependencies import (  # noqa: E402, F401
    SessionDep,
    UserProfileRepoDep,
    CollegeRepoDep,
    CollegeMajorStatsRepoDep,
)
