import os

from django.conf import settings
from django.core.management import call_command
from django.db import connections

from django_sqlite_tenant.conf import get_conf


def get_user_db_alias(user_id: int) -> str:
    return f"user_{user_id}"


def get_user_db_path(user_id: int) -> str:
    pattern = get_conf("DB_NAME_PATTERN")
    db_dir = get_conf("DB_DIR")
    filename = pattern.format(user_id=user_id)
    return os.path.join(str(db_dir), filename)


def get_catalog_db_path() -> str:
    catalog_alias = get_conf("CATALOG_ALIAS")
    return settings.DATABASES[catalog_alias]["NAME"]


def _build_user_db_config(db_path: str) -> dict:
    """Build a DATABASES entry for a user DB, independent of the default config."""
    conn_max_age = get_conf("CONN_MAX_AGE")
    return {
        "ENGINE": "django_sqlite_tenant.backends.sqlite3",
        "NAME": db_path,
        "OPTIONS": {},
        "CONN_MAX_AGE": conn_max_age,
        "CONN_HEALTH_CHECKS": False,
        "TIME_ZONE": None,
        "AUTOCOMMIT": True,
        "TEST": {"NAME": None},
    }


def get_or_create_user_db(user_id: int) -> bool:
    """
    Ensures the user's DB alias is registered in settings.DATABASES and the
    connection is available. Creates the DB file via migrations if it doesn't
    exist yet. Returns True if the DB is ready.
    """
    alias = get_user_db_alias(user_id)
    db_path = get_user_db_path(user_id)

    if not os.path.exists(db_path):
        return setup_user_db(user_id)

    if alias not in settings.DATABASES:
        settings.DATABASES[alias] = _build_user_db_config(db_path)

    return True


def setup_user_db(user_id: int) -> bool:
    """
    Creates the per-user SQLite DB file and applies migrations.
    Called on first user creation (via signal) and by create_user_db command.
    """
    alias = get_user_db_alias(user_id)
    db_path = get_user_db_path(user_id)

    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    settings.DATABASES[alias] = _build_user_db_config(db_path)

    init_command = get_conf("SQLITE_INIT_COMMAND")
    if init_command:
        conn = connections[alias]
        conn.ensure_connection()
        with conn.cursor() as cursor:
            for stmt in init_command.split(";"):
                stmt = stmt.strip()
                if stmt:
                    cursor.execute(stmt)

    try:
        call_command("migrate", database=alias, interactive=False, verbosity=0)
        return True
    except Exception as e:
        print(f"[django-sqlite-tenant] Error migrating DB for user {user_id}: {e}")
        return False
    finally:
        close_user_db(user_id)


def close_user_db(user_id: int) -> None:
    """Closes the connection and removes the alias from settings.DATABASES."""
    alias = get_user_db_alias(user_id)
    if alias in connections:
        connections[alias].close()
        del connections[alias]
    settings.DATABASES.pop(alias, None)


def delete_user_db(user_id: int) -> bool:
    """Closes the connection and deletes the user's DB file from disk."""
    close_user_db(user_id)
    db_path = get_user_db_path(user_id)
    if os.path.exists(db_path):
        os.remove(db_path)
        return True
    return False


def attach_catalog_to_connection(connection) -> None:
    """
    Runs ATTACH DATABASE on a newly opened user DB connection so that raw SQL
    can reference catalog.tablename, and the ORM can use Meta.db_table = "catalog.x".
    """
    catalog_path = get_catalog_db_path()
    attach_name = get_conf("CATALOG_ATTACH_NAME")
    with connection.cursor() as cursor:
        cursor.execute(f"ATTACH DATABASE %s AS {attach_name}", [catalog_path])
