import sys
from pathlib import Path

# Ensure backend root is in sys.path
backend_path = Path(__file__).resolve().parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.router import api_router
from app.database.session import engine
from app.database.base import Base
import app.models  # Register all models in SQLAlchemy metadata

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure required storage directories and database tables exist
    settings.ensure_directories()
    Base.metadata.create_all(bind=engine)
    yield
    # Shutdown logic if any

app = FastAPI(
    title=settings.APP_NAME,
    description="LifeOps AI – A Personal Life Decision and Action Intelligence System using Explainable Retrieval-Augmented Generation",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routers under /api
app.include_router(api_router, prefix="/api")

@app.get("/")
def root():
    return {
        "name": settings.APP_NAME,
        "description": "Personal Life Decision and Action Intelligence System",
        "status": "online",
        "docs_url": "/docs",
        "health_url": "/api/health",
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
