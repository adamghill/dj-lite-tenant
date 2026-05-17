# Changelog

## 0.1.0

Forked from [django-sqlite-user-db](https://github.com/MessyComposer/django-sqlite-user-db) by MessyComposer.

### Architecture Changes

- Switched from `asgiref.local.Local` to `contextvars.ContextVar`
- Replaced per-model `_is_user_model` flags with settings-driven routing via `DJ_LITE_TENANT["APPS"]`
- Changed DB alias detection from naming convention to path-based
- Added `slugify()` sanitization for tenant PKs in filenames
- Custom `dj_lite_tenant.backends.sqlite3` backend wired through `dj-lite`'s `sqlite_config`
- Template-based DB provisioning is now opt-in (`USE_DATABASE_TEMPLATE=True`); default is direct `migrate`

### New Features

- Cross-database `ATTACH DATABASE` — runs automatically on tenant connections for SQL joins
- ORM dot-schema support — custom backend enables `Meta.db_table = "catalog.tablename"`
- `ATTACHMENTS` — configurable dict of named databases to attach to every tenant connection
- `DB_NAME_PATTERN` — configurable filename pattern for tenant DB files
- `TENANT_MODEL` — custom tenant model support (defaults to Django's auth user model)
- `TENANT_ID_CALLABLE` — pluggable callable for extracting the tenant PK from a request
- `TENANT_SETTINGS` — configurable per-tenant DB connection options
- LRU connection registry with `MAX_OPEN_CONNECTIONS` eviction per worker
- Auto-create tenant DB on first request; auto-delete on model delete (`DELETE_TENANT_DB_ON_DELETE`)
- `post_migrate` signal clears template cache when tenant app migrations are applied
- `tenant_db()` context manager for out-of-request use (management commands, async tasks)
- `SwitchTenantAdmin` mixin — adds Switch/Reset buttons in the Django admin list view
- `set_tenant` / `unset_tenant` views + URL patterns for superuser tenant impersonation
- `create_tenant_db <pk>` management command — creates and migrates a specific tenant DB
- `migrate_tenant_dbs` management command — applies migrations to all existing tenant DBs
