-- 0002_w1a_schema.sql
-- Phase 2 / Wave W1a: 42 foundation entities.
--
-- Source of truth:
--   docs/architecture/database-design-v1/DATA_DICTIONARY.md
--   docs/architecture/database-design-v1/ENTITY_CATALOG.md
--   docs/architecture/database-design-v1/MVP_DEPENDENCY_MAP.md
--   docs/architecture/database-design-v1/POSTGRES_ARCHITECTURE.md
--   docs/implementation/database/W1A_PREFLIGHT_REPORT.md
--
-- Scope: IAM-01..08, GOV-01..11, POL-01..07, OPS-01..04, INT-01..09, DOC-01..03.
--
-- TODO(OD-12): the seven W1a -> W1b foreign keys are deliberately absent.
-- The seven columns exist and are indexed; their constraints are added in W1b
-- with ADD CONSTRAINT ... NOT VALID followed by VALIDATE CONSTRAINT, as
-- specified in W1A_PREFLIGHT_REPORT.md section 2 and POSTGRES_ARCHITECTURE 17.3.
--
-- Ownership: this development runner connects as a bootstrap superuser and
-- transfers every object to the documented owner_<schema> role at the end of
-- each section. In production the migration_owner role performs the same DDL
-- through SET ROLE owner_<schema>.
--
-- Conventions: snake_case, singular table names, uuid primary keys (except the
-- text-keyed integration.entity_type registry), timestamptz in UTC, text
-- lengths enforced with CHECK (char_length(...)), and ON DELETE RESTRICT for
-- every reference. No CASCADE is used on academic, document, or audit data.

-- ===========================================================================
-- 1. Identity (iam) -- IAM-01 .. IAM-08
-- ===========================================================================

CREATE TABLE iam.person (
    person_id            uuid        NOT NULL DEFAULT gen_random_uuid(),
    legal_name           text        NOT NULL,
    preferred_name       text        NULL,
    date_of_birth        date        NULL,
    gender               text        NULL,
    blood_group          text        NULL,
    photo_uri            text        NULL,
    deceased_flag        boolean     NOT NULL DEFAULT false,
    notes                text        NULL,
    created_at           timestamptz NOT NULL DEFAULT now(),
    created_by           uuid        NULL,
    updated_at           timestamptz NOT NULL DEFAULT now(),
    updated_by           uuid        NULL,
    row_version          integer     NOT NULL DEFAULT 1,
    CONSTRAINT pk_person PRIMARY KEY (person_id),
    CONSTRAINT ck_person_legal_name_length CHECK (char_length(legal_name) BETWEEN 1 AND 200),
    CONSTRAINT ck_person_preferred_name_length CHECK (preferred_name IS NULL OR char_length(preferred_name) <= 100),
    CONSTRAINT ck_person_gender CHECK (gender IS NULL OR gender IN ('female', 'male', 'other', 'prefer_not_to_say', 'unknown')),
    CONSTRAINT ck_person_blood_group CHECK (blood_group IS NULL OR blood_group IN ('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-', 'unknown')),
    CONSTRAINT ck_person_notes_length CHECK (notes IS NULL OR char_length(notes) <= 2000)
);
ALTER TABLE iam.person OWNER TO owner_iam;

CREATE INDEX ix_person_legal_name_trgm
    ON iam.person USING gin (lower(legal_name) gin_trgm_ops);
CREATE INDEX ix_person_date_of_birth ON iam.person (date_of_birth);

CREATE TABLE iam.identity_account (
    account_id           uuid        NOT NULL DEFAULT gen_random_uuid(),
    person_id            uuid        NOT NULL,
    idp_code             text        NOT NULL,
    subject              text        NOT NULL,
    username             text        NULL,
    email                text        NULL,
    account_type         text        NOT NULL DEFAULT 'interactive',
    mfa_enabled          boolean     NOT NULL DEFAULT false,
    status               text        NOT NULL DEFAULT 'pending',
    last_login_at        timestamptz NULL,
    disabled_at          timestamptz NULL,
    disabled_reason      text        NULL,
    created_at           timestamptz NOT NULL DEFAULT now(),
    created_by           uuid        NULL,
    updated_at           timestamptz NOT NULL DEFAULT now(),
    updated_by           uuid        NULL,
    row_version          integer     NOT NULL DEFAULT 1,
    CONSTRAINT pk_identity_account PRIMARY KEY (account_id),
    CONSTRAINT fk_identity_account_person FOREIGN KEY (person_id)
        REFERENCES iam.person (person_id) ON DELETE RESTRICT,
    CONSTRAINT fk_identity_account_created_by FOREIGN KEY (created_by)
        REFERENCES iam.identity_account (account_id) ON DELETE RESTRICT,
    CONSTRAINT fk_identity_account_updated_by FOREIGN KEY (updated_by)
        REFERENCES iam.identity_account (account_id) ON DELETE RESTRICT,
    CONSTRAINT uq_identity_account_idp_subject UNIQUE (idp_code, subject),
    CONSTRAINT ck_identity_account_idp_length CHECK (char_length(idp_code) <= 50),
    CONSTRAINT ck_identity_account_subject_length CHECK (char_length(subject) <= 255),
    CONSTRAINT ck_identity_account_username_length CHECK (username IS NULL OR char_length(username) <= 255),
    CONSTRAINT ck_identity_account_account_type CHECK (account_type IN ('interactive', 'service', 'guardian', 'alumni')),
    CONSTRAINT ck_identity_account_status CHECK (status IN ('active', 'disabled', 'locked', 'pending')),
    CONSTRAINT ck_identity_account_disabled_reason_length CHECK (disabled_reason IS NULL OR char_length(disabled_reason) <= 500)
);
ALTER TABLE iam.identity_account OWNER TO owner_iam;

CREATE UNIQUE INDEX uq_identity_account_username_lower
    ON iam.identity_account (lower(username)) WHERE username IS NOT NULL;
CREATE UNIQUE INDEX uq_identity_account_person_active
    ON iam.identity_account (person_id, idp_code) WHERE status = 'active';
CREATE INDEX ix_identity_account_person ON iam.identity_account (person_id);
CREATE INDEX ix_identity_account_status ON iam.identity_account (status);
CREATE INDEX ix_identity_account_created_by ON iam.identity_account (created_by);
CREATE INDEX ix_identity_account_updated_by ON iam.identity_account (updated_by);

-- The person <-> identity_account audit cycle is closed once both tables exist.
ALTER TABLE iam.person
    ADD CONSTRAINT fk_person_created_by FOREIGN KEY (created_by)
        REFERENCES iam.identity_account (account_id) ON DELETE RESTRICT,
    ADD CONSTRAINT fk_person_updated_by FOREIGN KEY (updated_by)
        REFERENCES iam.identity_account (account_id) ON DELETE RESTRICT;
CREATE INDEX ix_person_created_by ON iam.person (created_by);
CREATE INDEX ix_person_updated_by ON iam.person (updated_by);

CREATE TABLE iam.person_contact (
    person_contact_id    uuid        NOT NULL DEFAULT gen_random_uuid(),
    person_id            uuid        NOT NULL,
    contact_type         text        NOT NULL,
    label                text        NULL,
    value                text        NOT NULL,
    is_primary           boolean     NOT NULL DEFAULT false,
    is_verified          boolean     NOT NULL DEFAULT false,
    verified_at          timestamptz NULL,
    valid_from           date        NOT NULL DEFAULT current_date,
    valid_to             date        NULL,
    created_at           timestamptz NOT NULL DEFAULT now(),
    created_by           uuid        NULL,
    updated_at           timestamptz NOT NULL DEFAULT now(),
    updated_by           uuid        NULL,
    row_version          integer     NOT NULL DEFAULT 1,
    CONSTRAINT pk_person_contact PRIMARY KEY (person_contact_id),
    CONSTRAINT fk_person_contact_person FOREIGN KEY (person_id)
        REFERENCES iam.person (person_id) ON DELETE RESTRICT,
    CONSTRAINT fk_person_contact_created_by FOREIGN KEY (created_by)
        REFERENCES iam.identity_account (account_id) ON DELETE RESTRICT,
    CONSTRAINT fk_person_contact_updated_by FOREIGN KEY (updated_by)
        REFERENCES iam.identity_account (account_id) ON DELETE RESTRICT,
    CONSTRAINT ck_person_contact_type CHECK (contact_type IN ('email', 'phone', 'mobile', 'whatsapp', 'address', 'emergency', 'other')),
    CONSTRAINT ck_person_contact_label_length CHECK (label IS NULL OR char_length(label) <= 50),
    CONSTRAINT ck_person_contact_value_length CHECK (char_length(value) BETWEEN 1 AND 500),
    CONSTRAINT ck_person_contact_validity CHECK (valid_to IS NULL OR valid_to > valid_from),
    -- Conservative formats required by IAM-02. The application performs the
    -- authoritative validation; these checks only reject impossible shapes.
    CONSTRAINT ck_person_contact_email_format CHECK (
        contact_type <> 'email'
        OR value ~ '^[^@[:space:]]+@[^@[:space:]]+[.][^@[:space:]]+$'
    ),
    CONSTRAINT ck_person_contact_phone_format CHECK (
        contact_type NOT IN ('phone', 'mobile', 'whatsapp')
        OR value ~ '^[+0-9][0-9() -]{5,19}$'
    )
);
ALTER TABLE iam.person_contact OWNER TO owner_iam;

CREATE UNIQUE INDEX uq_person_contact_primary
    ON iam.person_contact (person_id, contact_type)
    WHERE is_primary AND valid_to IS NULL;
CREATE INDEX ix_person_contact_person_type ON iam.person_contact (person_id, contact_type);
CREATE INDEX ix_person_contact_value_lower ON iam.person_contact (lower(value));
CREATE INDEX ix_person_contact_created_by ON iam.person_contact (created_by);
CREATE INDEX ix_person_contact_updated_by ON iam.person_contact (updated_by);

CREATE TABLE iam.role (
    role_id              uuid        NOT NULL DEFAULT gen_random_uuid(),
    role_code            text        NOT NULL,
    name                 text        NOT NULL,
    category             text        NOT NULL,
    description          text        NULL,
    default_scope_type   text        NULL,
    is_system_role       boolean     NOT NULL DEFAULT false,
    is_active            boolean     NOT NULL DEFAULT true,
    created_at           timestamptz NOT NULL DEFAULT now(),
    created_by           uuid        NULL,
    updated_at           timestamptz NOT NULL DEFAULT now(),
    updated_by           uuid        NULL,
    row_version          integer     NOT NULL DEFAULT 1,
    CONSTRAINT pk_role PRIMARY KEY (role_id),
    CONSTRAINT fk_role_created_by FOREIGN KEY (created_by)
        REFERENCES iam.identity_account (account_id) ON DELETE RESTRICT,
    CONSTRAINT fk_role_updated_by FOREIGN KEY (updated_by)
        REFERENCES iam.identity_account (account_id) ON DELETE RESTRICT,
    CONSTRAINT ck_role_code_length CHECK (char_length(role_code) <= 50),
    CONSTRAINT ck_role_name_length CHECK (char_length(name) <= 100),
    CONSTRAINT ck_role_category CHECK (category IN ('governance', 'executive', 'academic', 'student', 'system')),
    CONSTRAINT ck_role_description_length CHECK (description IS NULL OR char_length(description) <= 1000),
    CONSTRAINT ck_role_default_scope_type CHECK (default_scope_type IS NULL OR default_scope_type IN ('institution', 'org_unit', 'programme', 'batch', 'term', 'course_offering', 'governance_body'))
);
ALTER TABLE iam.role OWNER TO owner_iam;

CREATE UNIQUE INDEX uq_role_code_lower ON iam.role (lower(role_code));
CREATE INDEX ix_role_category_active ON iam.role (category, is_active);
CREATE INDEX ix_role_created_by ON iam.role (created_by);
CREATE INDEX ix_role_updated_by ON iam.role (updated_by);

CREATE TABLE iam.permission (
    permission_id        uuid        NOT NULL DEFAULT gen_random_uuid(),
    permission_code      text        NOT NULL,
    resource             text        NOT NULL,
    action               text        NOT NULL,
    description          text        NULL,
    risk_level           text        NOT NULL DEFAULT 'medium',
    is_active            boolean     NOT NULL DEFAULT true,
    created_at           timestamptz NOT NULL DEFAULT now(),
    created_by           uuid        NULL,
    updated_at           timestamptz NOT NULL DEFAULT now(),
    updated_by           uuid        NULL,
    row_version          integer     NOT NULL DEFAULT 1,
    CONSTRAINT pk_permission PRIMARY KEY (permission_id),
    CONSTRAINT fk_permission_created_by FOREIGN KEY (created_by)
        REFERENCES iam.identity_account (account_id) ON DELETE RESTRICT,
    CONSTRAINT fk_permission_updated_by FOREIGN KEY (updated_by)
        REFERENCES iam.identity_account (account_id) ON DELETE RESTRICT,
    CONSTRAINT ck_permission_code_length CHECK (char_length(permission_code) <= 100),
    CONSTRAINT ck_permission_resource_length CHECK (char_length(resource) <= 50),
    CONSTRAINT ck_permission_action_length CHECK (char_length(action) <= 50),
    CONSTRAINT ck_permission_description_length CHECK (description IS NULL OR char_length(description) <= 500),
    CONSTRAINT ck_permission_risk_level CHECK (risk_level IN ('low', 'medium', 'high', 'critical'))
);
ALTER TABLE iam.permission OWNER TO owner_iam;

CREATE UNIQUE INDEX uq_permission_code_lower ON iam.permission (lower(permission_code));
CREATE INDEX ix_permission_resource_action ON iam.permission (resource, action);
CREATE INDEX ix_permission_created_by ON iam.permission (created_by);
CREATE INDEX ix_permission_updated_by ON iam.permission (updated_by);

CREATE TABLE iam.role_permission (
    role_permission_id   uuid        NOT NULL DEFAULT gen_random_uuid(),
    role_id              uuid        NOT NULL,
    permission_id        uuid        NOT NULL,
    granted_at           timestamptz NOT NULL DEFAULT now(),
    granted_by           uuid        NULL,
    created_at           timestamptz NOT NULL DEFAULT now(),
    created_by           uuid        NULL,
    updated_at           timestamptz NOT NULL DEFAULT now(),
    updated_by           uuid        NULL,
    row_version          integer     NOT NULL DEFAULT 1,
    CONSTRAINT pk_role_permission PRIMARY KEY (role_permission_id),
    CONSTRAINT fk_role_permission_role FOREIGN KEY (role_id)
        REFERENCES iam.role (role_id) ON DELETE RESTRICT,
    CONSTRAINT fk_role_permission_permission FOREIGN KEY (permission_id)
        REFERENCES iam.permission (permission_id) ON DELETE RESTRICT,
    CONSTRAINT fk_role_permission_granted_by FOREIGN KEY (granted_by)
        REFERENCES iam.identity_account (account_id) ON DELETE RESTRICT,
    CONSTRAINT fk_role_permission_created_by FOREIGN KEY (created_by)
        REFERENCES iam.identity_account (account_id) ON DELETE RESTRICT,
    CONSTRAINT fk_role_permission_updated_by FOREIGN KEY (updated_by)
        REFERENCES iam.identity_account (account_id) ON DELETE RESTRICT,
    CONSTRAINT uq_role_permission UNIQUE (role_id, permission_id)
);
ALTER TABLE iam.role_permission OWNER TO owner_iam;

CREATE INDEX ix_role_permission_permission ON iam.role_permission (permission_id);
CREATE INDEX ix_role_permission_granted_by ON iam.role_permission (granted_by);
CREATE INDEX ix_role_permission_created_by ON iam.role_permission (created_by);
CREATE INDEX ix_role_permission_updated_by ON iam.role_permission (updated_by);

-- ===========================================================================
-- 2. Institution, organisation, academic calendar (core) -- GOV-01, GOV-03,
--    GOV-08, GOV-09. Remaining core tables follow after doc.* exists.
-- ===========================================================================

