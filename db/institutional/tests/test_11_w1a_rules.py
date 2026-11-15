"""W1a behavioural rules: constraints, checks, seals, and triggers.

These tests execute the rules as the database enforces them. They complement
the structural checks in ``test_10_w1a_schema.py``.
"""

from __future__ import annotations

import psycopg

from w1a_support import (
    ACADEMIC_YEAR,
    ASSIGNMENT,
    BUNDLE_VERSION,
    DOC_INTERNAL,
    DOC_PUBLIC,
    ENTITY_TYPE,
    EXTERNAL_SYSTEM,
    INSTITUTION,
    ORG_CHILD,
    ORG_ROOT,
    P1,
    P2,
    RETENTION,
    ROLE,
    RULE,
    RULE_VERSION_CURRENT,
    RULE_VERSION_DRAFT,
    SYNC_RUN,
    TERM,
    VERSION_PUBLIC,
    expect_error,
    w1a_base,
)

_ = w1a_base  # imported fixture


def test_person_names_are_not_unique_but_date_of_birth_must_be_in_the_past(
    conn: psycopg.Connection, w1a_base: psycopg.Connection
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO iam.person (legal_name, date_of_birth) VALUES ('Person One', DATE '1990-01-01')"
        )
    expect_error(
        conn,
        "UPDATE iam.person SET date_of_birth = CURRENT_DATE WHERE person_id = %s",
        (P1,),
        contains="date_of_birth must be before current_date",
    )
    expect_error(
        conn,
        "INSERT INTO iam.person (legal_name, date_of_birth) VALUES ('Future Person', CURRENT_DATE + 1)",
        contains="date_of_birth must be before current_date",
    )
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE iam.person SET date_of_birth = DATE '1999-12-31' WHERE person_id = %s",
            (P1,),
        )


def test_system_role_delete_is_rejected(
    conn: psycopg.Connection, w1a_base: psycopg.Connection
) -> None:
    expect_error(
        conn,
        "DELETE FROM iam.role WHERE role_id = %s",
        (ROLE,),
        contains="system role",
    )
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO iam.role (role_code, name, category, is_system_role)
            VALUES ('TEMP_ROLE', 'Temporary', 'system', false)
            """
        )
        cur.execute("DELETE FROM iam.role WHERE role_code = 'TEMP_ROLE'")


def test_org_unit_path_is_materialised_and_cycles_are_rejected(
    conn: psycopg.Connection, w1a_base: psycopg.Connection
) -> None:
    with conn.cursor() as cur:
        cur.execute("SELECT path FROM core.org_unit WHERE org_unit_id = %s", (ORG_CHILD,))
        assert cur.fetchone() == ("ENG/CSE",)

    expect_error(
        conn,
        "UPDATE core.org_unit SET parent_org_unit_id = %s WHERE org_unit_id = %s",
        (ORG_CHILD, ORG_ROOT),
        contains="cycle detected",
    )

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO core.org_unit
                (org_unit_id, institution_id, parent_org_unit_id, code, name, unit_type)
            VALUES ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa3', %s, %s, 'SE', 'Software', 'department')
            """,
            (INSTITUTION, ORG_CHILD),
        )
        cur.execute(
            "UPDATE core.org_unit SET code = 'CSE2' WHERE org_unit_id = %s", (ORG_CHILD,)
        )
        cur.execute(
            "SELECT path FROM core.org_unit WHERE org_unit_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa3'"
        )
        assert cur.fetchone() == ("ENG/CSE2/SE",)


def test_rule_version_current_requires_an_approval_reference(
    conn: psycopg.Connection, w1a_base: psycopg.Connection
) -> None:
    expect_error(
        conn,
        """
        INSERT INTO policy.rule_version
            (rule_id, version_no, statement, effective_from, status, approval_reference)
        VALUES (%s, 3, 'Unapproved', CURRENT_DATE, 'Current', NULL)
        """,
        (RULE,),
        contains="requires approval_reference",
    )
    expect_error(
        conn,
        "UPDATE policy.rule_version SET status = 'Current' WHERE rule_version_id = %s",
        (RULE_VERSION_DRAFT,),
        contains="requires approval_reference",
    )
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE policy.rule_version SET status = 'Current', approval_reference = 'AC/1' WHERE rule_version_id = %s",
            (RULE_VERSION_DRAFT,),
        )


