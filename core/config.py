# ================================================================
# core/config.py — FastAPI Configuration (Render + SendGrid + Pydantic v2)
# ================================================================
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import EmailStr


class Settings(BaseSettings):
    # ------------------------
    # DATABASE CONFIG
    # ------------------------
    DATABASE_URL: str

    # ------------------------
    # SECURITY CONFIG
    # ------------------------
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # ------------------------
    # SENDGRID EMAIL CONFIG
    # ------------------------
    SENDGRID_API_KEY: str
    MAIL_FROM: EmailStr  # example: "TeamFlow <your_email@gmail.com>"

    # ------------------------
    # FRONTEND CONFIG
    # ------------------------
    FRONTEND_URL: str

    # ------------------------
    # ENVIRONMENT
    # ------------------------
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # ------------------------
    # Pydantic v2 Config
    # ------------------------
    model_config = SettingsConfigDict(
        env_file=".env",          # Loads from local .env in development
        env_file_encoding="utf-8",
        extra="ignore"            # Ignores unknown env vars (e.g., Render defaults)
    )


# Global settings instance
settings = Settings()
