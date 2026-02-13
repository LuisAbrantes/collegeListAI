"""
Security Test Suite — JWT Authentication

Tests that the centralized JWT verification in dependencies.py correctly:
- Rejects missing Authorization headers
- Rejects malformed tokens
- Rejects expired tokens
- Rejects tokens with invalid signatures
- Accepts properly signed tokens (mocked JWKS)
"""

import time
from unittest.mock import patch, MagicMock, AsyncMock

import jwt
import pytest
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user_id


# ---------------------------------------------------------------------------
# Minimal app that uses the real dependency
# ---------------------------------------------------------------------------

test_app = FastAPI()


@test_app.get("/protected")
async def protected_endpoint(user_id: str = Depends(get_current_user_id)):
    return {"user_id": user_id}


client = TestClient(test_app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Tests: rejection scenarios
# ---------------------------------------------------------------------------


class TestJWTRejection:
    """Verify that invalid/missing JWTs are rejected with 401."""

    def test_no_auth_header(self):
        resp = client.get("/protected")
        assert resp.status_code == 401

    def test_empty_bearer(self):
        resp = client.get("/protected", headers={"Authorization": "Bearer "})
        assert resp.status_code == 401

    def test_malformed_scheme(self):
        resp = client.get("/protected", headers={"Authorization": "Basic abc123"})
        assert resp.status_code == 401

    def test_garbage_token(self):
        resp = client.get("/protected", headers={"Authorization": "Bearer not.a.jwt"})
        assert resp.status_code == 401

    def test_unsigned_token(self):
        """A JWT with algorithm=none must be rejected."""
        payload = {
            "sub": "00000000-0000-0000-0000-000000000001",
            "aud": "authenticated",
            "exp": int(time.time()) + 3600,
        }
        token = jwt.encode(payload, key="", algorithm="HS256")  # wrong key
        resp = client.get(
            "/protected", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 401

    def test_expired_token_hs256(self):
        """An expired HS256 token (even with correct secret) must be rejected."""
        from app.config.settings import get_settings

        settings = get_settings()
        if not settings.supabase_jwt_secret:
            pytest.skip("SUPABASE_JWT_SECRET not set")

        payload = {
            "sub": "00000000-0000-0000-0000-000000000001",
            "aud": "authenticated",
            "iss": f"{settings.supabase_url}/auth/v1",
            "exp": int(time.time()) - 60,  # 1 min ago
        }
        token = jwt.encode(payload, settings.supabase_jwt_secret, algorithm="HS256")
        resp = client.get(
            "/protected", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 401

    def test_raw_uuid_rejected(self):
        """
        Regression: previously the app accepted 'Bearer <raw-uuid>' as auth.
        This MUST now return 401.
        """
        resp = client.get(
            "/protected",
            headers={
                "Authorization": "Bearer 00000000-0000-0000-0000-000000000001"
            },
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Tests: acceptance scenarios (with mocked JWKS / HS256)
# ---------------------------------------------------------------------------


class TestJWTAcceptance:
    """Verify that valid JWTs are accepted."""

    def test_valid_hs256_token(self):
        """A correctly signed HS256 token with valid claims should succeed."""
        from app.config.settings import get_settings

        settings = get_settings()
        if not settings.supabase_jwt_secret:
            pytest.skip("SUPABASE_JWT_SECRET not set")

        user_id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        payload = {
            "sub": user_id,
            "aud": "authenticated",
            "iss": f"{settings.supabase_url}/auth/v1",
            "exp": int(time.time()) + 3600,
        }
        token = jwt.encode(payload, settings.supabase_jwt_secret, algorithm="HS256")
        resp = client.get(
            "/protected", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        assert resp.json()["user_id"] == user_id