def test_referenced_rule_version_is_sealed(
    conn: psycopg.Connection, w1a_base: psycopg.Connection
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO policy.policy_bundle_member
                (policy_bundle_version_id, rule_version_id)
            VALUES (%s, %s)
            """,
            (BUNDLE_VERSION, RULE_VERSION_DRAFT),
        )
    expect_error(
        conn,
        "UPDATE policy.rule_version SET statement = 'changed' WHERE rule_version_id = %s",
        (RULE_VERSION_DRAFT,),
        contains="immutable",
    )
    expect_error(
        conn,
        "DELETE FROM policy.rule_version WHERE rule_version_id = %s",
        (RULE_VERSION_DRAFT,),
        contains="immutable",
    )


def test_document_version_seals_when_active(
    conn: psycopg.Connection, w1a_base: psycopg.Connection
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE doc.document_version SET status = 'active' WHERE document_version_id = %s",
            (VERSION_PUBLIC,),
        )
    expect_error(
        conn,
        "UPDATE doc.document_version SET change_note = 'late edit' WHERE document_version_id = %s",
        (VERSION_PUBLIC,),
        contains="sealed",
    )
    expect_error(
        conn,
        "DELETE FROM doc.document_version WHERE document_version_id = %s",
        (VERSION_PUBLIC,),
        contains="sealed",
    )


def test_append_only_tables_reject_update_and_delete(
    conn: psycopg.Connection, w1a_base: psycopg.Connection
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO ops.audit_event (action, record_hash) VALUES ('test.action', %s)",
            ("a" * 64,),
        )
        cur.execute(
            """
            INSERT INTO integration.sync_record
                (sync_run_id, entity_type_code, internal_id, operation, outcome)
            VALUES (%s, %s, %s, 'insert', 'success')
            """,
            (SYNC_RUN, ENTITY_TYPE, P1),
        )

    for statement, params in (
        ("UPDATE policy.policy_bundle_version SET status = 'active' WHERE policy_bundle_version_id = %s", (BUNDLE_VERSION,)),
        ("DELETE FROM policy.policy_bundle_version WHERE policy_bundle_version_id = %s", (BUNDLE_VERSION,)),
        ("UPDATE integration.sync_record SET outcome = 'failed' WHERE sync_run_id = %s", (SYNC_RUN,)),
        ("DELETE FROM integration.sync_record WHERE sync_run_id = %s", (SYNC_RUN,)),
        ("UPDATE ops.audit_event SET action = 'changed' WHERE action = 'test.action'", ()),
        ("DELETE FROM ops.audit_event WHERE action = 'test.action'", ()),
    ):
        expect_error(conn, statement, params, contains="append-only")


def test_sync_run_is_sealed_in_a_terminal_state(
    conn: psycopg.Connection, w1a_base: psycopg.Connection
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE integration.sync_run SET status = 'completed', finished_at = now() WHERE sync_run_id = %s",
            (SYNC_RUN,),
        )
    expect_error(
        conn,
        "UPDATE integration.sync_run SET status = 'failed' WHERE sync_run_id = %s",
        (SYNC_RUN,),
        contains="sealed",
    )
    expect_error(
        conn,
        "DELETE FROM integration.sync_run WHERE sync_run_id = %s",
        (SYNC_RUN,),
        contains="sealed",
    )


def test_person_contact_primary_and_format_rules(
    conn: psycopg.Connection, w1a_base: psycopg.Connection
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO iam.person_contact
                (person_id, contact_type, value, is_primary)
            VALUES (%s, 'email', 'first@example.com', true)
            """,
            (P1,),
        )
    expect_error(
        conn,
        """
        INSERT INTO iam.person_contact (person_id, contact_type, value, is_primary)
        VALUES (%s, 'email', 'second@example.com', true)
        """,
        (P1,),
        contains="uq_person_contact_primary",
    )
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO iam.person_contact (person_id, contact_type, value, is_primary)
            VALUES (%s, 'email', 'secondary@example.com', false)
            """,
            (P1,),
        )
    expect_error(
        conn,
        """
        INSERT INTO iam.person_contact (person_id, contact_type, value)
        VALUES (%s, 'email', 'not-an-email')
        """,
        (P1,),
        contains="ck_person_contact_email_format",
    )
    expect_error(
        conn,
        """
        INSERT INTO iam.person_contact (person_id, contact_type, value)
        VALUES (%s, 'phone', 'not-a-phone')
        """,
        (P1,),
        contains="ck_person_contact_phone_format",
    )


def test_role_assignment_scope_rules(
    conn: psycopg.Connection, w1a_base: psycopg.Connection
) -> None:
    expect_error(
        conn,
        """
        INSERT INTO iam.role_assignment
            (person_id, role_id, scope_type, scope_key, institution_id)
        VALUES (%s, %s, 'institution', %s, %s)
        """,
        (P1, ROLE, "99999999-9999-9999-9999-999999999999", INSTITUTION),
        contains="scope_key",
    )
    expect_error(
        conn,
        """
        INSERT INTO iam.role_assignment
            (person_id, role_id, scope_type, scope_key)
        VALUES (%s, %s, 'institution', %s)
        """,
        (P1, ROLE, INSTITUTION),
        contains="requires its scope column",
    )
    expect_error(
        conn,
        """
        INSERT INTO iam.role_assignment
            (person_id, role_id, scope_type, scope_key, institution_id, org_unit_id)
        VALUES (%s, %s, 'institution', %s, %s, %s)
        """,
        (P1, ROLE, INSTITUTION, INSTITUTION, ORG_ROOT),
        contains="ck_role_assignment_one_scope",
    )
    expect_error(
        conn,
        """
        INSERT INTO iam.role_assignment
            (person_id, role_id, scope_type, scope_key, institution_id)
        VALUES (%s, %s, 'institution', %s, %s)
        """,
        (P1, ROLE, INSTITUTION, INSTITUTION),
        contains="uq_role_assignment_active_scope",
    )
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO iam.role_assignment
                (person_id, role_id, scope_type, scope_key, institution_id, status)
            VALUES (%s, %s, 'institution', %s, %s, 'suspended')
            """,
            (P1, ROLE, INSTITUTION, INSTITUTION),
        )


