# app/api/deps.py
# API Dependencies — Supabase JWT validation, role resolution, auth helpers
# Security (07 §1-§2): Supabase Auth owns identity; ASPIRE user_role_assignments owns roles.

from datetime import UTC, datetime
from functools import lru_cache
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from jose.utils import base64url_decode
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_session
from app.core.events import EventBus
from app.models.enums import UserRole
from app.models.users import User, UserRoleAssignment

# Security scheme
security = HTTPBearer(auto_error=False)


class TokenPayload(BaseModel):
    """Supabase JWT payload (subset we care about)."""
    sub: str
    aud: str | list[str]
    iss: str
    exp: int
    iat: int
    role: str | None = None  # Supabase role claim (ignored for ASPIRE roles)


class JWK(BaseModel):
    """JSON Web Key from JWKS."""
    kty: str
    kid: str
    use: str
    n: str
    e: str
    alg: str


class JWKS(BaseModel):
    """JSON Web Key Set."""
    keys: list[JWK]


@lru_cache(maxsize=1)
def _fetch_jwks() -> JWKS:
    """Fetch and cache Supabase JWKS."""
    import httpx
    if not settings.supabase_jwks_uri:
        raise ValueError("SUPABASE_JWKS_URI not configured")
    resp = httpx.get(settings.supabase_jwks_uri, timeout=10.0)
    resp.raise_for_status()
    return JWKS.model_validate(resp.json())


def _get_signing_key(token: str) -> str:
    """Extract signing key from JWKS using token's kid header."""
    unverified_header = jwt.get_unverified_header(token)
    kid = unverified_header.get("kid")
    if not kid:
        raise JWTError("Token missing kid header")
    jwks = _fetch_jwks()
    for key in jwks.keys:
        if key.kid == kid:
            # Reconstruct PEM from JWK (RSA)
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.primitives.asymmetric import rsa
            n = base64url_decode(key.n.encode()).hex()
            e = base64url_decode(key.e.encode()).hex()
            # Construct public key from modulus and exponent
            n_int = int(n, 16)
            e_int = int(e, 16)
            pub_key = rsa.RSAPublicNumbers(e_int, n_int).public_key()
            pem = pub_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            return pem.decode()
    raise JWTError(f"Key with kid={kid} not found in JWKS")


def _decode_token(token: str) -> TokenPayload:
    """Validate and decode Supabase JWT using JWKS."""
    try:
        key = _get_signing_key(token)
        payload = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience=settings.next_public_supabase_publishable_key,
            options={"verify_aud": True},
        )
        return TokenPayload.model_validate(payload)
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> UUID:
    """Extract and validate user_id from Supabase JWT."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = _decode_token(credentials.credentials)
    return UUID(payload.sub)


async def get_auth_context(
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> "AuthContext":
    """Build auth context with ASPIRE roles from user_role_assignments."""
    # Get user
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.status != "ACTIVE":
        raise HTTPException(status_code=403, detail="User account suspended")

    # Get active role assignments for user's institution
    now = datetime.now(UTC)
    result = await session.execute(
        select(UserRoleAssignment).where(
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


class AuthContext:
    """Authenticated request context (roles from user_role_assignments, not JWT)."""
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


def require_roles(*required: UserRole):
    """Dependency factory requiring at least one of the specified roles."""
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


# Single denial detail for every failure mode of the student-scoped ownership
# check below: a foreign record, a nonexistent record, a cross-institution
# record and an unsupported role must be indistinguishable (no existence
# oracle — 07 §5 "Student data is confidential by default").
STUDENT_SCOPE_DENIED = "Not authorized for this student"


async def require_student_self_or_mentor(
    student_id: UUID,
    auth: AuthContext = Depends(get_auth_context),
    session: AsyncSession = Depends(get_session),
) -> AuthContext:
    """Record-level authorization for a student-scoped read (07 §2 matrix,
    DM-NEW-ORM01: role check alone is never sufficient — explicit row/scope
    filtering is mandatory).

    Allowed paths for student {student_id}'s records:
      * the authenticated user IS that student (own academic data)
      * ADMIN       — same institution (student_profiles.batch_id -> batches.institution_id)
      * MENTOR      — assigned mentee (student_profiles.mentor_id)
      * CLASS_TEACHER — own class (student_profiles.class_teacher_id)
      * FACULTY     — assigned course runs only (course_runs.faculty_id, same batch)
      * HOD         — denied: aggregates/escalations only, never individual
                      student records by default (07 §2 matrix, 07 §5)

    Every denial raises the same 403 detail so callers cannot probe whether a
    student id exists."""
    from app.models.academic import Batch, CourseRun
    from app.models.student import StudentProfile

    denied = HTTPException(
        status_code=status.HTTP_403_FORBIDDEN, detail=STUDENT_SCOPE_DENIED
    )

    result = await session.execute(
        select(StudentProfile, Batch.institution_id)
        .join(Batch, StudentProfile.batch_id == Batch.id)
        .where(StudentProfile.id == student_id)
    )
    row = result.first()
    if not row:
        # Missing profile and foreign profile are the same refusal.
        raise denied
    profile, institution_id = row

    # Own data is always allowed (07 §2 "Own academic data: Student ✅ Read").
    if profile.user_id == auth.user_id:
        return auth

    # Admin: everything inside own institution, nothing across institutions.
    if auth.is_admin():
        if institution_id == auth.institution_id:
            return auth
        raise denied

    # Mentor: assigned mentees only (07 §2 "Mentee data: Mentor ✅ Read").
    if auth.has_role(UserRole.MENTOR) and profile.mentor_id == auth.user_id:
        return auth

    # Class teacher: own class only (07 §2 "Class data: CT ✅ Own class").
    if auth.has_role(UserRole.CLASS_TEACHER) and profile.class_teacher_id == auth.user_id:
        return auth

    # Faculty: assigned course runs only. course_runs.faculty_id (migration
    # 003) is the scope-entity record; the student's batch bounds the runs in
    # which they can appear. No assigned run for this batch -> denied.
    if auth.has_role(UserRole.FACULTY):
        result = await session.execute(
            select(CourseRun.id)
            .where(
                CourseRun.faculty_id == auth.user_id,
                CourseRun.batch_id == profile.batch_id,
            )
            .limit(1)
        )
        if result.first():
            return auth
        raise denied

    # HOD (aggregates/escalations only) and any other role: fail closed.
    raise denied


# Audit logging helper. actor_id is nullable (migration 007: users FK with
# SET NULL) so agent/rule-engine runs — which have no acting user — can write
# their required audit rows with actor_type SYSTEM_AGENT/RULE_ENGINE.
async def log_audit(
    session: AsyncSession,
    actor_id: UUID | None,
    actor_type: str,
    action_type: str,
    entity_table: str,
    entity_id: UUID,
    previous_state: dict | None,
    new_state: dict | None,
    source_system: str,
) -> None:
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
        created_at=datetime.now(UTC),
    )
    session.add(log)


def get_event_bus(request: Request) -> EventBus:
    """In-process domain event bus (ADR-001 ARCH-02), created at app import time."""
    bus = getattr(request.app.state, "event_bus", None)
    if bus is None:
        bus = EventBus()
        request.app.state.event_bus = bus
    return bus
