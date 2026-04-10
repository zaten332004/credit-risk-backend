from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.schemas.schemas import TokenData, User
from app.db.session import SessionLocal
from app.db.models import UserDB, RoleDB
from app.core.config import settings

# HTTPBearer for simple token-based authentication
http_bearer = HTTPBearer(description="Enter your JWT token")

# Dùng pbkdf2_sha256 để tránh lỗi backend bcrypt trên môi trường hiện tại
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
legacy_bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Prefer SECRET_KEY from env (Settings); fallback for local dev only.
SECRET_KEY = (settings.SECRET_KEY or "").strip() or "CHANGE_ME_TO_A_SECURE_RANDOM_SECRET"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = max(1, int(settings.ACCESS_TOKEN_EXPIRE_MINUTES or 10080))


def normalize_role_name(role_name: Optional[str]) -> str:
    value = (role_name or "").strip().lower().replace("_", " ").replace("-", " ")
    value = " ".join(value.split())

    if value in {"admin", "administrator", "quản trị viên"}:
        return "admin"
    if value in {"manager", "quản lý", "quản lý rủi ro"}:
        return "manager"
    if value in {"analyst", "risk analyst", "credit analyst", "chuyên viên", "chuyên viên phân tích"}:
        return "analyst"
    if value in {"viewer", "user", "guest"}:
        return "viewer"
    return value or "viewer"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    plain_password = (plain_password or "").strip()
    hashed_password = (hashed_password or "").strip()

    # Try hashed password verification first (supports legacy bcrypt hashes)
    try:
        if hashed_password.startswith(("$2a$", "$2b$", "$2y$")):
            return legacy_bcrypt_context.verify(plain_password, hashed_password)
        return pwd_context.verify(plain_password, hashed_password)
    except:
        # Fallback to plaintext comparison (for legacy passwords)
        return plain_password == hashed_password


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
        if not verify_password(password, user.password_hash):
            return None
        
        # Get role name
        role = db.query(RoleDB).filter(RoleDB.role_id == user.role_id).first()
        role_name = normalize_role_name(role.role_name if role else "viewer")
        
        return User(
            id=user.user_id,
            email=user.email,
            full_name=user.username,
            is_active=True,
            is_admin=role_name == "admin",
        )
    finally:
        db.close()


def authenticate_user_by_username_or_email(username_or_email: str, password: str) -> Optional[dict]:
    """Authenticate by username or email - queries from database, return user dict with role"""
    db = SessionLocal()
    try:
        normalized_input = (username_or_email or "").strip()
        if not normalized_input:
            return None

        # Try email first
        user = (
            db.query(UserDB)
            .filter(func.lower(UserDB.email) == normalized_input.lower())
            .first()
        )
        
        # If not found, try username
        if not user:
            user = (
                db.query(UserDB)
                .filter(func.lower(UserDB.username) == normalized_input.lower())
                .first()
            )
        
        if not user:
            return None
        
        # Verify password
        if not verify_password(password, user.password_hash):
            return None
        
        # Get role name
        role = db.query(RoleDB).filter(RoleDB.role_id == user.role_id).first()
        role_name = normalize_role_name(role.role_name if role else "viewer")
        
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


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(http_bearer)) -> User:
    """Extract and validate JWT token from Bearer header"""
    token = credentials.credentials
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
        
        # Get role — must match normalize_role_name used when issuing JWTs (e.g. OAuth "risk analyst" → "analyst")
        role = db.query(RoleDB).filter(RoleDB.role_id == user.role_id).first()
        role_name = normalize_role_name(role.role_name if role else "viewer")

        return User(
            id=user.user_id,
            email=user.email,
            full_name=user.username,
            is_active=True,
            role=role_name,
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


async def get_current_manager_or_admin_user(current_user: User = Depends(get_current_active_user)) -> User:
    if current_user.role not in {"admin", "manager"}:
        raise HTTPException(status_code=403, detail="Manager or admin permission required")
    return current_user


async def get_current_manager_user(current_user: User = Depends(get_current_active_user)) -> User:
    """Require Manager role (or Admin with admin override)"""
    if current_user.role not in {"admin", "manager"}:
        raise HTTPException(status_code=403, detail="Manager permission required")
    return current_user


async def get_current_analyst_user(current_user: User = Depends(get_current_active_user)) -> User:
    """Require Analyst role (or higher: Manager, Admin)"""
    if current_user.role not in {"admin", "manager", "analyst"}:
        raise HTTPException(status_code=403, detail="Analyst permission required")
    return current_user

