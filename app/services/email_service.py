"""
Email Service
Handles sending verification emails, approval notifications, etc.
Supports: Console (demo), SMTP (Gmail, Outlook, etc.), Mailgun API
"""
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from app.core.config import settings


class EmailService:
    """Service for sending emails"""

    SMTP_TIMEOUT_SECONDS = 8
    MAILGUN_TIMEOUT_SECONDS = 8

    @staticmethod
    def send_verification_email(
        recipient_email: str,
        verification_token: str,
        verification_url: str,
        full_name: str | None = None
    ) -> bool:
        """
        Send email verification link
        
        Args:
            recipient_email: Email to send to
            verification_token: Token for verification
            verification_url: Full frontend URL including token (e.g., http://localhost:3000/auth/verify-email?token=xxx)
            full_name: User's full name (optional)
        
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            subject = "Email Verification - Credit Risk Management System"
            
            # HTML body
            html_body = f"""
            <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <div style="max-width: 600px; margin: 0 auto; border: 1px solid #ddd; padding: 20px; border-radius: 5px;">
                        <h2 style="color: #2c3e50;">Email Verification</h2>
                        
                        <p>Hello {full_name or 'User'},</p>
                        
                        <p>Thank you for registering with our Credit Risk Management System. To complete your registration, please verify your email address by clicking the link below:</p>
                        
                        <p style="text-align: center; margin: 30px 0;">
                            <a href="{verification_url}" 
                               style="background-color: #3498db; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">
                                Verify Email
                            </a>
                        </p>
                        
                        <p>Or copy and paste this link in your browser:</p>
                        <p style="word-break: break-all; background-color: #f5f5f5; padding: 10px; border-radius: 3px;">
                            {verification_url}
                        </p>
                        
                        <p style="color: #666; font-size: 12px;">
                            This link will expire in 24 hours. If you didn't create this account, please ignore this email.
                        </p>
                        
                        <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                        
                        <p style="color: #999; font-size: 12px; text-align: center;">
                            Credit Risk Management System<br>
                            © 2026. All rights reserved.
                        </p>
                    </div>
                </body>
            </html>
            """
            
            # Plain text fallback
            text_body = f"""
Email Verification

Hello {full_name or 'User'},

Thank you for registering with our Credit Risk Management System. To complete your registration, please verify your email address by visiting this link:

{verification_url}

This link will expire in 24 hours. If you didn't create this account, please ignore this email.

Best regards,
Credit Risk Management System
            """
            
            return EmailService._send_email(
                recipient_email=recipient_email,
                subject=subject,
                html_body=html_body,
                text_body=text_body
            )
            
        except Exception as e:
            print(f"[EMAIL_ERROR] Error sending verification email: {str(e)}")
            return False

    @staticmethod
    def send_email_change_code(
        recipient_email: str,
        verification_code: str,
        full_name: str | None = None,
    ) -> bool:
        try:
            subject = "Email Change Verification Code - Credit Risk Management System"

            html_body = f"""
            <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <div style="max-width: 600px; margin: 0 auto; border: 1px solid #ddd; padding: 20px; border-radius: 5px;">
                        <h2 style="color: #2c3e50;">Email Change Verification</h2>
                        <p>Hello {full_name or 'User'},</p>
                        <p>Use the verification code below to confirm your new email address:</p>
                        <div style="margin: 30px 0; text-align: center;">
                            <div style="display: inline-block; letter-spacing: 6px; font-size: 28px; font-weight: bold; padding: 12px 18px; background-color: #f5f7fb; border-radius: 8px; border: 1px solid #d7e0ef;">
                                {verification_code}
                            </div>
                        </div>
                        <p style="color: #666; font-size: 12px;">This code will expire in 10 minutes. If you did not request this change, please ignore this email.</p>
                    </div>
                </body>
            </html>
            """

            text_body = f"""
Email Change Verification

Hello {full_name or 'User'},

Use this verification code to confirm your new email address:

{verification_code}