CREATE TABLE core.institution (
    institution_id         uuid        NOT NULL DEFAULT gen_random_uuid(),
    legal_name             text        NOT NULL,
    short_name             text        NOT NULL,
    college_code           text        NOT NULL,
    aicte_id               text        NULL,
    address_line1          text        NULL,
    city                   text        NULL,
    district               text        NULL,
    state                  text        NULL,
    postal_code            text        NULL,
    country                text        NULL DEFAULT 'India',
    affiliation_university text        NULL,
    autonomy_status        text        NOT NULL DEFAULT 'affiliated',
    autonomy_from          date        NULL,
    autonomy_to            date        NULL,
    timezone               text        NOT NULL DEFAULT 'Asia/Kolkata',
    currency               text        NOT NULL DEFAULT 'INR',
    parent_institution_id  uuid        NULL,
    status                 text        NOT NULL DEFAULT 'active',
    created_at             timestamptz NOT NULL DEFAULT now(),
    created_by             uuid        NULL,
    updated_at             timestamptz NOT NULL DEFAULT now(),
    updated_by             uuid        NULL,
    row_version            integer     NOT NULL DEFAULT 1,
    CONSTRAINT pk_institution PRIMARY KEY (institution_id),
    CONSTRAINT fk_institution_parent FOREIGN KEY (parent_institution_id)
        REFERENCES core.institution (institution_id) ON DELETE RESTRICT,
    CONSTRAINT fk_institution_created_by FOREIGN KEY (created_by)
        REFERENCES iam.identity_account (account_id) ON DELETE RESTRICT,
    CONSTRAINT fk_institution_updated_by FOREIGN KEY (updated_by)
        REFERENCES iam.identity_account (account_id) ON DELETE RESTRICT,
    CONSTRAINT ck_institution_legal_name_length CHECK (char_length(legal_name) <= 300),
    CONSTRAINT ck_institution_short_name_length CHECK (char_length(short_name) <= 50),
    CONSTRAINT ck_institution_college_code_length CHECK (char_length(college_code) = 3),
    CONSTRAINT ck_institution_aicte_id_length CHECK (aicte_id IS NULL OR char_length(aicte_id) <= 50),
    CONSTRAINT ck_institution_address_line1_length CHECK (address_line1 IS NULL OR char_length(address_line1) <= 200),
    CONSTRAINT ck_institution_city_length CHECK (city IS NULL OR char_length(city) <= 100),
    CONSTRAINT ck_institution_district_length CHECK (district IS NULL OR char_length(district) <= 100),
    CONSTRAINT ck_institution_state_length CHECK (state IS NULL OR char_length(state) <= 100),
    CONSTRAINT ck_institution_postal_code_length CHECK (postal_code IS NULL OR char_length(postal_code) <= 10),
    CONSTRAINT ck_institution_country_length CHECK (country IS NULL OR char_length(country) <= 100),
    CONSTRAINT ck_institution_affiliation_university_length CHECK (affiliation_university IS NULL OR char_length(affiliation_university) <= 200),
    CONSTRAINT ck_institution_autonomy_status CHECK (autonomy_status IN ('autonomous', 'affiliated', 'transitional')),
    CONSTRAINT ck_institution_autonomy_dates CHECK (autonomy_to IS NULL OR (autonomy_from IS NOT NULL AND autonomy_to > autonomy_from)),
    CONSTRAINT ck_institution_currency_length CHECK (char_length(currency) = 3),
    CONSTRAINT ck_institution_status CHECK (status IN ('active', 'inactive'))
);
ALTER TABLE core.institution OWNER TO owner_core;

CREATE UNIQUE INDEX uq_institution_college_code_lower ON core.institution (lower(college_code));
CREATE INDEX ix_institution_parent ON core.institution (parent_institution_id);
CREATE INDEX ix_institution_created_by ON core.institution (created_by);
CREATE INDEX ix_institution_updated_by ON core.institution (updated_by);

CREATE TABLE core.org_unit (
    org_unit_id          uuid        NOT NULL DEFAULT gen_random_uuid(),
    institution_id       uuid        NOT NULL,
    parent_org_unit_id   uuid        NULL,
    code                 text        NOT NULL,
    name                 text        NOT NULL,
    unit_type            text        NOT NULL,
    path                 text        NULL,
    head_person_id       uuid        NULL,
    cost_centre          text        NULL,
    sort_order           integer     NOT NULL DEFAULT 0,
    is_active            boolean     NOT NULL DEFAULT true,
    created_at           timestamptz NOT NULL DEFAULT now(),
    created_by           uuid        NULL,
    updated_at           timestamptz NOT NULL DEFAULT now(),
    updated_by           uuid        NULL,
    row_version          integer     NOT NULL DEFAULT 1,
    CONSTRAINT pk_org_unit PRIMARY KEY (org_unit_id),
    CONSTRAINT fk_org_unit_institution FOREIGN KEY (institution_id)
        REFERENCES core.institution (institution_id) ON DELETE RESTRICT,
    CONSTRAINT fk_org_unit_parent FOREIGN KEY (parent_org_unit_id)
        REFERENCES core.org_unit (org_unit_id) ON DELETE RESTRICT,
    CONSTRAINT fk_org_unit_head_person FOREIGN KEY (head_person_id)
        REFERENCES iam.person (person_id) ON DELETE RESTRICT,
    CONSTRAINT fk_org_unit_created_by FOREIGN KEY (created_by)
        REFERENCES iam.identity_account (account_id) ON DELETE RESTRICT,
    CONSTRAINT fk_org_unit_updated_by FOREIGN KEY (updated_by)
        REFERENCES iam.identity_account (account_id) ON DELETE RESTRICT,
    CONSTRAINT ck_org_unit_not_own_parent CHECK (parent_org_unit_id IS NULL OR parent_org_unit_id <> org_unit_id),
    CONSTRAINT ck_org_unit_code_length CHECK (char_length(code) <= 30),
    CONSTRAINT ck_org_unit_name_length CHECK (char_length(name) <= 200),
    CONSTRAINT ck_org_unit_type CHECK (unit_type IN ('institution', 'department', 'office', 'cell', 'support', 'committee_support')),
    CONSTRAINT ck_org_unit_cost_centre_length CHECK (cost_centre IS NULL OR char_length(cost_centre) <= 50),
    CONSTRAINT ck_org_unit_sort_order CHECK (sort_order >= 0),
    CONSTRAINT uq_org_unit_institution_code UNIQUE (institution_id, code)
);
ALTER TABLE core.org_unit OWNER TO owner_core;

CREATE INDEX ix_org_unit_parent ON core.org_unit (parent_org_unit_id);
CREATE INDEX ix_org_unit_path ON core.org_unit (path text_pattern_ops);
CREATE INDEX ix_org_unit_head_person ON core.org_unit (head_person_id);
CREATE INDEX ix_org_unit_created_by ON core.org_unit (created_by);
CREATE INDEX ix_org_unit_updated_by ON core.org_unit (updated_by);

CREATE TABLE core.academic_year (
    academic_year_id     uuid        NOT NULL DEFAULT gen_random_uuid(),
    institution_id       uuid        NOT NULL,
    label                text        NOT NULL,
    start_date           date        NOT NULL,
    end_date             date        NOT NULL,
    status               text        NOT NULL DEFAULT 'planned',
    created_at           timestamptz NOT NULL DEFAULT now(),
    created_by           uuid        NULL,
    updated_at           timestamptz NOT NULL DEFAULT now(),
    updated_by           uuid        NULL,
    row_version          integer     NOT NULL DEFAULT 1,
    CONSTRAINT pk_academic_year PRIMARY KEY (academic_year_id),
    CONSTRAINT fk_academic_year_institution FOREIGN KEY (institution_id)
        REFERENCES core.institution (institution_id) ON DELETE RESTRICT,
    CONSTRAINT fk_academic_year_created_by FOREIGN KEY (created_by)
        REFERENCES iam.identity_account (account_id) ON DELETE RESTRICT,
    CONSTRAINT fk_academic_year_updated_by FOREIGN KEY (updated_by)
        REFERENCES iam.identity_account (account_id) ON DELETE RESTRICT,
    CONSTRAINT ck_academic_year_dates CHECK (end_date > start_date),
    CONSTRAINT ck_academic_year_status CHECK (status IN ('planned', 'active', 'closed')),
    CONSTRAINT uq_academic_year_institution_label UNIQUE (institution_id, label)
);
ALTER TABLE core.academic_year OWNER TO owner_core;

CREATE INDEX ix_academic_year_dates ON core.academic_year (start_date, end_date);
CREATE INDEX ix_academic_year_created_by ON core.academic_year (created_by);
CREATE INDEX ix_academic_year_updated_by ON core.academic_year (updated_by);

CREATE TABLE core.term (
    term_id              uuid        NOT NULL DEFAULT gen_random_uuid(),
    academic_year_id     uuid        NOT NULL,
    term_type            text        NOT NULL,
    term_no              smallint    NOT NULL,
    start_date           date        NOT NULL,
    end_date             date        NOT NULL,
    instruction_start    date        NULL,
    instruction_end      date        NULL,
    exam_start           date        NULL,
    exam_end             date        NULL,
    working_days_planned integer     NULL,
    working_days_actual  integer     NULL,
    status               text        NOT NULL DEFAULT 'planned',
    created_at           timestamptz NOT NULL DEFAULT now(),
    created_by           uuid        NULL,
    updated_at           timestamptz NOT NULL DEFAULT now(),
    updated_by           uuid        NULL,
    row_version          integer     NOT NULL DEFAULT 1,
    CONSTRAINT pk_term PRIMARY KEY (term_id),
    CONSTRAINT fk_term_academic_year FOREIGN KEY (academic_year_id)
        REFERENCES core.academic_year (academic_year_id) ON DELETE RESTRICT,
    CONSTRAINT fk_term_created_by FOREIGN KEY (created_by)
        REFERENCES iam.identity_account (account_id) ON DELETE RESTRICT,
    CONSTRAINT fk_term_updated_by FOREIGN KEY (updated_by)
        REFERENCES iam.identity_account (account_id) ON DELETE RESTRICT,
    CONSTRAINT ck_term_type CHECK (term_type IN ('odd', 'even', 'summer', 'supplementary', 'winter')),
    CONSTRAINT ck_term_no CHECK (term_no BETWEEN 1 AND 8),
    CONSTRAINT ck_term_dates CHECK (end_date > start_date),
    CONSTRAINT ck_term_working_days_planned CHECK (working_days_planned IS NULL OR working_days_planned >= 0),
    CONSTRAINT ck_term_working_days_actual CHECK (working_days_actual IS NULL OR working_days_actual >= 0),
    CONSTRAINT ck_term_status CHECK (status IN ('planned', 'active', 'closed')),
    CONSTRAINT uq_term_year_type_no UNIQUE (academic_year_id, term_type, term_no)
);
ALTER TABLE core.term OWNER TO owner_core;

CREATE INDEX ix_term_year_type ON core.term (academic_year_id, term_type);
CREATE INDEX ix_term_dates ON core.term (start_date, end_date);
CREATE INDEX ix_term_created_by ON core.term (created_by);
CREATE INDEX ix_term_updated_by ON core.term (updated_by);

-- ===========================================================================
-- 3. Integration entity registry and retention schedule
--    INT-01 and OPS-04 are created here because doc.document depends on both.
-- ===========================================================================

CREATE TABLE integration.entity_type (
    entity_type_code     text        NOT NULL,
    description          text        NULL,
    schema_name          text        NOT NULL,
    table_name           text        NOT NULL,
    is_active            boolean     NOT NULL DEFAULT true,
    created_at           timestamptz NOT NULL DEFAULT now(),
    created_by           uuid        NULL,
    CONSTRAINT pk_entity_type PRIMARY KEY (entity_type_code),
    CONSTRAINT ck_entity_type_code_length CHECK (char_length(entity_type_code) <= 60),
    CONSTRAINT ck_entity_type_description_length CHECK (description IS NULL OR char_length(description) <= 500),
    CONSTRAINT ck_entity_type_schema_name_length CHECK (char_length(schema_name) <= 60),
    CONSTRAINT ck_entity_type_table_name_length CHECK (char_length(table_name) <= 60)
);
ALTER TABLE integration.entity_type OWNER TO owner_integration;

CREATE UNIQUE INDEX uq_entity_type_schema_table
    ON integration.entity_type (schema_name, table_name);

CREATE TABLE ops.retention_schedule (
    retention_schedule_id  uuid        NOT NULL DEFAULT gen_random_uuid(),
    entity_type_code       text        NOT NULL,
    classification         text        NOT NULL,
    retention_period_months integer    NOT NULL,
    trigger_event          text        NULL,
    disposition            text        NOT NULL DEFAULT 'archive',
    legal_basis            text        NULL,
    status                 text        NOT NULL DEFAULT 'draft',
    approved_by            uuid        NULL,
    created_at             timestamptz NOT NULL DEFAULT now(),
    created_by             uuid        NULL,
    updated_at             timestamptz NOT NULL DEFAULT now(),
    updated_by             uuid        NULL,
    row_version            integer     NOT NULL DEFAULT 1,
    CONSTRAINT pk_retention_schedule PRIMARY KEY (retention_schedule_id),
    CONSTRAINT fk_retention_schedule_entity_type FOREIGN KEY (entity_type_code)
        REFERENCES integration.entity_type (entity_type_code) ON DELETE RESTRICT,
    CONSTRAINT fk_retention_schedule_approved_by FOREIGN KEY (approved_by)
        REFERENCES iam.person (person_id) ON DELETE RESTRICT,
    CONSTRAINT fk_retention_schedule_created_by FOREIGN KEY (created_by)
        REFERENCES iam.identity_account (account_id) ON DELETE RESTRICT,
    CONSTRAINT fk_retention_schedule_updated_by FOREIGN KEY (updated_by)
        REFERENCES iam.identity_account (account_id) ON DELETE RESTRICT,
    CONSTRAINT ck_retention_schedule_classification CHECK (classification IN ('P', 'I', 'C', 'R', 'G')),
    CONSTRAINT ck_retention_schedule_period CHECK (retention_period_months > 0),
    CONSTRAINT ck_retention_schedule_trigger_event_length CHECK (trigger_event IS NULL OR char_length(trigger_event) <= 200),
    CONSTRAINT ck_retention_schedule_disposition CHECK (disposition IN ('destroy', 'anonymize', 'archive')),
    CONSTRAINT ck_retention_schedule_legal_basis_length CHECK (legal_basis IS NULL OR char_length(legal_basis) <= 1000),
    CONSTRAINT ck_retention_schedule_status CHECK (status IN ('draft', 'approved', 'superseded')),
    CONSTRAINT ck_retention_schedule_approved_requires_approver CHECK (status <> 'approved' OR approved_by IS NOT NULL),
    CONSTRAINT uq_retention_schedule_entity_class UNIQUE (entity_type_code, classification)
);
ALTER TABLE ops.retention_schedule OWNER TO owner_ops;

CREATE INDEX ix_retention_schedule_entity_type ON ops.retention_schedule (entity_type_code);
CREATE INDEX ix_retention_schedule_approved_by ON ops.retention_schedule (approved_by);
CREATE INDEX ix_retention_schedule_created_by ON ops.retention_schedule (created_by);
CREATE INDEX ix_retention_schedule_updated_by ON ops.retention_schedule (updated_by);

-- ===========================================================================
-- 4. Documents -- DOC-01 .. DOC-03
-- ===========================================================================

