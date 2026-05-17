from django.db.backends.sqlite3.operations import DatabaseOperations as Base


class DatabaseOperations(Base):
    """
    Extends the standard SQLite DatabaseOperations to support dot-schema table
    names in Meta.db_table (e.g. "catalog.movie_movie").

    Standard SQLite quote_name wraps the whole string in double-quotes, turning
    "catalog.movie_movie" into the single identifier "catalog.movie_movie" (dot
    inside quotes = literal dot, not a schema separator).

    This override detects unquoted dotted names and emits "catalog"."movie_movie"
    instead, which SQLite interprets as schema.table — valid after ATTACH DATABASE.
    """

    def quote_name(self, name: str) -> str:
        if "." in name and not name.startswith('"'):
            (schema, table) = name.split(".", 1)

            return f'"{schema}"."{table}"'

        return super().quote_name(name)