This code will expire in 10 minutes. If you did not request this change, please ignore this email.
            """

            return EmailService._send_email(
                recipient_email=recipient_email,
                subject=subject,
                html_body=html_body,
                text_body=text_body,
            )
        except Exception as e:
            print(f"[EMAIL_ERROR] Error sending email change code: {str(e)}")
            return False

    @staticmethod
    def send_password_reset_code(
        recipient_email: str,
        verification_code: str,
        full_name: str | None = None,
    ) -> bool:
        try:
            subject = "Password Reset Verification Code - Credit Risk Management System"

            html_body = f"""
            <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <div style="max-width: 600px; margin: 0 auto; border: 1px solid #ddd; padding: 20px; border-radius: 5px;">
                        <h2 style="color: #2c3e50;">Password Reset</h2>
                        <p>Hello {full_name or 'User'},</p>
                        <p>Use the verification code below to reset your password:</p>
                        <div style="margin: 30px 0; text-align: center;">
                            <div style="display: inline-block; letter-spacing: 6px; font-size: 28px; font-weight: bold; padding: 12px 18px; background-color: #f5f7fb; border-radius: 8px; border: 1px solid #d7e0ef;">
                                {verification_code}
                            </div>
                        </div>
                        <p style="color: #666; font-size: 12px;">This code will expire in 10 minutes. If you did not request a password reset, please ignore this email.</p>
                    </div>
                </body>
            </html>
            """

            text_body = f"""
Password Reset

Hello {full_name or 'User'},

Use this verification code to reset your password:

{verification_code}

This code will expire in 10 minutes. If you did not request a password reset, please ignore this email.
            """

            return EmailService._send_email(
                recipient_email=recipient_email,
                subject=subject,
                html_body=html_body,
                text_body=text_body,
            )
        except Exception as e:
            print(f"[EMAIL_ERROR] Error sending password reset code: {str(e)}")
            return False

    @staticmethod
    def send_registration_approved_email(
        recipient_email: str,
        full_name: str | None = None,
        login_url: str = "http://localhost:3000/auth?mode=login"
    ) -> bool:
        """Send email notifying user registration was approved"""
        try:
            subject = "Registration Approved - Credit Risk Management System"
            
            html_body = f"""
            <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <div style="max-width: 600px; margin: 0 auto; border: 1px solid #ddd; padding: 20px; border-radius: 5px;">
                        <h2 style="color: #27ae60;">✓ Registration Approved</h2>
                        
                        <p>Hello {full_name or 'User'},</p>
                        
                        <p>Your registration has been approved! You can now log in and start using the system.</p>
                        
                        <p style="text-align: center; margin: 30px 0;">
                            <a href="{login_url}" 
                               style="background-color: #27ae60; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">
                                Log In Now
                            </a>
                        </p>
                        
                        <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                        
                        <p style="color: #999; font-size: 12px; text-align: center;">
                            Credit Risk Management System<br>
                            © 2026. All rights reserved.
                        </p>
                    </div>
                </body>
            </html>
            """
            
            text_body = f"""
Registration Approved

Hello {full_name or 'User'},

Your registration has been approved! You can now log in and start using the system.

Visit: {login_url}

Best regards,
Credit Risk Management System
            """
            
            return EmailService._send_email(
                recipient_email=recipient_email,
                subject=subject,
                html_body=html_body,
                text_body=text_body
            )
            
        except Exception as e:
            print(f"[EMAIL_ERROR] Error sending approval email: {str(e)}")
            return False

    @staticmethod
    def send_registration_rejected_email(
        recipient_email: str,
        full_name: str | None = None,
        rejection_reason: str | None = None
    ) -> bool:
        """Send email notifying user registration was rejected"""
        try:
            subject = "Registration Status - Credit Risk Management System"
            
            reason_text = rejection_reason or "Your registration did not meet the requirements."
            
            html_body = f"""
            <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <div style="max-width: 600px; margin: 0 auto; border: 1px solid #ddd; padding: 20px; border-radius: 5px;">
                        <h2 style="color: #e74c3c;">Registration Status Update</h2>
                        
                        <p>Hello {full_name or 'User'},</p>
                        
                        <p>Unfortunately, your registration has been rejected.</p>
                        
                        <p><strong>Reason:</strong></p>
                        <p style="background-color: #f5f5f5; padding: 10px; border-left: 4px solid #e74c3c; border-radius: 3px;">
                            {reason_text}
                        </p>
                        
                        <p>If you believe this is a mistake or have questions, please contact our support team.</p>
                        
                        <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                        
                        <p style="color: #999; font-size: 12px; text-align: center;">
                            Credit Risk Management System<br>
                            © 2026. All rights reserved.
                        </p>
                    </div>
                </body>
            </html>
            """
            
            text_body = f"""
