from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.sharing.models import ShareLink
from apps.notifications.services.notifications import notify_user
class Command(BaseCommand):
    help="Disable expired public links"
    def handle(self,*args,**options):
        expired=list(ShareLink.objects.filter(is_active=True,expires_at__lte=timezone.now()).select_related("created_by"))
        for link in expired:notify_user(link.created_by,"link_expired","Public link expired",f'A public link for “{getattr(link.item,"name",getattr(link.item,"display_name","item"))}” has expired.')
        count=ShareLink.objects.filter(pk__in=[x.pk for x in expired]).update(is_active=False);self.stdout.write(self.style.SUCCESS(f"Disabled {count} expired links"))
