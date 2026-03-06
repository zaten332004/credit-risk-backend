"""
User Registration Service
Handles user registration, email verification, and manager approval workflow
"""
import secrets
from datetime import datetime
from typing import Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.db.models import UserDB, RoleDB
from app.core.security import pwd_context
from app.schemas.schemas import UserRegistrationRequest, UserRegistrationResponse
from app.services.email_service import EmailService


class RegistrationService:
    """Service for user registration and approval workflow"""

    @staticmethod
    def register_user(db: Session, request: UserRegistrationRequest) -> Tuple[bool, str, Optional[UserRegistrationResponse]]:
        """
        Register new user (analyst or manager)
        Returns: (success, message, response)
        """
        try:
            # Check if username/email already exists (in User table)
            existing_user = db.query(UserDB).filter(
                (UserDB.username == request.username) | (UserDB.email == request.email)
            ).first()
            if existing_user:
                return False, "Username or email already exists", None

            # Validate registration type
            if request.registration_type.lower() not in ["analyst", "manager"]:
                return False, "Registration type must be 'analyst' or 'manager'", None

            # Hash password
            hashed_pwd = pwd_context.hash(request.password)

            # Generate email verification token
            verification_token = secrets.token_urlsafe(32)

            # Determine initial status
            # Analyst: pending (auto-approved after email verification)
            # Manager: pending (requires admin approval)
            initial_status = "pending"

            # Create user record in pending status
            user = UserDB(
                username=request.username,
                email=request.email,
                password=hashed_pwd,
                full_name=request.full_name,
                phone=request.phone,
                user_type=request.registration_type.lower(),
                status=initial_status,
                verification_token=verification_token,
                verification_sent_at=datetime.utcnow(),
                role_id=None,  # Will be assigned after approval
            )

            db.add(user)
            db.commit()
            db.refresh(user)

            # Build verification URL
            verification_url = f"http://localhost:8000/api/v1/auth/register/verify-email?token={verification_token}"

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
                message=f"Registration successful! Verification email sent to {request.email}. "
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

            # For analyst: auto-approve after email verification
            if user.user_type == "analyst":
                user.status = "approved"
                # Assign analyst role
                analyst_role = db.query(RoleDB).filter(RoleDB.role_name == "Analyst").first()
                if analyst_role:
                    user.role_id = analyst_role.role_id
                
                db.commit()

                # Send approval email to analyst
                EmailService.send_registration_approved_email(
                    recipient_email=user.email,
                    full_name=user.full_name,
                    login_url="http://localhost:8000/docs"
                )

                return True, "Email verified! Your analyst account is now active. Check your email for login instructions."
            else:
                # Manager: email verified, awaiting admin approval
                # Keep status as pending until admin approves
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

                user.status = "approved"
                user.approved_by = approved_by
                user.approved_at = datetime.utcnow()
                
                # Assign manager role
                manager_role = db.query(RoleDB).filter(RoleDB.role_name == "Manager").first()
                if manager_role:
                    user.role_id = manager_role.role_id

                db.commit()

                # Send approval email
                EmailService.send_registration_approved_email(
                    recipient_email=user.email,
                    full_name=user.full_name,
                    login_url="http://localhost:8000/docs"
                )

                return True, f"Registration approved for {user.username}. Approval email sent."

            elif action.lower() == "reject":
                if not rejection_reason:
                    return False, "Rejection reason required"

                user.status = "rejected"
                user.rejection_reason = rejection_reason
                user.approved_by = approved_by
                user.approved_at = datetime.utcnow()

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
    def get_pending_registrations(db: Session, user_type: Optional[str] = None) -> list:
        """Get all pending user registrations (status=pending)"""
        query = db.query(UserDB).filter(
            UserDB.status == "pending",
            UserDB.is_email_verified == True  # Only show verified but not yet approved
        )
        if user_type:
            query = query.filter(UserDB.user_type == user_type.lower())
        return query.all()

    @staticmethod
    def get_registration_by_id(db: Session, user_id: int) -> Optional[UserDB]:
        """Get registration by user ID"""
        return db.query(UserDB).filter(
            UserDB.user_id == user_id
        ).first()