CREATE TABLE doc.document (
    document_id          uuid        NOT NULL DEFAULT gen_random_uuid(),
    title                text        NOT NULL,
    document_type        text        NOT NULL,
    issuer_name          text        NOT NULL,
    issuer_org_unit_id   uuid        NULL,
    reference_no         text        NULL,
    document_date        date        NOT NULL,
    effective_date       date        NULL,
    classification       text        NOT NULL DEFAULT 'I',
    owner_org_unit_id    uuid        NULL,
    status               text        NOT NULL DEFAULT 'active',
    source_url           text        NULL,
    retention_schedule_id uuid       NULL,
    created_at           timestamptz NOT NULL DEFAULT now(),
    created_by           uuid        NULL,
    updated_at           timestamptz NOT NULL DEFAULT now(),
    updated_by           uuid        NULL,
    row_version          integer     NOT NULL DEFAULT 1,
    CONSTRAINT pk_document PRIMARY KEY (document_id),
    CONSTRAINT fk_document_issuer_org_unit FOREIGN KEY (issuer_org_unit_id)
        REFERENCES core.org_unit (org_unit_id) ON DELETE RESTRICT,
    CONSTRAINT fk_document_owner_org_unit FOREIGN KEY (owner_org_unit_id)
        REFERENCES core.org_unit (org_unit_id) ON DELETE RESTRICT,
    CONSTRAINT fk_document_retention_schedule FOREIGN KEY (retention_schedule_id)
        REFERENCES ops.retention_schedule (retention_schedule_id) ON DELETE RESTRICT,
    CONSTRAINT fk_document_created_by FOREIGN KEY (created_by)
        REFERENCES iam.identity_account (account_id) ON DELETE RESTRICT,
    CONSTRAINT fk_document_updated_by FOREIGN KEY (updated_by)
        REFERENCES iam.identity_account (account_id) ON DELETE RESTRICT,
    CONSTRAINT ck_document_title_length CHECK (char_length(title) <= 500),
    CONSTRAINT ck_document_type CHECK (document_type IN ('regulation', 'policy', 'order', 'notification', 'circular', 'prospectus', 'syllabus', 'minutes', 'report', 'form', 'other')),
    CONSTRAINT ck_document_issuer_name_length CHECK (char_length(issuer_name) <= 200),
    CONSTRAINT ck_document_effective_date CHECK (effective_date IS NULL OR effective_date >= document_date),
    CONSTRAINT ck_document_classification CHECK (classification IN ('P', 'I', 'C', 'R', 'G')),
    CONSTRAINT ck_document_status CHECK (status IN ('draft', 'active', 'superseded', 'withdrawn', 'archived')),
    CONSTRAINT ck_document_source_url_length CHECK (source_url IS NULL OR char_length(source_url) <= 2000)
);
ALTER TABLE doc.document OWNER TO owner_doc;

CREATE UNIQUE INDEX uq_document_issuer_reference
    ON doc.document (issuer_org_unit_id, reference_no)
    WHERE reference_no IS NOT NULL;
CREATE INDEX ix_document_type_date ON doc.document (document_type, document_date);
CREATE INDEX ix_document_classification ON doc.document (classification);
CREATE INDEX ix_document_title_fts ON doc.document USING gin (to_tsvector('simple', title));
CREATE INDEX ix_document_issuer_org_unit ON doc.document (issuer_org_unit_id);
CREATE INDEX ix_document_owner_org_unit ON doc.document (owner_org_unit_id);
CREATE INDEX ix_document_retention_schedule ON doc.document (retention_schedule_id);
CREATE INDEX ix_document_created_by ON doc.document (created_by);
CREATE INDEX ix_document_updated_by ON doc.document (updated_by);

CREATE TABLE doc.document_version (
    document_version_id  uuid        NOT NULL DEFAULT gen_random_uuid(),
    document_id          uuid        NOT NULL,
    version_no           integer     NOT NULL DEFAULT 1,
    version_label        text        NULL,
    file_uri             text        NOT NULL,
    mime_type            text        NOT NULL,
    file_size            bigint      NULL,
    sha256               text        NOT NULL,
    page_count           integer     NULL,
    ocr_used             boolean     NOT NULL DEFAULT false,
    language             text        NULL,
    change_note          text        NULL,
    supersedes_version_id uuid       NULL,
    effective_from       date        NULL,
    effective_to         date        NULL,
    status               text        NOT NULL DEFAULT 'draft',
    ingested_at          timestamptz NULL,
    approved_by          uuid        NULL,
    approved_at          timestamptz NULL,
    created_at           timestamptz NOT NULL DEFAULT now(),
    created_by           uuid        NULL,
    CONSTRAINT pk_document_version PRIMARY KEY (document_version_id),
    CONSTRAINT fk_document_version_document FOREIGN KEY (document_id)
        REFERENCES doc.document (document_id) ON DELETE RESTRICT,
    CONSTRAINT fk_document_version_supersedes FOREIGN KEY (supersedes_version_id)
        REFERENCES doc.document_version (document_version_id) ON DELETE RESTRICT,
    CONSTRAINT fk_document_version_approved_by FOREIGN KEY (approved_by)
        REFERENCES iam.person (person_id) ON DELETE RESTRICT,
    CONSTRAINT ck_document_version_version_no CHECK (version_no >= 1),
    CONSTRAINT ck_document_version_version_label_length CHECK (version_label IS NULL OR char_length(version_label) <= 50),
    CONSTRAINT ck_document_version_mime_type_length CHECK (char_length(mime_type) <= 100),
    CONSTRAINT ck_document_version_file_size CHECK (file_size IS NULL OR file_size >= 0),
    CONSTRAINT ck_document_version_sha256_length CHECK (length(sha256) = 64),
    CONSTRAINT ck_document_version_page_count CHECK (page_count IS NULL OR page_count >= 0),
    CONSTRAINT ck_document_version_language CHECK (language IS NULL OR language IN ('en', 'bn', 'hi', 'multilingual', 'other')),
    CONSTRAINT ck_document_version_change_note_length CHECK (change_note IS NULL OR char_length(change_note) <= 2000),
    CONSTRAINT ck_document_version_not_own_supersedes CHECK (supersedes_version_id IS NULL OR supersedes_version_id <> document_version_id),
    CONSTRAINT ck_document_version_effective_dates CHECK (effective_to IS NULL OR (effective_from IS NOT NULL AND effective_to > effective_from)),
    CONSTRAINT ck_document_version_status CHECK (status IN ('draft', 'active', 'superseded', 'withdrawn', 'archived')),
    CONSTRAINT uq_document_version_document_no UNIQUE (document_id, version_no),
    CONSTRAINT uq_document_version_sha256 UNIQUE (sha256)
);
ALTER TABLE doc.document_version OWNER TO owner_doc;

CREATE INDEX ix_document_version_document_no_desc
    ON doc.document_version (document_id, version_no DESC);
CREATE INDEX ix_document_version_sha256 ON doc.document_version (sha256);
CREATE INDEX ix_document_version_status ON doc.document_version (status);
CREATE INDEX ix_document_version_supersedes ON doc.document_version (supersedes_version_id);
CREATE INDEX ix_document_version_approved_by ON doc.document_version (approved_by);

CREATE TABLE doc.document_relation (
    document_relation_id uuid        NOT NULL DEFAULT gen_random_uuid(),
    from_version_id      uuid        NOT NULL,
    to_version_id        uuid        NOT NULL,
    relation_type        text        NOT NULL,
    note                 text        NULL,
    created_at           timestamptz NOT NULL DEFAULT now(),
    created_by           uuid        NULL,
    updated_at           timestamptz NOT NULL DEFAULT now(),
    updated_by           uuid        NULL,
    row_version          integer     NOT NULL DEFAULT 1,
    CONSTRAINT pk_document_relation PRIMARY KEY (document_relation_id),
    CONSTRAINT fk_document_relation_from FOREIGN KEY (from_version_id)
        REFERENCES doc.document_version (document_version_id) ON DELETE RESTRICT,
    CONSTRAINT fk_document_relation_to FOREIGN KEY (to_version_id)
        REFERENCES doc.document_version (document_version_id) ON DELETE RESTRICT,
    CONSTRAINT fk_document_relation_created_by FOREIGN KEY (created_by)
        REFERENCES iam.identity_account (account_id) ON DELETE RESTRICT,
    CONSTRAINT fk_document_relation_updated_by FOREIGN KEY (updated_by)
        REFERENCES iam.identity_account (account_id) ON DELETE RESTRICT,
    CONSTRAINT ck_document_relation_not_self CHECK (from_version_id <> to_version_id),
    CONSTRAINT ck_document_relation_type CHECK (relation_type IN ('supersedes', 'corrigendum', 'attachment', 'translation', 'duplicate', 'references')),
    CONSTRAINT ck_document_relation_note_length CHECK (note IS NULL OR char_length(note) <= 1000),
    CONSTRAINT uq_document_relation UNIQUE (from_version_id, to_version_id, relation_type)
);
ALTER TABLE doc.document_relation OWNER TO owner_doc;

CREATE INDEX ix_document_relation_to ON doc.document_relation (to_version_id);
CREATE INDEX ix_document_relation_created_by ON doc.document_relation (created_by);
CREATE INDEX ix_document_relation_updated_by ON doc.document_relation (updated_by);

-- ===========================================================================
-- 5. Governance bodies, authority assignments, and remaining core tables
--    GOV-02, GOV-04, GOV-05, GOV-06, GOV-07, GOV-10, GOV-11; IAM-07, IAM-08.
-- ===========================================================================

CREATE TABLE core.governance_body (
    governance_body_id   uuid        NOT NULL DEFAULT gen_random_uuid(),
    institution_id       uuid        NOT NULL,
    body_code            text        NOT NULL,
    name                 text        NOT NULL,
    body_type            text        NOT NULL,
    is_statutory         boolean     NOT NULL DEFAULT false,
    scope_org_unit_id    uuid        NULL,
    term_start           date        NOT NULL,
    term_end             date        NULL,
    constitution_order_version_id uuid NULL,
    chair_person_id      uuid        NULL,
    secretary_person_id  uuid        NULL,
    quorum_min           integer     NULL,
    status               text        NOT NULL DEFAULT 'constituted',
    created_at           timestamptz NOT NULL DEFAULT now(),
    created_by           uuid        NULL,
    updated_at           timestamptz NOT NULL DEFAULT now(),
    updated_by           uuid        NULL,
    row_version          integer     NOT NULL DEFAULT 1,
    CONSTRAINT pk_governance_body PRIMARY KEY (governance_body_id),
    CONSTRAINT fk_governance_body_institution FOREIGN KEY (institution_id)
        REFERENCES core.institution (institution_id) ON DELETE RESTRICT,
    CONSTRAINT fk_governance_body_scope_org_unit FOREIGN KEY (scope_org_unit_id)
        REFERENCES core.org_unit (org_unit_id) ON DELETE RESTRICT,
    CONSTRAINT fk_governance_body_constitution_order FOREIGN KEY (constitution_order_version_id)
        REFERENCES doc.document_version (document_version_id) ON DELETE RESTRICT,
    CONSTRAINT fk_governance_body_chair FOREIGN KEY (chair_person_id)
        REFERENCES iam.person (person_id) ON DELETE RESTRICT,
    CONSTRAINT fk_governance_body_secretary FOREIGN KEY (secretary_person_id)
        REFERENCES iam.person (person_id) ON DELETE RESTRICT,
    CONSTRAINT fk_governance_body_created_by FOREIGN KEY (created_by)
        REFERENCES iam.identity_account (account_id) ON DELETE RESTRICT,
    CONSTRAINT fk_governance_body_updated_by FOREIGN KEY (updated_by)
        REFERENCES iam.identity_account (account_id) ON DELETE RESTRICT,
    CONSTRAINT ck_governance_body_code_length CHECK (char_length(body_code) <= 50),
    CONSTRAINT ck_governance_body_name_length CHECK (char_length(name) <= 200),
    CONSTRAINT ck_governance_body_type CHECK (body_type IN ('BOG', 'AcademicCouncil', 'FinanceCommittee', 'BoardOfStudies', 'ExaminationCommittee', 'IQAC', 'Disciplinary', 'AntiRagging', 'ICC', 'Grievance', 'MAR', 'MOOCs', 'Library', 'Purchase', 'RD', 'TP', 'other')),
    CONSTRAINT ck_governance_body_term_dates CHECK (term_end IS NULL OR term_end > term_start),
    CONSTRAINT ck_governance_body_quorum CHECK (quorum_min IS NULL OR quorum_min >= 1),
    CONSTRAINT ck_governance_body_status CHECK (status IN ('constituted', 'active', 'dissolved', 'superseded')),
    CONSTRAINT uq_governance_body_institution_code_start UNIQUE (institution_id, body_code, term_start)
);
ALTER TABLE core.governance_body OWNER TO owner_core;

CREATE INDEX ix_governance_body_type_statutory ON core.governance_body (body_type, is_statutory);
CREATE INDEX ix_governance_body_term_end ON core.governance_body (term_end);
CREATE INDEX ix_governance_body_scope_org_unit ON core.governance_body (scope_org_unit_id);
CREATE INDEX ix_governance_body_constitution_order ON core.governance_body (constitution_order_version_id);
CREATE INDEX ix_governance_body_chair ON core.governance_body (chair_person_id);
CREATE INDEX ix_governance_body_secretary ON core.governance_body (secretary_person_id);
CREATE INDEX ix_governance_body_created_by ON core.governance_body (created_by);
CREATE INDEX ix_governance_body_updated_by ON core.governance_body (updated_by);

CREATE TABLE iam.role_assignment (
    role_assignment_id   uuid        NOT NULL DEFAULT gen_random_uuid(),
    person_id            uuid        NOT NULL,
    role_id              uuid        NOT NULL,
    scope_type           text        NOT NULL,
    scope_key            uuid        NOT NULL,
    institution_id       uuid        NULL,
    org_unit_id          uuid        NULL,
    programme_id         uuid        NULL,  -- TODO(OD-12): FK added in W1b
    batch_id             uuid        NULL,  -- TODO(OD-12): FK added in W1b
    term_id              uuid        NULL,
    course_offering_id   uuid        NULL,  -- TODO(OD-12): FK added in W1b
    governance_body_id   uuid        NULL,
    valid_from           date        NOT NULL DEFAULT current_date,
    valid_to             date        NULL,
    status               text        NOT NULL DEFAULT 'active',
    appointing_authority text        NULL,
    source_document_version_id uuid   NULL,
    delegated_from_assignment_id uuid NULL,
    source_membership_id uuid        NULL,
    approved_by          uuid        NULL,
    approved_at          timestamptz NULL,
    created_at           timestamptz NOT NULL DEFAULT now(),
    created_by           uuid        NULL,
    updated_at           timestamptz NOT NULL DEFAULT now(),
    updated_by           uuid        NULL,
    row_version          integer     NOT NULL DEFAULT 1,
    CONSTRAINT pk_role_assignment PRIMARY KEY (role_assignment_id),
    CONSTRAINT fk_role_assignment_person FOREIGN KEY (person_id)
        REFERENCES iam.person (person_id) ON DELETE RESTRICT,
    CONSTRAINT fk_role_assignment_role FOREIGN KEY (role_id)
        REFERENCES iam.role (role_id) ON DELETE RESTRICT,
    CONSTRAINT fk_role_assignment_institution FOREIGN KEY (institution_id)
        REFERENCES core.institution (institution_id) ON DELETE RESTRICT,
    CONSTRAINT fk_role_assignment_org_unit FOREIGN KEY (org_unit_id)
        REFERENCES core.org_unit (org_unit_id) ON DELETE RESTRICT,
    CONSTRAINT fk_role_assignment_term FOREIGN KEY (term_id)
        REFERENCES core.term (term_id) ON DELETE RESTRICT,
    CONSTRAINT fk_role_assignment_governance_body FOREIGN KEY (governance_body_id)
        REFERENCES core.governance_body (governance_body_id) ON DELETE RESTRICT,
    CONSTRAINT fk_role_assignment_source_document FOREIGN KEY (source_document_version_id)
        REFERENCES doc.document_version (document_version_id) ON DELETE RESTRICT,
    CONSTRAINT fk_role_assignment_delegated_from FOREIGN KEY (delegated_from_assignment_id)
        REFERENCES iam.role_assignment (role_assignment_id) ON DELETE RESTRICT,
    CONSTRAINT fk_role_assignment_approved_by FOREIGN KEY (approved_by)
        REFERENCES iam.person (person_id) ON DELETE RESTRICT,
    CONSTRAINT fk_role_assignment_created_by FOREIGN KEY (created_by)
        REFERENCES iam.identity_account (account_id) ON DELETE RESTRICT,
    CONSTRAINT fk_role_assignment_updated_by FOREIGN KEY (updated_by)
        REFERENCES iam.identity_account (account_id) ON DELETE RESTRICT,
    CONSTRAINT ck_role_assignment_scope_type CHECK (scope_type IN ('institution', 'org_unit', 'programme', 'batch', 'term', 'course_offering', 'governance_body')),
    CONSTRAINT ck_role_assignment_one_scope CHECK (num_nonnulls(institution_id, org_unit_id, programme_id, batch_id, term_id, course_offering_id, governance_body_id) = 1),
    CONSTRAINT ck_role_assignment_validity CHECK (valid_to IS NULL OR valid_to > valid_from),
    CONSTRAINT ck_role_assignment_status CHECK (status IN ('active', 'suspended', 'expired', 'revoked')),
    CONSTRAINT ck_role_assignment_appointing_authority_length CHECK (appointing_authority IS NULL OR char_length(appointing_authority) <= 200)
);
ALTER TABLE iam.role_assignment OWNER TO owner_iam;

