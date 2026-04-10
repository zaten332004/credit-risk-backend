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
    Login endpoint - Get JWT token
    
    Credentials:
    - admin / Admin@123456
    - manager / Manager@123456
    - risk_analyst / RiskAnalyst@123456
    """
    try:
        user_dict = authenticate_user_by_username_or_email(body.username_or_email, body.password)
        if not user_dict:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password"
            )
        
        # Create JWT token
        access_token = create_access_token(
            data={
                "sub": user_dict.get("email"),
                "role": user_dict.get("role", "viewer")
            }
        )
        
        return Token(
            access_token=access_token,
            token_type="bearer",
            user_id=user_dict.get("id"),
            email=user_dict.get("email"),
            full_name=user_dict.get("full_name"),
            role=user_dict.get("role", "viewer")
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login error: {str(e)}"
        )

