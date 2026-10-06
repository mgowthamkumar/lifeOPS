from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Text, ForeignKey, Boolean, DateTime, JSON
from sqlalchemy.orm import relationship
from app.database.base import Base
from app.models.base import TimestampMixin, generate_uuid

class Document(Base, TimestampMixin):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    collection_id = Column(String(36), ForeignKey("collections.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)  # pdf, docx, txt, csv, md
    file_size = Column(Integer, nullable=False)
    storage_path = Column(String(500), nullable=False)
    content_hash = Column(String(64), index=True, nullable=False)  # SHA-256
    current_version = Column(Integer, default=1, nullable=False)
    status = Column(String(50), default="UPLOADED", nullable=False, index=True)  # UPLOADED, PROCESSING, PROCESSED, FAILED, UPDATED, DELETED
    error_message = Column(Text, nullable=True)

    # Relationships
    collection = relationship("Collection", back_populates="documents")
    versions = relationship("DocumentVersion", back_populates="document", cascade="all, delete-orphan")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")

class DocumentVersion(Base):
    __tablename__ = "document_versions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    file_size = Column(Integer, nullable=False)
    content_hash = Column(String(64), nullable=False)
    storage_path = Column(String(500), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    document = relationship("Document", back_populates="versions")
    chunks = relationship("DocumentChunk", back_populates="version", cascade="all, delete-orphan")

class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    version_id = Column(String(36), ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    collection_id = Column(String(36), ForeignKey("collections.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    page_number = Column(Integer, nullable=True)
    content = Column(Text, nullable=False)
    token_count = Column(Integer, nullable=True)
    vector_id = Column(String(100), unique=True, index=True, nullable=False)
    metadata_json = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    document = relationship("Document", back_populates="chunks")
    version = relationship("DocumentVersion", back_populates="chunks")
