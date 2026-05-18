import logging
import os
import shutil
import threading
from pathlib import Path

from dj_lite import sqlite_config
from django.conf import settings
from django.core.management import call_command
from django.db import connections
from django.utils.text import slugify

from dj_lite_tenant import connection_registry
from dj_lite_tenant.conf import get_conf

logger = logging.getLogger(__name__)

_template_lock = threading.Lock()


def _safe_tenant_pk(tenant_pk: str) -> str:
    """Sanitise a tenant PK for use in DB aliases and filenames."""

    return slugify(str(tenant_pk), allow_unicode=False)


def get_tenant_db_alias(tenant_pk: str) -> str:
    return f"tenant_{_safe_tenant_pk(tenant_pk)}"


def is_tenant_db_alias(alias: str) -> bool:
    """
    Returns True if the given database alias is a per-tenant user database.
    Determined by checking whether the alias's configured path lives inside
    DJ_LITE_TENANT["DIR"], rather than relying on a naming convention.
    """

    db_config = settings.DATABASES.get(alias)

    if db_config is None:
        return False

    tenant_dir = Path(os.path.realpath(str(get_conf("DIR"))))
    db_path = Path(os.path.realpath(str(db_config.get("NAME", ""))))

    return db_path.is_relative_to(tenant_dir)


def get_tenant_db_path(tenant_pk: str) -> Path:
    pattern = get_conf("DB_NAME_PATTERN")
    db_dir = get_conf("DIR")
    filename = pattern.format(tenant_pk=_safe_tenant_pk(tenant_pk))

    return Path(db_dir) / filename


def _build_tenant_db_config(db_path: Path) -> dict:
    """Build a DATABASES entry for a user DB using dj-lite with custom backend override."""

    options = get_conf("TENANT_SETTINGS")
    db_dir = db_path.parent
    file_name = db_path.name

    config = sqlite_config(
        base_dir=db_dir,
        file_name=file_name,
        engine="dj_lite_tenant.backends.sqlite3",
    )
    config.update(options)

    return config


def get_or_create_tenant_db(tenant_pk: str) -> bool:
    """
    Ensures the tenant's DB alias is registered in settings.DATABASES and the
    connection is available. Creates the DB file via migrations if it doesn't
    exist yet. Returns True if the DB is ready.
    """

    alias = get_tenant_db_alias(tenant_pk)
    db_path = get_tenant_db_path(tenant_pk)

    if not os.path.exists(db_path):
        return setup_tenant_db(tenant_pk)

    if alias not in settings.DATABASES:
        settings.DATABASES[alias] = _build_tenant_db_config(db_path)

    connection_registry.touch(alias)
    connection_registry.evict_if_needed(get_conf("MAX_OPEN_CONNECTIONS"))

    return True


def _get_template_path() -> Path:
    """Return the path to the cached template database."""

    return Path(get_conf("DIR")) / ".template.sqlite3"


def clear_template_cache() -> None:
    """Remove the cached template database if it exists."""

    template_path = _get_template_path()

    if template_path.exists():
        template_path.unlink()
        logger.debug("Cleared template cache at %s", template_path)


def setup_tenant_db(tenant_pk: str) -> bool:
    """
    Creates the per-tenant SQLite DB file and applies migrations.
    Called on first tenant creation (via signal) and by create_tenant_db command.
    If USE_DATABASE_TEMPLATE is True, copies from template if available.
    """

    alias = get_tenant_db_alias(tenant_pk)
    db_path = get_tenant_db_path(tenant_pk)

    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    use_template = get_conf("USE_DATABASE_TEMPLATE")
    template_path = _get_template_path()

    if use_template and template_path.exists():
        try:
            shutil.copyfile(template_path, db_path)
            settings.DATABASES[alias] = _build_tenant_db_config(db_path)
            connection_registry.touch(alias)
            connection_registry.evict_if_needed(get_conf("MAX_OPEN_CONNECTIONS"))
            return True
        except Exception:
            logger.exception("Failed to copy template for tenant %s, falling back to migrate", tenant_pk)

    settings.DATABASES[alias] = _build_tenant_db_config(db_path)

    try:
        call_command("migrate", database=alias, interactive=False, verbosity=0)
    except Exception:
        logger.exception("Error migrating DB for tenant %s", tenant_pk)
        close_tenant_db(tenant_pk)

        return False

    if use_template and not template_path.exists():
        with _template_lock:
            if not template_path.exists():
                try:
                    shutil.copyfile(db_path, template_path)
                    logger.debug("Created template cache at %s", template_path)
                except Exception:
                    logger.exception("Failed to create template cache")

    connection_registry.touch(alias)
    connection_registry.evict_if_needed(get_conf("MAX_OPEN_CONNECTIONS"))

    return True


def close_tenant_db(tenant_pk: str) -> None:
    """Closes the connection and removes the alias from settings.DATABASES."""

    alias = get_tenant_db_alias(tenant_pk)
    connection_registry.remove(alias)

    if alias in connections:
        connections[alias].close()
        del connections[alias]
    settings.DATABASES.pop(alias, None)


def delete_tenant_db(tenant_pk: str) -> bool:
    """Closes the connection and deletes the tenant's DB file from disk."""

    close_tenant_db(tenant_pk)
    db_path = get_tenant_db_path(tenant_pk)

    if db_path.exists():
        db_path.unlink()

        return True

    return False


def get_attach_statements() -> list[str]:
    """Generate ATTACH DATABASE SQL statements based on ATTACHMENTS config."""

    aliases = get_conf("ATTACHMENTS")
    statements = []

    for db_alias, attach_name in aliases.items():
        db_path = str(settings.DATABASES[db_alias]["NAME"]).replace("'", "''")
        safe_name = attach_name.replace('"', '""')
        statements.append(f"ATTACH DATABASE 'file:{db_path}?mode=ro' AS \"{safe_name}\"")

    return statements


def attach_shared_databases(connection) -> None:
    """
    Runs ATTACH DATABASE on a newly opened user DB connection so that raw SQL
    can reference shared.tablename, and the ORM can use Meta.db_table = "shared.x".
    """

    with connection.cursor() as cursor:
        for stmt in get_attach_statements():
            cursor.execute(stmt)