Registration Status Update

Hello {full_name or 'User'},

Unfortunately, your registration has been rejected.

Reason: {reason_text}

If you believe this is a mistake or have questions, please contact our support team.

Best regards,
Credit Risk Management System
            """
            
            return EmailService._send_email(
                recipient_email=recipient_email,
                subject=subject,
                html_body=html_body,
                text_body=text_body
            )
            
        except Exception as e:
            print(f"[EMAIL_ERROR] Error sending rejection email: {str(e)}")
            return False

    @staticmethod
    def _send_email(
        recipient_email: str,
        subject: str,
        html_body: str,
        text_body: str
    ) -> bool:
        """
        Internal method to send email
        
        Supports multiple backends:
        - console: Logs to console (demo mode)
        - smtp: Traditional SMTP (Gmail, Outlook, etc.)
        - mailgun: Mailgun API (easiest to setup)
        """
        try:
            # Global kill-switch: keep API flows running but skip real email delivery.
            if not getattr(settings, "SMTP_ENABLED", False):
                print(f"[EMAIL_DISABLED] Skip sending email to {recipient_email}: {subject}")
                return True

            backend = getattr(settings, 'EMAIL_BACKEND', 'console')
            
            if backend == "mailgun":
                return EmailService._send_mailgun(recipient_email, subject, html_body, text_body)
            elif backend == "smtp":
                return EmailService._send_smtp(recipient_email, subject, html_body, text_body)
            else:  # console (demo mode)
                print("\n[DEMO MODE] Email notification:")
                print(f"   To: {recipient_email}")
                print(f"   Subject: {subject}")
                print(f"   Body: {text_body[:100]}...")
                return True
                
        except Exception as e:
            print(f"[EMAIL_ERROR] Email error: {str(e)}")
            return False
    
    @staticmethod
    def _send_mailgun(
        recipient_email: str,
        subject: str,
        html_body: str,
        text_body: str
    ) -> bool:
        """Send email via Mailgun API (recommended)"""
        try:
            api_key = getattr(settings, 'MAILGUN_API_KEY', '')
            domain = getattr(settings, 'MAILGUN_DOMAIN', '')
            
            if not api_key or not domain:
                print("[EMAIL_WARN] Mailgun API key or domain not configured. Falling back to console mode.")
                print(f"[CONSOLE] Email to {recipient_email}: {subject}")
                return True
            
            return requests.post(
                f"https://api.mailgun.net/v3/{domain}/messages",
                auth=("api", api_key),
                data={
                    "from": getattr(settings, 'SMTP_FROM', 'Credit Risk <noreply@creditrisk.com>'),
                    "to": recipient_email,
                    "subject": subject,
                    "text": text_body,
                    "html": html_body
                },
                timeout=EmailService.MAILGUN_TIMEOUT_SECONDS,
            ).status_code == 200
            
        except Exception as e:
            print(f"[EMAIL_ERROR] Mailgun error: {str(e)}")
            return False
    
    @staticmethod
    def _send_smtp(
        recipient_email: str,
        subject: str,
        html_body: str,
        text_body: str
    ) -> bool:
        """Send email via SMTP (Gmail, Outlook, etc.)"""
        try:
            smtp_server = getattr(settings, 'SMTP_SERVER', '')
            smtp_port = getattr(settings, 'SMTP_PORT', 587)
            smtp_user = getattr(settings, 'SMTP_USER', '')
            smtp_password = getattr(settings, 'SMTP_PASSWORD', '')
            from_email = getattr(settings, 'SMTP_FROM', 'noreply@creditrisk.com')
            
            if not smtp_user or not smtp_password:
                print("[EMAIL_WARN] SMTP credentials not configured. Falling back to console mode.")
                print(f"[CONSOLE] Email to {recipient_email}: {subject}")
                return True
            
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = from_email
            msg['To'] = recipient_email
            
            msg.attach(MIMEText(text_body, 'plain'))
            msg.attach(MIMEText(html_body, 'html'))
            
            with smtplib.SMTP(
                smtp_server,
                smtp_port,
                timeout=EmailService.SMTP_TIMEOUT_SECONDS,
            ) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.send_message(msg)
            
            print(f"[EMAIL_OK] Email sent to {recipient_email}")
            return True
            
        except Exception as e:
            print(f"[EMAIL_ERROR] SMTP error: {str(e)}")
            return False

