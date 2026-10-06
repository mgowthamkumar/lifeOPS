from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.collection import Collection
from app.repositories.base import BaseRepository

class CollectionRepository(BaseRepository[Collection]):
    def __init__(self, db: Session):
        super().__init__(Collection, db)

    def list_by_user(self, user_id: str) -> List[Collection]:
        return self.db.query(Collection).filter(Collection.user_id == user_id).all()

    def get_by_name(self, user_id: str, name: str) -> Optional[Collection]:
        return self.db.query(Collection).filter(Collection.user_id == user_id, Collection.name == name).first()
