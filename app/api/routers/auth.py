"""
Authentication endpoints: JWT login
"""
from fastapi import APIRouter, HTTPException, status

from app.core.security import authenticate_user_by_username_or_email, create_access_token
from app.schemas.schemas import Token, LoginRequest

router = APIRouter()


@router.post("/auth/login", response_model=Token, tags=["auth"])
async def login_for_access_token(body: LoginRequest) -> Token:
    """
    Login endpoint - accepts username or email + password
    Returns JWT token with user info and role
    
    Example:
    {
        "username_or_email": "admin" or "admin@example.com",
        "password": "admin123"
    }
    """
    user_dict = authenticate_user_by_username_or_email(body.username_or_email, body.password)
    if not user_dict:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password"
        )
    
    # Create access token with email and role
    access_token = create_access_token(
        data={
            "sub": user_dict.get("email"),
            "role": user_dict.get("role", "viewer")
        }
    )
    
    return Token(
        access_token=access_token,
        user_id=user_dict.get("id"),
        email=user_dict.get("email"),
        full_name=user_dict.get("full_name"),
        role=user_dict.get("role", "viewer")
    )
