from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from django_sqlite_tenant.utils import setup_user_db

User = get_user_model()


class Command(BaseCommand):
    help = "Create and migrate the SQLite database for a specific user."

    def add_arguments(self, parser):
        parser.add_argument("user_id", type=int, help="ID of the user")

    def handle(self, *args, **options):
        user_id = options["user_id"]
        try:
            User.objects.get(pk=user_id)
        except User.DoesNotExist:
            raise CommandError(f"User with id={user_id} does not exist.")

        self.stdout.write(f"Setting up DB for user {user_id}...")
        success = setup_user_db(user_id)
        if success:
            self.stdout.write(self.style.SUCCESS(f"Done — user {user_id} DB ready."))
        else:
            raise CommandError(f"Failed to set up DB for user {user_id}.")