CREATE UNIQUE INDEX uq_role_assignment_active_scope
    ON iam.role_assignment (person_id, role_id, scope_type, scope_key)
    WHERE status = 'active';
CREATE INDEX ix_role_assignment_person_status ON iam.role_assignment (person_id, status);
CREATE INDEX ix_role_assignment_role ON iam.role_assignment (role_id);
CREATE INDEX ix_role_assignment_scope ON iam.role_assignment (scope_type, scope_key);
CREATE INDEX ix_role_assignment_valid_to ON iam.role_assignment (valid_to);
CREATE INDEX ix_role_assignment_institution ON iam.role_assignment (institution_id);
CREATE INDEX ix_role_assignment_org_unit ON iam.role_assignment (org_unit_id);
CREATE INDEX ix_role_assignment_programme ON iam.role_assignment (programme_id);
CREATE INDEX ix_role_assignment_batch ON iam.role_assignment (batch_id);
CREATE INDEX ix_role_assignment_term ON iam.role_assignment (term_id);
CREATE INDEX ix_role_assignment_course_offering ON iam.role_assignment (course_offering_id);
CREATE INDEX ix_role_assignment_governance_body ON iam.role_assignment (governance_body_id);
CREATE INDEX ix_role_assignment_source_document ON iam.role_assignment (source_document_version_id);
CREATE INDEX ix_role_assignment_delegated_from ON iam.role_assignment (delegated_from_assignment_id);
CREATE INDEX ix_role_assignment_approved_by ON iam.role_assignment (approved_by);
CREATE INDEX ix_role_assignment_created_by ON iam.role_assignment (created_by);
CREATE INDEX ix_role_assignment_updated_by ON iam.role_assignment (updated_by);

CREATE OR REPLACE FUNCTION iam.enforce_role_assignment_scope()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    expected uuid;
BEGIN
    CASE NEW.scope_type
        WHEN 'institution' THEN expected := NEW.institution_id;
        WHEN 'org_unit' THEN expected := NEW.org_unit_id;
        WHEN 'programme' THEN expected := NEW.programme_id;
        WHEN 'batch' THEN expected := NEW.batch_id;
        WHEN 'term' THEN expected := NEW.term_id;
        WHEN 'course_offering' THEN expected := NEW.course_offering_id;
        WHEN 'governance_body' THEN expected := NEW.governance_body_id;
        ELSE
            RAISE EXCEPTION 'iam.role_assignment: unknown scope_type %', NEW.scope_type;
    END CASE;

    IF expected IS NULL THEN
        RAISE EXCEPTION 'iam.role_assignment: scope_type % requires its scope column', NEW.scope_type;
    END IF;
    IF NEW.scope_key <> expected THEN
        RAISE EXCEPTION 'iam.role_assignment: scope_key (%) must equal the populated % scope column',
            NEW.scope_key, NEW.scope_type;
    END IF;
    RETURN NEW;
END;
$$;
ALTER FUNCTION iam.enforce_role_assignment_scope() OWNER TO owner_iam;

CREATE TRIGGER trg_role_assignment_scope
    BEFORE INSERT OR UPDATE ON iam.role_assignment
    FOR EACH ROW EXECUTE FUNCTION iam.enforce_role_assignment_scope();

CREATE TABLE iam.delegation (
    delegation_id        uuid        NOT NULL DEFAULT gen_random_uuid(),
    from_assignment_id   uuid        NOT NULL,
    to_assignment_id     uuid        NOT NULL,
    reason               text        NOT NULL,
    valid_from           timestamptz NOT NULL DEFAULT now(),
    valid_to             timestamptz NOT NULL,
    limits_json          jsonb       NULL DEFAULT '{}',
    status               text        NOT NULL DEFAULT 'active',
    approved_by          uuid        NULL,
    approved_at          timestamptz NULL,
    created_at           timestamptz NOT NULL DEFAULT now(),
    created_by           uuid        NULL,
    updated_at           timestamptz NOT NULL DEFAULT now(),
    updated_by           uuid        NULL,
    row_version          integer     NOT NULL DEFAULT 1,
    CONSTRAINT pk_delegation PRIMARY KEY (delegation_id),
    CONSTRAINT fk_delegation_from_assignment FOREIGN KEY (from_assignment_id)
        REFERENCES iam.role_assignment (role_assignment_id) ON DELETE RESTRICT,
    CONSTRAINT fk_delegation_to_assignment FOREIGN KEY (to_assignment_id)
        REFERENCES iam.role_assignment (role_assignment_id) ON DELETE RESTRICT,
    CONSTRAINT fk_delegation_approved_by FOREIGN KEY (approved_by)
        REFERENCES iam.person (person_id) ON DELETE RESTRICT,
    CONSTRAINT fk_delegation_created_by FOREIGN KEY (created_by)
        REFERENCES iam.identity_account (account_id) ON DELETE RESTRICT,
    CONSTRAINT fk_delegation_updated_by FOREIGN KEY (updated_by)
        REFERENCES iam.identity_account (account_id) ON DELETE RESTRICT,
    CONSTRAINT ck_delegation_not_self CHECK (from_assignment_id <> to_assignment_id),
    CONSTRAINT ck_delegation_reason_length CHECK (char_length(reason) BETWEEN 10 AND 2000),
    CONSTRAINT ck_delegation_validity CHECK (valid_to > valid_from),
    CONSTRAINT ck_delegation_status CHECK (status IN ('active', 'expired', 'revoked'))
);
ALTER TABLE iam.delegation OWNER TO owner_iam;

CREATE INDEX ix_delegation_to_status ON iam.delegation (to_assignment_id, status);
CREATE INDEX ix_delegation_from_assignment ON iam.delegation (from_assignment_id);
CREATE INDEX ix_delegation_approved_by ON iam.delegation (approved_by);
CREATE INDEX ix_delegation_created_by ON iam.delegation (created_by);
CREATE INDEX ix_delegation_updated_by ON iam.delegation (updated_by);

CREATE TABLE core.governance_membership (
    governance_membership_id uuid    NOT NULL DEFAULT gen_random_uuid(),
    governance_body_id   uuid        NOT NULL,
    person_id            uuid        NOT NULL,
    role_in_body         text        NOT NULL DEFAULT 'member',
    valid_from           date        NOT NULL,
    valid_to             date        NULL,
    order_reference      text        NULL,
    order_document_version_id uuid   NULL,
    source_role_assignment_id uuid   NULL,
    status               text        NOT NULL DEFAULT 'active',
    created_at           timestamptz NOT NULL DEFAULT now(),
    created_by           uuid        NULL,
    updated_at           timestamptz NOT NULL DEFAULT now(),
    updated_by           uuid        NULL,
    row_version          integer     NOT NULL DEFAULT 1,
    CONSTRAINT pk_governance_membership PRIMARY KEY (governance_membership_id),
    CONSTRAINT fk_governance_membership_body FOREIGN KEY (governance_body_id)
        REFERENCES core.governance_body (governance_body_id) ON DELETE RESTRICT,
    CONSTRAINT fk_governance_membership_person FOREIGN KEY (person_id)
        REFERENCES iam.person (person_id) ON DELETE RESTRICT,
    CONSTRAINT fk_governance_membership_order_document FOREIGN KEY (order_document_version_id)
        REFERENCES doc.document_version (document_version_id) ON DELETE RESTRICT,
    CONSTRAINT fk_governance_membership_source_assignment FOREIGN KEY (source_role_assignment_id)
        REFERENCES iam.role_assignment (role_assignment_id) ON DELETE RESTRICT,
    CONSTRAINT fk_governance_membership_created_by FOREIGN KEY (created_by)
        REFERENCES iam.identity_account (account_id) ON DELETE RESTRICT,
    CONSTRAINT fk_governance_membership_updated_by FOREIGN KEY (updated_by)
        REFERENCES iam.identity_account (account_id) ON DELETE RESTRICT,
    CONSTRAINT ck_governance_membership_role CHECK (role_in_body IN ('chair', 'member', 'member_secretary', 'invitee', 'nominee', 'co_opted')),
    CONSTRAINT ck_governance_membership_validity CHECK (valid_to IS NULL OR valid_to > valid_from),
    CONSTRAINT ck_governance_membership_order_reference_length CHECK (order_reference IS NULL OR char_length(order_reference) <= 100),
    CONSTRAINT ck_governance_membership_status CHECK (status IN ('active', 'expired', 'revoked')),
    CONSTRAINT uq_governance_membership_body_person_start UNIQUE (governance_body_id, person_id, valid_from)
);
ALTER TABLE core.governance_membership OWNER TO owner_core;

CREATE INDEX ix_governance_membership_person_valid_to ON core.governance_membership (person_id, valid_to);
CREATE INDEX ix_governance_membership_body_status ON core.governance_membership (governance_body_id, status);
CREATE INDEX ix_governance_membership_order_document ON core.governance_membership (order_document_version_id);
CREATE INDEX ix_governance_membership_source_assignment ON core.governance_membership (source_role_assignment_id);
CREATE INDEX ix_governance_membership_created_by ON core.governance_membership (created_by);
CREATE INDEX ix_governance_membership_updated_by ON core.governance_membership (updated_by);

-- Deferred constraint from POSTGRES_ARCHITECTURE 5.3.
ALTER TABLE iam.role_assignment
    ADD CONSTRAINT fk_role_assignment_source_membership
    FOREIGN KEY (source_membership_id)
    REFERENCES core.governance_membership (governance_membership_id)
    ON DELETE RESTRICT
    DEFERRABLE INITIALLY DEFERRED;
CREATE INDEX ix_role_assignment_source_membership ON iam.role_assignment (source_membership_id);

CREATE TABLE core.society (
    society_id           uuid        NOT NULL DEFAULT gen_random_uuid(),
    institution_id       uuid        NOT NULL,
    name                 text        NOT NULL,
    registration_no      text        NULL,
    registered_on        date        NULL,
    address              text        NULL,
    rules_document_version_id uuid   NULL,
    status               text        NOT NULL DEFAULT 'active',
    created_at           timestamptz NOT NULL DEFAULT now(),
    created_by           uuid        NULL,
    updated_at           timestamptz NOT NULL DEFAULT now(),
    updated_by           uuid        NULL,
    row_version          integer     NOT NULL DEFAULT 1,
    CONSTRAINT pk_society PRIMARY KEY (society_id),
    CONSTRAINT fk_society_institution FOREIGN KEY (institution_id)
        REFERENCES core.institution (institution_id) ON DELETE RESTRICT,
    CONSTRAINT fk_society_rules_document FOREIGN KEY (rules_document_version_id)
        REFERENCES doc.document_version (document_version_id) ON DELETE RESTRICT,
    CONSTRAINT fk_society_created_by FOREIGN KEY (created_by)
        REFERENCES iam.identity_account (account_id) ON DELETE RESTRICT,
    CONSTRAINT fk_society_updated_by FOREIGN KEY (updated_by)
        REFERENCES iam.identity_account (account_id) ON DELETE RESTRICT,
    CONSTRAINT ck_society_name_length CHECK (char_length(name) <= 300),
    CONSTRAINT ck_society_address_length CHECK (address IS NULL OR char_length(address) <= 500),
    CONSTRAINT ck_society_status CHECK (status IN ('active', 'inactive'))
);
ALTER TABLE core.society OWNER TO owner_core;

CREATE UNIQUE INDEX uq_society_registration_no
    ON core.society (registration_no) WHERE registration_no IS NOT NULL;
CREATE INDEX ix_society_institution ON core.society (institution_id);
CREATE INDEX ix_society_rules_document ON core.society (rules_document_version_id);
CREATE INDEX ix_society_created_by ON core.society (created_by);
CREATE INDEX ix_society_updated_by ON core.society (updated_by);

CREATE TABLE core.statutory_approval (
    statutory_approval_id uuid       NOT NULL DEFAULT gen_random_uuid(),
    institution_id       uuid        NOT NULL,
    programme_id         uuid        NULL,  -- TODO(OD-12): FK added in W1b
    approval_type        text        NOT NULL,
    authority            text        NOT NULL,
    reference_no         text        NOT NULL,
    approved_on          date        NOT NULL,
    valid_from           date        NOT NULL,
    valid_to             date        NULL,
    scope_type           text        NOT NULL,
    conditions_text      text        NULL,
    status               text        NOT NULL DEFAULT 'current',
    document_version_id  uuid        NULL,
    created_at           timestamptz NOT NULL DEFAULT now(),
    created_by           uuid        NULL,
    updated_at           timestamptz NOT NULL DEFAULT now(),
    updated_by           uuid        NULL,
    row_version          integer     NOT NULL DEFAULT 1,
    CONSTRAINT pk_statutory_approval PRIMARY KEY (statutory_approval_id),
    CONSTRAINT fk_statutory_approval_institution FOREIGN KEY (institution_id)
        REFERENCES core.institution (institution_id) ON DELETE RESTRICT,
    CONSTRAINT fk_statutory_approval_document FOREIGN KEY (document_version_id)
        REFERENCES doc.document_version (document_version_id) ON DELETE RESTRICT,
    CONSTRAINT fk_statutory_approval_created_by FOREIGN KEY (created_by)
        REFERENCES iam.identity_account (account_id) ON DELETE RESTRICT,
    CONSTRAINT fk_statutory_approval_updated_by FOREIGN KEY (updated_by)
        REFERENCES iam.identity_account (account_id) ON DELETE RESTRICT,
    CONSTRAINT ck_statutory_approval_type CHECK (approval_type IN ('aicte_eoa', 'makaut_affiliation', 'ugc_autonomy', 'nba', 'naac', 'state', 'other')),
    CONSTRAINT ck_statutory_approval_authority_length CHECK (char_length(authority) <= 100),
    CONSTRAINT ck_statutory_approval_reference_length CHECK (char_length(reference_no) <= 100),
    CONSTRAINT ck_statutory_approval_validity CHECK (valid_to IS NULL OR valid_to > valid_from),
    CONSTRAINT ck_statutory_approval_scope_type CHECK (scope_type IN ('institution', 'programme')),
    CONSTRAINT ck_statutory_approval_scope_match CHECK (
        (scope_type = 'institution' AND programme_id IS NULL)
        OR (scope_type = 'programme' AND programme_id IS NOT NULL)
    ),
    CONSTRAINT ck_statutory_approval_conditions_length CHECK (conditions_text IS NULL OR char_length(conditions_text) <= 10000),
    CONSTRAINT ck_statutory_approval_status CHECK (status IN ('current', 'expired', 'withdrawn', 'draft')),
    CONSTRAINT uq_statutory_approval_type_authority_reference UNIQUE (approval_type, authority, reference_no)
);
ALTER TABLE core.statutory_approval OWNER TO owner_core;

CREATE INDEX ix_statutory_approval_type_valid_to ON core.statutory_approval (approval_type, valid_to);
CREATE INDEX ix_statutory_approval_programme ON core.statutory_approval (programme_id);
CREATE INDEX ix_statutory_approval_document ON core.statutory_approval (document_version_id);
CREATE INDEX ix_statutory_approval_created_by ON core.statutory_approval (created_by);
CREATE INDEX ix_statutory_approval_updated_by ON core.statutory_approval (updated_by);

