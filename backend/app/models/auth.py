"""
Authentication Pydantic schemas.
"""

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    """Schema for user registration request."""
    username: str = Field(..., min_length=3, max_length=50, description="Unique username for the account")
    password: str = Field(..., min_length=6, description="Plaintext password")


class UserLogin(BaseModel):
    """Schema for user login request."""
    username: str = Field(..., description="Account username")
    password: str = Field(..., description="Plaintext password")


class UserResponse(BaseModel):
    """Schema for user data sent in response."""
    id: str = Field(..., description="Unique user ID")
    username: str = Field(..., description="Account username")
