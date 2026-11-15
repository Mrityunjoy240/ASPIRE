"""Shared baseline data and helpers for W1a rule and security tests.

The fixture is deliberately small: one institution, two people, one authority
assignment, one term, three documents at different classifications, and one
row in each append-only table family. Every test runs inside a transaction that
is rolled back afterwards.
"""

from __future__ import annotations

from datetime import date, timedelta

import psycopg
import pytest

P1 = "11111111-1111-1111-1111-111111111111"
P2 = "11111111-1111-1111-1111-111111111112"
A1 = "22222222-2222-2222-2222-222222222221"
A2 = "22222222-2222-2222-2222-222222222222"
INSTITUTION = "33333333-3333-3333-3333-333333333331"
ROLE = "44444444-4444-4444-4444-444444444441"
PERMISSION = "55555555-5555-5555-5555-555555555551"
ASSIGNMENT = "66666666-6666-6666-6666-666666666661"
DOC_PUBLIC = "88888888-8888-8888-8888-888888888881"
DOC_INTERNAL = "88888888-8888-8888-8888-888888888882"
DOC_CONFIDENTIAL = "88888888-8888-8888-8888-888888888883"
VERSION_PUBLIC = "99999999-9999-9999-9999-999999999991"
VERSION_INTERNAL = "99999999-9999-9999-9999-999999999992"
VERSION_CONFIDENTIAL = "99999999-9999-9999-9999-999999999993"
ORG_ROOT = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1"
ORG_CHILD = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2"
ACADEMIC_YEAR = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb1"
TERM = "cccccccc-cccc-cccc-cccc-ccccccccccc1"
RULE = "dddddddd-dddd-dddd-dddd-ddddddddddd1"
RULE_VERSION_DRAFT = "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeee1"
RULE_VERSION_CURRENT = "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeee2"
BUNDLE = "ffffffff-ffff-ffff-ffff-fffffffffff1"
BUNDLE_VERSION = "f1f1f1f1-f1f1-f1f1-f1f1-f1f1f1f1f1f1"
ENTITY_TYPE = "test.entity"
EXTERNAL_SYSTEM = "abababab-abab-abab-abab-abababababab"
SYNC_RUN = "acacacac-acac-acac-acac-acacacacacac"
RETENTION = "adadadad-adad-adad-adad-adadadadadad"

TODAY = date.today()
YEAR_START = TODAY - timedelta(days=120)
YEAR_END = TODAY + timedelta(days=245)
TERM_START = TODAY - timedelta(days=90)
TERM_END = TODAY + timedelta(days=90)


def expect_error(
    conn: psycopg.Connection,
    statement: str,
    params=None,
    contains: str | None = None,
) -> str:
    """Run a statement expected to fail, rolling back only that attempt."""
    with conn.cursor() as cur:
        cur.execute("SAVEPOINT attempt")
        try:
            cur.execute(statement, params)
        except psycopg.Error as exc:
            cur.execute("ROLLBACK TO SAVEPOINT attempt")
            text = str(exc)
            if contains is not None:
                assert contains.lower() in text.lower(), text
            return text
        else:
            cur.execute("ROLLBACK TO SAVEPOINT attempt")
            raise AssertionError(f"statement unexpectedly succeeded: {statement}")


