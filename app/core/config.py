from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Credit Risk Analysis Dashboard & Chatbot System"
    API_V1_PREFIX: str = "/api/v1"

    # Email Configuration
    SMTP_ENABLED: bool = False  # Set to True to enable real email sending
    EMAIL_BACKEND: str = "console"  # Options: console, smtp, mailgun
    
    # SMTP Configuration (for traditional email)
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "noreply@creditrisk.com"
    
    # Mailgun Configuration (alternative to SMTP)
    MAILGUN_API_KEY: str = ""
    MAILGUN_DOMAIN: str = ""
    
    # Optional: allow loading from .env without breaking when absent
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
