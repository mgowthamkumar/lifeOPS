from datetime import datetime, timezone
from fastapi import APIRouter
from app.core.config import settings
from app.database.session import check_db_connection
from app.schemas.health import (
    HealthResponse,
    DatabaseHealth,
    VectorDBHealth,
    LLMHealth,
)

router = APIRouter(tags=["Health"])

@router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    # 1. Real database connection check
    db_connected = check_db_connection()
    db_type = "sqlite" if settings.DATABASE_URL.startswith("sqlite") else "postgresql"
    db_message = "Connected to persistent database" if db_connected else "Database connection failed"

    # 2. Vector DB directory and status check
    chroma_path = settings.resolve_path(settings.CHROMA_PERSIST_DIRECTORY)
    vector_configured = chroma_path.exists()
    vector_status = "Storage directory ready" if vector_configured else "Directory pending creation"

    # 3. LLM configuration check (Never reveal secret key)
    llm_configured = bool(settings.GEMINI_API_KEY and len(settings.GEMINI_API_KEY.strip()) > 0)
    llm_message = "Gemini API key configured" if llm_configured else "GEMINI_API_KEY not set in .env (RAG will require key)"

    # Compute overall status
    if not db_connected:
        overall_status = "unhealthy"
    elif not llm_configured:
        overall_status = "degraded"
    else:
        overall_status = "healthy"

    return HealthResponse(
        status=overall_status,
        timestamp=datetime.now(timezone.utc),
        app_name=settings.APP_NAME,
        version="0.1.0",
        database=DatabaseHealth(
            connected=db_connected,
            type=db_type,
            message=db_message,
        ),
        vector_db=VectorDBHealth(
            configured=vector_configured,
            persist_dir=str(chroma_path),
            status=vector_status,
        ),
        llm=LLMHealth(
            provider="Google Gemini",
            configured=llm_configured,
            model=settings.LLM_MODEL,
            message=llm_message,
        ),
        environment=settings.APP_ENV,
    )
