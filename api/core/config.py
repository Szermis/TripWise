import json

from pydantic import field_validator
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

    @field_validator("ALLOWED_ORIGINS", mode="before")
    def parse_allowed_origins(cls, v):
        if isinstance(v, str):
            # Try JSON first
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                # Fallback to comma-separated
                return [item.strip() for item in v.split(",")]
        return v

    class Config:
        env_file = ".env"


settings = Settings()
