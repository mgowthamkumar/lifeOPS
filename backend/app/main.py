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

def _run_sqlite_migrations():
    """Ensure newly added columns exist in existing SQLite databases."""
    from sqlalchemy import text
    try:
        with engine.begin() as conn:
            # Check decisions table columns
            res = conn.execute(text("PRAGMA table_info(decisions)"))
            columns = [row[1] for row in res.fetchall()]
            if columns and "constraints" not in columns:
                conn.execute(text("ALTER TABLE decisions ADD COLUMN constraints JSON DEFAULT '[]'"))

            # Check scenarios table columns
            res_s = conn.execute(text("PRAGMA table_info(scenarios)"))
            s_columns = [row[1] for row in res_s.fetchall()]
            if s_columns:
                if "user_id" not in s_columns:
                    conn.execute(text("ALTER TABLE scenarios ADD COLUMN user_id VARCHAR(36)"))
                if "parameters" not in s_columns:
                    conn.execute(text("ALTER TABLE scenarios ADD COLUMN parameters JSON DEFAULT '{}'"))
                if "simulation_result" not in s_columns:
                    conn.execute(text("ALTER TABLE scenarios ADD COLUMN simulation_result JSON DEFAULT '{}'"))

            # Check evidence table columns
            res_e = conn.execute(text("PRAGMA table_info(evidence)"))
            e_columns = [row[1] for row in res_e.fetchall()]
            if e_columns:
                if "investigation_id" not in e_columns:
                    conn.execute(text("ALTER TABLE evidence ADD COLUMN investigation_id VARCHAR(36)"))
                if "user_id" not in e_columns:
                    conn.execute(text("ALTER TABLE evidence ADD COLUMN user_id VARCHAR(36)"))
                if "chunk_index" not in e_columns:
                    conn.execute(text("ALTER TABLE evidence ADD COLUMN chunk_index INTEGER"))
                if "reasoning" not in e_columns:
                    conn.execute(text("ALTER TABLE evidence ADD COLUMN reasoning TEXT"))
                if "confidence" not in e_columns:
                    conn.execute(text("ALTER TABLE evidence ADD COLUMN confidence FLOAT"))
                if "uncertainty" not in e_columns:
                    conn.execute(text("ALTER TABLE evidence ADD COLUMN uncertainty FLOAT"))
                if "uncertainty_reasons" not in e_columns:
                    conn.execute(text("ALTER TABLE evidence ADD COLUMN uncertainty_reasons JSON DEFAULT '[]'"))
                if "stance" not in e_columns:
                    conn.execute(text("ALTER TABLE evidence ADD COLUMN stance VARCHAR(50) DEFAULT 'SUPPORTS'"))
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"SQLite migration check skipped or failed: {e}")

# Run schema setup and migrations on load
settings.ensure_directories()
Base.metadata.create_all(bind=engine)
_run_sqlite_migrations()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure required storage directories and database tables exist
    settings.ensure_directories()
    Base.metadata.create_all(bind=engine)
    _run_sqlite_migrations()
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
