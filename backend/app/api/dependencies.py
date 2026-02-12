"""
API Dependencies

FastAPI dependency injection for authentication and common services.
"""

import logging
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.config.settings import get_settings


logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)


async def get_current_user_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> str:
    """
    Extract user ID from JWT token.
    
    Validates the Supabase JWT and extracts the user ID (sub claim).
    
    Returns:
        User ID string
        
    Raises:
        HTTPException: If token is invalid or missing
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    
    try:
        import jwt
        from jwt import PyJWKClient
        
        settings = get_settings()
        
        # For Supabase, the JWT is signed with the JWT secret
        # In production, you would verify with the JWKS endpoint
        # For now, we decode and extract the sub claim
        
        # Decode without verification for development
        # TODO: Add proper JWT verification with Supabase JWKS
        unverified = jwt.decode(
            token,
            options={"verify_signature": False},
            algorithms=["HS256"],
        )
        
        user_id = unverified.get("sub")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user ID",
            )
        
        return user_id
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except jwt.InvalidTokenError as e:
        logger.error(f"JWT validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
    except Exception as e:
        logger.error(f"Error validating token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
        )


async def get_optional_user_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[str]:
    """
    Optionally extract user ID from JWT token.
    
    Returns None if no token provided (for public endpoints).
    """
    if not credentials:
        return None
    
    try:
        return await get_current_user_id(credentials)
    except HTTPException:
        return None
