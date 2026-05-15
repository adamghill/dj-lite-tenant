from django.db import models


class UserNote(models.Model):
    """A simple per-user model used in tests."""

    user_id = models.IntegerField()
    text = models.TextField()

    class Meta:
        app_label = "testapp"
