from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.schemas.schemas import TokenData, User
from app.db.session import SessionLocal
from app.db.models import UserDB, RoleDB

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# Dùng pbkdf2_sha256 để tránh lỗi backend bcrypt trên môi trường hiện tại
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

# Demo secret – với production nên đọc từ env / AWS Secrets Manager
SECRET_KEY = "CHANGE_ME_TO_A_SECURE_RANDOM_SECRET"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def authenticate_user(email: str, password: str) -> Optional[User]:
    """Legacy: authenticate by email - queries from database"""
    db = SessionLocal()
    try:
        user = db.query(UserDB).filter(UserDB.email == email).first()
        if not user:
            return None
        if not verify_password(password, user.password):
            return None
        
        # Get role name
        role = db.query(RoleDB).filter(RoleDB.role_id == user.role_id).first()
        role_name = role.role_name if role else "viewer"
        
        return User(
            id=user.user_id,
            email=user.email,
            full_name=user.username,
            is_active=True,
            is_admin=role_name.lower() == "admin",
        )
    finally:
        db.close()


def authenticate_user_by_username_or_email(username_or_email: str, password: str) -> Optional[dict]:
    """Authenticate by username or email - queries from database, return user dict with role"""
    db = SessionLocal()
    try:
        # Try email first
        user = db.query(UserDB).filter(UserDB.email == username_or_email).first()
        
        # If not found, try username
        if not user:
            user = db.query(UserDB).filter(UserDB.username == username_or_email).first()
        
        if not user:
            return None
        
        # Verify password
        if not verify_password(password, user.password):
            return None
        
        # Get role name
        role = db.query(RoleDB).filter(RoleDB.role_id == user.role_id).first()
        role_name = role.role_name.lower() if role else "viewer"
        
        return {
            "id": user.user_id,
            "username": user.username,
            "email": user.email,
            "full_name": user.username,
            "is_active": True,
            "is_admin": role_name == "admin",
            "role": role_name,
        }
    finally:
        db.close()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub: str | None = payload.get("sub")
        if sub is None:
            raise credentials_exception
        token_data = TokenData(sub=sub, role=payload.get("role"))
    except JWTError:
        raise credentials_exception

    # Query user from database
    db = SessionLocal()
    try:
        user = db.query(UserDB).filter(UserDB.email == token_data.sub).first()
        if user is None:
            raise credentials_exception
        
        # Get role
        role = db.query(RoleDB).filter(RoleDB.role_id == user.role_id).first()
        role_name = role.role_name.lower() if role else "viewer"
        
        return User(
            id=user.user_id,
            email=user.email,
            full_name=user.username,
            is_active=True,
            is_admin=role_name == "admin",
        )
    finally:
        db.close()


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


async def get_current_admin_user(current_user: User = Depends(get_current_active_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return current_user