def test_academic_calendar_has_one_approved_version_per_term(
    conn: psycopg.Connection, w1a_base: psycopg.Connection
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO core.academic_calendar (term_id, version_no, status)
            VALUES (%s, 1, 'approved')
            """,
            (TERM,),
        )
    expect_error(
        conn,
        """
        INSERT INTO core.academic_calendar (term_id, version_no, status)
        VALUES (%s, 2, 'approved')
        """,
        (TERM,),
        contains="uq_academic_calendar_approved_per_term",
    )
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO core.academic_calendar (term_id, version_no, status)
            VALUES (%s, 2, 'draft')
            """,
            (TERM,),
        )


def test_document_classification_cannot_be_downgraded(
    conn: psycopg.Connection, w1a_base: psycopg.Connection
) -> None:
    """DOC-02: the guard lives on doc.document, which owns classification.

    The documented "audited declassification record" exception is a future
    feature and is deliberately not implemented, so every downgrade is rejected.
    """
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE doc.document SET classification = 'C' WHERE document_id = %s",
            (DOC_INTERNAL,),
        )
        cur.execute(
            "UPDATE doc.document SET classification = 'C' WHERE document_id = %s",
            (DOC_INTERNAL,),
        )
    expect_error(
        conn,
        "UPDATE doc.document SET classification = 'P' WHERE document_id = %s",
        (DOC_INTERNAL,),
        contains="cannot be downgraded",
    )


