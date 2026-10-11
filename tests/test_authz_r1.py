# tests/test_authz_r1.py
# R1 — P0 security/correctness hardening (docs/11_ROADMAP.md §3, ADR-003 §6.3).
#
# Covers:
#   * record-level authorization matrix for student-scoped reads via the real
#     require_student_self_or_mentor dependency (own data / mentee / own class /
#     same-institution admin / assigned-run faculty; HOD denied — 07 §2)
#   * no-existence-oracle: foreign record and nonexistent record are the same 403
#   * int-raise defects: raise status.HTTP_XXX produced 500s — routes must now
#     answer 4xx HTTPException
#   * institution scoping of the cases queue admin/HOD path and approve path
#   * real dependency path: Supabase JWT -> JWKS (mocked, local RSA key) ->
#     _decode_token -> get_auth_context -> authorization (no LLM, no network)

import base64
import time
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from jose import jwt as jose_jwt

from app.api.deps import (
    JWK,
    JWKS,
    STUDENT_SCOPE_DENIED,
    AuthContext,
    get_auth_context,
    get_session,
)
from app.core.config import settings as app_settings
from app.main import app
from app.models.enums import InterventionCaseStatus, TaskStatus, UserRole
from app.models.intervention import InterventionCase
from app.models.student import StudentProfile
from app.models.tasks import StudentTask
from app.models.users import User

DENIED = STUDENT_SCOPE_DENIED


# ---------------------------------------------------------------- helpers


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def authz_deps():
    """Temporarily install dependency overrides (same pattern as test_api_routers)."""
    saved = dict(app.dependency_overrides)
    yield app.dependency_overrides
    app.dependency_overrides.clear()
    app.dependency_overrides.update(saved)


def _override(auth_overrides, auth, session) -> None:
    auth_overrides[get_auth_context] = lambda: auth
    auth_overrides[get_session] = lambda: session


def _override_session_only(auth_overrides, session) -> None:
    """Real auth chain (JWT + role resolution); only the DB session is mocked."""
    auth_overrides[get_session] = lambda: session


def _auth(roles, *, user_id=None, institution_id=None) -> AuthContext:
    return AuthContext(
        user_id=user_id or uuid.uuid4(),
        user=MagicMock(),
        roles=roles,
        institution_id=institution_id or uuid.uuid4(),
    )


def _profile(user_id, *, profile_id=None, mentor_id=None, class_teacher_id=None,
             batch_id=None) -> StudentProfile:
    now = datetime.now(UTC)
    return StudentProfile(
        id=profile_id or uuid.uuid4(),
        user_id=user_id,
        batch_id=batch_id or uuid.uuid4(),
        roll_number="BCREC-R1",
        mentor_id=mentor_id,
        class_teacher_id=class_teacher_id,
        enrollment_year=2024,
        created_at=now,
        updated_at=now,
    )


def _user(user_id, institution_id, *, status="ACTIVE") -> User:
    now = datetime.now(UTC)
    return User(
        id=user_id,
        institution_id=institution_id,
        email=f"{user_id.hex[:8]}@example.test",
        full_name="R1 Subject",
        status=status,
        created_at=now,
        updated_at=now,
    )


def _result(*, first=None, scalar=None, rows=None, scalars=None) -> MagicMock:
    m = MagicMock()
    m.first.return_value = first
    m.scalar_one_or_none.return_value = scalar
    m.all.return_value = rows if rows is not None else []
    sc = MagicMock()
    sc.all.return_value = scalars if scalars is not None else []
    m.scalars.return_value = sc
    return m


def _session(*results) -> AsyncMock:
    s = AsyncMock()
    s.execute = AsyncMock(side_effect=list(results))
    s.flush = AsyncMock()
    s.add = MagicMock()
    return s


# ---------------------------------------------------------------- 401 matrix


@pytest.mark.parametrize(
    "method,path",
    [
        ("GET", "/api/v1/attendance/{sid}/summary"),
        ("GET", "/api/v1/attendance/{sid}/what-if?course_id={cid}&target=75"),
        ("GET", "/api/v1/assessments/{sid}/summary?course_id={cid}"),
        ("GET", "/api/v1/tasks/student/{sid}"),
        ("GET", "/api/v1/students/{sid}"),
        ("GET", "/api/v1/students/me"),
        ("GET", "/api/v1/cases/queue"),
    ],
)
def test_unauthenticated_is_401(client, method, path):
    """Every protected route rejects a missing bearer token with 401."""
    url = path.format(sid=uuid.uuid4(), cid=uuid.uuid4())
    response = client.request(method, url)
    assert response.status_code == 401


