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

    # AI providers
    ai_chat_provider: str = ""  # gemini|openai|langflow|mock
    ai_chat_context_source: str = ""  # db|powerbi
    gemini_api_key: str = ""
    gemini_model: str = ""
    openai_api_key: str = ""
    openai_model: str = ""
    # Debug/testing toggles
    ai_chat_powerbi_query_allow_any: bool = False

    # CORS (comma-separated). Example: "http://localhost:5173,http://localhost:3000"
    cors_allow_origins: str = ""

    # Power BI (Service Principal)
    power_bi_tenant_id: str = ""
    power_bi_client_id: str = ""
    power_bi_client_secret: str = ""
    # Optional: default workspace/dataset for backend-to-PowerBI queries
    power_bi_workspace_id: str = ""
    power_bi_dataset_id: str = ""
    # Optional: custom DAX query to build AI context from Power BI directly.
    # If unset, context generation will return guidance instead of running hardcoded queries.
    power_bi_ai_context_dax: str = ""
    # Approach A: fixed "contract" table name for AI context in Power BI dataset
    power_bi_ai_context_table: str = "AI_Context"
    power_bi_ai_context_max_rows: int = 200
    power_bi_ai_context_max_chars: int = 4000
    # Comma-separated list of keys expected in AI_Context (warn if missing).
    power_bi_ai_context_required_keys: str = "DatasetName,DateRange"

    # Optional: allow loading from .env without breaking when absent
    # IMPORTANT: extra="ignore" so unknown keys in .env won't crash startup.
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
