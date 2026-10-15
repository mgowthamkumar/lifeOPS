from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.repositories.user_repository import UserRepository
from app.models.evidence_analysis import Evidence
from app.schemas.rag import RAGQueryRequest, RAGQueryResponse
from app.services.rag_service import rag_service
from app.services.vector_store import vector_store_service
from app.core.config import settings

router = APIRouter(prefix="/rag", tags=["RAG Decision Intelligence"])

def get_current_user_id(db: Session = Depends(get_db)) -> str:
    user_repo = UserRepository(db)
    user = user_repo.get_or_create_default()
    return user.id

@router.post("/query", response_model=RAGQueryResponse)
def execute_rag_query(
    request: RAGQueryRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> RAGQueryResponse:
    """
    Executes an evidence-grounded RAG query against a collection.
    Enforces semantic retrieval, relevance thresholding, and structured Gemini generation.
    Returns INSUFFICIENT EVIDENCE when evidence is absent or below threshold.
    """
    try:
        response = rag_service.query(
            db=db,
            collection_id=request.collection_id,
            question=request.question,
            top_k=request.top_k,
            relevance_threshold=request.relevance_threshold,
            user_id=user_id,
        )
        return response
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"RAG query execution failed: {str(e)}")

@router.get("/evidence", response_model=List[Dict[str, Any]])
def get_recent_evidence(
    limit: int = 10,
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Retrieves recently extracted evidence items logged from RAG queries."""
    items = db.query(Evidence).order_by(Evidence.created_at.desc()).limit(limit).all()
    return [
        {
            "id": item.id,
            "claim": item.claim,
            "extracted_text": item.extracted_text,
            "source_filename": item.source_filename,
            "page_number": item.page_number,
            "relevance_score": item.relevance_score,
            "created_at": item.created_at.isoformat() if item.created_at else None,
        }
        for item in items
    ]

@router.get("/config")
def get_rag_config():
    """Returns runtime model and embedding configuration."""
    return {
        "llm_model": settings.LLM_MODEL,
        "embedding_model": settings.EMBEDDING_MODEL,
        "embedding_backend": settings.EMBEDDING_BACKEND,
        "gemini_api_configured": bool(settings.GEMINI_API_KEY and settings.GEMINI_API_KEY.strip()),
    }
