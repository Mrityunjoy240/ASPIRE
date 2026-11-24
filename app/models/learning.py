# app/models/learning.py
from datetime import datetime
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class LearningDocument(Base):
    __tablename__ = "learning_documents"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    uploaded_by: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    access_scope: Mapped[str] = mapped_column(String, nullable=False)  # OWNER_ONLY | COURSE_SHARED | TEACHER_PUBLISHED | INSTITUTION_PUBLISHED
    scope_id: Mapped[UUID | None] = mapped_column(ForeignKey("course_runs.id", ondelete="SET NULL"))
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    processing_status: Mapped[str] = mapped_column(String, default="PENDING")  # PENDING | CHUNKED | FAILED
    subject_tag: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]

    uploader: Mapped["User"] = relationship()
    chunks: Mapped[list["DocumentChunk"]] = relationship(back_populates="document", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_learning_documents_uploaded_by", "uploaded_by"),
        Index("idx_learning_documents_scope", "access_scope", "scope_id"),
        Index("idx_learning_documents_processing", "processing_status"),
    )


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    document_id: Mapped[UUID] = mapped_column(ForeignKey("learning_documents.id", ondelete="RESTRICT"))
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(1024))
    created_at: Mapped[datetime]

    document: Mapped["LearningDocument"] = relationship(back_populates="chunks")

    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="unique_document_chunk"),
        Index("idx_document_chunks_document", "document_id"),
    )
