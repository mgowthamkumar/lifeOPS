import hashlib
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.document import Document, DocumentVersion, DocumentChunk
from app.models.collection import Collection
from app.repositories.document_repository import DocumentRepository
from app.repositories.collection_repository import CollectionRepository
from app.repositories.evidence_repository import ActivityLogRepository
from app.services.document_parser import DocumentParser
from app.services.embedding import embedding_service
from app.services.vector_store import vector_store_service

class DocumentService:
    """Orchestrates end-to-end document upload, extraction, chunking, embedding, indexing, and deletion."""

    def __init__(self):
        self.upload_dir = settings.resolve_path(settings.UPLOAD_DIRECTORY)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.max_size_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    def validate_file(self, filename: str, file_size: int) -> None:
        """Validates extension and file size."""
        if not DocumentParser.is_supported(filename):
            ext = Path(filename).suffix.lower()
            supported = ", ".join(DocumentParser.SUPPORTED_EXTENSIONS)
            raise ValueError(f"Unsupported file format '{ext}'. Supported formats: {supported}")

        if file_size > self.max_size_bytes:
            raise ValueError(f"File size ({file_size / (1024 * 1024):.1f}MB) exceeds limit of {settings.MAX_UPLOAD_SIZE_MB}MB.")

        if file_size == 0:
            raise ValueError("Uploaded file is empty.")

    def compute_hash(self, content_bytes: bytes) -> str:
        """Calculates SHA-256 hash."""
        return hashlib.sha256(content_bytes).hexdigest()

    def save_file_to_disk(self, filename: str, content_bytes: bytes, doc_id: str) -> Path:
        """Saves file to data/uploads using safe document-specific path."""
        safe_name = Path(filename).name
        target_path = self.upload_dir / f"{doc_id}_{safe_name}"
        with open(target_path, "wb") as f:
            f.write(content_bytes)
        return target_path

    def upload_and_process(
        self,
        db: Session,
        collection_id: str,
        filename: str,
        content_bytes: bytes,
        user_id: Optional[str] = None,
    ) -> Document:
        """Complete ingestion pipeline."""
        # 1. Validate
        self.validate_file(filename, len(content_bytes))

        # Check collection exists
        col_repo = CollectionRepository(db)
        collection = col_repo.get(collection_id)
        if not collection:
            raise ValueError(f"Collection with ID '{collection_id}' not found.")

        # 2. Compute hash and detect duplicates
        content_hash = self.compute_hash(content_bytes)
        doc_repo = DocumentRepository(db)
        existing_doc = doc_repo.get_by_content_hash(collection_id, content_hash)
        ext = Path(filename).suffix.lower().replace(".", "")

        if existing_doc:
            if existing_doc.status == "PROCESSED":
                return existing_doc
            # 3. Reuse existing non-PROCESSED (e.g. FAILED) document record
            doc = doc_repo.update(
                existing_doc.id,
                filename=filename,
                file_type=ext,
                file_size=len(content_bytes),
                status="PROCESSING",
                error_message=None,
            )
            # Clean up any leftover chunks, vectors, or versions from the prior attempt
            vector_store_service.delete_by_document(collection_id, document_id=doc.id)
            db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).delete()
            db.query(DocumentVersion).filter(DocumentVersion.document_id == doc.id).delete()
            db.commit()
        else:
            # 3. Create initial document record
            doc = doc_repo.create(
                collection_id=collection_id,
                filename=filename,
                file_type=ext,
                file_size=len(content_bytes),
                storage_path="",  # Updated after saving
                content_hash=content_hash,
                current_version=1,
                status="PROCESSING",
            )

        try:
            # 4. Save file to disk
            saved_path = self.save_file_to_disk(filename, content_bytes, doc.id)
            doc_repo.update(doc.id, storage_path=str(saved_path))

            # 5. Create Version 1
            version = doc_repo.add_version(
                document_id=doc.id,
                version_number=1,
                file_size=len(content_bytes),
                content_hash=content_hash,
                storage_path=str(saved_path),
            )

            # 6. Extract and Chunk text
            sections = DocumentParser.extract_text(saved_path)
            chunks_data = DocumentParser.chunk_sections(sections)

            if not chunks_data:
                raise ValueError("No extractable text found in document.")

            # 7. Generate Embeddings & Prepare ChromaDB data
            texts = [c["content"] for c in chunks_data]
            embeddings = embedding_service.embed_texts(texts)

            chroma_ids = []
            chroma_metadatas = []
            db_chunks_to_create = []

            for idx, c in enumerate(chunks_data):
                vector_id = f"{collection_id}_{doc.id}_v1_{idx}"
                chroma_ids.append(vector_id)
                meta = {
                    "document_id": doc.id,
                    "collection_id": collection_id,
                    "filename": filename,
                    "version": 1,
                    "chunk_index": c["chunk_index"],
                    "page_number": c["page_number"] or 1,
                }
                chroma_metadatas.append(meta)

                db_chunks_to_create.append({
                    "document_id": doc.id,
                    "version_id": version.id,
                    "collection_id": collection_id,
                    "chunk_index": c["chunk_index"],
                    "page_number": c["page_number"],
                    "content": c["content"],
                    "token_count": c["token_count"],
                    "vector_id": vector_id,
                    "metadata_json": meta,
                })

            # 8. Store in ChromaDB
            vector_store_service.add_chunks(
                collection_name=collection_id,
                ids=chroma_ids,
                embeddings=embeddings,
                documents=texts,
                metadatas=chroma_metadatas,
            )

            # 9. Store Chunks in relational DB
            doc_repo.add_chunks(db_chunks_to_create)

            # 10. Mark PROCESSED
            doc = doc_repo.update(doc.id, status="PROCESSED", error_message=None)

            # Activity log
            log_repo = ActivityLogRepository(db)
            log_repo.log_activity(
                entity_type="DOCUMENT",
                action="PROCESSED",
                entity_id=doc.id,
                user_id=user_id,
                details=f"Processed '{filename}' ({len(chunks_data)} chunks indexed).",
            )
            return doc

        except Exception as e:
            # Mark FAILED if processing errors occur
            doc = doc_repo.update(doc.id, status="FAILED", error_message=str(e))
            raise e

    def reprocess_document(self, db: Session, document_id: str) -> Document:
        """Reprocesses an existing document from stored disk file."""
        doc_repo = DocumentRepository(db)
        doc = doc_repo.get(document_id)
        if not doc:
            raise ValueError(f"Document '{document_id}' not found.")

        file_path = Path(doc.storage_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Underlying file not found at: {file_path}")

        try:
            # 1. Re-extract, re-chunk, and embed FIRST before deleting existing data
            sections = DocumentParser.extract_text(file_path)
            chunks_data = DocumentParser.chunk_sections(sections)
            texts = [c["content"] for c in chunks_data]
            embeddings = embedding_service.embed_texts(texts)

            # 2. Only after extraction & embedding succeed, remove old vectors & chunks
            vector_store_service.delete_by_document(doc.collection_id, document_id=doc.id)
            db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).delete()
            db.commit()

            # 3. Resolve / ensure active DocumentVersion
            active_version = db.query(DocumentVersion).filter(
                DocumentVersion.document_id == doc.id,
                DocumentVersion.is_active == True,
            ).first()

            if not active_version:
                # Check if an existing version can be activated
                latest_version = db.query(DocumentVersion).filter(
                    DocumentVersion.document_id == doc.id
                ).order_by(DocumentVersion.version_number.desc()).first()
                if latest_version:
                    latest_version.is_active = True
                    db.commit()
                    db.refresh(latest_version)
                    active_version = latest_version
                else:
                    # Create the missing version before assigning its ID
                    content_bytes = file_path.read_bytes()
                    file_hash = hashlib.sha256(content_bytes).hexdigest()
                    active_version = DocumentVersion(
                        document_id=doc.id,
                        version_number=1,
                        file_size=len(content_bytes),
                        content_hash=file_hash,
                        storage_path=str(file_path),
                        is_active=True,
                    )
                    db.add(active_version)
                    db.commit()
                    db.refresh(active_version)

            version_id = active_version.id
            v_num = active_version.version_number

            # 4. Prepare new chunks
            chroma_ids = []
            chroma_metadatas = []
            db_chunks_to_create = []

            for idx, c in enumerate(chunks_data):
                vector_id = f"{doc.collection_id}_{doc.id}_v{v_num}_{idx}"
                chroma_ids.append(vector_id)
                meta = {
                    "document_id": doc.id,
                    "collection_id": doc.collection_id,
                    "filename": doc.filename,
                    "version": v_num,
                    "chunk_index": c["chunk_index"],
                    "page_number": c["page_number"] or 1,
                }
                chroma_metadatas.append(meta)
                db_chunks_to_create.append({
                    "document_id": doc.id,
                    "version_id": version_id,
                    "collection_id": doc.collection_id,
                    "chunk_index": c["chunk_index"],
                    "page_number": c["page_number"],
                    "content": c["content"],
                    "token_count": c["token_count"],
                    "vector_id": vector_id,
                    "metadata_json": meta,
                })

            # 5. Index into ChromaDB and store DB chunks
            vector_store_service.add_chunks(
                collection_name=doc.collection_id,
                ids=chroma_ids,
                embeddings=embeddings,
                documents=texts,
                metadatas=chroma_metadatas,
            )
            doc_repo.add_chunks(db_chunks_to_create)

            return doc_repo.update(doc.id, status="PROCESSED", error_message=None)

        except Exception as e:
            doc = doc_repo.update(doc.id, status="FAILED", error_message=str(e))
            raise e

    def update_document(
        self,
        db: Session,
        document_id: str,
        filename: str,
        new_content_bytes: bytes,
    ) -> Document:
        """Uploads a newer version of an existing document and replaces vector chunks."""
        doc_repo = DocumentRepository(db)
        doc = doc_repo.get(document_id)
        if not doc:
            raise ValueError(f"Document '{document_id}' not found.")

        self.validate_file(filename, len(new_content_bytes))
        new_hash = self.compute_hash(new_content_bytes)

        # 1. Save new version file to disk
        new_version_num = doc.current_version + 1
        saved_path = self.save_file_to_disk(filename, new_content_bytes, f"{doc.id}_v{new_version_num}")

        # 2. Add DocumentVersion record
        version = doc_repo.add_version(
            document_id=doc.id,
            version_number=new_version_num,
            file_size=len(new_content_bytes),
            content_hash=new_hash,
            storage_path=str(saved_path),
        )

        try:
            # 3. Extract, chunk, and embed replacement content FIRST
            sections = DocumentParser.extract_text(saved_path)
            chunks_data = DocumentParser.chunk_sections(sections)
            texts = [c["content"] for c in chunks_data]
            embeddings = embedding_service.embed_texts(texts)

            # 4. Remove old vectors ONLY after embeddings succeed
            vector_store_service.delete_by_document(doc.collection_id, document_id=doc.id)

            # 5. Insert new vectors & DB chunks
            chroma_ids = []
            chroma_metadatas = []
            db_chunks_to_create = []

            for idx, c in enumerate(chunks_data):
                vector_id = f"{doc.collection_id}_{doc.id}_v{new_version_num}_{idx}"
                chroma_ids.append(vector_id)
                meta = {
                    "document_id": doc.id,
                    "collection_id": doc.collection_id,
                    "filename": filename,
                    "version": new_version_num,
                    "chunk_index": c["chunk_index"],
                    "page_number": c["page_number"] or 1,
                }
                chroma_metadatas.append(meta)
                db_chunks_to_create.append({
                    "document_id": doc.id,
                    "version_id": version.id,
                    "collection_id": doc.collection_id,
                    "chunk_index": c["chunk_index"],
                    "page_number": c["page_number"],
                    "content": c["content"],
                    "token_count": c["token_count"],
                    "vector_id": vector_id,
                    "metadata_json": meta,
                })

            vector_store_service.add_chunks(
                collection_name=doc.collection_id,
                ids=chroma_ids,
                embeddings=embeddings,
                documents=texts,
                metadatas=chroma_metadatas,
            )
            doc_repo.add_chunks(db_chunks_to_create)

            return doc_repo.update(
                doc.id,
                filename=filename,
                file_size=len(new_content_bytes),
                content_hash=new_hash,
                current_version=new_version_num,
                storage_path=str(saved_path),
                status="PROCESSED",
                error_message=None,
            )

        except Exception as e:
            # Clean up the newly created DocumentVersion and restore previous active version
            try:
                db.delete(version)
                db.commit()
                prev_version = db.query(DocumentVersion).filter(
                    DocumentVersion.document_id == doc.id,
                    DocumentVersion.version_number == doc.current_version,
                ).first()
                if prev_version:
                    prev_version.is_active = True
                    db.commit()
            except Exception:
                db.rollback()

            # Clean up saved file on disk
            try:
                if saved_path.exists():
                    os.remove(saved_path)
            except Exception:
                pass

            # Mark FAILED following upload_and_process
            doc = doc_repo.update(doc.id, status="FAILED", error_message=str(e))
            raise e

    def delete_document(self, db: Session, document_id: str) -> bool:
        """Deletes vectors from ChromaDB, removes files, and deletes DB records."""
        doc_repo = DocumentRepository(db)
        doc = doc_repo.get(document_id)
        if not doc:
            return False

        # 1. Remove vectors from ChromaDB
        vector_store_service.delete_by_document(doc.collection_id, document_id=doc.id)

        # 2. Remove file from disk
        try:
            if doc.storage_path and os.path.exists(doc.storage_path):
                os.remove(doc.storage_path)
        except Exception:
            pass

        # 3. Delete from DB (cascades chunks and versions)
        return doc_repo.delete(doc.id)

document_service = DocumentService()
