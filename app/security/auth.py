# app/security/auth.py
# RBAC & Authentication (Security 07 §1-§2)
# Supabase Auth owns identity; ASPIRE user_role_assignments owns roles.
# FastAPI service connection carries NO JWT/auth.uid().

from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.enums import UserRole
from app.models.users import User, UserRoleAssignment

security = HTTPBearer(auto_error=False)


class AuthContext:
    """Authenticated request context (no Supabase JWT role claims)."""
    def __init__(
        self,
        user_id: UUID,
        user: User,
        roles: list[UserRole],
        institution_id: UUID,
    ):
        self.user_id = user_id
        self.user = user
        self.roles = roles
        self.institution_id = institution_id

    def has_role(self, *roles: UserRole) -> bool:
        return any(r in self.roles for r in roles)

    def is_admin(self) -> bool:
        return UserRole.ADMIN in self.roles

    def is_mentor(self) -> bool:
        return UserRole.MENTOR in self.roles

    def is_faculty(self) -> bool:
        return UserRole.FACULTY in self.roles

    def is_student(self) -> bool:
        return UserRole.STUDENT in self.roles


async def get_current_user_id(credentials: HTTPAuthorizationCredentials | None = Depends(security)) -> UUID:
    """Extract user_id from Supabase JWT (sub claim)."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
        )

    # Verify JWT with Supabase JWKS (simplified - use jose in production)
    try:
        payload = jwt.decode(
            credentials.credentials,
            options={"verify_signature": False},  # TODO: proper JWKS verification
        )
        user_id_str = payload.get("sub")
        if not user_id_str:
            raise HTTPException(status_code=401, detail="Invalid token: no sub claim")
        return UUID(user_id_str)
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")


async def get_auth_context(
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> AuthContext:
    """Build auth context with ASPIRE roles (from user_role_assignments, not JWT)."""
    # Get user
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get active role assignments for user's institution
    now = datetime.utcnow()
    result = await session.execute(
        select(UserRoleAssignment)
        .where(
            UserRoleAssignment.user_id == user_id,
            UserRoleAssignment.institution_id == user.institution_id,
            UserRoleAssignment.valid_from <= now,
            (UserRoleAssignment.valid_to.is_(None)) | (UserRoleAssignment.valid_to >= now),
        )
    )
    assignments = result.scalars().all()

    roles = [a.role for a in assignments]

    return AuthContext(
        user_id=user_id,
        user=user,
        roles=roles,
        institution_id=user.institution_id,
    )


# Role-based dependency factories
def require_roles(*required: UserRole):
    """Dependency that requires at least one of the specified roles."""
    async def _check(auth: AuthContext = Depends(get_auth_context)) -> AuthContext:
        if not auth.has_role(*required):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of: {[r.value for r in required]}",
            )
        return auth
    return _check


def require_admin(auth: AuthContext = Depends(get_auth_context)) -> AuthContext:
    if not auth.is_admin():
        raise HTTPException(status_code=403, detail="Admin role required")
    return auth


def require_mentor_or_admin(auth: AuthContext = Depends(get_auth_context)) -> AuthContext:
    if not auth.has_role(UserRole.MENTOR, UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Mentor or Admin role required")
    return auth


def require_faculty_or_admin(auth: AuthContext = Depends(get_auth_context)) -> AuthContext:
    if not auth.has_role(UserRole.FACULTY, UserRole.CLASS_TEACHER, UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Faculty or Admin role required")
    return auth


# Student can only access own data
async def require_student_self_or_mentor(
    student_id: UUID,
    auth: AuthContext = Depends(get_auth_context),
) -> AuthContext:
    """Allow student to access own data, or mentor/admin to access mentee data."""
    if auth.is_student():
        # Check if student_id matches auth user's student profile
        # (Would need student_profiles lookup in real implementation)
        return auth
    if auth.has_role(UserRole.MENTOR, UserRole.ADMIN, UserRole.HOD):
        return auth
    raise HTTPException(status_code=403, detail="Not authorized for this student")


# Audit logging helper
async def log_audit(
    session,
    actor_id: UUID,
    actor_type: str,
    action_type: str,
    entity_table: str,
    entity_id: UUID,
    previous_state: dict | None,
    new_state: dict | None,
    source_system: str,
) -> None:
    from datetime import datetime

    from app.models.audit import AuditLog
    log = AuditLog(
        actor_id=actor_id,
        actor_type=actor_type,
        action_type=action_type,
        entity_table=entity_table,
        entity_id=entity_id,
        previous_state=previous_state,
        new_state=new_state,
        source_system=source_system,
        created_at=datetime.utcnow(),
    )
    session.add(log)
