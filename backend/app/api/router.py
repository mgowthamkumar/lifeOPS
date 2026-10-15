from fastapi import APIRouter
from app.api.health import router as health_router
from app.api.collections import router as collections_router
from app.api.documents import router as documents_router
from app.api.rag import router as rag_router
from app.api.goals import router as goals_router
from app.api.tasks import router as tasks_router
from app.api.action_planner import router as action_planner_router
from app.api.decisions import router as decisions_router
from app.api.scenarios import router as scenarios_router
from app.api.evidence import router as evidence_router
from app.api.history import router as history_router
from app.api.settings import router as settings_router
from app.api.dashboard import router as dashboard_router
from app.api.users import router as users_router

api_router = APIRouter()

api_router.include_router(health_router)
api_router.include_router(users_router)
api_router.include_router(dashboard_router)
api_router.include_router(collections_router)
api_router.include_router(documents_router)
api_router.include_router(rag_router)
api_router.include_router(goals_router)
api_router.include_router(tasks_router)
api_router.include_router(action_planner_router)
api_router.include_router(decisions_router)
api_router.include_router(scenarios_router)
api_router.include_router(evidence_router)
api_router.include_router(history_router)
api_router.include_router(settings_router)

