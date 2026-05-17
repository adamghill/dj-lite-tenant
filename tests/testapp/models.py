from django.conf import settings
from django.db import models


class UserNote(models.Model):
    """
    A per-user model that demonstrates cross-database FK traversal.
    The user FK lives in the shared (default) DB, while UserNote lives
    in the tenant DB. Accessing note.user triggers a query to the shared DB.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        db_constraint=False,  # SQLite can't enforce FKs across attached DBs
    )
    text = models.TextField()

    class Meta:
        app_label = "testapp"
