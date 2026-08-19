from datetime import timedelta
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone
from apps.files.models import File,Folder
from apps.files.services.file_operations import permanent_delete
class Command(BaseCommand):
    help="Permanently remove items past trash retention"
    def handle(self,*args,**options):
        try:
            from apps.adminpanel.models import SystemSettings
            days=SystemSettings.load().trash_retention_days
        except Exception:days=settings.FILEBOX_TRASH_RETENTION_DAYS
        cutoff=timezone.now()-timedelta(days=days);count=0
        for item in File.objects.filter(is_deleted=True,deleted_at__lt=cutoff):permanent_delete(item,item.owner);count+=1
        roots=Folder.objects.filter(is_deleted=True,deleted_at__lt=cutoff).filter(Q(parent__isnull=True)|Q(parent__is_deleted=False))
        for item in roots:permanent_delete(item,item.owner);count+=1
        self.stdout.write(self.style.SUCCESS(f"Permanently deleted {count} trash items"))
