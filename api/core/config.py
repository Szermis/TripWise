# app/core/config.py

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "TripWise"
    API_V1_STR: str = "/api/v1"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./TripWise.db"

    # Security
    SECRET_KEY: str = "your-super-secret-key"

    # AI
    OPENAI_API_KEY: str = "your-openai-api-key"

    # CORS
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"]

    class Config:
        env_file = ".env"


settings = Settings()
