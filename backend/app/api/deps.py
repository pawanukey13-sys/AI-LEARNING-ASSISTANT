"""
Dependency injection helpers for API endpoints.
"""

from fastapi import Cookie, HTTPException, status
from app.core.security import verify_token
from app.core.mock_db import fake_users_db
from app.models.auth import UserResponse


async def get_current_user(access_token: str | None = Cookie(None)) -> UserResponse:
    """
    Dependency to retrieve the currently logged-in user from the HTTP-Only cookie.
    
    Raises 401 Unauthorized if the cookie is missing, expired, or invalid.
    """
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Please log in."
        )
    
    payload = verify_token(access_token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid token. Please log in again."
        )
    
    username: str | None = payload.get("sub")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload."
        )
    
    user_record = fake_users_db.get(username)
    if not user_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer exists."
        )
    
    return UserResponse(
        id=user_record["id"],
        username=user_record["username"]
    )
