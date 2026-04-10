from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Credit Risk Analysis Dashboard & Chatbot System"
    API_V1_PREFIX: str = "/api/v1"
    FRONTEND_BASE_URL: str = "http://localhost:3000"
    BACKEND_PUBLIC_BASE_URL: str = "http://localhost:8000"

    # Email Configuration
    SMTP_ENABLED: bool = False  # Set to True to enable real email sending
    EMAIL_BACKEND: str = "console"  # Options: console, smtp, mailgun, resend

    # Resend (HTTPS API — works on Railway where outbound SMTP is often blocked)
    RESEND_API_KEY: str = ""

    # SMTP Configuration (for traditional email)
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "noreply@creditrisk.com"

    # Mailgun Configuration (alternative to SMTP)
    MAILGUN_API_KEY: str = ""
    MAILGUN_DOMAIN: str = ""

    # OAuth login
    google_oauth_client_id: str = ""
    github_oauth_client_id: str = ""

    # Database
    DATABASE_URL: str = ""
    SECRET_KEY: str = ""
    # JWT lifetime (minutes). Frontend enforces idle logout separately; keep this long enough for active work sessions.
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080

    # AI providers
    ai_chat_provider: str = ""  # gemini|openai|langflow|mock
    ai_chat_context_source: str = ""  # db|powerbi
    gemini_api_key: str = ""
    gemini_model: str = ""
    openai_api_key: str = ""
    openai_model: str = ""
    # Debug/testing toggles
    ai_chat_powerbi_query_allow_any: bool = False

    # Optional FAQ retrieval context for Gemini chat
    bank_faq_csv_path: str = ""
    bank_faq_top_k: int = 3

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
    # Contract / sampling hub table (align with loan portfolio semantic model, not AI_Context).
    power_bi_ai_context_table: str = "LoanPortfolio"
    power_bi_ai_context_max_rows: int = 200
    power_bi_ai_context_max_chars: int = 4000
    # all_tables|contract_table
    power_bi_ai_context_mode: str = "all_tables"
    # Department-style facts/dims (customer / loans / collateral), similar to loan_dataset CSV domains.
    power_bi_ai_context_tables: str = "CustomerMaster,LoanPortfolio,CollateralRegister"
    power_bi_ai_context_max_tables: int = 12
    power_bi_ai_context_max_columns: int = 8
    # Optional comma-separated keys to warn if missing on contract_table (empty = skip check).
    power_bi_ai_context_required_keys: str = ""

    # Optional: allow loading from .env without breaking when absent
    # IMPORTANT: extra="ignore" so unknown keys in .env won't crash startup.
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
