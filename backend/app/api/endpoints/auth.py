"""
Authentication endpoints.
"""

import uuid
from fastapi import APIRouter, Depends, HTTPException, Response, status
from app.models.auth import UserCreate, UserLogin, UserResponse
from app.core.security import get_password_hash, verify_password, create_access_token
from app.core.mock_db import fake_users_db
from app.api.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new user",
    description="Creates a new user and sets a secure HTTP-Only cookie containing the access token."
)
async def register(response: Response, user_in: UserCreate) -> UserResponse:
    """Register a new user account."""
    username = user_in.username.strip()
    if username in fake_users_db:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered. Please choose another."
        )
    
    user_id = str(uuid.uuid4())
    hashed_password = get_password_hash(user_in.password)
    
    # Save user dict to mock database
    user_record = {
        "id": user_id,
        "username": username,
        "hashed_password": hashed_password
    }
    fake_users_db[username] = user_record
    
    # Create token and set HTTP-only cookie
    token = create_access_token({"sub": username})
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=1800,
        # secure=False is fine for local http development
        secure=False 
    )
    
    return UserResponse(id=user_id, username=username)


@router.post(
    "/login",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="User login",
    description="Authenticates credentials and sets a secure HTTP-Only cookie containing the access token."
)
async def login(response: Response, user_in: UserLogin) -> UserResponse:
    """Log in an existing user."""
    username = user_in.username.strip()
    user_record = fake_users_db.get(username)
    if not user_record or not verify_password(user_in.password, user_record["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password."
        )
    
    # Create token and set HTTP-only cookie
    token = create_access_token({"sub": username})
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=1800,
        secure=False
    )
    
    return UserResponse(id=user_record["id"], username=username)


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="User logout",
    description="Clears the authentication HTTP-Only cookie."
)
async def logout(response: Response) -> dict[str, str]:
    """Log out the current user."""
    response.delete_cookie(
        key="access_token",
        httponly=True,
        samesite="lax",
        secure=False
    )
    return {"message": "Logged out successfully"}


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current user details",
    description="Verifies the current session cookie and returns user details if valid."
)
async def get_me(current_user: UserResponse = Depends(get_current_user)) -> UserResponse:
    """Get profile of current logged-in user."""
    return current_user
