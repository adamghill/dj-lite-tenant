from django.db.backends.sqlite3.base import DatabaseWrapper as Base

from dj_lite_tenant.backends.sqlite3.operations import DatabaseOperations


class DatabaseWrapper(Base):
    """
    Custom SQLite DatabaseWrapper that uses DatabaseOperations with dot-schema
    quote_name support, enabling ORM queries against ATTACH'd databases via
    Meta.db_table = "catalog.tablename".
    """

    ops_class = DatabaseOperations
