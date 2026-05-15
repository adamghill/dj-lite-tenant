from django.contrib.auth import get_user_model
from django.db.backends.signals import connection_created
from django.db.models.signals import post_save
from django.dispatch import receiver

from django_sqlite_tenant.utils import attach_catalog_to_connection, setup_user_db

User = get_user_model()


@receiver(post_save, sender=User)
def create_user_database(sender, instance, created, **kwargs):
    """Create and migrate a per-user SQLite DB when a new user is saved."""
    if created:
        setup_user_db(instance.id)


@receiver(connection_created)
def on_connection_created(sender, connection, **kwargs):
    """
    When a per-user DB connection is opened, ATTACH the catalog DB so that
    raw SQL and ORM dot-schema queries (catalog.tablename) work seamlessly.
    """
    if connection.alias.startswith("user_"):
        try:
            attach_catalog_to_connection(connection)
        except Exception as e:
            print(f"[django-sqlite-tenant] Could not ATTACH catalog to {connection.alias}: {e}")
