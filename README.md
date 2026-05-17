# dj-lite-tenant

Per-user SQLite databases for Django for ultimate multi-tenant isolation.

> **Status:** Very experimental, but it works. Not intended for production use yet.

Forked from [django-sqlite-user-db](https://github.com/MessyComposer/django-sqlite-user-db) by MessyComposer.

---

## Features

- Per-user SQLite databases, created automatically for ultimate isolation
- Configurable settings for tenant databases (with performant defaults)
- Cross-database joins work with Django's ORM and raw SQL queries
- The correct tenant database is automatically used based on the current user
- Sync and async support
- Optional database template creation for fast tenant provisioning
- Django admin integration to access different user's database for superusers

## Installation

```bash
uv add dj-lite-tenant
```

OR

```bash
pip install dj-lite-tenant
```

### `settings.py`

```python
INSTALLED_APPS = [
    ...
    "dj_lite_tenant",
]

MIDDLEWARE = [
    ...
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "dj_lite_tenant.middleware.TenantDatabaseMiddleware",  # must follow auth middleware
    ...
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db/data.sqlite3",
    },
}

DATABASE_ROUTERS = ["dj_lite_tenant.routers.TenantDatabaseRouter"]

DJ_LITE_TENANT = {
    "DIR": BASE_DIR / "db/tenants",
    "APPS": {"app_label", "app_label.ModelName"},
    # Optional:
    # "ATTACHMENTS": {"default": "shared"},
    # "DB_NAME_PATTERN": "tenant_{tenant_pk}.sqlite3",
    # "DELETE_TENANT_DB_ON_DELETE": False,
    # "MAX_OPEN_CONNECTIONS": 100,
    # "TENANT_ID_CALLABLE": "dj_lite_tenant.middleware.get_tenant_pk_from_request",
    # "TENANT_MODEL": "app_label.ModelName",
    # "TENANT_SETTINGS": {
    #     "CONN_MAX_AGE": 0,
    #     "CONN_HEALTH_CHECKS": False,
    #     "TIME_ZONE": None,
    #     "AUTOCOMMIT": True,
    #     "ATOMIC_REQUESTS": False,
    #     "TEST": {"NAME": None},
    # },
    # "USE_DATABASE_TEMPLATE": False,
}
```

## Settings

### DIR

The directory where per-tenant SQLite databases are stored.

### APPS

Defines which apps or specific models should be stored in tenant databases. Values are app labels (`"notes"`) or `"app.Model"` strings (`"catalog.Product"`). Models not explicitly named will be stored in the shared DB.

```python
DJ_LITE_TENANT = {
    ...
    "APPS": {
        "notes",           # all models from the 'notes' app
        "catalog.Product", # only Product model from 'catalog' app
        "catalog.Order",   # only Order model from 'catalog' app
        # Other models in 'catalog' (e.g., catalog.Category) stay in the shared DB
    },
}
```

### TENANT_MODEL

An `"app_label.ModelName"` string identifying the model used as the tenant. Defaults to `None`, which uses Django's `get_user_model()`.

### TENANT_ID_CALLABLE

A dotted path to a `callable(request) -> str | None` that extracts the tenant identifier from the request. Defaults to `"dj_lite_tenant.middleware.get_tenant_pk_from_request"`.

### ATTACHMENTS

Maps Django DB aliases to [SQLite `ATTACH` aliases](https://sqlite.org/lang_attach.html). This allows tenant models to reference models in the shared database.

### DB_NAME_PATTERN

Pattern for tenant database filenames. Defaults to `"tenant_{tenant_pk}.sqlite3"`.

### MAX_OPEN_CONNECTIONS

LRU eviction threshold per worker process. Defaults to `100`.

### USE_DATABASE_TEMPLATE

When `True`, copies the first tenant DB as a template instead of using running migrations when a new tenant database is created. Defaults to `False`. See [Enabling database template](#enabling-database-template) for details.

### DELETE_TENANT_DB_ON_DELETE

When `True`, automatically deletes the tenant DB file when the tenant instance is deleted. Defaults to `False`. See [Tenant database cleanup](#tenant-database-cleanup) for details.

### TENANT_SETTINGS

Additional settings for the tenant database. More details in [Django documentation](https://docs.djangoproject.com/en/stable/ref/settings/#databases).

```python
DJ_LITE_TENANT = {
    ...
    "TENANT_SETTINGS": {
        "CONN_MAX_AGE": 600,
    },
}
```

## Cross-database ORM queries

Models in the tenant database can have a ForeignKey to a model in the shared database.

```{note}
Setting `db_constraint=False` is not required, however it does make it explicit for others that SQLite cannot enforce FKs across attached databases.
```

```python
# models.py

from django.conf import settings
from django.db import models

class Note(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        db_constraint=False,  # FK lives in shared DB; tenant DB can't enforce it
    )
    text = models.TextField()
```

Django's router automatically directs queries to the right database, so foreign key traversal works transparently:

```python
# views.py

def all_notes(request):
    # If a user is logged in, the middleware already activated the tenant DB, so this query hits the current user's DB
    notes = Note.objects.all()

    # note.user hits the default DB automatically
    return JsonResponse(
        {
            "notes": [
                {"text": note.text, "user": note.user.username} for note in notes
            ]
        }
    )
```

## Using tenant databases outside of the request lifecycle

The middleware automatically activates the correct tenant database during HTTP requests, but for out-of-request contexts you can use the `tenant_db` context manager:

```python
from dj_lite_tenant.middleware import tenant_db
from django.contrib.auth import get_user_model
from django.core.tasks import task


@task
def process_user_notes(user_pk):
    user = get_user_model().objects.get(pk=user_pk)

    with tenant_db(user):
        # All ORM queries for tenant apps now hit this user's database
        notes = Note.objects.all()
        Note.objects.create(user=user, text="Created from a background task")
```

`tenant_db` accepts any object with a `.pk` attribute (typically a User or your custom tenant model). It opens the tenant's database connection on entry and cleans it up on exit.

## Admin integration

A `ModelAdmin` subclass can be used so superusers can access other user's data:

```{note}
This is designed for simple setups where `TENANT_MODEL` is the User model. For more complex setups with a separate tenant model (e.g., Organization), you'll need a custom solution that maps users to their tenant.
```

```python
# admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from dj_lite_tenant.admin import SwitchTenantAdmin

admin.site.unregister(User)

@admin.register(User)
class UserAdmin(SwitchTenantAdmin, BaseUserAdmin):
    pass
```

Add the URLs to your project's `urls.py`:

```python
from django.urls import include, path

urlpatterns = [
    path("admin/", include("dj_lite_tenant.urls")),  # Must come BEFORE admin.site.urls
    path("admin/", admin.site.urls),
]
```

## Running migrations for existing tenant databases

When you add a new model to a tenant app, you need to run migrations for all existing tenant databases:

```bash
python manage.py migrate_tenant_dbs
```

This command applies migrations to all existing per-tenant SQLite databases found in `DJ_LITE_TENANT['DIR']`.

## Tenant database cleanup

By default, when a tenant (e.g., User) is deleted, the tenant's SQLite database file is **not** automatically deleted. This is a safety precaution to prevent accidental data loss from cascade deletes, bulk operations, or admin UI actions.

### Manual cleanup

To delete a tenant database file explicitly:

```python
from dj_lite_tenant.utils import delete_tenant_db

delete_tenant_db(str(user.pk))  # Returns True if file was deleted, False if not found
```

### Automatic cleanup

To automatically delete tenant DB files when the tenant is deleted, set `DELETE_TENANT_DB_ON_DELETE=True`:

```python
DJ_LITE_TENANT = {
    ...
    "DELETE_TENANT_DB_ON_DELETE": True,
}
```

When enabled, the tenant DB file is deleted immediately after the tenant instance is deleted. When disabled, a warning is logged if the DB file remains after tenant deletion.

## Enabling database template

By default, every new tenant database is created by running all migrations for the tenant apps. Setting `USE_DATABASE_TEMPLATE` to `True` stores a "template" of the database so new tenant databases can be created faster.:

```python
DJ_LITE_TENANT = {
    ...
    "USE_DATABASE_TEMPLATE": True,
}
```

### How it works

1. The **first** tenant database is created normally via `migrate`.
2. That fully-migrated database is copied to a template file (`.template.sqlite3`) inside `DJ_LITE_TENANT['DIR']`.
3. Every subsequent tenant database is created by copying the template file instead of running all of the migrations to get to the current state.
4. If the template copy fails for any reason, the system falls back to running migrations automatically.
5. The template cache is invalidated whenever migrations are applied to any tenant app (via the `post_migrate` signal), so it stays in sync with your schema.

### Manually clearing the database template

```python
from dj_lite_tenant.utils import clear_template_cache

clear_template_cache()
```
