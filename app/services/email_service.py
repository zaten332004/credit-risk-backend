"""
Email Service
Handles sending verification emails, approval notifications, etc.
Supports: Console (demo), SMTP (often blocked on Railway), Mailgun API, Resend API
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
    RESEND_TIMEOUT_SECONDS = 8

    @staticmethod
    def _display_name(full_name: str | None) -> str:
        name = (full_name or "").strip()
        return name or "User"

    @staticmethod
    def _normalize_from_address(raw_from: str | None) -> str:
        value = (raw_from or "").strip()
        if not value:
            return "Credit Risk <noreply@creditrisk.com>"
        if "<" in value and ">" in value:
            return value
        if "@" in value:
            return f"Credit Risk <{value}>"
        return value

    @staticmethod
    def _build_email_html(
        *,
        title: str,
        greeting: str,
        intro: str,
        action_label: str | None = None,
        action_url: str | None = None,
        code: str | None = None,
        note: str | None = None,
        extra_html: str | None = None,
    ) -> str:
        action_html = ""
        if action_label and action_url:
            action_html = f"""
            <p style="text-align:center; margin:24px 0;">
                <a href="{action_url}" style="background:#1f6feb; color:#ffffff; text-decoration:none; padding:10px 18px; border-radius:8px; display:inline-block; font-weight:600;">
                    {action_label}
                </a>
            </p>
            <p style="word-break:break-all; background:#f6f8fa; padding:10px 12px; border-radius:8px; color:#475467; font-size:13px;">
                {action_url}
            </p>
            """

        code_html = ""
        if code:
            code_html = f"""
            <div style="margin:24px 0; text-align:center;">
                <span style="display:inline-block; letter-spacing:6px; font-size:28px; font-weight:700; padding:12px 18px; background:#f6f8fa; border:1px solid #e5e7eb; border-radius:10px;">
                    {code}
                </span>
            </div>
            """

        note_html = f'<p style="color:#667085; font-size:12px; margin-top:16px;">{note}</p>' if note else ""
        extra = extra_html or ""

        return f"""
        <html>
            <body style="font-family:Arial, Helvetica, sans-serif; background:#f2f4f7; margin:0; padding:24px; color:#101828;">
                <div style="max-width:640px; margin:0 auto; background:#ffffff; border:1px solid #eaecf0; border-radius:12px; padding:24px;">
                    <p style="margin:0 0 8px; color:#475467; font-size:12px; letter-spacing:.04em; text-transform:uppercase;">Credit Risk Management System</p>
                    <h2 style="margin:0 0 16px; font-size:22px; color:#101828;">{title}</h2>
                    <p style="margin:0 0 12px;">{greeting}</p>
                    <p style="margin:0 0 8px; color:#344054;">{intro}</p>
                    {code_html}
                    {action_html}
                    {extra}
                    {note_html}
                    <hr style="border:none; border-top:1px solid #eaecf0; margin:24px 0 12px;">
                    <p style="margin:0; color:#98a2b3; font-size:12px;">This is an automated email from Credit Risk Management System.</p>
                </div>
            </body>
        </html>
        """

    @staticmethod
    def _build_email_text(
        *,
        title: str,
        greeting: str,
        intro: str,
        action_url: str | None = None,
        code: str | None = None,
        note: str | None = None,
        extra_lines: list[str] | None = None,
    ) -> str:
        lines: list[str] = [title, "", greeting, "", intro]
        if code:
            lines.extend(["", f"Code: {code}"])
        if action_url:
            lines.extend(["", f"Link: {action_url}"])
        if extra_lines:
            lines.extend([""] + extra_lines)
        if note:
            lines.extend(["", note])
        lines.extend(["", "Credit Risk Management System"])
        return "\n".join(lines)

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
            subject = "Verify your email - Credit Risk"
            html_body = EmailService._build_email_html(
                title="Email verification required",
                greeting=f"Hello {EmailService._display_name(full_name)},",
                intro="Thank you for registering. Please verify your email to activate your account.",
                action_label="Verify email",
                action_url=verification_url,
                note="This link expires in 24 hours. If you did not sign up, you can safely ignore this message.",
            )
            text_body = EmailService._build_email_text(
                title="Email verification",
                greeting=f"Hello {EmailService._display_name(full_name)},",
                intro="Please verify your email to activate your account.",
                action_url=verification_url,
                note="This link expires in 24 hours.",
            )
            
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
            subject = "Email change code - Credit Risk"
            html_body = EmailService._build_email_html(
                title="Confirm your new email address",
                greeting=f"Hello {EmailService._display_name(full_name)},",
                intro="Use the verification code below to complete your email change request.",
                code=verification_code,
                note="This code expires in 10 minutes. If you did not request this change, please ignore this message.",
            )
            text_body = EmailService._build_email_text(
                title="Email change verification",
                greeting=f"Hello {EmailService._display_name(full_name)},",
                intro="Use the code below to confirm your new email address.",
                code=verification_code,
                note="This code expires in 10 minutes.",
            )

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
            subject = "Password reset code - Credit Risk"
            html_body = EmailService._build_email_html(
                title="Password reset request",
                greeting=f"Hello {EmailService._display_name(full_name)},",
                intro="Use the verification code below to reset your password.",
                code=verification_code,
                note="This code expires in 10 minutes. If you did not request a password reset, ignore this email.",
            )
            text_body = EmailService._build_email_text(
                title="Password reset",
                greeting=f"Hello {EmailService._display_name(full_name)},",
                intro="Use the code below to reset your password.",
                code=verification_code,
                note="This code expires in 10 minutes.",
            )

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
            subject = "Registration approved - Credit Risk"
            html_body = EmailService._build_email_html(
                title="Your registration is approved",
                greeting=f"Hello {EmailService._display_name(full_name)},",
                intro="Your account has been approved. You can now sign in and start using the system.",
                action_label="Log in now",
                action_url=login_url,
            )
            text_body = EmailService._build_email_text(
                title="Registration approved",
                greeting=f"Hello {EmailService._display_name(full_name)},",
                intro="Your account has been approved. You can now log in.",
                action_url=login_url,
            )
            
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
            subject = "Registration status update - Credit Risk"
            reason_text = rejection_reason or "Your registration did not meet the requirements."
            html_body = EmailService._build_email_html(
                title="Registration update",
                greeting=f"Hello {EmailService._display_name(full_name)},",
                intro="Unfortunately, your registration request was not approved.",
                extra_html=(
                    '<p style="margin:16px 0 6px;"><strong>Reason:</strong></p>'
                    f'<p style="margin:0; background:#fef3f2; border:1px solid #fecdca; color:#b42318; padding:12px; border-radius:8px;">{reason_text}</p>'
                ),
                note="If you believe this is a mistake, please contact support.",
            )
            text_body = EmailService._build_email_text(
                title="Registration status update",
                greeting=f"Hello {EmailService._display_name(full_name)},",
                intro="Your registration request was not approved.",
                extra_lines=[f"Reason: {reason_text}", "If you believe this is a mistake, please contact support."],
            )
            
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
        - resend: Resend API over HTTPS (recommended on Railway; SMTP ports often blocked)
        """
        try:
            backend = getattr(settings, 'EMAIL_BACKEND', 'console')
            
            if backend == "mailgun":
                return EmailService._send_mailgun(recipient_email, subject, html_body, text_body)
            elif backend == "resend":
                return EmailService._send_resend(recipient_email, subject, html_body, text_body)
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
                    "from": EmailService._normalize_from_address(getattr(settings, 'SMTP_FROM', 'Credit Risk <noreply@creditrisk.com>')),
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
    def _send_resend(
        recipient_email: str,
        subject: str,
        html_body: str,
        text_body: str,
    ) -> bool:
        """Send via Resend REST API (port 443; avoids Railway SMTP blocks)."""
        try:
            api_key = (getattr(settings, "RESEND_API_KEY", None) or "").strip()
            from_addr = EmailService._normalize_from_address(getattr(settings, "SMTP_FROM", None))
            if not api_key:
                print("[EMAIL_WARN] RESEND_API_KEY not set. Falling back to console mode.")
                print(f"[CONSOLE] Email to {recipient_email}: {subject}")
                return True
            if not from_addr:
                print("[EMAIL_WARN] SMTP_FROM not set for Resend. Set e.g. 'App <onboarding@resend.dev>' or your verified domain.")
                return False

            resp = requests.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": from_addr,
                    "to": [recipient_email],
                    "subject": subject,
                    "html": html_body,
                    "text": text_body,
                },
                timeout=EmailService.RESEND_TIMEOUT_SECONDS,
            )
            if resp.status_code in (200, 201):
                print(f"[EMAIL_OK] Resend accepted email to {recipient_email}")
                return True
            print(f"[EMAIL_ERROR] Resend HTTP {resp.status_code}: {resp.text[:500]}")
            return False
        except Exception as e:
            print(f"[EMAIL_ERROR] Resend error: {str(e)}")
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

