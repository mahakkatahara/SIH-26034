"""
Application Configuration — loaded from environment variables via pydantic-settings
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import List, Union
import json


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Application
    APP_ENV: str = "development"
    APP_NAME: str = "Legal Metrology Inspection System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # Server
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    BACKEND_CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="after")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            if v.startswith("["):
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    # Database
    DATABASE_URL: str = (
        "postgresql+asyncpg://lmis_user:changeme@localhost:5432/legal_metrology_db"
    )

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""

    # JWT
    JWT_SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION_32_CHAR_MIN"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # File uploads
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 20
    ALLOWED_IMAGE_TYPES: Union[List[str], str] = [
        "image/jpeg", "image/png", "image/webp", "image/tiff"
    ]

    @field_validator("ALLOWED_IMAGE_TYPES", mode="after")
    @classmethod
    def parse_allowed_types(cls, v):
        if isinstance(v, str):
            if v.startswith("["):
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [t.strip() for t in v.split(",") if t.strip()]
        return v

    # AI Pipeline
    AI_PIPELINE_MODE: str = "stub"   # stub | paddleocr | custom
    AI_CONFIDENCE_THRESHOLD: float = 0.75
    AI_STUB_DELAY_SECONDS: float = 2.0

    # Rule Engine
    RULES_FILE_PATH: str = "../rule-engine/rules/rules.json"
    RULE_ENGINE_VERSION: str = "1.0.0"

    # Reports
    REPORT_OUTPUT_DIR: str = "./reports/output"

    # LLM (Phase 7)
    LLM_ENABLED: bool = False
    LLM_PROVIDER: str = ""
    LLM_API_KEY: str = ""
    LLM_MODEL: str = ""

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"


settings = Settings()
