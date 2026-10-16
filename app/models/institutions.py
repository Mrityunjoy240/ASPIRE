# app/models/institutions.py
from uuid import UUID

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Institution(Base):
    __tablename__ = "institutions"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    slug: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String, default="ACTIVE")
    # created_at handled by DB default

    users: Mapped[list["User"]] = relationship(back_populates="institution")
