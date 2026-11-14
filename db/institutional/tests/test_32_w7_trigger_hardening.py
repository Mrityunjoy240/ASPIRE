"""W7 / Phase 9B TRG-EXEC regression: trigger functions are hardened and fire.

The ten W1a trigger functions must no longer be executable by PUBLIC or by a
runtime role, must remain SECURITY INVOKER and owner-held, and their 17
dependent triggers must still fire. The tests below exercise every trigger.
"""

from __future__ import annotations

import psycopg

from w1a_support import (
    ASSIGNMENT,
    BUNDLE_VERSION,
    ENTITY_TYPE,
    INSTITUTION,
    ORG_CHILD,
    ORG_ROOT,
    P1,
    ROLE,
    RULE_VERSION_DRAFT,
    SYNC_RUN,
    VERSION_PUBLIC,
    expect_error,
    w1a_base,
)
from w1b_support import w1b_base
from w2_support import w2_base
from w3_support import w3_base
from w4_support import w4_base
from w5_support import w5_base
from w6_support import (
    CHUNK_PUBLIC,
    CITATION,
    MESSAGE_P3_USER,
    RETRIEVAL_HIT,
    RETRIEVAL_LOG,
    w6_base,
)

_ = (w1a_base, w1b_base, w2_base, w3_base, w4_base, w5_base, w6_base)

FUNCTIONS = (
    ("core", "refresh_org_unit_descendant_paths", "owner_core"),
    ("core", "set_org_unit_path", "owner_core"),
    ("doc", "seal_document_version", "owner_doc"),
    ("iam", "check_person_date_of_birth", "owner_iam"),
    ("iam", "enforce_role_assignment_scope", "owner_iam"),
    ("iam", "reject_system_role_delete", "owner_iam"),
    ("integration", "seal_sync_run", "owner_integration"),
    ("ops", "reject_mutation", "owner_ops"),
    ("policy", "check_rule_version_current", "owner_policy"),
    ("policy", "seal_referenced_rule_version", "owner_policy"),
)

FUNCTION_NAMES = tuple(name for _, name, _ in FUNCTIONS)

DESIGN_SCHEMAS = (
    "academic",
    "assessment",
    "attendance",
    "cip",
    "core",
    "doc",
    "exam",
    "faculty",
    "iam",
    "integration",
    "knowledge",
    "ops",
    "policy",
    "student",
)

NEW_ORG_UNIT = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa3"
SYNC_RECORD = "acacacac-acac-acac-acac-acacacacacad"
AUDIT_EVENT = "aeaeaeae-aeae-aeae-aeae-aeaeaeaeaeae"


def test_public_cannot_execute_ten_functions(
    conn: psycopg.Connection, w6_base: psycopg.Connection
) -> None:
    with conn.cursor() as cur:
        for schema, name, _owner in FUNCTIONS:
            cur.execute(
                """
                SELECT count(*)
                FROM pg_proc p
                JOIN pg_namespace n ON n.oid = p.pronamespace,
                aclexplode(coalesce(p.proacl, acldefault('f', p.proowner))) a
                WHERE n.nspname = %s
                  AND p.proname = %s
                  AND p.pronargs = 0
                  AND a.grantee = 0
                  AND a.privilege_type = 'EXECUTE'
                """,
                (schema, name),
            )
            assert cur.fetchone()[0] == 0, f"PUBLIC EXECUTE remains on {schema}.{name}"

    with conn.cursor() as cur:
        cur.execute("SET LOCAL ROLE app_erp")
    try:
        expect_error(
            conn,
            "SELECT core.set_org_unit_path()",
            contains="permission denied",
        )
        expect_error(
            conn,
            "SELECT ops.reject_mutation()",
            contains="permission denied",
        )
    finally:
        with conn.cursor() as cur:
            cur.execute("RESET ROLE")


