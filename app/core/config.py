from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Credit Risk Analysis Dashboard & Chatbot System"
    API_V1_PREFIX: str = "/api/v1"

    # Optional: allow loading from .env without breaking when absent
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
