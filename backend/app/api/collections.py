from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.collection import Collection
from app.models.document import Document, DocumentChunk
from app.repositories.collection_repository import CollectionRepository
from app.repositories.user_repository import UserRepository
from app.services.vector_store import vector_store_service
from app.schemas.collection import CollectionCreate, CollectionUpdate, CollectionResponse

router = APIRouter(prefix="/collections", tags=["Collections"])

def get_current_user_id(db: Session = Depends(get_db)) -> str:
    """Helper to ensure a persistent default user exists."""
    user_repo = UserRepository(db)
    user = user_repo.get_or_create_default()
    return user.id

@router.get("", response_model=List[CollectionResponse])
def list_collections(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> List[CollectionResponse]:
    col_repo = CollectionRepository(db)
    collections = col_repo.list_by_user(user_id)
    
    result = []
    for col in collections:
        doc_count = db.query(Document).filter(
            Document.collection_id == col.id,
            Document.status != "DELETED",
        ).count()
        chunk_count = db.query(DocumentChunk).filter(DocumentChunk.collection_id == col.id).count()
        
        result.append(CollectionResponse(
            id=col.id,
            user_id=col.user_id,
            name=col.name,
            description=col.description,
            document_count=doc_count,
            chunk_count=chunk_count,
            created_at=col.created_at,
            updated_at=col.updated_at,
        ))
    return result

@router.post("", response_model=CollectionResponse, status_code=status.HTTP_201_CREATED)
def create_collection(
    payload: CollectionCreate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> CollectionResponse:
    col_repo = CollectionRepository(db)
    existing = col_repo.get_by_name(user_id, payload.name)
    if existing:
        raise HTTPException(status_code=400, detail=f"Collection '{payload.name}' already exists.")

    col = col_repo.create(
        user_id=user_id,
        name=payload.name,
        description=payload.description,
    )
    # Ensure ChromaDB collection is initialized
    vector_store_service.get_or_create_collection(col.id)

    return CollectionResponse(
        id=col.id,
        user_id=col.user_id,
        name=col.name,
        description=col.description,
        document_count=0,
        chunk_count=0,
        created_at=col.created_at,
        updated_at=col.updated_at,
    )

@router.get("/{id}", response_model=CollectionResponse)
def get_collection(
    id: str,
    db: Session = Depends(get_db),
) -> CollectionResponse:
    col_repo = CollectionRepository(db)
    col = col_repo.get(id)
    if not col:
        raise HTTPException(status_code=404, detail="Collection not found.")

    doc_count = db.query(Document).filter(
        Document.collection_id == col.id,
        Document.status != "DELETED",
    ).count()
    chunk_count = db.query(DocumentChunk).filter(DocumentChunk.collection_id == col.id).count()

    return CollectionResponse(
        id=col.id,
        user_id=col.user_id,
        name=col.name,
        description=col.description,
        document_count=doc_count,
        chunk_count=chunk_count,
        created_at=col.created_at,
        updated_at=col.updated_at,
    )

@router.put("/{id}", response_model=CollectionResponse)
def update_collection(
    id: str,
    payload: CollectionUpdate,
    db: Session = Depends(get_db),
) -> CollectionResponse:
    col_repo = CollectionRepository(db)
    update_data = {k: v for k, v in payload.model_dump().items() if v is not None}
    col = col_repo.update(id, **update_data)
    if not col:
        raise HTTPException(status_code=404, detail="Collection not found.")

    doc_count = db.query(Document).filter(
        Document.collection_id == col.id,
        Document.status != "DELETED",
    ).count()
    chunk_count = db.query(DocumentChunk).filter(DocumentChunk.collection_id == col.id).count()

    return CollectionResponse(
        id=col.id,
        user_id=col.user_id,
        name=col.name,
        description=col.description,
        document_count=doc_count,
        chunk_count=chunk_count,
        created_at=col.created_at,
        updated_at=col.updated_at,
    )

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_collection(
    id: str,
    db: Session = Depends(get_db),
):
    col_repo = CollectionRepository(db)
    col = col_repo.get(id)
    if not col:
        raise HTTPException(status_code=404, detail="Collection not found.")

    # Remove all vectors for this collection from ChromaDB
    vector_store_service.delete_collection(col.id)

    # Delete from DB (cascades to documents, versions, chunks)
    col_repo.delete(col.id)
    return None
