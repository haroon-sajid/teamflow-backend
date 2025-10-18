# ================================================================
# core/config.py — FastAPI Configuration (SendGrid + Pydantic v2)
# ================================================================
from pydantic_settings import BaseSettings
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

    class Config:
        env_file = ".env"


# Global settings instance
settings = Settings()