@pytest.fixture()
def w1a_base(conn: psycopg.Connection):
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO iam.person (person_id, legal_name, date_of_birth)
            VALUES (%s, 'Person One', DATE '2000-01-01'),
                   (%s, 'Person Two', DATE '2001-02-02')
            """,
            (P1, P2),
        )
        cur.execute(
            """
            INSERT INTO iam.identity_account
                (account_id, person_id, idp_code, subject, username, status)
            VALUES (%s, %s, 'local', 'person-one', 'person.one', 'active'),
                   (%s, %s, 'local', 'person-two', 'person.two', 'active')
            """,
            (A1, P1, A2, P2),
        )
        cur.execute(
            """
            INSERT INTO core.institution
                (institution_id, legal_name, short_name, college_code)
            VALUES (%s, 'Test Institute', 'TI', '100')
            """,
            (INSTITUTION,),
        )
        cur.execute(
            """
            INSERT INTO core.org_unit
                (org_unit_id, institution_id, code, name, unit_type)
            VALUES (%s, %s, 'ENG', 'Engineering', 'department')
            """,
            (ORG_ROOT, INSTITUTION),
        )
        cur.execute(
            """
            INSERT INTO core.org_unit
                (org_unit_id, institution_id, parent_org_unit_id, code, name, unit_type)
            VALUES (%s, %s, %s, 'CSE', 'Computer Science', 'department')
            """,
            (ORG_CHILD, INSTITUTION, ORG_ROOT),
        )
        cur.execute(
            """
            INSERT INTO core.academic_year
                (academic_year_id, institution_id, label, start_date, end_date)
            VALUES (%s, %s, '2026-27', %s, %s)
            """,
            (ACADEMIC_YEAR, INSTITUTION, YEAR_START, YEAR_END),
        )
        cur.execute(
            """
            INSERT INTO core.term
                (term_id, academic_year_id, term_type, term_no, start_date, end_date)
            VALUES (%s, %s, 'odd', 1, %s, %s)
            """,
            (TERM, ACADEMIC_YEAR, TERM_START, TERM_END),
        )
        cur.execute(
            """
            INSERT INTO iam.role (role_id, role_code, name, category, is_system_role)
            VALUES (%s, 'TEST_ROLE', 'Test Role', 'system', true)
            """,
            (ROLE,),
        )
        cur.execute(
            """
            INSERT INTO iam.permission (permission_id, permission_code, resource, action)
            VALUES (%s, 'test.read', 'test', 'read')
            """,
            (PERMISSION,),
        )
        cur.execute(
            "INSERT INTO iam.role_permission (role_id, permission_id) VALUES (%s, %s)",
            (ROLE, PERMISSION),
        )
        cur.execute(
            """
            INSERT INTO iam.role_assignment
                (role_assignment_id, person_id, role_id, scope_type, scope_key, institution_id)
            VALUES (%s, %s, %s, 'institution', %s, %s)
            """,
            (ASSIGNMENT, P1, ROLE, INSTITUTION, INSTITUTION),
        )
        cur.execute(
            """
            INSERT INTO doc.document
                (document_id, title, document_type, issuer_name, document_date, classification)
            VALUES
                (%s, 'Public document', 'other', 'BCREC', %s, 'P'),
                (%s, 'Internal document', 'other', 'BCREC', %s, 'I'),
                (%s, 'Confidential document', 'other', 'BCREC', %s, 'C')
            """,
            (
                DOC_PUBLIC, TODAY,
                DOC_INTERNAL, TODAY,
                DOC_CONFIDENTIAL, TODAY,
            ),
        )
        cur.execute(
            """
            INSERT INTO doc.document_version
                (document_version_id, document_id, version_no, file_uri, mime_type, sha256, status)
            VALUES
                (%s, %s, 1, 's3://docs/public.pdf', 'application/pdf', %s, 'draft'),
                (%s, %s, 1, 's3://docs/internal.pdf', 'application/pdf', %s, 'draft'),
                (%s, %s, 1, 's3://docs/confidential.pdf', 'application/pdf', %s, 'draft')
            """,
            (
                VERSION_PUBLIC, DOC_PUBLIC, "a" * 64,
                VERSION_INTERNAL, DOC_INTERNAL, "b" * 64,
                VERSION_CONFIDENTIAL, DOC_CONFIDENTIAL, "c" * 64,
            ),
        )
        cur.execute(
            """
            INSERT INTO policy.rule (rule_id, rule_code, title, domain)
            VALUES (%s, 'TEST_RULE', 'Test Rule', 'other')
            """,
            (RULE,),
        )
        cur.execute(
            """
            INSERT INTO policy.rule_version
                (rule_version_id, rule_id, version_no, statement, effective_from, status, approval_reference)
            VALUES
                (%s, %s, 1, 'Draft statement', %s, 'Draft', NULL),
                (%s, %s, 2, 'Current statement', %s, 'Current', 'AC/2026/1')
            """,
            (
                RULE_VERSION_DRAFT, RULE, TODAY,
                RULE_VERSION_CURRENT, RULE, TODAY,
            ),
        )
        cur.execute(
            """
            INSERT INTO policy.policy_bundle (policy_bundle_id, bundle_code, name, domain)
            VALUES (%s, 'TEST_BUNDLE', 'Test Bundle', 'other')
            """,
            (BUNDLE,),
        )
        cur.execute(
            """
            INSERT INTO policy.policy_bundle_version
                (policy_bundle_version_id, policy_bundle_id, version_no, effective_from, status)
            VALUES (%s, %s, 1, %s, 'draft')
            """,
            (BUNDLE_VERSION, BUNDLE, TODAY),
        )
        cur.execute(
            """
            INSERT INTO integration.entity_type
                (entity_type_code, description, schema_name, table_name)
            VALUES (%s, 'Test entity', 'iam', 'person')
            """,
            (ENTITY_TYPE,),
        )
        cur.execute(
            """
            INSERT INTO integration.external_system (external_system_id, code, name, system_type)
            VALUES (%s, 'TEST_SYS', 'Test System', 'college_erp')
            """,
            (EXTERNAL_SYSTEM,),
        )
        cur.execute(
            """
            INSERT INTO integration.sync_run
                (sync_run_id, external_system_id, entity_type_code)
            VALUES (%s, %s, %s)
            """,
            (SYNC_RUN, EXTERNAL_SYSTEM, ENTITY_TYPE),
        )
        cur.execute(
            """
            INSERT INTO ops.retention_schedule
                (retention_schedule_id, entity_type_code, classification,
                 retention_period_months, disposition, status)
            VALUES (%s, %s, 'I', 12, 'archive', 'draft')
            """,
            (RETENTION, ENTITY_TYPE),
        )

    try:
        yield conn
    finally:
        conn.rollback()