# ------------------------------------------- require_student_self_or_mentor


def test_student_own_record_allowed(authz_deps, client):
    """Student reads own attendance summary (own academic data — 07 §2)."""
    student = _auth([UserRole.STUDENT])
    profile = _profile(student.user_id)
    session = _session(
        _result(first=(profile, uuid.uuid4())),  # helper: profile + institution
        _result(rows=[]),                        # handler: no derived rows
    )
    _override(authz_deps, student, session)

    response = client.get(f"/api/v1/attendance/{profile.id}/summary")
    assert response.status_code == 200
    assert response.json() == []


def test_student_foreign_record_403_no_oracle(authz_deps, client):
    """Student A on student B's data: 403 — identical to the nonexistent-id 403."""
    student = _auth([UserRole.STUDENT])
    foreign = _profile(uuid.uuid4())  # belongs to a different user
    session = _session(_result(first=(foreign, uuid.uuid4())))
    _override(authz_deps, student, session)
    response = client.get(f"/api/v1/attendance/{foreign.id}/summary")
    assert response.status_code == 403
    foreign_detail = response.json()["detail"]

    missing = _session(_result(first=None))  # student id does not exist
    _override(authz_deps, student, missing)
    response_missing = client.get(f"/api/v1/attendance/{uuid.uuid4()}/summary")
    assert response_missing.status_code == 403
    assert response_missing.json()["detail"] == foreign_detail == DENIED


def test_mentor_assigned_mentee_allowed(authz_deps, client):
    mentor = _auth([UserRole.MENTOR])
    profile = _profile(uuid.uuid4(), mentor_id=mentor.user_id)
    session = _session(_result(first=(profile, uuid.uuid4())), _result(rows=[]))
    _override(authz_deps, mentor, session)

    response = client.get(f"/api/v1/attendance/{profile.id}/summary")
    assert response.status_code == 200


def test_mentor_unassigned_student_403(authz_deps, client):
    mentor = _auth([UserRole.MENTOR])
    profile = _profile(uuid.uuid4(), mentor_id=uuid.uuid4())  # someone else's mentee
    session = _session(_result(first=(profile, uuid.uuid4())))
    _override(authz_deps, mentor, session)

    response = client.get(f"/api/v1/attendance/{profile.id}/summary")
    assert response.status_code == 403
    assert response.json()["detail"] == DENIED


def test_class_teacher_own_class_allowed_foreign_403(authz_deps, client):
    ct = _auth([UserRole.CLASS_TEACHER])
    own = _profile(uuid.uuid4(), class_teacher_id=ct.user_id)
    session = _session(_result(first=(own, uuid.uuid4())), _result(rows=[]))
    _override(authz_deps, ct, session)
    assert client.get(f"/api/v1/attendance/{own.id}/summary").status_code == 200

    foreign = _profile(uuid.uuid4(), class_teacher_id=uuid.uuid4())
    session = _session(_result(first=(foreign, uuid.uuid4())))
    _override(authz_deps, ct, session)
    assert client.get(f"/api/v1/attendance/{foreign.id}/summary").status_code == 403


def test_admin_same_institution_allowed_cross_403(authz_deps, client):
    institution_id = uuid.uuid4()
    admin = _auth([UserRole.ADMIN], institution_id=institution_id)
    own_inst = _profile(uuid.uuid4())
    session = _session(_result(first=(own_inst, institution_id)), _result(rows=[]))
    _override(authz_deps, admin, session)
    assert client.get(f"/api/v1/attendance/{own_inst.id}/summary").status_code == 200

    other_inst = _profile(uuid.uuid4())
    session = _session(_result(first=(other_inst, uuid.uuid4())))
    _override(authz_deps, admin, session)
    response = client.get(f"/api/v1/attendance/{other_inst.id}/summary")
    assert response.status_code == 403
    assert response.json()["detail"] == DENIED


