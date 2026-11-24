"""Design-derived constants and parsers for the database tests.

Everything in this module comes from the approved design documents under
``docs/architecture/database-design-v1``. Tests must not duplicate the
dictionary by hand: they parse it, so a design change is either reflected in
the implementation or fails the suite.

The per-wave maps list the entities the approved plan assigns to each wave.
``DEFERRED_ENTITIES`` records Initial Release entities that cannot be created
under an open design decision; they remain accounted for separately so the
108-entity total is never silently reduced.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DESIGN_DIR = REPO_ROOT / "docs" / "architecture" / "database-design-v1"
DICTIONARY = DESIGN_DIR / "DATA_DICTIONARY.md"

W1A_ENTITIES = {
    "IAM-01": "iam.person",
    "IAM-02": "iam.person_contact",
    "IAM-03": "iam.identity_account",
    "IAM-04": "iam.role",
    "IAM-05": "iam.permission",
    "IAM-06": "iam.role_permission",
    "IAM-07": "iam.role_assignment",
    "IAM-08": "iam.delegation",
    "GOV-01": "core.institution",
    "GOV-02": "core.society",
    "GOV-03": "core.org_unit",
    "GOV-04": "core.governance_body",
    "GOV-05": "core.governance_membership",
    "GOV-06": "core.statutory_approval",
    "GOV-07": "core.affiliation_record",
    "GOV-08": "core.academic_year",
    "GOV-09": "core.term",
    "GOV-10": "core.academic_calendar",
    "GOV-11": "core.calendar_milestone",
    "POL-01": "policy.rule",
    "POL-02": "policy.rule_version",
    "POL-03": "policy.rule_scope",
    "POL-04": "policy.rule_conflict",
    "POL-05": "policy.policy_bundle",
    "POL-06": "policy.policy_bundle_version",
    "POL-07": "policy.policy_bundle_member",
    "OPS-01": "ops.audit_event",
    "OPS-02": "ops.data_quality_issue",
    "OPS-03": "ops.break_glass_grant",
    "OPS-04": "ops.retention_schedule",
    "INT-01": "integration.entity_type",
    "INT-02": "integration.external_system",
    "INT-03": "integration.external_id_mapping",
    "INT-04": "integration.source_of_truth_rule",
    "INT-05": "integration.sync_run",
    "INT-06": "integration.sync_record",
    "INT-07": "integration.sync_conflict",
    "INT-08": "integration.record_provenance",
    "INT-09": "integration.outbox_event",
    "DOC-01": "doc.document",
    "DOC-02": "doc.document_version",
    "DOC-03": "doc.document_relation",
}

W1A_TABLES = set(W1A_ENTITIES.values())
W1A_SCHEMAS = {"iam", "core", "doc", "policy", "integration", "ops"}

# W1b: MVP_DEPENDENCY_MAP.md wave membership (ACD-13 is not Initial Release).
W1B_ENTITIES = {
    "ACD-01": "academic.department",
    "ACD-02": "academic.programme",
    "ACD-03": "academic.programme_version",
    "ACD-04": "academic.batch",
    "ACD-05": "academic.section",
    "ACD-06": "academic.curriculum",
    "ACD-07": "academic.curriculum_course",
    "ACD-08": "academic.course",
    "ACD-09": "academic.course_version",
    "ACD-10": "academic.course_offering",
    "ACD-11": "academic.offering_faculty",
    "ACD-12": "academic.timetable_slot",
    "ACD-14": "academic.section_teacher_assignment",
}

W1B_TABLES = set(W1B_ENTITIES.values())
W1B_SCHEMAS = {"academic"}

# W2: MVP_DEPENDENCY_MAP.md wave membership (STU-13 and STU-14 are future).
W2_ENTITIES = {
    "STU-01": "student.admission_application",
    "STU-02": "student.admission_offer",
    "STU-03": "student.student",
    "STU-04": "student.guardian",
    "STU-05": "student.student_guardian",
    "STU-06": "student.student_document",
    "STU-07": "student.university_registration",
    "STU-08": "student.exam_roll_number",
    "STU-09": "student.semester_registration",
    "STU-10": "student.course_registration",
    "STU-11": "student.status_history",
    "STU-12": "student.eligibility_determination",
    "STU-15": "student.section_assignment",
}

W2_TABLES = set(W2_ENTITIES.values())
W2_SCHEMAS = {"student"}

# W3: MVP_DEPENDENCY_MAP.md wave membership.
W3_ENTITIES = {
    "FAC-01": "faculty.faculty_profile",
    "FAC-02": "faculty.staff_profile",
    "FAC-03": "faculty.mentor_assignment",
}

W3_TABLES = set(W3_ENTITIES.values())
W3_SCHEMAS = {"faculty"}

# W4: MVP_DEPENDENCY_MAP.md wave membership.
W4_ENTITIES = {
    "ATT-01": "attendance.session",
    "ATT-02": "attendance.record",
    "ATT-03": "attendance.correction",
    "ATT-04": "attendance.summary",
    "ATT-05": "attendance.eligibility_assessment",
    "ATT-06": "attendance.condonation_case",
    "ASM-01": "assessment.scheme",
    "ASM-02": "assessment.component",
    "ASM-03": "assessment.schedule",
    "ASM-04": "assessment.mark_entry",
    "ASM-05": "assessment.mark_entry_version",
    "ASM-06": "assessment.mark_correction",
    "ASM-07": "assessment.conflict_declaration",
}

W4_TABLES = set(W4_ENTITIES.values())
W4_SCHEMAS = {"attendance", "assessment"}

# W5: MVP_DEPENDENCY_MAP.md wave membership (IE6 results + IE7 notices).
W5_ENTITIES = {
    "EXM-01": "exam.result_import",
    "EXM-02": "exam.result_set",
    "EXM-03": "exam.result_record",
    "EXM-04": "exam.result_revision",
    "EXM-05": "exam.result_input",
    "EXM-06": "exam.grade_card",
    "EXM-07": "exam.grade_card_result",
    "DOC-04": "doc.notice",
    "DOC-05": "doc.notice_version",
    "DOC-06": "doc.notice_audience",
}

W5_TABLES = set(W5_ENTITIES.values())
W5_SCHEMAS = {"exam", "doc"}

# W6: MVP_DEPENDENCY_MAP.md wave membership (IE8 knowledge/CIP).
# KNW-02 knowledge.embedding is deliberately not implemented: OD-06 forbids
# creating the vector column before the embedding model and dimension are
# decided, and the deployed PostgreSQL image has no vector extension.
W6_ENTITIES = {
    "KNW-01": "knowledge.document_chunk",
    "KNW-02": "knowledge.embedding",
    "KNW-03": "knowledge.ingestion_run",
    "CIP-01": "cip.conversation",
    "CIP-02": "cip.call_session",
    "CIP-03": "cip.message",
    "CIP-04": "cip.retrieval_log",
    "CIP-05": "cip.retrieval_hit",
    "CIP-06": "cip.citation",
    "CIP-07": "cip.feedback",
    "CIP-08": "cip.escalation",
    "CIP-09": "cip.eval_case",
    "CIP-10": "cip.eval_run",
    "CIP-11": "cip.eval_result",
}

DEFERRED_ENTITIES = {
    "KNW-02": "knowledge.embedding",
}

W6_IMPLEMENTED_ENTITIES = {
    entity_id: table
    for entity_id, table in W6_ENTITIES.items()
    if entity_id not in DEFERRED_ENTITIES
}
W6_TABLES = set(W6_IMPLEMENTED_ENTITIES.values())
W6_SCHEMAS = {"knowledge", "cip"}

# W7 / Phase 9B: scoped machine credentials (AUTH-BOOT-lite).
#
# These three tables are not part of the 108-entity Initial Release catalogue.
# They were added by migration 0019 as the approved API-key mechanism and are
# listed here so the inventory tests can account for them explicitly rather
# than widening a wildcard.
W7_ENTITIES = {
    "AUTH-API-01": "iam.api_client",
    "AUTH-API-02": "iam.api_key",
    "AUTH-API-03": "iam.api_key_scope",
}
W7_TABLES = set(W7_ENTITIES.values())
W7_SCHEMAS = {"iam"}
W7_RLS_TABLES = set(W7_TABLES)

# Everything implemented so far. Each wave adds its entities here; the final
# state is the 108-entity Initial Release less the deferred KNW-02.
IMPLEMENTED_ENTITIES = {
    **W1A_ENTITIES,
    **W1B_ENTITIES,
    **W2_ENTITIES,
    **W3_ENTITIES,
    **W4_ENTITIES,
    **W5_ENTITIES,
    **W6_IMPLEMENTED_ENTITIES,
    **W7_ENTITIES,
}
IMPLEMENTED_TABLES = set(IMPLEMENTED_ENTITIES.values())
IMPLEMENTED_SCHEMAS = (
    W1A_SCHEMAS | W1B_SCHEMAS | W2_SCHEMAS | W3_SCHEMAS | W4_SCHEMAS | W5_SCHEMAS
    | W6_SCHEMAS | W7_SCHEMAS
)

# W1A_PREFLIGHT_REPORT.md section 2 and POSTGRES_ARCHITECTURE.md section 17.3.
STAGED_FOREIGN_KEYS = (
    ("fk_role_assignment_programme", "iam.role_assignment", "programme_id"),
    ("fk_role_assignment_batch", "iam.role_assignment", "batch_id"),
    ("fk_role_assignment_course_offering", "iam.role_assignment", "course_offering_id"),
    ("fk_statutory_approval_programme", "core.statutory_approval", "programme_id"),
    ("fk_affiliation_record_programme", "core.affiliation_record", "programme_id"),
    ("fk_rule_scope_programme", "policy.rule_scope", "programme_id"),
    ("fk_rule_scope_batch", "policy.rule_scope", "batch_id"),
)

# DATA_DICTIONARY.md section 1.6: RLS tables in W1a.
RLS_TABLES = {
    "iam.person",
    "iam.person_contact",
    "iam.identity_account",
    "iam.role_assignment",
    "doc.document",
    "doc.document_version",
    "doc.document_relation",
}

# W1b adds RLS only on the table with a documented policy intent (9.3).
W1B_RLS_TABLES = {"academic.section_teacher_assignment"}
# DATA_DICTIONARY.md 1.6: RLS on every table in the student schema.
W2_RLS_TABLES = set(W2_TABLES)
IMPLEMENTED_RLS_TABLES = RLS_TABLES | W1B_RLS_TABLES | W2_RLS_TABLES | W7_RLS_TABLES

# Documented "Unique / checks" entries that materialise as unique indexes.
# (table, key expressions, predicate fragments that must all appear)
UNIQUE_INDEXES = (
    ("iam.person_contact", ("person_id", "contact_type"), ("is_primary", "valid_to is null")),
    ("iam.identity_account", ("idp_code", "subject"), ()),
    ("iam.identity_account", ("lower(username)",), ("username is not null",)),
    ("iam.identity_account", ("person_id", "idp_code"), ("status = 'active'",)),
    ("iam.role", ("lower(role_code)",), ()),
    ("iam.permission", ("lower(permission_code)",), ()),
    ("iam.role_permission", ("role_id", "permission_id"), ()),
    (
        "iam.role_assignment",
        ("person_id", "role_id", "scope_type", "scope_key"),
        ("status = 'active'",),
    ),
    ("core.institution", ("lower(college_code)",), ()),
    ("core.society", ("registration_no",), ("registration_no is not null",)),
    ("core.org_unit", ("institution_id", "code"), ()),
    ("core.governance_body", ("institution_id", "body_code", "term_start"), ()),
    (
        "core.governance_membership",
        ("governance_body_id", "person_id", "valid_from"),
        (),
    ),
    (
        "core.statutory_approval",
        ("approval_type", "authority", "reference_no"),
        (),
    ),
    ("core.affiliation_record", ("programme_id", "academic_year_id"), ()),
    ("core.academic_year", ("institution_id", "label"), ()),
    ("core.term", ("academic_year_id", "term_type", "term_no"), ()),
    ("core.academic_calendar", ("term_id", "version_no"), ()),
    ("core.academic_calendar", ("term_id",), ("status = 'approved'",)),
    ("core.calendar_milestone", ("academic_calendar_id", "milestone_code"), ()),
    (
        "doc.document",
        ("issuer_org_unit_id", "reference_no"),
        ("reference_no is not null",),
    ),
    ("doc.document_version", ("document_id", "version_no"), ()),
    ("doc.document_version", ("sha256",), ()),
    (
        "doc.document_relation",
        ("from_version_id", "to_version_id", "relation_type"),
        (),
    ),
    ("policy.rule", ("lower(rule_code)",), ()),
    ("policy.rule_version", ("rule_id", "version_no"), ()),
    (
        "policy.rule_scope",
        (
            "rule_version_id",
            "scope_type",
            "institution_id",
            "programme_id",
            "batch_id",
            "term_id",
            "course_type",
            "student_category",
        ),
        (),
    ),
    ("policy.rule_conflict", ("rule_version_a_id", "rule_version_b_id"), ()),
    ("policy.policy_bundle", ("lower(bundle_code)",), ()),
    ("policy.policy_bundle_version", ("policy_bundle_id", "version_no"), ()),
    (
        "policy.policy_bundle_member",
        ("policy_bundle_version_id", "rule_version_id"),
        (),
    ),
    ("integration.entity_type", ("schema_name", "table_name"), ()),
    ("integration.external_system", ("lower(code)",), ()),
    (
        "integration.external_id_mapping",
        ("entity_type_code", "internal_id", "external_system_id", "valid_from"),
        (),
    ),
    (
        "integration.external_id_mapping",
        ("entity_type_code", "external_id", "external_system_id"),
        ("valid_to is null",),
    ),
    (
        "integration.source_of_truth_rule",
        ("entity_type_code", "field_name", "effective_from"),
        (),
    ),
    (
        "integration.sync_record",
        ("sync_run_id", "entity_type_code", "internal_id", "operation", "external_id"),
        (),
    ),
    (
        "integration.record_provenance",
        ("entity_type_code", "internal_id", "field_name"),
        (),
    ),
    ("ops.retention_schedule", ("entity_type_code", "classification"), ()),
)

# Documented W1b unique keys. Expressions are lowercased by the test.
W1B_UNIQUE_INDEXES = (
    ("academic.department", ("org_unit_id",), ()),
    ("academic.department", ("lower(code)",), ()),
    ("academic.programme", ("institution_id", "bcrec_code"), ()),
    ("academic.programme", ("institution_id", "lower(programme_code)"), ()),
    ("academic.programme_version", ("programme_id", "version_no"), ()),
    ("academic.batch", ("programme_id", "admission_year", "entry_mode"), ()),
    ("academic.section", ("batch_id", "section_code"), ()),
    ("academic.section", ("section_id", "batch_id"), ()),
    (
        "academic.curriculum",
        ("programme_version_id", "term_no", "version_no"),
        (),
    ),
    ("academic.curriculum_course", ("curriculum_id", "course_version_id"), ()),
    ("academic.curriculum_course", ("curriculum_id", "term_no", "sequence_no"), ()),
    ("academic.course", ("lower(course_code)",), ()),
    ("academic.course_version", ("course_id", "version_no"), ()),
    (
        "academic.course_offering",
        ("course_version_id", "term_id", "section_id"),
        (),
    ),
    ("academic.course_offering", ("lower(offering_code)",), ()),
    (
        "academic.offering_faculty",
        ("course_offering_id", "person_id", "role_in_offering", "valid_from"),
        (),
    ),
    (
        "academic.offering_faculty",
        ("course_offering_id",),
        ("role_in_offering = 'coordinator'", "valid_to is null"),
    ),
    (
        "academic.timetable_slot",
        ("course_offering_id", "day_of_week", "start_time", "valid_from"),
        (),
    ),
    (
        "academic.section_teacher_assignment",
        ("section_id", "person_id", "role_in_section", "valid_from"),
        (),
    ),
    (
        "academic.section_teacher_assignment",
        ("section_id",),
        (
            "role_in_section = 'class_teacher'",
            "status = 'active'",
            "valid_to is null",
        ),
    ),
)

W1B_TRIGGERS = {
    ("academic", "course_version", "trg_course_version_freeze"),
    ("academic", "course_offering", "trg_course_offering_section_batch"),
}

# Documented W2 unique keys. Expressions are lowercased by the test.
W2_UNIQUE_INDEXES = (
    ("student.admission_application", ("admission_year", "application_no"), ()),
    ("student.admission_offer", ("application_id",), ()),
    ("student.admission_offer", ("offer_no",), ()),
    ("student.student", ("college_roll_no",), ()),
    ("student.student", ("person_id", "batch_id"), ()),
    ("student.student", ("student_id", "batch_id"), ()),
    ("student.guardian", ("person_id",), ()),
    ("student.student_guardian", ("student_id", "guardian_id"), ()),
    (
        "student.student_guardian",
        ("student_id",),
        ("is_primary", "valid_to is null"),
    ),
    (
        "student.student_document",
        ("student_id", "document_type", "document_version_id"),
        (),
    ),
    ("student.university_registration", ("student_id",), ()),
    (
        "student.university_registration",
        ("lower(registration_number)",),
        ("registration_number is not null",),
    ),
    ("student.exam_roll_number", ("roll_number",), ()),
    ("student.exam_roll_number", ("student_id",), ("is_current",)),
    ("student.semester_registration", ("student_id", "term_id"), ()),
    (
        "student.semester_registration",
        ("semester_registration_id", "student_id"),
        (),
    ),
    (
        "student.semester_registration",
        ("registration_no",),
        ("registration_no is not null",),
    ),
    (
        "student.course_registration",
        ("semester_registration_id", "course_offering_id"),
        (),
    ),
    (
        "student.course_registration",
        ("course_registration_id", "student_id", "course_offering_id"),
        (),
    ),
    ("student.section_assignment", ("student_id", "effective_from"), ()),
    (
        "student.section_assignment",
        ("student_id",),
        ("effective_to is null", "status = 'active'"),
    ),
)

W2_TRIGGERS = {
    ("student", "exam_roll_number", "trg_exam_roll_number_format"),
    ("student", "eligibility_determination", "trg_eligibility_determination_seal"),
}

# Documented W3 unique keys. Expressions are lowercased by the test.
W3_UNIQUE_INDEXES = (
    ("faculty.faculty_profile", ("person_id",), ()),
    ("faculty.faculty_profile", ("lower(employee_id)",), ()),
    ("faculty.staff_profile", ("person_id",), ()),
    ("faculty.staff_profile", ("lower(employee_id)",), ()),
    (
        "faculty.mentor_assignment",
        ("student_id", "term_id"),
        ("status = 'active'",),
    ),
)

W3_TRIGGERS = {
    ("faculty", "mentor_assignment", "trg_mentor_assignment_active_profile"),
}

W4_TRIGGERS = {
    ("assessment", "component", "trg_component_immutable"),
    ("assessment", "component", "trg_component_weight_sum"),
    ("assessment", "mark_entry_version", "trg_mark_version_immutable"),
    ("assessment", "mark_correction", "trg_mark_correction_versions"),
    ("assessment", "mark_entry_version", "trg_mark_conflict"),
    ("attendance", "record", "trg_attendance_conflict"),
}

W5_TRIGGERS = {
    ("exam", "result_revision", "trg_result_revision_seal"),
    ("exam", "result_input", "trg_result_input_append_only"),
    ("exam", "grade_card_result", "trg_grade_card_result_append_only"),
    ("exam", "grade_card_result", "trg_grade_card_result_revision"),
}

W6_TRIGGERS = {
    ("knowledge", "document_chunk", "trg_document_chunk_source_classification"),
    ("knowledge", "document_chunk", "trg_document_chunk_append_only"),
    ("cip", "message", "trg_message_append_only"),
    ("cip", "retrieval_log", "trg_retrieval_log_append_only"),
    ("cip", "retrieval_hit", "trg_retrieval_hit_append_only"),
    ("cip", "citation", "trg_citation_append_only"),
}

TYPE_MAP = {
    "timestamptz": "timestamp with time zone",
    "uuid": "uuid",
    "text": "text",
    "date": "date",
    "boolean": "boolean",
    "integer": "integer",
    "smallint": "smallint",
    "bigint": "bigint",
    "jsonb": "jsonb",
    "inet": "inet",
    "numeric": "numeric",
    "numeric(4,1)": "numeric",
    "numeric(4,2)": "numeric",
    "numeric(4,3)": "numeric",
    "numeric(5,1)": "numeric",
    "numeric(5,2)": "numeric",
    "numeric(6,2)": "numeric",
    "numeric(8,6)": "numeric",
    "time": "time without time zone",
}

AUDIT_COLUMNS = {
    "MUTABLE": (
        ("created_at", "timestamptz", "NO", "now()"),
        ("created_by", "uuid", "YES", "NULL"),
        ("updated_at", "timestamptz", "NO", "now()"),
        ("updated_by", "uuid", "YES", "NULL"),
        ("row_version", "integer", "NO", "1"),
    ),
    "IMMUTABLE": (
        ("created_at", "timestamptz", "NO", "now()"),
        ("created_by", "uuid", "YES", "NULL"),
    ),
}

_ENTITY_HEADING = re.compile(
    r"^### ([A-Z]{3}-\d{2}) `([a-z_]+\.[a-z_]+)`\s*$", re.MULTILINE
)
_COLUMN_HEADER = "| Column | Type | Null | Key / check | Default | Sens | Meaning |"


def normalise_default(value: str | None) -> str | None:
    """Map a dictionary default or a PostgreSQL ``column_default`` to one form."""
    if value is None:
        return None
    value = value.strip()
    if value in ("", "—", "-", "NULL"):
        return None
    value = re.sub(r"::[A-Za-z0-9_ \"\[\].]+$", "", value)
    if len(value) >= 2 and value[0] == value[-1] == "'":
        value = value[1:-1]
    return value.lower()


def _sections() -> dict[str, dict[str, object]]:
    text = DICTIONARY.read_text(encoding="utf-8")
    matches = list(_ENTITY_HEADING.finditer(text))
    sections: dict[str, dict[str, object]] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        section = text[match.start() : end]
        table = match.group(2)
        columns = []
        seen = set()
        start = section.find(_COLUMN_HEADER)
        assert start != -1, f"{table}: column table header not found"
        body = section[start + len(_COLUMN_HEADER) :].lstrip("\n")
        for raw_line in body.splitlines():
            line = raw_line.strip()
            if not line.startswith("|"):
                if columns:
                    break
                continue
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if len(cells) != 7 or cells[0] in ("Column", "---") or set(cells[0]) <= {"-"}:
                continue
            name, type_name, nullable, key_check, default, _sensitivity, _meaning = cells
            if name in seen:
                continue
            seen.add(name)
            columns.append(
                {
                    "name": name,
                    "type": type_name,
                    "null": nullable,
                    "key_check": key_check,
                    "default": default,
                }
            )

        audit_match = re.search(r"\+ `AUDIT_(MUTABLE|IMMUTABLE)`\.", section)
        assert audit_match, f"{table}: AUDIT block not found"
        for column in AUDIT_COLUMNS[audit_match.group(1)]:
            if column[0] in seen:
                continue
            seen.add(column[0])
            columns.append(
                {
                    "name": column[0],
                    "type": column[1],
                    "null": column[2],
                    "key_check": "",
                    "default": column[3],
                }
            )

        pk_match = re.search(r"\*\*PK:\*\* `([a-z_]+)`", section)
        assert pk_match, f"{table}: PK not found"
        sections[table] = {
            "id": match.group(1),
            "columns": columns,
            "pk": pk_match.group(1),
        }
    return sections


DICTIONARY_SECTIONS = _sections()


def expected_columns(table: str) -> list[dict[str, str]]:
    assert table in DICTIONARY_SECTIONS, f"{table} is not in DATA_DICTIONARY.md"
    return list(DICTIONARY_SECTIONS[table]["columns"])


def expected_primary_key(table: str) -> str:
    return str(DICTIONARY_SECTIONS[table]["pk"])


def documented_enum_checks(table: str) -> list[tuple[str, list[str]]]:
    """Extract ``column IN (value, ...)`` rules from a dictionary section."""
    result = []
    for column in expected_columns(table):
        match = re.search(r"\bIN \(([^)]+)\)", column["key_check"], re.IGNORECASE)
        if not match:
            continue
        values = [value.strip() for value in match.group(1).split(",") if value.strip()]
        if values:
            result.append((column["name"], values))
    return result