def test_functions_remain_invoker_and_owner_held(
    conn: psycopg.Connection, w6_base: psycopg.Connection
) -> None:
    with conn.cursor() as cur:
        for schema, name, owner in FUNCTIONS:
            cur.execute(
                """
                SELECT p.prosecdef, pg_get_userbyid(p.proowner)
                FROM pg_proc p
                JOIN pg_namespace n ON n.oid = p.pronamespace
                WHERE n.nspname = %s
                  AND p.proname = %s
                  AND p.pronargs = 0
                """,
                (schema, name),
            )
            row = cur.fetchone()
            assert row is not None, f"{schema}.{name} is missing"
            assert row == (False, owner), f"{schema}.{name}: {row}"


def test_person_dob_trigger_fires(
    conn: psycopg.Connection, w6_base: psycopg.Connection
) -> None:
    expect_error(
        conn,
        "UPDATE iam.person SET date_of_birth = CURRENT_DATE WHERE person_id = %s",
        (P1,),
        contains="before current_date",
    )


def test_role_assignment_scope_trigger_fires(
    conn: psycopg.Connection, w6_base: psycopg.Connection
) -> None:
    expect_error(
        conn,
        "UPDATE iam.role_assignment SET scope_key = %s WHERE role_assignment_id = %s",
        ("99999999-9999-9999-9999-999999999999", ASSIGNMENT),
        contains="scope_key",
    )


def test_system_role_delete_trigger_fires(
    conn: psycopg.Connection, w6_base: psycopg.Connection
) -> None:
    expect_error(
        conn,
        "DELETE FROM iam.role WHERE role_id = %s",
        (ROLE,),
        contains="system role",
    )


