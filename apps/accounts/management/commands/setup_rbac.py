from django.core.management.base import BaseCommand

from apps.accounts.services.rbac import ROLE_DEFINITIONS, ensure_roles


class Command(BaseCommand):
    help = "Create or synchronize FlowDrive platform roles and permissions."

    def handle(self, *args, **options):
        ensure_roles()
        self.stdout.write(self.style.SUCCESS(f"Synchronized {len(ROLE_DEFINITIONS)} RBAC roles."))