def test_rule_conflict_pair_is_ordered_and_distinct(
    conn: psycopg.Connection, w1a_base: psycopg.Connection
) -> None:
    expect_error(
        conn,
        """
        INSERT INTO policy.rule_conflict (rule_version_a_id, rule_version_b_id, description)
        VALUES (%s, %s, 'reversed')
        """,
        (RULE_VERSION_CURRENT, RULE_VERSION_DRAFT),
        contains="ck_rule_conflict_ordered",
    )
    expect_error(
        conn,
        """
        INSERT INTO policy.rule_conflict (rule_version_a_id, rule_version_b_id, description)
        VALUES (%s, %s, 'same')
        """,
        (RULE_VERSION_DRAFT, RULE_VERSION_DRAFT),
        contains="ck_rule_conflict_distinct",
    )
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO policy.rule_conflict (rule_version_a_id, rule_version_b_id, description)
            VALUES (%s, %s, 'valid pair')
            """,
            (RULE_VERSION_DRAFT, RULE_VERSION_CURRENT),
        )


def test_bundle_member_and_rule_scope_uniqueness(
    conn: psycopg.Connection, w1a_base: psycopg.Connection
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO policy.policy_bundle_member (policy_bundle_version_id, rule_version_id)
            VALUES (%s, %s)
            """,
            (BUNDLE_VERSION, RULE_VERSION_DRAFT),
        )
        cur.execute(
            """
            INSERT INTO policy.rule_scope (rule_version_id, scope_type, institution_id)
            VALUES (%s, 'institution', %s)
            """,
            (RULE_VERSION_DRAFT, INSTITUTION),
        )
    expect_error(
        conn,
        """
        INSERT INTO policy.policy_bundle_member (policy_bundle_version_id, rule_version_id)
        VALUES (%s, %s)
        """,
        (BUNDLE_VERSION, RULE_VERSION_DRAFT),
        contains="uq_policy_bundle_member",
    )
    expect_error(
        conn,
        """
        INSERT INTO policy.rule_scope (rule_version_id, scope_type, institution_id)
        VALUES (%s, 'institution', %s)
        """,
        (RULE_VERSION_DRAFT, INSTITUTION),
        contains="uq_rule_scope",
    )
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO policy.rule_scope (rule_version_id, scope_type, term_id)
            VALUES (%s, 'term', %s)
            """,
            (RULE_VERSION_DRAFT, TERM),
        )


def test_rule_scope_attributes_can_narrow_an_entity_scope(
    conn: psycopg.Connection, w1a_base: psycopg.Connection
) -> None:
    """Review ruling: course_type/student_category narrow an entity scope.

    They are the sole scope only when scope_type names them; an entity
    scope_type may carry either narrowing attribute.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO policy.rule_scope
                (rule_version_id, scope_type, institution_id, course_type)
            VALUES (%s, 'institution', %s, 'theory')
            """,
            (RULE_VERSION_DRAFT, INSTITUTION),
        )
        cur.execute(
            """
            INSERT INTO policy.rule_scope
                (rule_version_id, scope_type, institution_id, student_category)
            VALUES (%s, 'institution', %s, 'OBC')
            """,
            (RULE_VERSION_DRAFT, INSTITUTION),
        )
        cur.execute(
            """
            INSERT INTO policy.rule_scope
                (rule_version_id, scope_type, student_category)
            VALUES (%s, 'student_category', 'SC')
            """,
            (RULE_VERSION_DRAFT,),
        )
    expect_error(
        conn,
        """
        INSERT INTO policy.rule_scope
            (rule_version_id, scope_type, institution_id, course_type)
        VALUES (%s, 'course_type', %s, 'theory')
        """,
        (RULE_VERSION_DRAFT, INSTITUTION),
        contains="ck_rule_scope_scope_match",
    )


def test_document_reference_pairs_are_unique(
    conn: psycopg.Connection, w1a_base: psycopg.Connection
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO doc.document
                (title, document_type, issuer_name, issuer_org_unit_id,
                 reference_no, document_date, classification)
            VALUES ('Reference one', 'other', 'BCREC', %s, 'REF-1', CURRENT_DATE, 'I')
            """,
            (ORG_ROOT,),
        )
    expect_error(
        conn,
        """
        INSERT INTO doc.document
            (title, document_type, issuer_name, issuer_org_unit_id,
             reference_no, document_date, classification)
        VALUES ('Reference two', 'other', 'BCREC', %s, 'REF-1', CURRENT_DATE, 'I')
        """,
        (ORG_ROOT,),
        contains="uq_document_issuer_reference",
    )


