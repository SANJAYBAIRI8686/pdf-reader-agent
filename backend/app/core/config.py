import os
from pathlib import Path
from typing import Any, Dict, Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    # Project Setup
    APP_NAME: str = "AI Research Assistant"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"

    # Security
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days

    # Database
    DATABASE_URL: str

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_url(cls, v: Optional[str]) -> str:
        if not v:
            # Fallback to local SQLite if DATABASE_URL is not set
            return "sqlite:///./research_assistant.db"
        # FastAPI / SQLAlchemy requires a sqlite+aiosqlite prefix if running asynchronously,
        # but for clean, standard synchronous setup we keep sqlite.
        # Let's ensure SQLite connections use correct parameters
        return v

    # AI & RAG
    OPENAI_API_KEY: str
    LLM_PROVIDER: str = "openai"  # openai or ollama
    LLM_MODEL: str = "gpt-4o-mini"
    EMBEDDING_MODEL: str = "text-embedding-3-small"

    # Vector Storage
    CHROMA_DB_DIR: str = "./chroma_data"
    CHROMA_COLLECTION_NAME: str = "research_documents"

    # File Upload Settings
    UPLOAD_DIR: str = "./uploaded_files"
    MAX_UPLOAD_SIZE_MB: int = 50

    def get_upload_path(self) -> Path:
        path = Path(self.UPLOAD_DIR)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_chroma_path(self) -> Path:
        path = Path(self.CHROMA_DB_DIR)
        path.mkdir(parents=True, exist_ok=True)
        return path

# Instantiate the settings singleton
settings = Settings()
