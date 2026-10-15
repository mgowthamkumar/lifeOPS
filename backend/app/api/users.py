from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserResponse, UserContextUpdate

router = APIRouter(prefix="/users", tags=["Users"])

def get_current_user(db: Session = Depends(get_db)):
    user_repo = UserRepository(db)
    return user_repo.get_or_create_default()

@router.get("/me", response_model=UserResponse, summary="Get current user and context")
def get_user_me(user = Depends(get_current_user)):
    return user

@router.put("/context", response_model=UserResponse, summary="Update user context and preferences")
def update_user_context(
    update: UserContextUpdate,
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
):
    user_repo = UserRepository(db)
    updated_kwargs = {}
    if update.full_name is not None:
        updated_kwargs["full_name"] = update.full_name
    if update.preferences is not None:
        user_prefs = dict(user.preferences or {})
        user_prefs.update(update.preferences)
        updated_kwargs["preferences"] = user_prefs
    if update.context is not None:
        user_ctx = dict(user.context or {})
        user_ctx.update(update.context)
        updated_kwargs["context"] = user_ctx

    updated_user = user_repo.update(user.id, **updated_kwargs)
    return updated_user
