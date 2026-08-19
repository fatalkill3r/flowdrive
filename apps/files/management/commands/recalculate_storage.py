from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db.models import Sum
from apps.files.models import File,FileVersion
class Command(BaseCommand):
    help="Reconcile maintained storage counters with current, Trash, and version bytes"
    def handle(self,*args,**options):
        count=0
        for user in get_user_model().objects.select_related("profile"):
            current=File.objects.filter(owner=user).aggregate(v=Sum("size"))["v"] or 0;versions=FileVersion.objects.filter(file__owner=user).aggregate(v=Sum("size"))["v"] or 0;user.profile.storage_used=current+versions;user.profile.save(update_fields=["storage_used"]);count+=1
        self.stdout.write(self.style.SUCCESS(f"Reconciled {count} user storage counters"))
