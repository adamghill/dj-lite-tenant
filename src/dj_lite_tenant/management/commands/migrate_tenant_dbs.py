import re
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured as ImproperlyConfiguredError
from django.core.management.base import BaseCommand

from dj_lite_tenant.conf import get_conf
from dj_lite_tenant.utils import setup_tenant_db


def _build_tenant_db_re() -> re.Pattern:
    """
    Build a regex from DB_NAME_PATTERN that captures the tenant_pk slug.
    e.g. "tenant_{tenant_pk}.sqlite3" -> r"^tenant_(.+)\\.sqlite3$"
    """

    raw = get_conf("DB_NAME_PATTERN")

    if "{tenant_pk}" not in raw:
        raise ImproperlyConfiguredError("DJ_LITE_TENANT['DB_NAME_PATTERN'] must contain '{tenant_pk}'.")

    pattern = re.escape(raw)
    regex = pattern.replace(r"\{tenant_pk\}", r"(.+)")

    return re.compile(f"^{regex}$")


class Command(BaseCommand):
    help = "Apply migrations to all existing per-tenant SQLite databases."

    def handle(self, *args, **options):  # noqa: ARG002
        db_dir = Path(get_conf("DIR"))

        if not db_dir.is_dir():
            self.stderr.write(self.style.ERROR(f"DIR does not exist: {db_dir}"))
            return

        tenant_db_re = _build_tenant_db_re()
        files = [f.name for f in db_dir.iterdir() if tenant_db_re.match(f.name)]

        if not files:
            self.stdout.write("No tenant databases found.")
            return

        self.stdout.write(f"Migrating {len(files)} tenant database(s)...")
        ok = 0
        failed = 0

        for filename in sorted(files):
            match = tenant_db_re.match(filename)
            tenant_pk = match.group(1)
            self.stdout.write(f"  tenant {tenant_pk}...", ending=" ")

            if setup_tenant_db(tenant_pk):
                self.stdout.write(self.style.SUCCESS("ok"))
                ok += 1
            else:
                self.stdout.write(self.style.ERROR("failed"))
                failed += 1

        self.stdout.write(f"\nDone: {ok} ok, {failed} failed.")
