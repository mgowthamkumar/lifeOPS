import os
import json
from pathlib import Path
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings

# Base directory for the project
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent

import sys

# Ensure backend root is in sys.path
backend_dir = (BASE_DIR / "backend").resolve()
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

class Settings(BaseSettings):
    APP_NAME: str = "LifeOps AI"
    APP_ENV: str = "development"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "127.0.0.1"
    
    # CORS
    CORS_ORIGINS: Union[str, List[str]] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ]

    # Database
    DATABASE_URL: str = "sqlite:///./data/lifeops.db"

    # Storage paths
    UPLOAD_DIRECTORY: str = "./data/uploads"
    CHROMA_PERSIST_DIRECTORY: str = "./data/chroma"
    MAX_UPLOAD_SIZE_MB: int = 25

    # AI / LLM Configuration
    GEMINI_API_KEY: str = ""
    LLM_MODEL: str = "gemini-2.5-flash"
    EMBEDDING_MODEL: str = "models/text-embedding-004"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                return [i.strip() for i in v.split(",") if i.strip()]
        return v

    def resolve_path(self, relative_path: str) -> Path:
        """Resolves relative storage paths to absolute paths within workspace."""
        path = Path(relative_path)
        if not path.is_absolute():
            return (BASE_DIR / path).resolve()
        return path

    def get_database_url(self) -> str:
        """Returns database URL with absolute file path for SQLite."""
        if self.DATABASE_URL.startswith("sqlite:///./") or self.DATABASE_URL.startswith("sqlite:////"):
            # Extract relative path after sqlite:///
            rel_part = self.DATABASE_URL.replace("sqlite:///", "")
            abs_path = self.resolve_path(rel_part)
            abs_path.parent.mkdir(parents=True, exist_ok=True)
            return f"sqlite:///{abs_path.as_posix()}"
        return self.DATABASE_URL

    def ensure_directories(self) -> None:
        """Ensure necessary storage directories exist."""
        upload_path = self.resolve_path(self.UPLOAD_DIRECTORY)
        chroma_path = self.resolve_path(self.CHROMA_PERSIST_DIRECTORY)
        db_parent = self.resolve_path("./data")
        
        upload_path.mkdir(parents=True, exist_ok=True)
        chroma_path.mkdir(parents=True, exist_ok=True)
        db_parent.mkdir(parents=True, exist_ok=True)

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