def test_faculty_assigned_run_allowed_unassigned_403(authz_deps, client):
    """Faculty scope = assigned course runs (course_runs.faculty_id, same batch)."""
    faculty = _auth([UserRole.FACULTY])
    profile = _profile(uuid.uuid4())
    assigned = _session(
        _result(first=(profile, uuid.uuid4())),   # helper: profile
        _result(first=(uuid.uuid4(),)),            # helper: assigned run exists
        _result(rows=[]),                          # handler
    )
    _override(authz_deps, faculty, assigned)
    assert client.get(f"/api/v1/attendance/{profile.id}/summary").status_code == 200

    unassigned = _session(
        _result(first=(profile, uuid.uuid4())),
        _result(first=None),  # no course run assigned to this faculty for the batch
    )
    _override(authz_deps, faculty, unassigned)
    response = client.get(f"/api/v1/attendance/{profile.id}/summary")
    assert response.status_code == 403
    assert response.json()["detail"] == DENIED


def test_hod_denied_on_individual_student_record(authz_deps, client):
    """07 §2/§5: HOD sees aggregates/escalations, never individual records."""
    hod = _auth([UserRole.HOD])
    profile = _profile(uuid.uuid4())
    session = _session(_result(first=(profile, uuid.uuid4())))
    _override(authz_deps, hod, session)

    response = client.get(f"/api/v1/attendance/{profile.id}/summary")
    assert response.status_code == 403
    assert response.json()["detail"] == DENIED


def test_student_scoped_routes_share_the_matrix(authz_deps, client):
    """The same ownership dependency guards tasks list, student view and
    assessments summary (foreign student -> 403 on each)."""
    student = _auth([UserRole.STUDENT])
    foreign = _profile(uuid.uuid4())
    for url in (
        f"/api/v1/tasks/student/{foreign.id}",
        f"/api/v1/students/{foreign.id}",
        f"/api/v1/assessments/{foreign.id}/summary?course_id={uuid.uuid4()}",
    ):
        session = _session(_result(first=(foreign, uuid.uuid4())))
        _override(authz_deps, student, session)
        response = client.get(url)
        assert response.status_code == 403, url
        assert response.json()["detail"] == DENIED


# ------------------------------------------- int-raise defects (were 500s)


def test_students_me_non_student_403(authz_deps, client):
    mentor = _auth([UserRole.MENTOR])
    session = _session()
    _override(authz_deps, mentor, session)

    response = client.get("/api/v1/students/me")
    assert response.status_code == 403
    assert response.json()["detail"] == "Student role required"


def test_students_me_student_without_profile_404(authz_deps, client):
    student = _auth([UserRole.STUDENT])
    session = _session(_result(scalar=None))
    _override(authz_deps, student, session)

    response = client.get("/api/v1/students/me")
    assert response.status_code == 404
    assert response.json()["detail"] == "Student profile not found"


def _student_task(task_id, student_id, status):
    now = datetime.now(UTC)
    return StudentTask(
        id=task_id,
        student_id=student_id,
        source_type="MENTOR",
        source_id=uuid.uuid4(),
        created_by=uuid.uuid4(),
        title="R1 task",
        deadline=None,
        status=status,
        explicit_priority=None,
        urgency_score=None,
        created_at=now,
        updated_at=now,
    )


def test_task_complete_unknown_and_foreign_same_404(authz_deps, client):
    """complete resolves the caller's profile first, then filters by
    student_profiles.id — unknown and foreign tasks are the same 404."""
    student = _auth([UserRole.STUDENT])
    profile = _profile(student.user_id)

    session = _session(_result(scalar=profile), _result(scalar=None))
    _override(authz_deps, student, session)
    unknown = client.post(f"/api/v1/tasks/{uuid.uuid4()}/complete", json={})
    assert unknown.status_code == 404
    assert unknown.json()["detail"] == "Task not found"

    session = _session(_result(scalar=profile), _result(scalar=None))
    _override(authz_deps, student, session)
    foreign = client.post(f"/api/v1/tasks/{uuid.uuid4()}/complete", json={})
    assert foreign.status_code == 404
    assert foreign.json()["detail"] == unknown.json()["detail"]


