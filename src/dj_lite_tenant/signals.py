import logging

from django.db.backends.signals import connection_created
from django.db.models.signals import post_migrate
from django.dispatch import receiver

from dj_lite_tenant.conf import get_conf, is_tenant_app_or_model
from dj_lite_tenant.utils import (
    attach_catalog_to_connection,
    clear_template_cache,
    delete_tenant_db,
    get_tenant_db_path,
    is_tenant_db_alias,
    setup_tenant_db,
)

logger = logging.getLogger(__name__)


def create_tenant_database(sender, instance, created, **kwargs):  # noqa: ARG001
    """Create and migrate a per-tenant SQLite DB when a new tenant instance is saved."""
    if created:
        setup_tenant_db(str(instance.pk))


def delete_tenant_database(sender, instance, **kwargs):  # noqa: ARG001
    """
    Delete the tenant's DB file when the tenant is deleted.

    Only runs if DELETE_TENANT_DB_ON_DELETE is True.
    Otherwise, logs a warning that the DB file was left behind.
    """
    tenant_pk = str(instance.pk)

    if get_conf("DELETE_TENANT_DB_ON_DELETE"):
        deleted = delete_tenant_db(tenant_pk)
        if deleted:
            logger.info("Deleted tenant DB for tenant %s", tenant_pk)
        else:
            logger.debug("No tenant DB found to delete for tenant %s", tenant_pk)
    else:
        db_path = get_tenant_db_path(tenant_pk)
        if db_path.exists():
            logger.warning(
                "Tenant %s deleted but DB file remains at %s. "
                "Set DELETE_TENANT_DB_ON_DELETE=True to auto-delete, "
                "or manually call delete_tenant_db() to clean up.",
                tenant_pk,
                db_path,
            )


@receiver(connection_created)
def on_connection_created(sender, connection, **kwargs):  # noqa: ARG001
    """
    When a per-user DB connection is opened, ATTACH the catalog DB so that
    raw SQL and ORM dot-schema queries (catalog.tablename) work seamlessly.
    """
    if is_tenant_db_alias(connection.alias):
        try:
            attach_catalog_to_connection(connection)
        except Exception:
            logger.exception("Could not ATTACH catalog to %s", connection.alias)


@receiver(post_migrate)
def invalidate_template_cache(sender, **kwargs):  # noqa: ARG001
    """Clear the template cache when migrations are applied to tenant apps."""
    if is_tenant_app_or_model(sender.label):
        clear_template_cache()