CREATE TABLE core.affiliation_record (
    affiliation_record_id uuid       NOT NULL DEFAULT gen_random_uuid(),
    programme_id         uuid        NOT NULL,  -- TODO(OD-12): FK added in W1b
    academic_year_id     uuid        NOT NULL,
    statutory_approval_id uuid       NULL,
    intake_approved      integer     NOT NULL DEFAULT 0,
    intake_admitted      integer     NULL,
    affiliation_status   text        NOT NULL DEFAULT 'pending',
    conditions_text      text        NULL,
    order_reference      text        NULL,
    created_at           timestamptz NOT NULL DEFAULT now(),
    created_by           uuid        NULL,
    updated_at           timestamptz NOT NULL DEFAULT now(),
    updated_by           uuid        NULL,
    row_version          integer     NOT NULL DEFAULT 1,
    CONSTRAINT pk_affiliation_record PRIMARY KEY (affiliation_record_id),
    CONSTRAINT fk_affiliation_record_academic_year FOREIGN KEY (academic_year_id)
        REFERENCES core.academic_year (academic_year_id) ON DELETE RESTRICT,
    CONSTRAINT fk_affiliation_record_statutory_approval FOREIGN KEY (statutory_approval_id)
        REFERENCES core.statutory_approval (statutory_approval_id) ON DELETE RESTRICT,
    CONSTRAINT fk_affiliation_record_created_by FOREIGN KEY (created_by)
        REFERENCES iam.identity_account (account_id) ON DELETE RESTRICT,
    CONSTRAINT fk_affiliation_record_updated_by FOREIGN KEY (updated_by)
        REFERENCES iam.identity_account (account_id) ON DELETE RESTRICT,
    CONSTRAINT ck_affiliation_record_intake_approved CHECK (intake_approved >= 0),
    CONSTRAINT ck_affiliation_record_intake_admitted CHECK (intake_admitted IS NULL OR intake_admitted >= 0),
    CONSTRAINT ck_affiliation_record_status CHECK (affiliation_status IN ('approved', 'conditional', 'withdrawn', 'pending')),
    CONSTRAINT ck_affiliation_record_conditions_length CHECK (conditions_text IS NULL OR char_length(conditions_text) <= 10000),
    CONSTRAINT ck_affiliation_record_order_reference_length CHECK (order_reference IS NULL OR char_length(order_reference) <= 100),
    CONSTRAINT uq_affiliation_record_programme_year UNIQUE (programme_id, academic_year_id)
);
ALTER TABLE core.affiliation_record OWNER TO owner_core;

CREATE INDEX ix_affiliation_record_year ON core.affiliation_record (academic_year_id);
CREATE INDEX ix_affiliation_record_programme ON core.affiliation_record (programme_id);
CREATE INDEX ix_affiliation_record_statutory_approval ON core.affiliation_record (statutory_approval_id);
CREATE INDEX ix_affiliation_record_created_by ON core.affiliation_record (created_by);
CREATE INDEX ix_affiliation_record_updated_by ON core.affiliation_record (updated_by);

CREATE TABLE core.academic_calendar (
    academic_calendar_id uuid        NOT NULL DEFAULT gen_random_uuid(),
    term_id              uuid        NOT NULL,
    version_no           integer     NOT NULL DEFAULT 1,
    status               text        NOT NULL DEFAULT 'draft',
    approved_by          uuid        NULL,
    approved_at          timestamptz NULL,
    change_note          text        NULL,
    source_document_version_id uuid  NULL,
    created_at           timestamptz NOT NULL DEFAULT now(),
    created_by           uuid        NULL,
    updated_at           timestamptz NOT NULL DEFAULT now(),
    updated_by           uuid        NULL,
    row_version          integer     NOT NULL DEFAULT 1,
    CONSTRAINT pk_academic_calendar PRIMARY KEY (academic_calendar_id),
    CONSTRAINT fk_academic_calendar_term FOREIGN KEY (term_id)
        REFERENCES core.term (term_id) ON DELETE RESTRICT,
    CONSTRAINT fk_academic_calendar_approved_by FOREIGN KEY (approved_by)
        REFERENCES iam.person (person_id) ON DELETE RESTRICT,
    CONSTRAINT fk_academic_calendar_source_document FOREIGN KEY (source_document_version_id)
        REFERENCES doc.document_version (document_version_id) ON DELETE RESTRICT,
    CONSTRAINT fk_academic_calendar_created_by FOREIGN KEY (created_by)
        REFERENCES iam.identity_account (account_id) ON DELETE RESTRICT,
    CONSTRAINT fk_academic_calendar_updated_by FOREIGN KEY (updated_by)
        REFERENCES iam.identity_account (account_id) ON DELETE RESTRICT,
    CONSTRAINT ck_academic_calendar_version_no CHECK (version_no >= 1),
    CONSTRAINT ck_academic_calendar_status CHECK (status IN ('draft', 'provisional', 'approved', 'superseded')),
    CONSTRAINT ck_academic_calendar_change_note_length CHECK (change_note IS NULL OR char_length(change_note) <= 2000),
    CONSTRAINT uq_academic_calendar_term_version UNIQUE (term_id, version_no)
);
ALTER TABLE core.academic_calendar OWNER TO owner_core;

CREATE UNIQUE INDEX uq_academic_calendar_approved_per_term
    ON core.academic_calendar (term_id) WHERE status = 'approved';
CREATE INDEX ix_academic_calendar_term_status ON core.academic_calendar (term_id, status);
CREATE INDEX ix_academic_calendar_approved_by ON core.academic_calendar (approved_by);
CREATE INDEX ix_academic_calendar_source_document ON core.academic_calendar (source_document_version_id);
CREATE INDEX ix_academic_calendar_created_by ON core.academic_calendar (created_by);
CREATE INDEX ix_academic_calendar_updated_by ON core.academic_calendar (updated_by);

CREATE TABLE core.calendar_milestone (
    calendar_milestone_id uuid       NOT NULL DEFAULT gen_random_uuid(),
    academic_calendar_id uuid        NOT NULL,
    milestone_code       text        NOT NULL,
    label                text        NOT NULL,
    planned_start        date        NULL,
    planned_end          date        NULL,
    actual_start         date        NULL,
    actual_end           date        NULL,
    applies_to_json      jsonb       NULL DEFAULT '{}',
    status               text        NOT NULL DEFAULT 'planned',
    created_at           timestamptz NOT NULL DEFAULT now(),
    created_by           uuid        NULL,
    updated_at           timestamptz NOT NULL DEFAULT now(),
    updated_by           uuid        NULL,
    row_version          integer     NOT NULL DEFAULT 1,
    CONSTRAINT pk_calendar_milestone PRIMARY KEY (calendar_milestone_id),
    CONSTRAINT fk_calendar_milestone_calendar FOREIGN KEY (academic_calendar_id)
        REFERENCES core.academic_calendar (academic_calendar_id) ON DELETE RESTRICT,
    CONSTRAINT fk_calendar_milestone_created_by FOREIGN KEY (created_by)
        REFERENCES iam.identity_account (account_id) ON DELETE RESTRICT,
    CONSTRAINT fk_calendar_milestone_updated_by FOREIGN KEY (updated_by)
        REFERENCES iam.identity_account (account_id) ON DELETE RESTRICT,
    CONSTRAINT ck_calendar_milestone_code_length CHECK (char_length(milestone_code) <= 50),
    CONSTRAINT ck_calendar_milestone_label_length CHECK (char_length(label) <= 200),
    CONSTRAINT ck_calendar_milestone_planned_dates CHECK (planned_end IS NULL OR planned_start IS NULL OR planned_end >= planned_start),
    CONSTRAINT ck_calendar_milestone_actual_dates CHECK (actual_end IS NULL OR actual_start IS NULL OR actual_end >= actual_start),
    CONSTRAINT ck_calendar_milestone_status CHECK (status IN ('planned', 'in_progress', 'completed', 'cancelled')),
    CONSTRAINT uq_calendar_milestone_code UNIQUE (academic_calendar_id, milestone_code)
);
ALTER TABLE core.calendar_milestone OWNER TO owner_core;

CREATE INDEX ix_calendar_milestone_planned_start ON core.calendar_milestone (academic_calendar_id, planned_start);
CREATE INDEX ix_calendar_milestone_created_by ON core.calendar_milestone (created_by);
CREATE INDEX ix_calendar_milestone_updated_by ON core.calendar_milestone (updated_by);

-- ===========================================================================
-- 6. Policy engine -- POL-01 .. POL-07
-- ===========================================================================

CREATE TABLE policy.rule (
    rule_id              uuid        NOT NULL DEFAULT gen_random_uuid(),
    rule_code            text        NOT NULL,
    title                text        NOT NULL,
    domain               text        NOT NULL,
    description          text        NULL,
    owner_role_code      text        NULL,
    created_at           timestamptz NOT NULL DEFAULT now(),
    created_by           uuid        NULL,
    updated_at           timestamptz NOT NULL DEFAULT now(),
    updated_by           uuid        NULL,
    row_version          integer     NOT NULL DEFAULT 1,
    CONSTRAINT pk_rule PRIMARY KEY (rule_id),
    CONSTRAINT fk_rule_created_by FOREIGN KEY (created_by)
        REFERENCES iam.identity_account (account_id) ON DELETE RESTRICT,
    CONSTRAINT fk_rule_updated_by FOREIGN KEY (updated_by)
        REFERENCES iam.identity_account (account_id) ON DELETE RESTRICT,
    CONSTRAINT ck_rule_code_length CHECK (char_length(rule_code) <= 30),
    CONSTRAINT ck_rule_title_length CHECK (char_length(title) <= 200),
    CONSTRAINT ck_rule_domain CHECK (domain IN ('admission', 'registration', 'attendance', 'assessment', 'passing', 'progression', 'supplementary', 'degree', 'correction', 'ppr', 'mar', 'discipline', 'placement', 'service', 'calendar', 'examination', 'affiliation', 'other')),
    CONSTRAINT ck_rule_description_length CHECK (description IS NULL OR char_length(description) <= 2000),
    CONSTRAINT ck_rule_owner_role_code_length CHECK (owner_role_code IS NULL OR char_length(owner_role_code) <= 50)
);
ALTER TABLE policy.rule OWNER TO owner_policy;

CREATE UNIQUE INDEX uq_rule_code_lower ON policy.rule (lower(rule_code));
CREATE INDEX ix_rule_domain ON policy.rule (domain);
CREATE INDEX ix_rule_created_by ON policy.rule (created_by);
CREATE INDEX ix_rule_updated_by ON policy.rule (updated_by);

CREATE TABLE policy.rule_version (
    rule_version_id      uuid        NOT NULL DEFAULT gen_random_uuid(),
    rule_id              uuid        NOT NULL,
    version_no           integer     NOT NULL DEFAULT 1,
    statement            text        NOT NULL,
    authority            text        NOT NULL DEFAULT 'BCREC',
    parameters_json      jsonb       NOT NULL DEFAULT '{}',
    effective_from       date        NOT NULL,
    effective_to         date        NULL,
    status               text        NOT NULL DEFAULT 'Draft',
    confidence           text        NOT NULL DEFAULT 'Medium',
    confidence_reason    text        NULL,
    source_document_version_id uuid   NULL,
    source_locator       text        NULL,
    approval_reference   text        NULL,
    supersedes_version_id uuid       NULL,
    approved_by          uuid        NULL,
    created_at           timestamptz NOT NULL DEFAULT now(),
    created_by           uuid        NULL,
    CONSTRAINT pk_rule_version PRIMARY KEY (rule_version_id),
    CONSTRAINT fk_rule_version_rule FOREIGN KEY (rule_id)
        REFERENCES policy.rule (rule_id) ON DELETE RESTRICT,
    CONSTRAINT fk_rule_version_source_document FOREIGN KEY (source_document_version_id)
        REFERENCES doc.document_version (document_version_id) ON DELETE RESTRICT,
    CONSTRAINT fk_rule_version_supersedes FOREIGN KEY (supersedes_version_id)
        REFERENCES policy.rule_version (rule_version_id) ON DELETE RESTRICT,
    CONSTRAINT fk_rule_version_approved_by FOREIGN KEY (approved_by)
        REFERENCES iam.person (person_id) ON DELETE RESTRICT,
    CONSTRAINT ck_rule_version_version_no CHECK (version_no >= 1),
    CONSTRAINT ck_rule_version_statement_length CHECK (char_length(statement) <= 5000),
    CONSTRAINT ck_rule_version_authority CHECK (authority IN ('BCREC', 'MAKAUT', 'AICTE', 'other')),
    CONSTRAINT ck_rule_version_effective_dates CHECK (effective_to IS NULL OR effective_to >= effective_from),
    CONSTRAINT ck_rule_version_status CHECK (status IN ('Current', 'Draft', 'Historical', 'Superseded', 'Disputed', 'Unknown')),
    CONSTRAINT ck_rule_version_confidence CHECK (confidence IN ('High', 'Medium', 'Low')),
    CONSTRAINT ck_rule_version_confidence_reason_length CHECK (confidence_reason IS NULL OR char_length(confidence_reason) <= 1000),
    CONSTRAINT ck_rule_version_source_locator_length CHECK (source_locator IS NULL OR char_length(source_locator) <= 300),
    CONSTRAINT ck_rule_version_approval_reference_length CHECK (approval_reference IS NULL OR char_length(approval_reference) <= 200),
    CONSTRAINT ck_rule_version_not_own_supersedes CHECK (supersedes_version_id IS NULL OR supersedes_version_id <> rule_version_id),
    CONSTRAINT uq_rule_version_rule_no UNIQUE (rule_id, version_no)
);
ALTER TABLE policy.rule_version OWNER TO owner_policy;

CREATE INDEX ix_rule_version_rule_no_desc ON policy.rule_version (rule_id, version_no DESC);
CREATE INDEX ix_rule_version_status ON policy.rule_version (status);
CREATE INDEX ix_rule_version_effective_from ON policy.rule_version (effective_from);
CREATE INDEX ix_rule_version_source_document ON policy.rule_version (source_document_version_id);
CREATE INDEX ix_rule_version_supersedes ON policy.rule_version (supersedes_version_id);
CREATE INDEX ix_rule_version_approved_by ON policy.rule_version (approved_by);

CREATE TABLE policy.rule_scope (
    rule_scope_id        uuid        NOT NULL DEFAULT gen_random_uuid(),
    rule_version_id      uuid        NOT NULL,
    scope_type           text        NOT NULL DEFAULT 'institution',
    institution_id       uuid        NULL,
    programme_id         uuid        NULL,  -- TODO(OD-12): FK added in W1b
    batch_id             uuid        NULL,  -- TODO(OD-12): FK added in W1b
    term_id              uuid        NULL,
    course_type          text        NULL,
    student_category     text        NULL,
    created_at           timestamptz NOT NULL DEFAULT now(),
    created_by           uuid        NULL,
    updated_at           timestamptz NOT NULL DEFAULT now(),
    updated_by           uuid        NULL,
    row_version          integer     NOT NULL DEFAULT 1,
    CONSTRAINT pk_rule_scope PRIMARY KEY (rule_scope_id),
    CONSTRAINT fk_rule_scope_rule_version FOREIGN KEY (rule_version_id)
        REFERENCES policy.rule_version (rule_version_id) ON DELETE RESTRICT,
    CONSTRAINT fk_rule_scope_institution FOREIGN KEY (institution_id)
        REFERENCES core.institution (institution_id) ON DELETE RESTRICT,
    CONSTRAINT fk_rule_scope_term FOREIGN KEY (term_id)
        REFERENCES core.term (term_id) ON DELETE RESTRICT,
    CONSTRAINT fk_rule_scope_created_by FOREIGN KEY (created_by)
        REFERENCES iam.identity_account (account_id) ON DELETE RESTRICT,
    CONSTRAINT fk_rule_scope_updated_by FOREIGN KEY (updated_by)
        REFERENCES iam.identity_account (account_id) ON DELETE RESTRICT,
    CONSTRAINT ck_rule_scope_scope_type CHECK (scope_type IN ('institution', 'programme', 'batch', 'term', 'course_type', 'student_category')),
    CONSTRAINT ck_rule_scope_course_type CHECK (course_type IS NULL OR course_type IN ('theory', 'practical', 'sessional', 'project', 'mooc', 'non_credit')),
    CONSTRAINT ck_rule_scope_student_category_length CHECK (student_category IS NULL OR char_length(student_category) <= 50),
    CONSTRAINT ck_rule_scope_scope_match CHECK (
        (scope_type = 'institution' AND institution_id IS NOT NULL AND programme_id IS NULL AND batch_id IS NULL AND term_id IS NULL)
        OR (scope_type = 'programme' AND programme_id IS NOT NULL AND institution_id IS NULL AND batch_id IS NULL AND term_id IS NULL)
        OR (scope_type = 'batch' AND batch_id IS NOT NULL AND institution_id IS NULL AND programme_id IS NULL AND term_id IS NULL)
        OR (scope_type = 'term' AND term_id IS NOT NULL AND institution_id IS NULL AND programme_id IS NULL AND batch_id IS NULL)
        OR (scope_type = 'course_type' AND num_nonnulls(institution_id, programme_id, batch_id, term_id) = 0 AND course_type IS NOT NULL)
        OR (scope_type = 'student_category' AND num_nonnulls(institution_id, programme_id, batch_id, term_id) = 0 AND student_category IS NOT NULL)
    ),
    CONSTRAINT uq_rule_scope UNIQUE NULLS NOT DISTINCT (rule_version_id, scope_type, institution_id, programme_id, batch_id, term_id, course_type, student_category)
);
ALTER TABLE policy.rule_scope OWNER TO owner_policy;

