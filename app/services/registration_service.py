"""
User Registration Service
Handles user registration, email verification, and manager approval workflow
"""
import secrets
from datetime import datetime
from typing import Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import aliased

from app.db.models import UserDB, RoleDB
from app.core.config import settings
from app.core.security import pwd_context
from app.schemas.schemas import UserRegistrationRequest, UserRegistrationResponse
from app.services.audit_service import log_action
from app.services.email_service import EmailService


class RegistrationService:
    """Service for user registration and approval workflow"""

    @staticmethod
    def _build_unique_username(db: Session, username_seed: str) -> str:
        base = "".join(ch for ch in (username_seed or "") if ch.isalnum() or ch in {"_", "."}).strip("._")
        base = (base or "user")[:40]

        candidate = base
        i = 1
        while db.query(UserDB).filter(UserDB.username == candidate).first():
            suffix = f"_{i}"
            candidate = f"{base[: max(1, 50 - len(suffix))]}{suffix}"
            i += 1
        return candidate

    @staticmethod
    def _serialize_registration(user: UserDB, approver: UserDB | None = None) -> dict:
        approver_name = None
        if approver:
            approver_name = approver.full_name or approver.username

        return {
            "user_id": user.user_id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "phone": user.phone,
            "user_type": user.user_type,
            "status": user.status,
            "is_email_verified": user.is_email_verified,
            "created_at": user.created_at,
            "approved_by": user.approved_by,
            "approved_by_name": approver_name,
            "approved_at": user.approved_at,
            "rejection_reason": user.rejection_reason,
        }

    @staticmethod
    def _frontend_verify_url(token: str) -> str:
        base_url = settings.FRONTEND_BASE_URL.rstrip("/")
        return f"{base_url}/auth/verify-email?token={token}"

    @staticmethod
    def _frontend_login_url() -> str:
        base_url = settings.FRONTEND_BASE_URL.rstrip("/")
        return f"{base_url}/auth?mode=login"

    @staticmethod
    def resend_verification_email(db: Session, email: str) -> Tuple[bool, str]:
        normalized_email = (email or "").strip().lower()
        if not normalized_email:
            return False, "Email is required"

        user = db.query(UserDB).filter(UserDB.email == normalized_email).first()
        if not user:
            return False, "Registration not found"

        if user.is_email_verified:
            return False, "Email already verified"

        verification_token = secrets.token_urlsafe(32)
        user.verification_token = verification_token
        user.verification_sent_at = datetime.utcnow()

        verification_url = RegistrationService._frontend_verify_url(verification_token)

        email_sent = EmailService.send_verification_email(
            recipient_email=user.email,
            verification_token=verification_token,
            verification_url=verification_url,
            full_name=user.full_name,
        )

        if not email_sent:
            db.rollback()
            return False, "Could not send verification email"

        log_action(
            db,
            user_id=user.user_id,
            action="RESEND_VERIFICATION_EMAIL",
            entity_type="UserRegistration",
            entity_id=user.user_id,
            new_value={
                "email": user.email,
                "verification_sent_at": user.verification_sent_at.isoformat() if user.verification_sent_at else None,
            },
        )
        db.commit()
        return True, f"Verification email sent again to {user.email}"

    @staticmethod
    def register_user(db: Session, request: UserRegistrationRequest) -> Tuple[bool, str, Optional[UserRegistrationResponse]]:
        """
        Register new user (analyst or manager)
        Returns: (success, message, response)
        """
        try:
            normalized_email = (request.email or "").strip().lower()
            existing_email = db.query(UserDB).filter(UserDB.email == normalized_email).first()
            if existing_email:
                return False, "Email already exists", None

            # Validate registration type
            if request.registration_type.lower() not in ["analyst", "manager"]:
                return False, "Registration type must be 'analyst' or 'manager'", None

            # Hash password
            hashed_pwd = pwd_context.hash(request.password)
            username = RegistrationService._build_unique_username(db, request.username)

            # Generate email verification token
            verification_token = secrets.token_urlsafe(32)

            # Determine initial status
            # Analyst: pending (auto-approved after email verification)
            # Manager: pending (requires admin approval)
            initial_status = "pending"

            # Create user record in pending status
            user = UserDB(
                username=username,
                email=normalized_email,
                password_hash=hashed_pwd,
                full_name=request.full_name,
                phone=request.phone,
                user_type=request.registration_type.lower(),
                status=initial_status,
                verification_token=verification_token,
                verification_sent_at=datetime.utcnow(),
                role_id=None,  # Will be assigned after approval
            )

            db.add(user)
            db.flush()
            log_action(
                db,
                user_id=user.user_id,
                action="REGISTER_USER",
                entity_type="UserRegistration",
                entity_id=user.user_id,
                new_value={
                    "username": user.username,
                    "email": user.email,
                    "user_type": user.user_type,
                    "status": user.status,
                },
            )
            db.commit()
            db.refresh(user)

            # Build verification URL
            verification_url = RegistrationService._frontend_verify_url(verification_token)

            # Send verification email
            email_sent = EmailService.send_verification_email(
                recipient_email=request.email,
                verification_token=verification_token,
                verification_url=verification_url,
                full_name=request.full_name
            )

            response = UserRegistrationResponse(
                registration_id=user.user_id,
                username=user.username,
                email=user.email,
                registration_type=user.user_type,
                status=user.status,
                is_email_verified=user.is_email_verified,
                verification_token=verification_token,
                verification_link=verification_url,
                created_at=user.created_at,
                message=f"Registration successful! Verification email sent to {user.email}. "
                        f"Please click the link in the email to verify your account. "
                        f"For manager registration, admin approval will be required after email verification."
            )

            return True, "Registration successful", response

        except IntegrityError as e:
            db.rollback()
            return False, f"Database error: {str(e)}", None
        except Exception as e:
            db.rollback()
            return False, f"Registration error: {str(e)}", None

    @staticmethod
    def verify_email(db: Session, token: str) -> Tuple[bool, str]:
        """
        Verify user email with token
        Returns: (success, message)
        """
        try:
            user = db.query(UserDB).filter(
                UserDB.verification_token == token
            ).first()

            if not user:
                return False, "Invalid verification token"

            if user.is_email_verified:
                return False, "Email already verified"

            user.is_email_verified = True
            user.verification_token = None
            old_state = {
                "status": user.status,
                "is_email_verified": False,
                "role_id": user.role_id,
            }

            # Keep all registration types pending until admin approval.
            log_action(
                db,
                user_id=user.user_id,
                action="VERIFY_EMAIL",
                entity_type="UserRegistration",
                entity_id=user.user_id,
                old_value=old_state,
                new_value={
                    "status": user.status,
                    "is_email_verified": user.is_email_verified,
                    "role_id": user.role_id,
                },
            )
            db.commit()
            return True, "Email verified successfully! Your account is pending admin approval."

        except Exception as e:
            db.rollback()
            return False, f"Verification error: {str(e)}"

    @staticmethod
    def approve_registration(
        db: Session,
        user_id: int,
        approved_by: int,
        action: str,
        rejection_reason: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Admin approves or rejects manager registration
        Returns: (success, message)
        """
        try:
            user = db.query(UserDB).filter(
                UserDB.user_id == user_id
            ).first()

            if not user:
                return False, "User not found"

            if user.status != "pending":
                return False, f"User already {user.status}"

            if action.lower() == "approve":
                # Check if email is verified
                if not user.is_email_verified:
                    return False, "Email must be verified before approval"

                old_state = {
                    "status": user.status,
                    "role_id": user.role_id,
                    "approved_by": user.approved_by,
                    "approved_at": user.approved_at.isoformat() if user.approved_at else None,
                }
                user.status = "approved"
                user.approved_by = approved_by
                user.approved_at = datetime.utcnow()
                
                # Assign role based on registration type
                if (user.user_type or "").strip().lower() == "manager":
                    selected_role = (
                        db.query(RoleDB)
                        .filter(RoleDB.role_name.in_(["manager", "Manager"]))
                        .first()
                    )
                else:
                    selected_role = (
                        db.query(RoleDB)
                        .filter(RoleDB.role_name.in_(["risk analyst", "Risk Analyst", "analyst", "Analyst"]))
                        .first()
                    )
                if selected_role:
                    user.role_id = selected_role.role_id

                log_action(
                    db,
                    user_id=approved_by,
                    action="APPROVE_REGISTRATION",
                    entity_type="UserRegistration",
                    entity_id=user.user_id,
                    old_value=old_state,
                    new_value={
                        "status": user.status,
                        "role_id": user.role_id,
                        "approved_by": user.approved_by,
                        "approved_at": user.approved_at.isoformat() if user.approved_at else None,
                    },
                )

                db.commit()

                # Send approval email
                EmailService.send_registration_approved_email(
                    recipient_email=user.email,
                    full_name=user.full_name,
                    login_url=RegistrationService._frontend_login_url()
                )

                return True, f"Registration approved for {user.username}. Approval email sent."

            elif action.lower() == "reject":
                if not rejection_reason:
                    return False, "Rejection reason required"

                old_state = {
                    "status": user.status,
                    "rejection_reason": user.rejection_reason,
                    "approved_by": user.approved_by,
                    "approved_at": user.approved_at.isoformat() if user.approved_at else None,
                }
                user.status = "rejected"
                user.rejection_reason = rejection_reason
                user.approved_by = approved_by
                user.approved_at = datetime.utcnow()

                log_action(
                    db,
                    user_id=approved_by,
                    action="REJECT_REGISTRATION",
                    entity_type="UserRegistration",
                    entity_id=user.user_id,
                    old_value=old_state,
                    new_value={
                        "status": user.status,
                        "rejection_reason": user.rejection_reason,
                        "approved_by": user.approved_by,
                        "approved_at": user.approved_at.isoformat() if user.approved_at else None,
                    },
                )

                db.commit()

                # Send rejection email
                EmailService.send_registration_rejected_email(
                    recipient_email=user.email,
                    full_name=user.full_name,
                    rejection_reason=rejection_reason
                )

                return True, f"Registration rejected for {user.username}. Rejection email sent."

            else:
                return False, "Action must be 'approve' or 'reject'"

        except Exception as e:
            db.rollback()
            return False, f"Approval error: {str(e)}"

    @staticmethod
    def list_registrations(db: Session, user_type: Optional[str] = None, status: Optional[str] = None) -> list[dict]:
        """Get registrations for admin review filtered by type and status."""
        approver_alias = aliased(UserDB)
        effective_user_type = (user_type or "").strip().lower()
        effective_status = (status or "all").strip().lower()

        query = (
            db.query(UserDB, approver_alias)
            .outerjoin(approver_alias, approver_alias.user_id == UserDB.approved_by)
        )
        if effective_user_type and effective_user_type != "all":
            query = query.filter(UserDB.user_type == effective_user_type)
        if effective_status != "all":
            query = query.filter(UserDB.status == effective_status)

        rows = query.order_by(UserDB.created_at.desc()).all()
        return [RegistrationService._serialize_registration(user, approver) for user, approver in rows]

    @staticmethod
    def get_registration_by_id(db: Session, user_id: int) -> Optional[dict]:
        """Get registration by user ID."""
        approver_alias = aliased(UserDB)
        row = (
            db.query(UserDB, approver_alias)
            .outerjoin(approver_alias, approver_alias.user_id == UserDB.approved_by)
            .filter(UserDB.user_id == user_id)
            .first()
        )
        if not row:
            return None

        user, approver = row
        return RegistrationService._serialize_registration(user, approver)
