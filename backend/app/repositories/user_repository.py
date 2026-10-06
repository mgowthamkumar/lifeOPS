from typing import Optional
from sqlalchemy.orm import Session
from app.models.user import User
from app.repositories.base import BaseRepository

class UserRepository(BaseRepository[User]):
    def __init__(self, db: Session):
        super().__init__(User, db)

    def get_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email).first()

    def get_or_create_default(self, email: str = "user@lifeops.ai", full_name: str = "LifeOps User") -> User:
        user = self.get_by_email(email)
        if not user:
            user = self.create(email=email, full_name=full_name, preferences={}, context={})
        return user