CREATE INDEX ix_rule_scope_rule_version ON policy.rule_scope (rule_version_id);
CREATE INDEX ix_rule_scope_batch ON policy.rule_scope (batch_id);
CREATE INDEX ix_rule_scope_programme ON policy.rule_scope (programme_id);
CREATE INDEX ix_rule_scope_institution ON policy.rule_scope (institution_id);
CREATE INDEX ix_rule_scope_term ON policy.rule_scope (term_id);
CREATE INDEX ix_rule_scope_created_by ON policy.rule_scope (created_by);
CREATE INDEX ix_rule_scope_updated_by ON policy.rule_scope (updated_by);

CREATE TABLE policy.rule_conflict (
    rule_conflict_id     uuid        NOT NULL DEFAULT gen_random_uuid(),
    rule_version_a_id    uuid        NOT NULL,
    rule_version_b_id    uuid        NOT NULL,
    resolution_rule_version_id uuid  NULL,
    description          text        NOT NULL,
    status               text        NOT NULL DEFAULT 'open',
    resolution_note      text        NULL,
    resolved_by          uuid        NULL,
    resolved_at          timestamptz NULL,
    created_at           timestamptz NOT NULL DEFAULT now(),
    created_by           uuid        NULL,
    updated_at           timestamptz NOT NULL DEFAULT now(),
    updated_by           uuid        NULL,
    row_version          integer     NOT NULL DEFAULT 1,
    CONSTRAINT pk_rule_conflict PRIMARY KEY (rule_conflict_id),
    CONSTRAINT fk_rule_conflict_a FOREIGN KEY (rule_version_a_id)
        REFERENCES policy.rule_version (rule_version_id) ON DELETE RESTRICT,
    CONSTRAINT fk_rule_conflict_b FOREIGN KEY (rule_version_b_id)
        REFERENCES policy.rule_version (rule_version_id) ON DELETE RESTRICT,
    CONSTRAINT fk_rule_conflict_resolution FOREIGN KEY (resolution_rule_version_id)
        REFERENCES policy.rule_version (rule_version_id) ON DELETE RESTRICT,
    CONSTRAINT fk_rule_conflict_resolved_by FOREIGN KEY (resolved_by)
        REFERENCES iam.person (person_id) ON DELETE RESTRICT,
    CONSTRAINT fk_rule_conflict_created_by FOREIGN KEY (created_by)
        REFERENCES iam.identity_account (account_id) ON DELETE RESTRICT,
    CONSTRAINT fk_rule_conflict_updated_by FOREIGN KEY (updated_by)
        REFERENCES iam.identity_account (account_id) ON DELETE RESTRICT,
    CONSTRAINT ck_rule_conflict_distinct CHECK (rule_version_a_id <> rule_version_b_id),
    CONSTRAINT ck_rule_conflict_ordered CHECK (rule_version_a_id < rule_version_b_id),
    CONSTRAINT ck_rule_conflict_description_length CHECK (char_length(description) <= 2000),
    CONSTRAINT ck_rule_conflict_status CHECK (status IN ('open', 'resolved', 'accepted_risk')),
    CONSTRAINT ck_rule_conflict_note_length CHECK (resolution_note IS NULL OR char_length(resolution_note) <= 2000),
    CONSTRAINT ck_rule_conflict_resolved_after_created CHECK (resolved_at IS NULL OR resolved_at >= created_at),
    CONSTRAINT uq_rule_conflict_pair UNIQUE (rule_version_a_id, rule_version_b_id)
);
ALTER TABLE policy.rule_conflict OWNER TO owner_policy;

CREATE INDEX ix_rule_conflict_status ON policy.rule_conflict (status);
CREATE INDEX ix_rule_conflict_b ON policy.rule_conflict (rule_version_b_id);
CREATE INDEX ix_rule_conflict_resolution ON policy.rule_conflict (resolution_rule_version_id);
CREATE INDEX ix_rule_conflict_resolved_by ON policy.rule_conflict (resolved_by);
CREATE INDEX ix_rule_conflict_created_by ON policy.rule_conflict (created_by);
CREATE INDEX ix_rule_conflict_updated_by ON policy.rule_conflict (updated_by);

CREATE TABLE policy.policy_bundle (
    policy_bundle_id     uuid        NOT NULL DEFAULT gen_random_uuid(),
    bundle_code          text        NOT NULL,
    name                 text        NOT NULL,
    domain               text        NOT NULL,
    description          text        NULL,
    owner_role_code      text        NULL,
    created_at           timestamptz NOT NULL DEFAULT now(),
    created_by           uuid        NULL,
    updated_at           timestamptz NOT NULL DEFAULT now(),
    updated_by           uuid        NULL,
    row_version          integer     NOT NULL DEFAULT 1,
    CONSTRAINT pk_policy_bundle PRIMARY KEY (policy_bundle_id),
    CONSTRAINT fk_policy_bundle_created_by FOREIGN KEY (created_by)
        REFERENCES iam.identity_account (account_id) ON DELETE RESTRICT,
    CONSTRAINT fk_policy_bundle_updated_by FOREIGN KEY (updated_by)
        REFERENCES iam.identity_account (account_id) ON DELETE RESTRICT,
    CONSTRAINT ck_policy_bundle_code_length CHECK (char_length(bundle_code) <= 50),
    CONSTRAINT ck_policy_bundle_name_length CHECK (char_length(name) <= 200),
    CONSTRAINT ck_policy_bundle_domain CHECK (domain IN ('admission', 'registration', 'attendance', 'assessment', 'passing', 'progression', 'supplementary', 'degree', 'correction', 'ppr', 'mar', 'discipline', 'placement', 'service', 'calendar', 'examination', 'affiliation', 'other')),
    CONSTRAINT ck_policy_bundle_description_length CHECK (description IS NULL OR char_length(description) <= 2000),
    CONSTRAINT ck_policy_bundle_owner_role_code_length CHECK (owner_role_code IS NULL OR char_length(owner_role_code) <= 50)
);
ALTER TABLE policy.policy_bundle OWNER TO owner_policy;

CREATE UNIQUE INDEX uq_policy_bundle_code_lower ON policy.policy_bundle (lower(bundle_code));
CREATE INDEX ix_policy_bundle_created_by ON policy.policy_bundle (created_by);
CREATE INDEX ix_policy_bundle_updated_by ON policy.policy_bundle (updated_by);

CREATE TABLE policy.policy_bundle_version (
    policy_bundle_version_id uuid    NOT NULL DEFAULT gen_random_uuid(),
    policy_bundle_id     uuid        NOT NULL,
    version_no           integer     NOT NULL DEFAULT 1,
    effective_from       date        NOT NULL,
    effective_to         date        NULL,
    status               text        NOT NULL DEFAULT 'draft',
    approval_reference   text        NULL,
    approved_by          uuid        NULL,
    created_at           timestamptz NOT NULL DEFAULT now(),
    created_by           uuid        NULL,
    CONSTRAINT pk_policy_bundle_version PRIMARY KEY (policy_bundle_version_id),
    CONSTRAINT fk_policy_bundle_version_bundle FOREIGN KEY (policy_bundle_id)
        REFERENCES policy.policy_bundle (policy_bundle_id) ON DELETE RESTRICT,
    CONSTRAINT fk_policy_bundle_version_approved_by FOREIGN KEY (approved_by)
        REFERENCES iam.person (person_id) ON DELETE RESTRICT,
    CONSTRAINT ck_policy_bundle_version_version_no CHECK (version_no >= 1),
    CONSTRAINT ck_policy_bundle_version_effective_dates CHECK (effective_to IS NULL OR effective_to >= effective_from),
    CONSTRAINT ck_policy_bundle_version_status CHECK (status IN ('draft', 'approved', 'active', 'superseded')),
    CONSTRAINT ck_policy_bundle_version_approval_reference_length CHECK (approval_reference IS NULL OR char_length(approval_reference) <= 200),
    CONSTRAINT uq_policy_bundle_version_no UNIQUE (policy_bundle_id, version_no)
);
ALTER TABLE policy.policy_bundle_version OWNER TO owner_policy;

CREATE INDEX ix_policy_bundle_version_no_desc ON policy.policy_bundle_version (policy_bundle_id, version_no DESC);
CREATE INDEX ix_policy_bundle_version_status ON policy.policy_bundle_version (status);
CREATE INDEX ix_policy_bundle_version_approved_by ON policy.policy_bundle_version (approved_by);

CREATE TABLE policy.policy_bundle_member (
    policy_bundle_member_id uuid     NOT NULL DEFAULT gen_random_uuid(),
    policy_bundle_version_id uuid    NOT NULL,
    rule_version_id      uuid        NOT NULL,
    sequence_no          smallint    NOT NULL DEFAULT 1,
    is_required          boolean     NOT NULL DEFAULT true,
    created_at           timestamptz NOT NULL DEFAULT now(),
    created_by           uuid        NULL,
    CONSTRAINT pk_policy_bundle_member PRIMARY KEY (policy_bundle_member_id),
    CONSTRAINT fk_policy_bundle_member_bundle_version FOREIGN KEY (policy_bundle_version_id)
        REFERENCES policy.policy_bundle_version (policy_bundle_version_id) ON DELETE RESTRICT,
    CONSTRAINT fk_policy_bundle_member_rule_version FOREIGN KEY (rule_version_id)
        REFERENCES policy.rule_version (rule_version_id) ON DELETE RESTRICT,
    CONSTRAINT ck_policy_bundle_member_sequence CHECK (sequence_no >= 1),
    CONSTRAINT uq_policy_bundle_member UNIQUE (policy_bundle_version_id, rule_version_id)
);
ALTER TABLE policy.policy_bundle_member OWNER TO owner_policy;

CREATE INDEX ix_policy_bundle_member_rule_version ON policy.policy_bundle_member (rule_version_id);

-- ===========================================================================
-- 7. Integration control -- INT-02 .. INT-09
-- ===========================================================================

CREATE TABLE integration.external_system (
    external_system_id   uuid        NOT NULL DEFAULT gen_random_uuid(),
    code                 text        NOT NULL,
    name                 text        NOT NULL,
    system_type          text        NOT NULL,
    base_url             text        NULL,
    owner_org_unit_id    uuid        NULL,
    status               text        NOT NULL DEFAULT 'planned',
    capabilities_json    jsonb       NULL DEFAULT '{}',
    last_health_at       timestamptz NULL,
    created_at           timestamptz NOT NULL DEFAULT now(),
    created_by           uuid        NULL,
    updated_at           timestamptz NOT NULL DEFAULT now(),
    updated_by           uuid        NULL,
    row_version          integer     NOT NULL DEFAULT 1,
    CONSTRAINT pk_external_system PRIMARY KEY (external_system_id),
    CONSTRAINT fk_external_system_owner_org_unit FOREIGN KEY (owner_org_unit_id)
        REFERENCES core.org_unit (org_unit_id) ON DELETE RESTRICT,
    CONSTRAINT fk_external_system_created_by FOREIGN KEY (created_by)
        REFERENCES iam.identity_account (account_id) ON DELETE RESTRICT,
    CONSTRAINT fk_external_system_updated_by FOREIGN KEY (updated_by)
        REFERENCES iam.identity_account (account_id) ON DELETE RESTRICT,
    CONSTRAINT ck_external_system_code_length CHECK (char_length(code) <= 50),
    CONSTRAINT ck_external_system_name_length CHECK (char_length(name) <= 200),
    CONSTRAINT ck_external_system_type CHECK (system_type IN ('college_erp', 'makaut_portal', 'payment_gateway', 'email', 'sms', 'lms', 'idp', 'nad', 'other')),
    CONSTRAINT ck_external_system_base_url_length CHECK (base_url IS NULL OR char_length(base_url) <= 500),
    CONSTRAINT ck_external_system_status CHECK (status IN ('active', 'inactive', 'planned', 'retired'))
);
ALTER TABLE integration.external_system OWNER TO owner_integration;

CREATE UNIQUE INDEX uq_external_system_code_lower ON integration.external_system (lower(code));
CREATE INDEX ix_external_system_type_status ON integration.external_system (system_type, status);
CREATE INDEX ix_external_system_owner_org_unit ON integration.external_system (owner_org_unit_id);
CREATE INDEX ix_external_system_created_by ON integration.external_system (created_by);
CREATE INDEX ix_external_system_updated_by ON integration.external_system (updated_by);

CREATE TABLE integration.external_id_mapping (
    external_id_mapping_id uuid      NOT NULL DEFAULT gen_random_uuid(),
    entity_type_code     text        NOT NULL,
    external_system_id   uuid        NOT NULL,
    internal_id          uuid        NOT NULL,
    external_id          text        NOT NULL,
    is_primary           boolean     NOT NULL DEFAULT true,
    valid_from           date        NOT NULL DEFAULT current_date,
    valid_to             date        NULL,
    confidence           text        NOT NULL DEFAULT 'high',
    created_at           timestamptz NOT NULL DEFAULT now(),
    created_by           uuid        NULL,
    updated_at           timestamptz NOT NULL DEFAULT now(),
    updated_by           uuid        NULL,
    row_version          integer     NOT NULL DEFAULT 1,
    CONSTRAINT pk_external_id_mapping PRIMARY KEY (external_id_mapping_id),
    CONSTRAINT fk_external_id_mapping_entity_type FOREIGN KEY (entity_type_code)
        REFERENCES integration.entity_type (entity_type_code) ON DELETE RESTRICT,
    CONSTRAINT fk_external_id_mapping_system FOREIGN KEY (external_system_id)
        REFERENCES integration.external_system (external_system_id) ON DELETE RESTRICT,
    CONSTRAINT fk_external_id_mapping_created_by FOREIGN KEY (created_by)
        REFERENCES iam.identity_account (account_id) ON DELETE RESTRICT,
    CONSTRAINT fk_external_id_mapping_updated_by FOREIGN KEY (updated_by)
        REFERENCES iam.identity_account (account_id) ON DELETE RESTRICT,
    CONSTRAINT ck_external_id_mapping_external_id_length CHECK (char_length(external_id) <= 200),
    CONSTRAINT ck_external_id_mapping_validity CHECK (valid_to IS NULL OR valid_to > valid_from),
    CONSTRAINT ck_external_id_mapping_confidence CHECK (confidence IN ('high', 'medium', 'low')),
    CONSTRAINT uq_external_id_mapping_internal UNIQUE (entity_type_code, internal_id, external_system_id, valid_from)
);
ALTER TABLE integration.external_id_mapping OWNER TO owner_integration;

CREATE UNIQUE INDEX uq_external_id_mapping_current_external
    ON integration.external_id_mapping (entity_type_code, external_id, external_system_id)
    WHERE valid_to IS NULL;
CREATE INDEX ix_external_id_mapping_entity_internal ON integration.external_id_mapping (entity_type_code, internal_id);
CREATE INDEX ix_external_id_mapping_system_external ON integration.external_id_mapping (external_system_id, external_id);
CREATE INDEX ix_external_id_mapping_created_by ON integration.external_id_mapping (created_by);
CREATE INDEX ix_external_id_mapping_updated_by ON integration.external_id_mapping (updated_by);

