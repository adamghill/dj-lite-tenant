# django-sqlite-tenant

Per-user SQLite databases for Django, with optional cross-database `ATTACH` support and an ORM-compatible dot-schema backend.

> **Status:** Experimental. Not intended for production use yet.

Forked from [django-sqlite-user-db](https://github.com/MessyComposer/django-sqlite-user-db) by MessyComposer with substantial rewrites.

---

## Features

- Per-user SQLite database files, created on signup
- `contextvars`-based middleware (async-safe, no `asgiref` dependency)
- Settings-driven routing — no per-model flags required
- WAL / PRAGMA initialisation on new user DBs
- `ATTACH DATABASE` wired automatically on every user DB connection — enables raw SQL cross-DB joins
- Custom `DatabaseWrapper` backend: `Meta.db_table = "catalog.movie_movie"` routes ORM queries to the attached catalog DB
- `migrate_user_dbs` and `create_user_db` management commands
- Admin "Switch User" panel

---

## Installation

```bash
pip install django-sqlite-tenant
```

### `settings.py`

```python
INSTALLED_APPS = [
    ...
    "django_sqlite_tenant",
]

MIDDLEWARE = [
    ...
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django_sqlite_tenant.middleware.TenantDatabaseMiddleware",  # must follow auth middleware
    ...
]

DATABASE_ROUTERS = ["django_sqlite_tenant.routers.TenantDatabaseRouter"]

DJANGO_SQLITE_TENANT = {
    "DB_DIR": BASE_DIR / "db/users",        # where per-user .sqlite3 files are stored
    "APP_LABELS": {"myapp"},                 # app labels whose models go in per-user DBs
    "CATALOG_ALIAS": "default",             # shared DB to ATTACH on every user connection
    "CATALOG_ATTACH_NAME": "catalog",       # ATTACH alias used in SQL: catalog.tablename
    # Optional:
    # "SQLITE_INIT_COMMAND": "PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;",
    # "DB_NAME_PATTERN": "user_{user_id}.sqlite3",
    # "CONN_MAX_AGE": 600,          # v0.2: persistent connection TTL (seconds)
    # "MAX_OPEN_CONNECTIONS": 100,  # v0.2: LRU eviction threshold per worker
}
```

### Custom backend (for ORM dot-schema support)

To use `Meta.db_table = "catalog.tablename"` in your models so the ORM generates `"catalog"."tablename"` in SQL:

```python
# In DATABASES, set ENGINE for user DB aliases:
"ENGINE": "django_sqlite_tenant.backends.sqlite3"
```

---

## Cross-database raw SQL

Every user DB connection automatically runs `ATTACH 'path/to/default.sqlite3' AS catalog`. You can then write:

```python
from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("""
        SELECT m.title
        FROM catalog.movie_movie m
        JOIN movie_profile_watchlist w ON w.movie_id = m.id
        WHERE w.profile_id = %s
    """, [profile_id])
```

---

## Cross-database ORM queries

With the custom backend and `Meta.db_table = "catalog.movie_movie"` on your shared models, Django's ORM generates valid cross-DB SQL:

```python
Profile.objects.filter(watchlist__title__icontains="blade")
# → SELECT ... FROM "user_db"."movie_profile"
#   JOIN "catalog"."movie_movie" ON ...
```

---

## Out-of-request usage

```python
from django_sqlite_tenant.middleware import tenant_db

user = User.objects.get(pk=1)
with tenant_db(user):
    MyUserModel.objects.create(...)
```

---

## Management commands

```bash
python manage.py migrate_user_dbs       # apply migrations to all existing user DBs
python manage.py create_user_db <id>    # create/migrate a specific user's DB
```

---

## Admin panel

Register the mixin in your `admin.py`:

```python
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django_sqlite_tenant.admin import SwitchUserAdminMixin

@admin.register(User)
class UserAdmin(SwitchUserAdminMixin, BaseUserAdmin):
    pass
```

Add to `urls.py`:

```python
path("admin/", include("django_sqlite_tenant.urls", namespace="django_sqlite_tenant")),
```

---

## Known limitations & roadmap

- v0.2: Persistent connection pooling with LRU eviction (see `docs/plans/adr-001-connection-pooling.md`)
- v0.2: Async ASGI connection verification
- Connection handling is per-process; each gunicorn worker maintains its own connection set (correct and expected)
