# Database implementation — BCREC Central

This directory holds the implementation artefacts for the approved database
design in [`docs/architecture/database-design-v1/`](../docs/architecture/database-design-v1/).
The approved design documents are never modified here.

**Scope:** the 108 Initial Release entities only. Future/Blocked entities are
not implemented. `knowledge.embedding` is blocked by OD-06 and is not created.

---

## 1. Layout

```text
database/
  migrate.py                 forward-only SQL migration runner
  requirements.txt           psycopg[binary] + pytest
  config/
    .env.example             local configuration template (no credentials)
    postgresql.conf.snippet  required server settings
  migrations/
    0001_bootstrap.sql       extensions, schemas, roles, migration history
  seeds/                     reference data (added with the waves that need it)
  tests/                     automated schema and integrity tests
```

`public.schema_migration` is infrastructure metadata. It is deliberately
excluded from the 108-entity comparison and from every design count.

---

## 2. Start PostgreSQL 16

The repository already defines a `postgres:16-alpine` service:

```powershell
docker compose up -d postgres
docker compose exec postgres pg_isready -U bcrec -d bcrec
```

`docker-compose.yml` starts PostgreSQL with `shared_preload_libraries=pg_stat_statements`,
which the approved design requires. A native installation must apply
[`config/postgresql.conf.snippet`](config/postgresql.conf.snippet) and restart.

No destructive command is part of this workflow. The compose volume is preserved.

---

## 3. Configure the connection

```powershell
Copy-Item database/config/.env.example database/config/.env
# edit database/config/.env with local values
```

`database/config/.env` is git-ignored (`*.env`). Never commit a real credential.

The implementation uses a dedicated development database, `bcrec_central`, so
the legacy `bcrec` database is untouched:

```powershell
docker compose exec postgres psql -U bcrec -d postgres -c "CREATE DATABASE bcrec_central OWNER bcrec;"
```

---

## 4. Install the client and apply migrations

```powershell
python -m pip install -r database/requirements.txt
python database/migrate.py status
python database/migrate.py apply
python database/migrate.py verify
```

Development-only role passwords (never in production, never in source control):

```powershell
$env:BCREC_ROLE_PASSWORD = "choose-a-local-password"
python database/migrate.py provision-dev-roles
```

---

## 5. Run the tests

```powershell
python -m pytest database/tests -q
```

The suite creates a dedicated database named `bcrec_test_<suffix>` from
`BCREC_MAINTENANCE_URL`, applies every migration to it, validates the result,
and drops only that test database. The fixture refuses to create or drop any
database whose name does not start with `bcrec_test_`.

---

## 6. Migration rules

- Forward-only. There are no down-migrations. A failed file aborts its
  transaction; recovery is restore plus fix-forward.
- One logical change per file, named `NNNN_description.sql`.
- An applied file is immutable. The runner stores a SHA-256 checksum and refuses
  to run if a file changes after it was applied.
- One transaction per file. `CREATE INDEX CONCURRENTLY` and other
  non-transactional statements are not used on empty tables in this release.
- Schema objects are owned by `owner_<schema>`, not by a runtime role.
- A wave may reference only earlier waves. When a later dependency is
  unavoidable, the column is created in the earlier wave and the foreign key is
  added in the wave that creates the target (POSTGRES_ARCHITECTURE section 17.3,
  OD-12). The seven W1a → W1b references are staged this way.
- Seeds are data, never schema, and live in `seeds/`.