def test_org_unit_path_and_descendant_triggers_fire(
    conn: psycopg.Connection, w6_base: psycopg.Connection
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO core.org_unit
                (org_unit_id, institution_id, parent_org_unit_id, code, name, unit_type)
            VALUES (%s, %s, %s, 'AI', 'Artificial Intelligence', 'department')
            """,
            (NEW_ORG_UNIT, INSTITUTION, ORG_CHILD),
        )
        cur.execute(
            "SELECT path FROM core.org_unit WHERE org_unit_id = %s",
            (NEW_ORG_UNIT,),
        )
        assert cur.fetchone()[0] == "ENG/CSE/AI"

        cur.execute(
            "UPDATE core.org_unit SET code = 'CSE2' WHERE org_unit_id = %s",
            (ORG_CHILD,),
        )
        cur.execute(
            "SELECT path FROM core.org_unit WHERE org_unit_id = %s",
            (NEW_ORG_UNIT,),
        )
        assert cur.fetchone()[0] == "ENG/CSE2/AI"

    expect_error(
        conn,
        "UPDATE core.org_unit SET parent_org_unit_id = %s WHERE org_unit_id = %s",
        (NEW_ORG_UNIT, ORG_ROOT),
        contains="cycle detected",
    )


def test_rule_version_current_trigger_fires(
    conn: psycopg.Connection, w6_base: psycopg.Connection
) -> None:
    expect_error(
        conn,
        "UPDATE policy.rule_version SET status = 'Current', approval_reference = NULL "
        "WHERE rule_version_id = %s",
        (RULE_VERSION_DRAFT,),
        contains="requires approval_reference",
    )


def test_rule_version_seal_trigger_fires(
    conn: psycopg.Connection, w6_base: psycopg.Connection
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


def test_document_version_seal_trigger_fires(
    conn: psycopg.Connection, w6_base: psycopg.Connection
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE doc.document_version SET status = 'active' "
            "WHERE document_version_id = %s",
            (VERSION_PUBLIC,),
        )
    expect_error(
        conn,
        "UPDATE doc.document_version SET change_note = 'late edit' "
        "WHERE document_version_id = %s",
        (VERSION_PUBLIC,),
        contains="sealed",
    )


def test_sync_run_seal_trigger_fires(
    conn: psycopg.Connection, w6_base: psycopg.Connection
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE integration.sync_run SET status = 'completed', finished_at = now() "
            "WHERE sync_run_id = %s",
            (SYNC_RUN,),
        )
    expect_error(
        conn,
        "UPDATE integration.sync_run SET status = 'failed' WHERE sync_run_id = %s",
        (SYNC_RUN,),
        contains="sealed",
    )


def test_append_only_triggers_fire(
    conn: psycopg.Connection, w6_base: psycopg.Connection
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO integration.sync_record
                (sync_record_id, sync_run_id, entity_type_code, internal_id,
                 operation, outcome)
            VALUES (%s, %s, %s, %s, 'insert', 'success')
            """,
            (SYNC_RECORD, SYNC_RUN, ENTITY_TYPE, P1),
        )
        cur.execute(
            """
            INSERT INTO ops.audit_event (audit_event_id, action, record_hash)
            VALUES (%s, 'test.trigger', %s)
            """,
            (AUDIT_EVENT, "a" * 64),
        )

    cases = (
        (
            "UPDATE policy.policy_bundle_version SET status = 'active' "
            "WHERE policy_bundle_version_id = %s",
            (BUNDLE_VERSION,),
        ),
        (
            "DELETE FROM policy.policy_bundle_version "
            "WHERE policy_bundle_version_id = %s",
            (BUNDLE_VERSION,),
        ),
        (
            "UPDATE integration.sync_record SET outcome = 'failed' "
            "WHERE sync_record_id = %s",
            (SYNC_RECORD,),
        ),
        (
            "DELETE FROM integration.sync_record WHERE sync_record_id = %s",
            (SYNC_RECORD,),
        ),
        (
            "UPDATE ops.audit_event SET action = 'changed' WHERE audit_event_id = %s",
            (AUDIT_EVENT,),
        ),
        (
            "DELETE FROM ops.audit_event WHERE audit_event_id = %s",
            (AUDIT_EVENT,),
        ),
        (
            "UPDATE knowledge.document_chunk SET chunk_text = 'edited' "
            "WHERE chunk_id = %s",
            (CHUNK_PUBLIC,),
        ),
        (
            "DELETE FROM knowledge.document_chunk WHERE chunk_id = %s",
            (CHUNK_PUBLIC,),
        ),
        (
            "UPDATE cip.message SET language = 'en' WHERE message_id = %s",
            (MESSAGE_P3_USER,),
        ),
        (
            "DELETE FROM cip.message WHERE message_id = %s",
            (MESSAGE_P3_USER,),
        ),
        (
            "UPDATE cip.retrieval_log SET result_count = 0 "
            "WHERE retrieval_log_id = %s",
            (RETRIEVAL_LOG,),
        ),
        (
            "DELETE FROM cip.retrieval_log WHERE retrieval_log_id = %s",
            (RETRIEVAL_LOG,),
        ),
        (
            "UPDATE cip.retrieval_hit SET rank = 2 WHERE retrieval_hit_id = %s",
            (RETRIEVAL_HIT,),
        ),
        (
            "DELETE FROM cip.retrieval_hit WHERE retrieval_hit_id = %s",
            (RETRIEVAL_HIT,),
        ),
        (
            "UPDATE cip.citation SET displayed = false WHERE citation_id = %s",
            (CITATION,),
        ),
        (
            "DELETE FROM cip.citation WHERE citation_id = %s",
            (CITATION,),
        ),
    )

    for statement, params in cases:
        expect_error(conn, statement, params, contains="append-only")


def test_trigger_count_unchanged(
    conn: psycopg.Connection, w6_base: psycopg.Connection
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT count(*)
            FROM pg_trigger t
            JOIN pg_class c ON c.oid = t.tgrelid
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE NOT t.tgisinternal
              AND n.nspname = ANY(%s)
            """,
            (list(DESIGN_SCHEMAS),),
        )
        assert cur.fetchone()[0] == 34

        cur.execute(
            """
            SELECT count(*)
            FROM pg_trigger t
            JOIN pg_proc p ON p.oid = t.tgfoid
            WHERE NOT t.tgisinternal
              AND p.proname = ANY(%s)
            """,
            (list(FUNCTION_NAMES),),
        )
        assert cur.fetchone()[0] == 17
