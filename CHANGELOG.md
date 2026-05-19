# Changelog

## 0.2.0

- Shared databases now attach correctly when using in-memory SQLite (e.g. during tests)
- Improved runtime error messages for misconfigured settings via `typeguard`

## 0.1.0

Forked from [django-sqlite-user-db](https://github.com/MessyComposer/django-sqlite-user-db) by MessyComposer.

- Each tenant gets an isolated SQLite database, created automatically on first use
- Tenant routing is driven by `DJ_LITE_TENANT["APPS"]` — no per-model flags needed
- Cross-database queries work out of the box via `ATTACH DATABASE` and ORM dot-schema support (`Meta.db_table = "shared.tablename"`)
- Configurable via `ATTACHMENTS`, `DB_NAME_PATTERN`, `TENANT_MODEL`, `TENANT_ID_CALLABLE`, `TENANT_SETTINGS`, and `MAX_OPEN_CONNECTIONS`
- `USE_DATABASE_TEMPLATE` speeds up tenant provisioning by copying a pre-migrated template DB
- `tenant_db()` context manager for use outside of HTTP requests (management commands, async tasks)
- `SwitchTenantAdmin` mixin lets superusers switch tenant context from the Django admin
- `create_tenant_db` and `migrate_tenant_dbs` management commands for DB lifecycle management