def test_task_complete_already_completed_400(authz_deps, client):
    student = _auth([UserRole.STUDENT])
    profile = _profile(student.user_id)
    task = _student_task(uuid.uuid4(), profile.id, TaskStatus.COMPLETED)
    session = _session(_result(scalar=profile), _result(scalar=task))
    _override(authz_deps, student, session)

    response = client.post(f"/api/v1/tasks/{task.id}/complete", json={})
    assert response.status_code == 400
    assert response.json()["detail"] == "Task already completed"


def test_task_snooze_non_pending_400(authz_deps, client):
    student = _auth([UserRole.STUDENT])
    profile = _profile(student.user_id)
    task = _student_task(uuid.uuid4(), profile.id, TaskStatus.SNOOZED)
    session = _session(_result(scalar=profile), _result(scalar=task))
    _override(authz_deps, student, session)

    response = client.post(f"/api/v1/tasks/{task.id}/snooze")
    assert response.status_code == 400
    assert response.json()["detail"] == "Only pending tasks can be snoozed"


def test_task_complete_student_without_profile_403(authz_deps, client):
    student = _auth([UserRole.STUDENT])
    session = _session(_result(scalar=None))
    _override(authz_deps, student, session)

    response = client.post(f"/api/v1/tasks/{uuid.uuid4()}/complete", json={})
    assert response.status_code == 403
    assert response.json()["detail"] == DENIED


