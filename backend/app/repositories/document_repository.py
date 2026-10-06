from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.document import Document, DocumentVersion, DocumentChunk
from app.repositories.base import BaseRepository

class DocumentRepository(BaseRepository[Document]):
    def __init__(self, db: Session):
        super().__init__(Document, db)

    def list_by_collection(self, collection_id: str) -> List[Document]:
        return self.db.query(Document).filter(
            Document.collection_id == collection_id,
            Document.status != "DELETED",
        ).all()

    def get_by_content_hash(self, collection_id: str, content_hash: str) -> Optional[Document]:
        return self.db.query(Document).filter(
            Document.collection_id == collection_id,
            Document.content_hash == content_hash,
            Document.status != "DELETED",
        ).first()

    def add_version(self, document_id: str, version_number: int, file_size: int, content_hash: str, storage_path: str) -> DocumentVersion:
        # Deactivate old versions
        self.db.query(DocumentVersion).filter(DocumentVersion.document_id == document_id).update({"is_active": False})
        version = DocumentVersion(
            document_id=document_id,
            version_number=version_number,
            file_size=file_size,
            content_hash=content_hash,
            storage_path=storage_path,
            is_active=True,
        )
        self.db.add(version)
        self.db.commit()
        self.db.refresh(version)
        return version

    def add_chunks(self, chunks_data: List[dict]) -> List[DocumentChunk]:
        created_chunks = []
        for data in chunks_data:
            chunk = DocumentChunk(**data)
            self.db.add(chunk)
            created_chunks.append(chunk)
        self.db.commit()
        for chunk in created_chunks:
            self.db.refresh(chunk)
        return created_chunks

    def get_chunks_by_document(self, document_id: str) -> List[DocumentChunk]:
        return self.db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).all()
