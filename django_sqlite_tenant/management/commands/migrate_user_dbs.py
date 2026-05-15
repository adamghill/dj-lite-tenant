import os
import re

from django.core.management.base import BaseCommand

from django_sqlite_tenant.conf import get_conf
from django_sqlite_tenant.utils import setup_user_db

_USER_DB_RE = re.compile(r"^user_(\d+)\.sqlite3$")


class Command(BaseCommand):
    help = "Apply migrations to all existing per-user SQLite databases."

    def handle(self, *args, **options):
        db_dir = str(get_conf("DB_DIR"))

        if not os.path.isdir(db_dir):
            self.stderr.write(f"DB_DIR does not exist: {db_dir}")
            return

        files = [f for f in os.listdir(db_dir) if _USER_DB_RE.match(f)]
        if not files:
            self.stdout.write("No user databases found.")
            return

        self.stdout.write(f"Migrating {len(files)} user database(s)...")
        ok = 0
        failed = 0

        for filename in sorted(files):
            match = _USER_DB_RE.match(filename)
            user_id = int(match.group(1))
            self.stdout.write(f"  user {user_id}...", ending=" ")
            if setup_user_db(user_id):
                self.stdout.write(self.style.SUCCESS("ok"))
                ok += 1
            else:
                self.stdout.write(self.style.ERROR("failed"))
                failed += 1

        self.stdout.write(f"\nDone: {ok} ok, {failed} failed.")
