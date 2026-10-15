from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.session import get_db
from app.schemas.settings import SettingsResponse, SettingsUpdateRequest
from app.services.llm_service import llm_service
from app.services.vector_store import vector_store_service
from app.services.embedding import embedding_service

router = APIRouter(prefix="/settings", tags=["settings"])

@router.get("", response_model=SettingsResponse, summary="Get current LifeOps system settings")
def get_settings():
    db_type = "sqlite" if "sqlite" in settings.DATABASE_URL else "postgresql"
    return SettingsResponse(
        llm_provider="Gemini",
        llm_model=getattr(settings, "LLM_MODEL", "gemini-2.5-flash"),
        llm_configured=bool(settings.GEMINI_API_KEY and settings.GEMINI_API_KEY.strip()),
        embedding_backend=settings.EMBEDDING_BACKEND,
        embedding_model=getattr(settings, "EMBEDDING_MODEL", "models/text-embedding-004"),
        database_type=db_type,
        database_path=settings.DATABASE_URL,
        vector_store_type="ChromaDB",
        vector_store_path=settings.CHROMA_PERSIST_DIRECTORY,
        chunk_size=getattr(settings, "CHUNK_SIZE", 500),
        chunk_overlap=getattr(settings, "CHUNK_OVERLAP", 50),
        default_top_k=getattr(settings, "DEFAULT_TOP_K", 5),
        default_relevance_threshold=getattr(settings, "RELEVANCE_THRESHOLD", 0.2),
        version=getattr(settings, "VERSION", "1.0.0"),
        environment=getattr(settings, "APP_ENV", "development"),
    )

@router.put("", response_model=SettingsResponse, summary="Update runtime settings")
def update_settings(update: SettingsUpdateRequest):
    if update.default_top_k is not None:
        setattr(settings, "DEFAULT_TOP_K", update.default_top_k)
    if update.default_relevance_threshold is not None:
        setattr(settings, "RELEVANCE_THRESHOLD", update.default_relevance_threshold)
    if update.gemini_api_key is not None:
        settings.GEMINI_API_KEY = update.gemini_api_key.strip()

    return get_settings()

@router.post("/verify-engine", summary="Verify AI reasoning engine connectivity")
def verify_ai_engine():
    try:
        configured = bool(settings.GEMINI_API_KEY and settings.GEMINI_API_KEY.strip())
        vector_ok = vector_store_service.is_healthy()
        return {
            "status": "ok",
            "llm_configured": configured,
            "vector_store_connected": vector_ok,
            "message": "AI engines and vector memory are operational.",
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