CREATE TABLE integration.source_of_truth_rule (
    source_of_truth_rule_id uuid     NOT NULL DEFAULT gen_random_uuid(),
    entity_type_code     text        NOT NULL,
    field_name           text        NOT NULL,
    authoritative_system_id uuid    NULL,
    fallback_system_id   uuid        NULL,
    conflict_policy      text        NOT NULL DEFAULT 'manual_review',
    effective_from       date        NOT NULL,
    effective_to         date        NULL,
    status               text        NOT NULL DEFAULT 'draft',
    approved_by          uuid        NULL,
    created_at           timestamptz NOT NULL DEFAULT now(),
    created_by           uuid        NULL,
    updated_at           timestamptz NOT NULL DEFAULT now(),
    updated_by           uuid        NULL,
    row_version          integer     NOT NULL DEFAULT 1,
    CONSTRAINT pk_source_of_truth_rule PRIMARY KEY (source_of_truth_rule_id),
    CONSTRAINT fk_source_of_truth_rule_entity_type FOREIGN KEY (entity_type_code)
        REFERENCES integration.entity_type (entity_type_code) ON DELETE RESTRICT,
    CONSTRAINT fk_source_of_truth_rule_authoritative FOREIGN KEY (authoritative_system_id)
        REFERENCES integration.external_system (external_system_id) ON DELETE RESTRICT,
    CONSTRAINT fk_source_of_truth_rule_fallback FOREIGN KEY (fallback_system_id)
        REFERENCES integration.external_system (external_system_id) ON DELETE RESTRICT,
    CONSTRAINT fk_source_of_truth_rule_approved_by FOREIGN KEY (approved_by)
        REFERENCES iam.person (person_id) ON DELETE RESTRICT,
    CONSTRAINT fk_source_of_truth_rule_created_by FOREIGN KEY (created_by)
        REFERENCES iam.identity_account (account_id) ON DELETE RESTRICT,
    CONSTRAINT fk_source_of_truth_rule_updated_by FOREIGN KEY (updated_by)
        REFERENCES iam.identity_account (account_id) ON DELETE RESTRICT,
    CONSTRAINT ck_source_of_truth_rule_field_length CHECK (char_length(field_name) <= 100),
    CONSTRAINT ck_source_of_truth_rule_systems_differ CHECK (authoritative_system_id IS NULL OR fallback_system_id IS NULL OR authoritative_system_id <> fallback_system_id),
    CONSTRAINT ck_source_of_truth_rule_conflict_policy CHECK (conflict_policy IN ('authoritative_wins', 'manual_review', 'newest_wins')),
    CONSTRAINT ck_source_of_truth_rule_effective_dates CHECK (effective_to IS NULL OR effective_to >= effective_from),
    CONSTRAINT ck_source_of_truth_rule_status CHECK (status IN ('draft', 'active', 'superseded')),
    CONSTRAINT uq_source_of_truth_rule_field_date UNIQUE (entity_type_code, field_name, effective_from)
);
ALTER TABLE integration.source_of_truth_rule OWNER TO owner_integration;

CREATE INDEX ix_source_of_truth_rule_field ON integration.source_of_truth_rule (entity_type_code, field_name);
CREATE INDEX ix_source_of_truth_rule_authoritative ON integration.source_of_truth_rule (authoritative_system_id);
CREATE INDEX ix_source_of_truth_rule_fallback ON integration.source_of_truth_rule (fallback_system_id);
CREATE INDEX ix_source_of_truth_rule_approved_by ON integration.source_of_truth_rule (approved_by);
CREATE INDEX ix_source_of_truth_rule_created_by ON integration.source_of_truth_rule (created_by);
CREATE INDEX ix_source_of_truth_rule_updated_by ON integration.source_of_truth_rule (updated_by);

CREATE TABLE integration.sync_run (
    sync_run_id          uuid        NOT NULL DEFAULT gen_random_uuid(),
    external_system_id   uuid        NOT NULL,
    entity_type_code     text        NOT NULL,
    direction            text        NOT NULL DEFAULT 'pull',
    mode                 text        NOT NULL DEFAULT 'incremental',
    started_at           timestamptz NOT NULL DEFAULT now(),
    finished_at          timestamptz NULL,
    status               text        NOT NULL DEFAULT 'running',
    records_read         integer     NOT NULL DEFAULT 0,
    records_written      integer     NOT NULL DEFAULT 0,
    records_failed       integer     NOT NULL DEFAULT 0,
    cursor_before        text        NULL,
    cursor_after         text        NULL,
    error_summary        text        NULL,
    adapter_version      text        NULL,
    operator_person_id   uuid        NULL,
    created_at           timestamptz NOT NULL DEFAULT now(),
    created_by           uuid        NULL,
    CONSTRAINT pk_sync_run PRIMARY KEY (sync_run_id),
    CONSTRAINT fk_sync_run_system FOREIGN KEY (external_system_id)
        REFERENCES integration.external_system (external_system_id) ON DELETE RESTRICT,
    CONSTRAINT fk_sync_run_entity_type FOREIGN KEY (entity_type_code)
        REFERENCES integration.entity_type (entity_type_code) ON DELETE RESTRICT,
    CONSTRAINT fk_sync_run_operator FOREIGN KEY (operator_person_id)
        REFERENCES iam.person (person_id) ON DELETE RESTRICT,
    CONSTRAINT ck_sync_run_direction CHECK (direction IN ('pull', 'push', 'bidirectional')),
    CONSTRAINT ck_sync_run_mode CHECK (mode IN ('full', 'incremental', 'event', 'manual_file')),
    CONSTRAINT ck_sync_run_finished_after_start CHECK (finished_at IS NULL OR finished_at >= started_at),
    CONSTRAINT ck_sync_run_status CHECK (status IN ('running', 'completed', 'completed_with_errors', 'failed', 'aborted')),
    CONSTRAINT ck_sync_run_records_read CHECK (records_read >= 0),
    CONSTRAINT ck_sync_run_records_written CHECK (records_written >= 0),
    CONSTRAINT ck_sync_run_records_failed CHECK (records_failed >= 0),
    CONSTRAINT ck_sync_run_cursor_before_length CHECK (cursor_before IS NULL OR char_length(cursor_before) <= 500),
    CONSTRAINT ck_sync_run_cursor_after_length CHECK (cursor_after IS NULL OR char_length(cursor_after) <= 500),
    CONSTRAINT ck_sync_run_error_summary_length CHECK (error_summary IS NULL OR char_length(error_summary) <= 5000),
    CONSTRAINT ck_sync_run_adapter_version_length CHECK (adapter_version IS NULL OR char_length(adapter_version) <= 50)
);
ALTER TABLE integration.sync_run OWNER TO owner_integration;

CREATE INDEX ix_sync_run_system_started_desc ON integration.sync_run (external_system_id, started_at DESC);
CREATE INDEX ix_sync_run_status ON integration.sync_run (status);
CREATE INDEX ix_sync_run_entity_type ON integration.sync_run (entity_type_code);
CREATE INDEX ix_sync_run_operator ON integration.sync_run (operator_person_id);

CREATE TABLE integration.sync_record (
    sync_record_id       uuid        NOT NULL DEFAULT gen_random_uuid(),
    sync_run_id          uuid        NOT NULL,
    entity_type_code     text        NOT NULL,
    internal_id          uuid        NULL,
    external_id          text        NULL,
    operation            text        NOT NULL,
    outcome              text        NOT NULL,
    error_code           text        NULL,
    error_detail         text        NULL,
    created_at           timestamptz NOT NULL DEFAULT now(),
    created_by           uuid        NULL,
    CONSTRAINT pk_sync_record PRIMARY KEY (sync_record_id),
    CONSTRAINT fk_sync_record_run FOREIGN KEY (sync_run_id)
        REFERENCES integration.sync_run (sync_run_id) ON DELETE RESTRICT,
    CONSTRAINT fk_sync_record_entity_type FOREIGN KEY (entity_type_code)
        REFERENCES integration.entity_type (entity_type_code) ON DELETE RESTRICT,
    CONSTRAINT ck_sync_record_operation CHECK (operation IN ('insert', 'update', 'skip', 'delete', 'conflict')),
    CONSTRAINT ck_sync_record_outcome CHECK (outcome IN ('success', 'failed')),
    CONSTRAINT ck_sync_record_external_id_length CHECK (external_id IS NULL OR char_length(external_id) <= 200),
    CONSTRAINT ck_sync_record_error_code_length CHECK (error_code IS NULL OR char_length(error_code) <= 50),
    CONSTRAINT ck_sync_record_error_detail_length CHECK (error_detail IS NULL OR char_length(error_detail) <= 2000),
    CONSTRAINT uq_sync_record UNIQUE (sync_run_id, entity_type_code, internal_id, operation, external_id)
);
ALTER TABLE integration.sync_record OWNER TO owner_integration;

CREATE INDEX ix_sync_record_run_outcome ON integration.sync_record (sync_run_id, outcome);
CREATE INDEX ix_sync_record_entity_internal ON integration.sync_record (entity_type_code, internal_id);

CREATE TABLE integration.sync_conflict (
    sync_conflict_id     uuid        NOT NULL DEFAULT gen_random_uuid(),
    sync_run_id          uuid        NOT NULL,
    entity_type_code     text        NOT NULL,
    internal_id          uuid        NULL,
    field_name           text        NOT NULL,
    internal_value_json  jsonb       NULL,
    external_value_json  jsonb       NULL,
    source_of_truth_rule_id uuid    NULL,
    status               text        NOT NULL DEFAULT 'open',
    resolution           text        NOT NULL DEFAULT 'none',
    resolution_note      text        NULL,
    resolved_by          uuid        NULL,
    resolved_at          timestamptz NULL,
    created_at           timestamptz NOT NULL DEFAULT now(),
    created_by           uuid        NULL,
    updated_at           timestamptz NOT NULL DEFAULT now(),
    updated_by           uuid        NULL,
    row_version          integer     NOT NULL DEFAULT 1,
    CONSTRAINT pk_sync_conflict PRIMARY KEY (sync_conflict_id),
    CONSTRAINT fk_sync_conflict_run FOREIGN KEY (sync_run_id)
        REFERENCES integration.sync_run (sync_run_id) ON DELETE RESTRICT,
    CONSTRAINT fk_sync_conflict_entity_type FOREIGN KEY (entity_type_code)
        REFERENCES integration.entity_type (entity_type_code) ON DELETE RESTRICT,
    CONSTRAINT fk_sync_conflict_source_rule FOREIGN KEY (source_of_truth_rule_id)
        REFERENCES integration.source_of_truth_rule (source_of_truth_rule_id) ON DELETE RESTRICT,
    CONSTRAINT fk_sync_conflict_resolved_by FOREIGN KEY (resolved_by)
        REFERENCES iam.person (person_id) ON DELETE RESTRICT,
    CONSTRAINT fk_sync_conflict_created_by FOREIGN KEY (created_by)
        REFERENCES iam.identity_account (account_id) ON DELETE RESTRICT,
    CONSTRAINT fk_sync_conflict_updated_by FOREIGN KEY (updated_by)
        REFERENCES iam.identity_account (account_id) ON DELETE RESTRICT,
    CONSTRAINT ck_sync_conflict_field_length CHECK (char_length(field_name) <= 100),
    CONSTRAINT ck_sync_conflict_status CHECK (status IN ('open', 'resolved', 'deferred')),
    CONSTRAINT ck_sync_conflict_resolution CHECK (resolution IN ('use_internal', 'use_external', 'manual', 'none')),
    CONSTRAINT ck_sync_conflict_note_length CHECK (resolution_note IS NULL OR char_length(resolution_note) <= 2000),
    CONSTRAINT ck_sync_conflict_resolved_after_created CHECK (resolved_at IS NULL OR resolved_at >= created_at),
    CONSTRAINT ck_sync_conflict_resolved_has_resolver CHECK (status <> 'resolved' OR resolved_by IS NOT NULL)
);
ALTER TABLE integration.sync_conflict OWNER TO owner_integration;

CREATE INDEX ix_sync_conflict_status_created ON integration.sync_conflict (status, created_at);
CREATE INDEX ix_sync_conflict_entity_internal ON integration.sync_conflict (entity_type_code, internal_id);
CREATE INDEX ix_sync_conflict_run ON integration.sync_conflict (sync_run_id);
CREATE INDEX ix_sync_conflict_source_rule ON integration.sync_conflict (source_of_truth_rule_id);
CREATE INDEX ix_sync_conflict_resolved_by ON integration.sync_conflict (resolved_by);
CREATE INDEX ix_sync_conflict_created_by ON integration.sync_conflict (created_by);
CREATE INDEX ix_sync_conflict_updated_by ON integration.sync_conflict (updated_by);

CREATE TABLE integration.record_provenance (
    record_provenance_id uuid        NOT NULL DEFAULT gen_random_uuid(),
    entity_type_code     text        NOT NULL,
    internal_id          uuid        NOT NULL,
    field_name           text        NOT NULL,
    source_system_id     uuid        NULL,
    sync_run_id          uuid        NULL,
    observed_at          timestamptz NOT NULL DEFAULT now(),
    value_hash           text        NOT NULL,
    is_human_override    boolean     NOT NULL DEFAULT false,
    created_at           timestamptz NOT NULL DEFAULT now(),
    created_by           uuid        NULL,
    updated_at           timestamptz NOT NULL DEFAULT now(),
    updated_by           uuid        NULL,
    row_version          integer     NOT NULL DEFAULT 1,
    CONSTRAINT pk_record_provenance PRIMARY KEY (record_provenance_id),
    CONSTRAINT fk_record_provenance_entity_type FOREIGN KEY (entity_type_code)
        REFERENCES integration.entity_type (entity_type_code) ON DELETE RESTRICT,
    CONSTRAINT fk_record_provenance_source_system FOREIGN KEY (source_system_id)
        REFERENCES integration.external_system (external_system_id) ON DELETE RESTRICT,
    CONSTRAINT fk_record_provenance_sync_run FOREIGN KEY (sync_run_id)
        REFERENCES integration.sync_run (sync_run_id) ON DELETE RESTRICT,
    CONSTRAINT fk_record_provenance_created_by FOREIGN KEY (created_by)
        REFERENCES iam.identity_account (account_id) ON DELETE RESTRICT,
    CONSTRAINT fk_record_provenance_updated_by FOREIGN KEY (updated_by)
        REFERENCES iam.identity_account (account_id) ON DELETE RESTRICT,
    CONSTRAINT ck_record_provenance_field_length CHECK (char_length(field_name) <= 100),
    CONSTRAINT ck_record_provenance_value_hash_length CHECK (length(value_hash) = 64),
    CONSTRAINT uq_record_provenance_field UNIQUE (entity_type_code, internal_id, field_name)
);
ALTER TABLE integration.record_provenance OWNER TO owner_integration;

CREATE INDEX ix_record_provenance_entity_internal ON integration.record_provenance (entity_type_code, internal_id);
CREATE INDEX ix_record_provenance_observed_at ON integration.record_provenance (observed_at);
CREATE INDEX ix_record_provenance_source_system ON integration.record_provenance (source_system_id);
CREATE INDEX ix_record_provenance_sync_run ON integration.record_provenance (sync_run_id);
CREATE INDEX ix_record_provenance_created_by ON integration.record_provenance (created_by);
CREATE INDEX ix_record_provenance_updated_by ON integration.record_provenance (updated_by);

CREATE TABLE integration.outbox_event (
    outbox_event_id      uuid        NOT NULL DEFAULT gen_random_uuid(),
    aggregate_type       text        NOT NULL,
    aggregate_id         uuid        NOT NULL,
    event_type           text        NOT NULL,
    payload_json         jsonb       NOT NULL DEFAULT '{}',
    occurred_at          timestamptz NOT NULL DEFAULT now(),
    published_at         timestamptz NULL,
    status               text        NOT NULL DEFAULT 'pending',
    retry_count          integer     NOT NULL DEFAULT 0,
    created_at           timestamptz NOT NULL DEFAULT now(),
    created_by           uuid        NULL,
    CONSTRAINT pk_outbox_event PRIMARY KEY (outbox_event_id),
    CONSTRAINT ck_outbox_event_aggregate_type_length CHECK (char_length(aggregate_type) <= 60),
    CONSTRAINT ck_outbox_event_event_type_length CHECK (char_length(event_type) <= 100),
    CONSTRAINT ck_outbox_event_published_after_occurred CHECK (published_at IS NULL OR published_at >= occurred_at),
    CONSTRAINT ck_outbox_event_status CHECK (status IN ('pending', 'published', 'failed', 'dead_letter')),
    CONSTRAINT ck_outbox_event_retry_count CHECK (retry_count >= 0)
);
ALTER TABLE integration.outbox_event OWNER TO owner_integration;

CREATE INDEX ix_outbox_event_pending ON integration.outbox_event (occurred_at) WHERE status = 'pending';
CREATE INDEX ix_outbox_event_aggregate ON integration.outbox_event (aggregate_type, aggregate_id);

-- ===========================================================================
-- 8. Audit and operations -- OPS-01 .. OPS-03 (OPS-04 created earlier)
-- ===========================================================================

