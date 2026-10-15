from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.document import Document, DocumentChunk
from app.repositories.document_repository import DocumentRepository
from app.services.document_service import document_service
from app.schemas.document import DocumentResponse, DocumentDetailResponse, ChunkResponse

router = APIRouter(prefix="/documents", tags=["Documents"])

@router.get("", response_model=List[DocumentResponse])
def list_documents(
    collection_id: Optional[str] = None,
    db: Session = Depends(get_db),
) -> List[DocumentResponse]:
    doc_repo = DocumentRepository(db)
    if collection_id:
        docs = doc_repo.list_by_collection(collection_id)
    else:
        docs = db.query(Document).filter(Document.status != "DELETED").all()

    result = []
    for doc in docs:
        chunk_count = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).count()
        result.append(DocumentResponse(
            id=doc.id,
            collection_id=doc.collection_id,
            filename=doc.filename,
            file_type=doc.file_type,
            file_size=doc.file_size,
            content_hash=doc.content_hash,
            current_version=doc.current_version,
            status=doc.status,
            error_message=doc.error_message,
            chunk_count=chunk_count,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
        ))
    return result

@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    collection_id: str = Form(...),
    db: Session = Depends(get_db),
) -> DocumentResponse:
    content_bytes = await file.read()
    try:
        doc = document_service.upload_and_process(
            db=db,
            collection_id=collection_id,
            filename=file.filename or "uploaded_document",
            content_bytes=content_bytes,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")

    chunk_count = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).count()
    return DocumentResponse(
        id=doc.id,
        collection_id=doc.collection_id,
        filename=doc.filename,
        file_type=doc.file_type,
        file_size=doc.file_size,
        content_hash=doc.content_hash,
        current_version=doc.current_version,
        status=doc.status,
        error_message=doc.error_message,
        chunk_count=chunk_count,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )

@router.get("/{id}", response_model=DocumentDetailResponse)
def get_document(
    id: str,
    db: Session = Depends(get_db),
) -> DocumentDetailResponse:
    doc_repo = DocumentRepository(db)
    doc = doc_repo.get(id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    chunks = doc_repo.get_chunks_by_document(doc.id)
    chunk_responses = [
        ChunkResponse(
            id=c.id,
            chunk_index=c.chunk_index,
            page_number=c.page_number,
            content=c.content,
            token_count=c.token_count,
            vector_id=c.vector_id,
            created_at=c.created_at,
        )
        for c in chunks
    ]

    return DocumentDetailResponse(
        id=doc.id,
        collection_id=doc.collection_id,
        filename=doc.filename,
        file_type=doc.file_type,
        file_size=doc.file_size,
        content_hash=doc.content_hash,
        current_version=doc.current_version,
        status=doc.status,
        error_message=doc.error_message,
        chunk_count=len(chunks),
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        chunks=chunk_responses,
    )

@router.post("/{id}/reprocess", response_model=DocumentResponse)
def reprocess_document(
    id: str,
    db: Session = Depends(get_db),
) -> DocumentResponse:
    try:
        doc = document_service.reprocess_document(db=db, document_id=id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reprocessing error: {str(e)}")

    chunk_count = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).count()
    return DocumentResponse(
        id=doc.id,
        collection_id=doc.collection_id,
        filename=doc.filename,
        file_type=doc.file_type,
        file_size=doc.file_size,
        content_hash=doc.content_hash,
        current_version=doc.current_version,
        status=doc.status,
        error_message=doc.error_message,
        chunk_count=chunk_count,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )

@router.put("/{id}/update", response_model=DocumentResponse)
async def update_document(
    id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> DocumentResponse:
    content_bytes = await file.read()
    try:
        doc = document_service.update_document(
            db=db,
            document_id=id,
            filename=file.filename or "updated_document",
            new_content_bytes=content_bytes,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Update error: {str(e)}")

    chunk_count = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).count()
    return DocumentResponse(
        id=doc.id,
        collection_id=doc.collection_id,
        filename=doc.filename,
        file_type=doc.file_type,
        file_size=doc.file_size,
        content_hash=doc.content_hash,
        current_version=doc.current_version,
        status=doc.status,
        error_message=doc.error_message,
        chunk_count=chunk_count,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    id: str,
    db: Session = Depends(get_db),
):
    success = document_service.delete_document(db=db, document_id=id)
    if not success:
        raise HTTPException(status_code=404, detail="Document not found.")
    return None
