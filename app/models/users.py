# app/models/users.py
from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import UserRole


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    institution_id: Mapped[UUID] = mapped_column(ForeignKey("institutions.id", ondelete="RESTRICT"))
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String, default="ACTIVE")
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]

    institution: Mapped["Institution"] = relationship(back_populates="users")
    role_assignments: Mapped[list["UserRoleAssignment"]] = relationship(
        back_populates="user",
        foreign_keys="UserRoleAssignment.user_id",
    )
    assigned_role_assignments: Mapped[list["UserRoleAssignment"]] = relationship(
        back_populates="assigner",
        foreign_keys="UserRoleAssignment.assigned_by",
    )


class UserRoleAssignment(Base):
    __tablename__ = "user_role_assignments"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    institution_id: Mapped[UUID] = mapped_column(ForeignKey("institutions.id", ondelete="RESTRICT"))
    role: Mapped[UserRole] = mapped_column(nullable=False)
    scope_entity_type: Mapped[str | None]
    scope_entity_id: Mapped[UUID | None]
    valid_from: Mapped[datetime] = mapped_column(nullable=False)
    valid_to: Mapped[datetime | None]
    assigned_by: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime]

    user: Mapped["User"] = relationship(back_populates="role_assignments", foreign_keys=[user_id])
    assigner: Mapped["User"] = relationship(back_populates="assigned_role_assignments", foreign_keys=[assigned_by])
    institution: Mapped["Institution"] = relationship()

    __table_args__ = (
        UniqueConstraint(
            "user_id", "role", "scope_entity_type", "scope_entity_id", "valid_from",
            name="unique_role_assignment"
        ),
    )
