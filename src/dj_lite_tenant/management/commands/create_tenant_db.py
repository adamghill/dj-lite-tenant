from django.core.management.base import BaseCommand, CommandError

from dj_lite_tenant.conf import get_tenant_model
from dj_lite_tenant.utils import setup_tenant_db


class Command(BaseCommand):
    help = "Create and migrate the SQLite database for a specific tenant."

    def add_arguments(self, parser):
        parser.add_argument("tenant_pk", help="Primary key of the tenant")

    def handle(self, *args, **options):  # noqa: ARG002
        tenant_pk = str(options["tenant_pk"])
        TenantModel = get_tenant_model()  # noqa: N806

        try:
            TenantModel.objects.get(pk=tenant_pk)
        except TenantModel.DoesNotExist as err:
            raise CommandError(f"{TenantModel.__name__} with pk={tenant_pk} does not exist.") from err

        self.stdout.write(f"Setting up DB for tenant {tenant_pk}...")
        success = setup_tenant_db(tenant_pk)

        if success:
            self.stdout.write(self.style.SUCCESS(f"Done — tenant {tenant_pk} DB ready."))
        else:
            raise CommandError(f"Failed to set up DB for tenant {tenant_pk}.")