def test_attendance_what_if_no_state_404(authz_deps, client):
    student = _auth([UserRole.STUDENT])
    profile = _profile(student.user_id)
    session = _session(_result(first=(profile, uuid.uuid4())), _result(first=None))
    _override(authz_deps, student, session)

    course_id = uuid.uuid4()
    response = client.get(
        f"/api/v1/attendance/{profile.id}/what-if?course_id={course_id}&target=75"
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Attendance state not found"


def test_assessments_no_active_semester_404(authz_deps, client):
    student = _auth([UserRole.STUDENT])
    profile = _profile(student.user_id)
    session = _session(
        _result(first=(profile, uuid.uuid4())),   # helper: profile
        _result(first=(profile.batch_id, 2024)),  # handler: batch/enrollment
        _result(scalar=None),                     # handler: no active semester
    )
    _override(authz_deps, student, session)

    response = client.get(
        f"/api/v1/assessments/{profile.id}/summary?course_id={uuid.uuid4()}"
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "No active semester found"


def test_assessments_unknown_course_run_404(authz_deps, client):
    student = _auth([UserRole.STUDENT])
    profile = _profile(student.user_id)
    session = _session(
        _result(first=(profile, uuid.uuid4())),   # helper: profile
        _result(first=(profile.batch_id, 2024)),  # handler: batch/enrollment
        _result(scalar=uuid.uuid4()),             # handler: active semester
        _result(first=None),                      # handler: no course run
    )
    _override(authz_deps, student, session)

    response = client.get(
        f"/api/v1/assessments/{profile.id}/summary?course_id={uuid.uuid4()}"
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Course run not found"


# ------------------------------------------- cases: institution scoping


def test_queue_admin_path_is_institution_scoped(authz_deps, client):
    from sqlalchemy.dialects import postgresql

    admin = _auth([UserRole.ADMIN])
    captured = []

    async def execute(stmt):
        captured.append(stmt)
        return _result(rows=[])

    session = AsyncMock()
    session.execute = execute
    _override(authz_deps, admin, session)

    response = client.get("/api/v1/cases/queue")
    assert response.status_code == 200

    sql = str(captured[0].compile(dialect=postgresql.dialect())).upper()
    assert "JOIN STUDENT_PROFILES" in sql
    assert "JOIN BATCHES" in sql
    assert "INSTITUTION_ID" in sql


def test_queue_mentor_path_scoped_by_mentor_id(authz_deps, client):
    from sqlalchemy.dialects import postgresql

    mentor = _auth([UserRole.MENTOR])
    captured = []

    async def execute(stmt):
        captured.append(stmt)
        return _result(rows=[])

    session = AsyncMock()
    session.execute = execute
    _override(authz_deps, mentor, session)

    response = client.get("/api/v1/cases/queue")
    assert response.status_code == 200

    sql = str(captured[0].compile(dialect=postgresql.dialect())).upper()
    assert "MENTOR_ID" in sql


def _case(case_id, student_id, mentor_id, status=InterventionCaseStatus.PENDING_APPROVAL):
    now = datetime.now(UTC)
    return InterventionCase(
        id=case_id,
        student_id=student_id,
        mentor_id=mentor_id,
        status=status,
        urgency_band="URGENT",
        opened_at=now,
        created_at=now,
        updated_at=now,
    )


def test_approve_admin_cross_institution_403(authz_deps, client):
    admin = _auth([UserRole.ADMIN])
    case_id = uuid.uuid4()
    case = _case(case_id, uuid.uuid4(), uuid.uuid4())  # mentor is someone else
    session = _session(
        _result(scalar=case),               # FOR UPDATE case fetch
        _result(scalar=uuid.uuid4()),       # case's institution != admin's
    )
    _override(authz_deps, admin, session)

    response = client.post(f"/api/v1/cases/{case_id}/approve", json={"decision": "APPROVED"})
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authorized for this case"


def test_approve_unassigned_mentor_403(authz_deps, client):
    """A mentor acting on another mentor's case is refused with the same
    constant detail (07 §2: Own mentees only; RBAC-06)."""
    mentor = _auth([UserRole.MENTOR])
    case_id = uuid.uuid4()
    case = _case(case_id, uuid.uuid4(), uuid.uuid4())  # assigned elsewhere
    session = _session(_result(scalar=case))
    _override(authz_deps, mentor, session)

    response = client.post(f"/api/v1/cases/{case_id}/approve", json={"decision": "APPROVED"})
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authorized for this case"


def test_approve_admin_same_institution_reaches_service(authz_deps, client):
    """Same-institution admin passes the record-level check and proceeds into
    the approval service (which then refuses: no plan awaiting a decision)."""
    institution_id = uuid.uuid4()
    admin = _auth([UserRole.ADMIN], institution_id=institution_id)
    case_id = uuid.uuid4()
    case = _case(case_id, uuid.uuid4(), uuid.uuid4())
    session = _session(
        _result(scalar=case),
        _result(scalar=institution_id),  # same institution
        _result(scalars=[]),             # no plans
    )
    _override(authz_deps, admin, session)

    response = client.post(f"/api/v1/cases/{case_id}/approve", json={"decision": "APPROVED"})
    assert response.status_code == 400


def test_approve_non_mentor_non_admin_403(authz_deps, client):
    """A faculty user is stopped at the role gate (07 §2: cases = mentor /
    HOD escalations / admin) before any case lookup."""
    faculty = _auth([UserRole.FACULTY])
    session = _session()
    _override(authz_deps, faculty, session)

    response = client.post(f"/api/v1/cases/{uuid.uuid4()}/approve", json={"decision": "APPROVED"})
    assert response.status_code == 403
    assert response.json()["detail"] == "Mentor or Admin role required"


# ------------------------------------------- real dependency path (JWKS)


@pytest.fixture
def rsa_jwks():
    """Local RSA key + matching JWKS document (stands in for Supabase)."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    priv_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    pub = key.public_key().public_numbers()

    def b64url(value: int) -> str:
        raw = value.to_bytes((value.bit_length() + 7) // 8, "big")
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()

    jwk = JWK(
        kty="RSA",
        kid="r1-test-key",
        use="sig",
        alg="RS256",
        n=b64url(pub.n),
        e=b64url(pub.e),
    )
    return priv_pem, JWKS(keys=[jwk])


def _signed_token(priv_pem, *, sub, aud="r1-test-aud", exp_delta=300, kid="r1-test-key",
                  extra_headers=None, extra_claims=None):
    now = int(time.time())
    payload = {
        "sub": str(sub),
        "aud": aud,
        "iss": "supabase-test",
        "iat": now,
        "exp": now + exp_delta,
        "role": "authenticated",
    }
    if extra_claims:
        payload.update(extra_claims)
    headers = {"kid": kid} if kid else {}
    if extra_headers:
        headers.update(extra_headers)
    return jose_jwt.encode(payload, priv_pem, algorithm="RS256", headers=headers)


@pytest.fixture
def aud_patch(monkeypatch):
    """Deterministic audience for token validation (never reads .env)."""
    monkeypatch.setattr(app_settings, "next_public_supabase_publishable_key", "r1-test-aud")


def test_real_jwt_chain_builds_context_and_authorizes(authz_deps, client, rsa_jwks, aud_patch):
    """End-to-end dependency path: bearer token -> JWKS (mocked) -> RS256
    verify -> get_auth_context roles from user_role_assignments -> ownership
    helper -> handler. Supabase 'role' claim is identity-only (EC-USR-01)."""
    priv_pem, jwks = rsa_jwks
    user_id = uuid.uuid4()
    institution_id = uuid.uuid4()
    user = _user(user_id, institution_id)
    assignment = MagicMock()
    assignment.role = UserRole.STUDENT
    profile = _profile(user_id)
    session = _session(
        _result(scalar=user),                # get_auth_context: user row
        _result(scalars=[assignment]),       # get_auth_context: role assignments
        _result(first=(profile, institution_id)),  # ownership helper
        _result(rows=[]),                    # handler
    )
    _override_session_only(authz_deps, session)

    token = _signed_token(priv_pem, sub=user_id, extra_claims={"role": "anon"})
    with patch("app.api.deps._fetch_jwks", return_value=jwks):
        response = client.get(
            f"/api/v1/attendance/{profile.id}/summary",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert response.status_code == 200


@pytest.mark.parametrize(
    "token_kwargs,expected",
    [
        ({"exp_delta": -60}, 401),          # expired
        ({"aud": "someone-else"}, 401),     # wrong audience
        ({"kid": None}, 401),               # missing kid header
    ],
)
def test_real_jwt_chain_rejects_bad_tokens(authz_deps, client, rsa_jwks, aud_patch,
                                           token_kwargs, expected):
    priv_pem, jwks = rsa_jwks
    session = _session()
    _override_session_only(authz_deps, session)

    token = _signed_token(priv_pem, sub=uuid.uuid4(), **token_kwargs)
    with patch("app.api.deps._fetch_jwks", return_value=jwks):
        response = client.get(
            f"/api/v1/attendance/{uuid.uuid4()}/summary",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert response.status_code == expected


def test_real_jwt_chain_rejects_tampered_signature(authz_deps, client, rsa_jwks, aud_patch):
    priv_pem, jwks = rsa_jwks
    session = _session()
    _override_session_only(authz_deps, session)

    token = _signed_token(priv_pem, sub=uuid.uuid4())
    tampered = token[:-8] + ("A" if token[-8] != "A" else "B") + token[-7:]
    with patch("app.api.deps._fetch_jwks", return_value=jwks):
        response = client.get(
            f"/api/v1/attendance/{uuid.uuid4()}/summary",
            headers={"Authorization": f"Bearer {tampered}"},
        )
    assert response.status_code == 401


def test_real_jwt_chain_suspended_user_403(authz_deps, client, rsa_jwks, aud_patch):
    priv_pem, jwks = rsa_jwks
    user_id = uuid.uuid4()
    user = _user(user_id, uuid.uuid4(), status="SUSPENDED")
    session = _session(_result(scalar=user))
    _override_session_only(authz_deps, session)

    token = _signed_token(priv_pem, sub=user_id)
    with patch("app.api.deps._fetch_jwks", return_value=jwks):
        response = client.get(
            f"/api/v1/attendance/{uuid.uuid4()}/summary",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert response.status_code == 403
    assert response.json()["detail"] == "User account suspended"


def test_real_jwt_chain_no_role_assignments_403(authz_deps, client, rsa_jwks, aud_patch):
    """Valid identity but zero ASPIRE role assignments -> ownership denies."""
    priv_pem, jwks = rsa_jwks
    user_id = uuid.uuid4()
    user = _user(user_id, uuid.uuid4())
    session = _session(
        _result(scalar=user),
        _result(scalars=[]),  # no role assignments in window
        _result(first=None),  # helper: profile missing -> denied
    )
    _override_session_only(authz_deps, session)

    token = _signed_token(priv_pem, sub=user_id)
    with patch("app.api.deps._fetch_jwks", return_value=jwks):
        response = client.get(
            f"/api/v1/attendance/{uuid.uuid4()}/summary",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert response.status_code == 403
    assert response.json()["detail"] == DENIED
