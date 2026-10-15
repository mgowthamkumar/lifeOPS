from fastapi import APIRouter
from app.api.health import router as health_router
from app.api.collections import router as collections_router
from app.api.documents import router as documents_router
from app.api.rag import router as rag_router

api_router = APIRouter()

api_router.include_router(health_router)
api_router.include_router(collections_router)
api_router.include_router(documents_router)
api_router.include_router(rag_router)