CREATE TABLE ops.audit_event (
    audit_event_id       uuid        NOT NULL DEFAULT gen_random_uuid(),
    occurred_at          timestamptz NOT NULL DEFAULT now(),
    actor_person_id      uuid        NULL,
    actor_account_id     uuid        NULL,
    role_assignment_id   uuid        NULL,
    action               text        NOT NULL,
    entity_type_code     text        NULL,
    entity_id            uuid        NULL,
    before_json          jsonb       NULL,
    after_json           jsonb       NULL,
    reason               text        NULL,
    correlation_id       text        NULL,
    source_channel       text        NULL,
    ip_address           inet        NULL,
    user_agent           text        NULL,
    prev_hash            text        NULL,
    record_hash          text        NOT NULL,
    created_at           timestamptz NOT NULL DEFAULT now(),
    created_by           uuid        NULL,
    CONSTRAINT pk_audit_event PRIMARY KEY (audit_event_id),
    CONSTRAINT fk_audit_event_actor_person FOREIGN KEY (actor_person_id)
        REFERENCES iam.person (person_id) ON DELETE RESTRICT,
    CONSTRAINT fk_audit_event_actor_account FOREIGN KEY (actor_account_id)
        REFERENCES iam.identity_account (account_id) ON DELETE RESTRICT,
    CONSTRAINT fk_audit_event_role_assignment FOREIGN KEY (role_assignment_id)
        REFERENCES iam.role_assignment (role_assignment_id) ON DELETE RESTRICT,
    CONSTRAINT fk_audit_event_entity_type FOREIGN KEY (entity_type_code)
        REFERENCES integration.entity_type (entity_type_code) ON DELETE RESTRICT,
    CONSTRAINT ck_audit_event_action_length CHECK (char_length(action) <= 100),
    CONSTRAINT ck_audit_event_reason_length CHECK (reason IS NULL OR char_length(reason) <= 2000),
    CONSTRAINT ck_audit_event_correlation_id_length CHECK (correlation_id IS NULL OR char_length(correlation_id) <= 100),
    CONSTRAINT ck_audit_event_source_channel CHECK (source_channel IS NULL OR source_channel IN ('web', 'api', 'batch', 'integration', 'system')),
    CONSTRAINT ck_audit_event_user_agent_length CHECK (user_agent IS NULL OR char_length(user_agent) <= 500),
    CONSTRAINT ck_audit_event_prev_hash_length CHECK (prev_hash IS NULL OR length(prev_hash) IN (0, 64)),
    CONSTRAINT ck_audit_event_record_hash_length CHECK (length(record_hash) = 64)
);
ALTER TABLE ops.audit_event OWNER TO owner_ops;

CREATE INDEX ix_audit_event_occurred_desc ON ops.audit_event (occurred_at DESC);
CREATE INDEX ix_audit_event_entity ON ops.audit_event (entity_type_code, entity_id);
CREATE INDEX ix_audit_event_actor_occurred_desc ON ops.audit_event (actor_person_id, occurred_at DESC);
CREATE INDEX ix_audit_event_correlation ON ops.audit_event (correlation_id);
CREATE INDEX ix_audit_event_actor_account ON ops.audit_event (actor_account_id);
CREATE INDEX ix_audit_event_role_assignment ON ops.audit_event (role_assignment_id);

CREATE TABLE ops.data_quality_issue (
    data_quality_issue_id uuid       NOT NULL DEFAULT gen_random_uuid(),
    entity_type_code     text        NOT NULL,
    record_id            uuid        NULL,
    issue_type           text        NOT NULL,
    severity             text        NOT NULL DEFAULT 'medium',
    description          text        NOT NULL,
    detected_at          timestamptz NOT NULL DEFAULT now(),
    status               text        NOT NULL DEFAULT 'open',
    assigned_to_person_id uuid       NULL,
    resolution           text        NULL,
    resolved_at          timestamptz NULL,
    created_at           timestamptz NOT NULL DEFAULT now(),
    created_by           uuid        NULL,
    updated_at           timestamptz NOT NULL DEFAULT now(),
    updated_by           uuid        NULL,
    row_version          integer     NOT NULL DEFAULT 1,
    CONSTRAINT pk_data_quality_issue PRIMARY KEY (data_quality_issue_id),
    CONSTRAINT fk_data_quality_issue_entity_type FOREIGN KEY (entity_type_code)
        REFERENCES integration.entity_type (entity_type_code) ON DELETE RESTRICT,
    CONSTRAINT fk_data_quality_issue_assigned_to FOREIGN KEY (assigned_to_person_id)
        REFERENCES iam.person (person_id) ON DELETE RESTRICT,
    CONSTRAINT fk_data_quality_issue_created_by FOREIGN KEY (created_by)
        REFERENCES iam.identity_account (account_id) ON DELETE RESTRICT,
    CONSTRAINT fk_data_quality_issue_updated_by FOREIGN KEY (updated_by)
        REFERENCES iam.identity_account (account_id) ON DELETE RESTRICT,
    CONSTRAINT ck_data_quality_issue_type_length CHECK (char_length(issue_type) <= 50),
    CONSTRAINT ck_data_quality_issue_severity CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    CONSTRAINT ck_data_quality_issue_description_length CHECK (char_length(description) <= 2000),
    CONSTRAINT ck_data_quality_issue_status CHECK (status IN ('open', 'investigating', 'resolved', 'accepted', 'deferred')),
    CONSTRAINT ck_data_quality_issue_resolution_length CHECK (resolution IS NULL OR char_length(resolution) <= 2000),
    CONSTRAINT ck_data_quality_issue_resolved_after_detected CHECK (resolved_at IS NULL OR resolved_at >= detected_at)
);
ALTER TABLE ops.data_quality_issue OWNER TO owner_ops;

CREATE INDEX ix_data_quality_issue_status_severity ON ops.data_quality_issue (status, severity);
CREATE INDEX ix_data_quality_issue_entity_record ON ops.data_quality_issue (entity_type_code, record_id);
CREATE INDEX ix_data_quality_issue_assigned_to ON ops.data_quality_issue (assigned_to_person_id);
CREATE INDEX ix_data_quality_issue_created_by ON ops.data_quality_issue (created_by);
CREATE INDEX ix_data_quality_issue_updated_by ON ops.data_quality_issue (updated_by);

CREATE TABLE ops.break_glass_grant (
    break_glass_grant_id uuid        NOT NULL DEFAULT gen_random_uuid(),
    person_id            uuid        NOT NULL,
    role_assignment_id   uuid        NULL,
    reason               text        NOT NULL,
    starts_at            timestamptz NOT NULL DEFAULT now(),
    expires_at           timestamptz NOT NULL,
    scope_description    text        NULL,
    status               text        NOT NULL DEFAULT 'requested',
    approved_by          uuid        NULL,
    reviewed_by          uuid        NULL,
    reviewed_at          timestamptz NULL,
    created_at           timestamptz NOT NULL DEFAULT now(),
    created_by           uuid        NULL,
    updated_at           timestamptz NOT NULL DEFAULT now(),
    updated_by           uuid        NULL,
    row_version          integer     NOT NULL DEFAULT 1,
    CONSTRAINT pk_break_glass_grant PRIMARY KEY (break_glass_grant_id),
    CONSTRAINT fk_break_glass_grant_person FOREIGN KEY (person_id)
        REFERENCES iam.person (person_id) ON DELETE RESTRICT,
    CONSTRAINT fk_break_glass_grant_role_assignment FOREIGN KEY (role_assignment_id)
        REFERENCES iam.role_assignment (role_assignment_id) ON DELETE RESTRICT,
    CONSTRAINT fk_break_glass_grant_approved_by FOREIGN KEY (approved_by)
        REFERENCES iam.person (person_id) ON DELETE RESTRICT,
    CONSTRAINT fk_break_glass_grant_reviewed_by FOREIGN KEY (reviewed_by)
        REFERENCES iam.person (person_id) ON DELETE RESTRICT,
    CONSTRAINT fk_break_glass_grant_created_by FOREIGN KEY (created_by)
        REFERENCES iam.identity_account (account_id) ON DELETE RESTRICT,
    CONSTRAINT fk_break_glass_grant_updated_by FOREIGN KEY (updated_by)
        REFERENCES iam.identity_account (account_id) ON DELETE RESTRICT,
    CONSTRAINT ck_break_glass_grant_reason_length CHECK (char_length(reason) BETWEEN 10 AND 2000),
    CONSTRAINT ck_break_glass_grant_expiry CHECK (expires_at > starts_at),
    CONSTRAINT ck_break_glass_grant_scope_length CHECK (scope_description IS NULL OR char_length(scope_description) <= 1000),
    CONSTRAINT ck_break_glass_grant_status CHECK (status IN ('requested', 'active', 'expired', 'revoked', 'reviewed'))
);
ALTER TABLE ops.break_glass_grant OWNER TO owner_ops;

CREATE INDEX ix_break_glass_grant_status_expires ON ops.break_glass_grant (status, expires_at);
CREATE INDEX ix_break_glass_grant_person ON ops.break_glass_grant (person_id);
CREATE INDEX ix_break_glass_grant_role_assignment ON ops.break_glass_grant (role_assignment_id);
CREATE INDEX ix_break_glass_grant_approved_by ON ops.break_glass_grant (approved_by);
CREATE INDEX ix_break_glass_grant_reviewed_by ON ops.break_glass_grant (reviewed_by);
CREATE INDEX ix_break_glass_grant_created_by ON ops.break_glass_grant (created_by);
CREATE INDEX ix_break_glass_grant_updated_by ON ops.break_glass_grant (updated_by);

-- ===========================================================================
-- 9. Documented triggers
-- ===========================================================================

-- IAM-01: date_of_birth < current_date is enforced by a trigger, as stated in
-- the dictionary (a CHECK would freeze a non-immutable expression).
CREATE OR REPLACE FUNCTION iam.check_person_date_of_birth()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.date_of_birth IS NOT NULL AND NEW.date_of_birth >= current_date THEN
        RAISE EXCEPTION 'iam.person: date_of_birth must be before current_date';
    END IF;
    RETURN NEW;
END;
$$;
ALTER FUNCTION iam.check_person_date_of_birth() OWNER TO owner_iam;

CREATE TRIGGER trg_person_date_of_birth
    BEFORE INSERT OR UPDATE OF date_of_birth ON iam.person
    FOR EACH ROW EXECUTE FUNCTION iam.check_person_date_of_birth();

-- IAM-04: a system role cannot be deleted.
CREATE OR REPLACE FUNCTION iam.reject_system_role_delete()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF OLD.is_system_role THEN
        RAISE EXCEPTION 'iam.role: system role % cannot be deleted', OLD.role_code;
    END IF;
    RETURN OLD;
END;
$$;
ALTER FUNCTION iam.reject_system_role_delete() OWNER TO owner_iam;

CREATE TRIGGER trg_role_protect_system
    BEFORE DELETE ON iam.role
    FOR EACH ROW EXECUTE FUNCTION iam.reject_system_role_delete();

-- GOV-03: materialized path and hierarchy-cycle check.
CREATE OR REPLACE FUNCTION core.set_org_unit_path()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    parent_path text;
    ancestor    uuid;
    new_path    text;
BEGIN
    IF NEW.parent_org_unit_id IS NULL THEN
        new_path := NEW.code;
    ELSE
        IF NEW.parent_org_unit_id = NEW.org_unit_id THEN
            RAISE EXCEPTION 'core.org_unit: an org unit cannot be its own parent';
        END IF;

        ancestor := NEW.parent_org_unit_id;
        WHILE ancestor IS NOT NULL LOOP
            IF ancestor = NEW.org_unit_id THEN
                RAISE EXCEPTION 'core.org_unit: cycle detected while setting parent %', NEW.parent_org_unit_id;
            END IF;
            SELECT parent_org_unit_id INTO ancestor
            FROM core.org_unit
            WHERE org_unit_id = ancestor;
        END LOOP;

        SELECT path INTO parent_path
        FROM core.org_unit
        WHERE org_unit_id = NEW.parent_org_unit_id;

        IF parent_path IS NULL THEN
            RAISE EXCEPTION 'core.org_unit: parent % has no materialized path', NEW.parent_org_unit_id;
        END IF;
        new_path := parent_path || '/' || NEW.code;
    END IF;

    NEW.path := new_path;
    RETURN NEW;
END;
$$;
ALTER FUNCTION core.set_org_unit_path() OWNER TO owner_core;

CREATE TRIGGER trg_org_unit_path
    BEFORE INSERT OR UPDATE OF parent_org_unit_id, code ON core.org_unit
    FOR EACH ROW EXECUTE FUNCTION core.set_org_unit_path();

CREATE OR REPLACE FUNCTION core.refresh_org_unit_descendant_paths()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.path IS DISTINCT FROM OLD.path THEN
        UPDATE core.org_unit
        SET path = NEW.path || substr(path, char_length(OLD.path) + 1)
        WHERE starts_with(path, OLD.path || '/');
    END IF;
    RETURN NULL;
END;
$$;
ALTER FUNCTION core.refresh_org_unit_descendant_paths() OWNER TO owner_core;

CREATE TRIGGER trg_org_unit_descendant_paths
    AFTER UPDATE OF path ON core.org_unit
    FOR EACH ROW EXECUTE FUNCTION core.refresh_org_unit_descendant_paths();

-- POL-02: a Draft rule can never be marked Current without an approval reference.
CREATE OR REPLACE FUNCTION policy.check_rule_version_current()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.status = 'Current' AND NEW.approval_reference IS NULL THEN
        RAISE EXCEPTION 'policy.rule_version: status Current requires approval_reference';
    END IF;
    RETURN NEW;
END;
$$;
ALTER FUNCTION policy.check_rule_version_current() OWNER TO owner_policy;

CREATE TRIGGER trg_rule_version_current
    BEFORE INSERT OR UPDATE ON policy.rule_version
    FOR EACH ROW EXECUTE FUNCTION policy.check_rule_version_current();

-- POL-02: once a rule version is referenced by a bundle it becomes immutable.
CREATE OR REPLACE FUNCTION policy.seal_referenced_rule_version()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM policy.policy_bundle_member
        WHERE rule_version_id = OLD.rule_version_id
    ) THEN
        RAISE EXCEPTION 'policy.rule_version: version % is referenced by a bundle and is immutable', OLD.rule_version_id;
    END IF;
    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END;
$$;
ALTER FUNCTION policy.seal_referenced_rule_version() OWNER TO owner_policy;

CREATE TRIGGER trg_rule_version_seal
    BEFORE UPDATE OR DELETE ON policy.rule_version
    FOR EACH ROW EXECUTE FUNCTION policy.seal_referenced_rule_version();

-- DOC-02: a version is sealed once it becomes active or superseded.
CREATE OR REPLACE FUNCTION doc.seal_document_version()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF OLD.status IN ('active', 'superseded') THEN
        RAISE EXCEPTION 'doc.document_version: version % is sealed', OLD.document_version_id;
    END IF;
    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END;
$$;
ALTER FUNCTION doc.seal_document_version() OWNER TO owner_doc;

CREATE TRIGGER trg_document_version_seal
    BEFORE UPDATE OR DELETE ON doc.document_version
    FOR EACH ROW EXECUTE FUNCTION doc.seal_document_version();

-- POL-06 and INT-05/INT-06: append-only operational records.
CREATE OR REPLACE FUNCTION ops.reject_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION '%.% is append-only', TG_TABLE_SCHEMA, TG_TABLE_NAME;
END;
$$;
ALTER FUNCTION ops.reject_mutation() OWNER TO owner_ops;

CREATE TRIGGER trg_policy_bundle_version_append_only
    BEFORE UPDATE OR DELETE ON policy.policy_bundle_version
    FOR EACH ROW EXECUTE FUNCTION ops.reject_mutation();

CREATE TRIGGER trg_sync_record_append_only
    BEFORE UPDATE OR DELETE ON integration.sync_record
    FOR EACH ROW EXECUTE FUNCTION ops.reject_mutation();

CREATE TRIGGER trg_audit_event_append_only
    BEFORE UPDATE OR DELETE ON ops.audit_event
    FOR EACH ROW EXECUTE FUNCTION ops.reject_mutation();

-- INT-05: a sync run becomes immutable once it reaches a terminal state.
CREATE OR REPLACE FUNCTION integration.seal_sync_run()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF OLD.status IN ('completed', 'completed_with_errors', 'failed', 'aborted') THEN
        RAISE EXCEPTION 'integration.sync_run: run % is sealed', OLD.sync_run_id;
    END IF;
    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END;
$$;
ALTER FUNCTION integration.seal_sync_run() OWNER TO owner_integration;

CREATE TRIGGER trg_sync_run_seal
    BEFORE UPDATE OR DELETE ON integration.sync_run
    FOR EACH ROW EXECUTE FUNCTION integration.seal_sync_run();

