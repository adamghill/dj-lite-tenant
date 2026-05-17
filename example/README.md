# dj-lite-tenant example

A minimal Django project demonstrating per-user SQLite databases.

## Setup

```bash
# From the repo root
uv run python example/manage.py migrate
uv run python example/manage.py createsuperuser
uv run python example/manage.py runserver
```

Or from inside the `example/` directory:

```bash
cd example
uv run python manage.py migrate
uv run python manage.py createsuperuser
uv run python manage.py runserver
```

## What it shows

- **notes** app — `Note` model is routed to the current user's private SQLite DB (`db/users/user_<id>.sqlite3`)
- **catalog** app — `Movie` model lives in the shared default DB; accessible from any user's DB connection via `ATTACH`
- **Admin** — the User list has Switch/Reset buttons (via `SwitchTenantAdminMixin`) so a superuser can inspect another user's notes. This is designed for simple setups where User = Tenant.
- **`/movies/`** — queries the shared catalog DB using `.using("default")`

## Layout

```
example/
  manage.py
  db/                  # created on first migrate (git-ignored)
    default.sqlite3    # shared catalog DB
    users/             # per-user DB files created automatically on login
  example/             # Django project package (settings, urls, wsgi)
  catalog/             # shared Movie model
  notes/               # per-user Note model + views + admin
  templates/           # base.html + per-view templates
```