def test_document_version_hash_and_number_are_unique(
    conn: psycopg.Connection, w1a_base: psycopg.Connection
) -> None:
    expect_error(
        conn,
        """
        INSERT INTO doc.document_version
            (document_id, version_no, file_uri, mime_type, sha256, status)
        VALUES (%s, 1, 's3://docs/duplicate.pdf', 'application/pdf', %s, 'draft')
        """,
        (DOC_PUBLIC, "d" * 64),
        contains="uq_document_version_document_no",
    )
    expect_error(
        conn,
        """
        INSERT INTO doc.document_version
            (document_id, version_no, file_uri, mime_type, sha256, status)
        VALUES (%s, 2, 's3://docs/duplicate-bytes.pdf', 'application/pdf', %s, 'draft')
        """,
        (DOC_PUBLIC, "a" * 64),
        contains="uq_document_version_sha256",
    )
    expect_error(
        conn,
        """
        INSERT INTO doc.document_version
            (document_id, version_no, file_uri, mime_type, sha256, status)
        VALUES (%s, 2, 's3://docs/bad-hash.pdf', 'application/pdf', 'short', 'draft')
        """,
        (DOC_PUBLIC,),
        contains="ck_document_version_sha256_length",
    )


def test_external_id_mapping_current_identity_is_unique(
    conn: psycopg.Connection, w1a_base: psycopg.Connection
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO integration.external_id_mapping
                (entity_type_code, external_system_id, internal_id, external_id)
            VALUES (%s, %s, %s, 'EXT-1')
            """,
            (ENTITY_TYPE, EXTERNAL_SYSTEM, P1),
        )
    expect_error(
        conn,
        """
        INSERT INTO integration.external_id_mapping
            (entity_type_code, external_system_id, internal_id, external_id)
        VALUES (%s, %s, %s, 'EXT-1')
        """,
        (ENTITY_TYPE, EXTERNAL_SYSTEM, P2),
        contains="uq_external_id_mapping_current_external",
    )
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO integration.external_id_mapping
                (entity_type_code, external_system_id, internal_id, external_id, valid_to)
            VALUES (%s, %s, %s, 'EXT-1', CURRENT_DATE + 1)
            """,
            (ENTITY_TYPE, EXTERNAL_SYSTEM, P2),
        )


