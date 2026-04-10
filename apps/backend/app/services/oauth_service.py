"""
OAuth login service for Google and GitHub.
Creates analyst users by default on first login.
"""
import secrets
from typing import Optional

import requests
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token, normalize_role_name, pwd_context
from app.db.models import RoleDB, UserDB
from app.schemas.schemas import Token


class OAuthService:
    @staticmethod
    def login_with_google(db: Session, id_token: str) -> Token:
        payload = OAuthService._verify_google_token(id_token)
        email = payload.get("email")
        if not email:
            raise ValueError("Google token missing email")
        if payload.get("email_verified") not in ("true", True):
            raise ValueError("Google account email is not verified")

        full_name = payload.get("name")
        user = OAuthService._get_or_create_analyst_user(
            db=db,
            email=email,
            full_name=full_name,
            username_seed=(payload.get("given_name") or email.split("@")[0]),
        )
        return OAuthService._build_token(db, user)

    @staticmethod
    def login_with_github(db: Session, access_token: str) -> Token:
        user_payload = OAuthService._fetch_github_user(access_token)
        email = OAuthService._fetch_github_primary_email(access_token, user_payload)
        if not email:
            raise ValueError("GitHub account does not expose a verified email")

        full_name = user_payload.get("name")
        user = OAuthService._get_or_create_analyst_user(
            db=db,
            email=email,
            full_name=full_name,
            username_seed=(user_payload.get("login") or email.split("@")[0]),
        )
        return OAuthService._build_token(db, user)

    @staticmethod
    def _verify_google_token(id_token: str) -> dict:
        response = requests.get(
            "https://oauth2.googleapis.com/tokeninfo",
            params={"id_token": id_token},
            timeout=10,
        )
        if response.status_code == 200:
            payload = response.json()
            configured_client_id = settings.google_oauth_client_id.strip()
            if configured_client_id and payload.get("aud") != configured_client_id:
                raise ValueError("Google token audience is invalid")
            return payload

        userinfo = requests.get(
            "https://openidconnect.googleapis.com/v1/userinfo",
            headers={"Authorization": f"Bearer {id_token}"},
            timeout=10,
        )
        if userinfo.status_code != 200:
            raise ValueError("Invalid Google token")

        payload = userinfo.json()
        if not payload.get("email"):
            raise ValueError("Google token missing email")
        return payload

    @staticmethod
    def _fetch_github_user(access_token: str) -> dict:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github+json",
        }
        response = requests.get("https://api.github.com/user", headers=headers, timeout=10)
        if response.status_code != 200:
            raise ValueError("Invalid GitHub token")
        return response.json()

    @staticmethod
    def _fetch_github_primary_email(access_token: str, user_payload: dict) -> Optional[str]:
        if user_payload.get("email"):
            return user_payload.get("email")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github+json",
        }
        response = requests.get("https://api.github.com/user/emails", headers=headers, timeout=10)
        if response.status_code != 200:
            return None

        emails = response.json()
        if not isinstance(emails, list):
            return None
        for email_obj in emails:
            if email_obj.get("verified") and email_obj.get("primary"):
                return email_obj.get("email")
        for email_obj in emails:
            if email_obj.get("verified"):
                return email_obj.get("email")
        return None

    @staticmethod
    def _get_or_create_analyst_user(db: Session, email: str, full_name: Optional[str], username_seed: str) -> UserDB:
        user = db.query(UserDB).filter(UserDB.email == email).first()
        if user:
            return user

        analyst_role = OAuthService._get_role_by_name(db, "risk analyst") or OAuthService._get_role_by_name(db, "analyst")
        if not analyst_role:
            raise ValueError("Role 'risk analyst' is not configured in Role table")

        username = OAuthService._build_unique_username(db, username_seed)
        temp_password = pwd_context.hash(secrets.token_urlsafe(32))

        user = UserDB(
            username=username,
            email=email,
            password_hash=temp_password,
            full_name=full_name,
            user_type="analyst",
            status="approved",
            is_email_verified=True,
            role_id=analyst_role.role_id,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def _build_token(db: Session, user: UserDB) -> Token:
        role = db.query(RoleDB).filter(RoleDB.role_id == user.role_id).first()
        role_name = normalize_role_name(role.role_name if role else "viewer")

        access_token = create_access_token(data={"sub": user.email, "role": role_name})
        return Token(
            access_token=access_token,
            token_type="bearer",
            user_id=user.user_id,
            email=user.email,
            full_name=user.full_name or user.username,
            role=role_name,
        )

    @staticmethod
    def _get_role_by_name(db: Session, role_name: str) -> Optional[RoleDB]:
        role_name = role_name.lower()
        roles = db.query(RoleDB).all()
        for role in roles:
            if (role.role_name or "").lower() == role_name:
                return role
        return None

    @staticmethod
    def _build_unique_username(db: Session, username_seed: str) -> str:
        base = "".join(ch for ch in username_seed if ch.isalnum() or ch in {"_", "."}).strip("._")
        base = (base or "oauth_user")[:40]

        candidate = base
        i = 1
        while db.query(UserDB).filter(UserDB.username == candidate).first():
            suffix = f"_{i}"
            candidate = f"{base[: max(1, 50 - len(suffix))]}{suffix}"
            i += 1
        return candidate
