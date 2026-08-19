from django.core.management.base import BaseCommand
from apps.files.models import File
from apps.files.services.versioning import prune_versions
class Command(BaseCommand):
    help="Enforce configured file version retention"
    def handle(self,*args,**options):
        count=sum(prune_versions(item) for item in File.objects.iterator());self.stdout.write(self.style.SUCCESS(f"Pruned {count} historical versions"))