def test_numeric_and_date_checks(conn: psycopg.Connection, w1a_base: psycopg.Connection) -> None:
    expect_error(
        conn,
        """
        INSERT INTO core.academic_year
            (institution_id, label, start_date, end_date)
        VALUES (%s, '2027-28', CURRENT_DATE, CURRENT_DATE)
        """,
        (INSTITUTION,),
        contains="ck_academic_year_dates",
    )
    expect_error(
        conn,
        """
        INSERT INTO core.term
            (academic_year_id, term_type, term_no, start_date, end_date)
        VALUES (%s, 'even', 2, CURRENT_DATE, CURRENT_DATE)
        """,
        (ACADEMIC_YEAR,),
        contains="ck_term_dates",
    )
    expect_error(
        conn,
        """
        INSERT INTO core.affiliation_record
            (programme_id, academic_year_id, intake_approved)
        VALUES (%s, %s, -1)
        """,
        ("99999999-9999-9999-9999-999999999999", ACADEMIC_YEAR),
        contains="ck_affiliation_record_intake_approved",
    )
    expect_error(
        conn,
        """
        INSERT INTO core.academic_calendar (term_id, version_no, status)
        VALUES (%s, 0, 'draft')
        """,
        (TERM,),
        contains="ck_academic_calendar_version_no",
    )
    expect_error(
        conn,
        "UPDATE integration.sync_run SET finished_at = started_at - interval '1 hour' WHERE sync_run_id = %s",
        (SYNC_RUN,),
        contains="ck_sync_run_finished_after_start",
    )
    expect_error(
        conn,
        """
        INSERT INTO integration.outbox_event
            (aggregate_type, aggregate_id, event_type, occurred_at, published_at, status)
        VALUES ('test', %s, 'test.created', now(), now() - interval '1 hour', 'published')
        """,
        (P1,),
        contains="ck_outbox_event_published_after_occurred",
    )
    expect_error(
        conn,
        "UPDATE doc.document SET effective_date = document_date - 1 WHERE document_id = %s",
        (DOC_PUBLIC,),
        contains="ck_document_effective_date",
    )
    expect_error(
        conn,
        "UPDATE doc.document_version SET page_count = -1 WHERE document_version_id = %s",
        (VERSION_PUBLIC,),
        contains="ck_document_version_page_count",
    )
    expect_error(
        conn,
        "UPDATE ops.retention_schedule SET status = 'approved' WHERE retention_schedule_id = %s",
        (RETENTION,),
        contains="ck_retention_schedule_approved_requires_approver",
    )
    expect_error(
        conn,
        """
        INSERT INTO ops.break_glass_grant (person_id, reason, expires_at)
        VALUES (%s, 'short', now() + interval '1 hour')
        """,
        (P1,),
        contains="ck_break_glass_grant_reason_length",
    )
    expect_error(
        conn,
        """
        INSERT INTO ops.break_glass_grant (person_id, reason, starts_at, expires_at)
        VALUES (%s, 'A valid reason', now(), now())
        """,
        (P1,),
        contains="ck_break_glass_grant_expiry",
    )


def test_audit_event_hash_columns_are_checked(
    conn: psycopg.Connection, w1a_base: psycopg.Connection
) -> None:
    expect_error(
        conn,
        "INSERT INTO ops.audit_event (action, record_hash) VALUES ('test', 'short')",
        contains="ck_audit_event_record_hash_length",
    )
    expect_error(
        conn,
        """
        INSERT INTO ops.audit_event (action, prev_hash, record_hash)
        VALUES ('test', 'short', %s)
        """,
        ("a" * 64,),
        contains="ck_audit_event_prev_hash_length",
    )
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ops.audit_event (action, prev_hash, record_hash)
            VALUES ('test', %s, %s)
            """,
            ("b" * 64, "c" * 64),
        )


def test_identity_account_uniqueness(conn: psycopg.Connection, w1a_base: psycopg.Connection) -> None:
    expect_error(
        conn,
        """
        INSERT INTO iam.identity_account (person_id, idp_code, subject, username, status)
        VALUES (%s, 'local', 'person-one-second', 'another.username', 'active')
        """,
        (P1,),
        contains="uq_identity_account_person_active",
    )
    expect_error(
        conn,
        """
        INSERT INTO iam.identity_account (person_id, idp_code, subject, username)
        VALUES (%s, 'local', 'another-subject', 'PERSON.ONE')
        """,
        (P2,),
        contains="uq_identity_account_username_lower",
    )
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO iam.identity_account
                (person_id, idp_code, subject, username, status)
            VALUES (%s, 'local', 'person-one-disabled', 'person.one.disabled', 'disabled')
            """,
            (P1,),
        )


def test_retention_schedule_approval_requires_an_approver(
    conn: psycopg.Connection, w1a_base: psycopg.Connection
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE ops.retention_schedule
            SET status = 'approved', approved_by = %s
            WHERE retention_schedule_id = %s
            """,
            (P1, RETENTION),
        )
