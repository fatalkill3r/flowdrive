from datetime import timedelta
from django.urls import reverse
from django.utils import timezone
from apps.notifications.models import Notification,NotificationPreference
def enabled(user,kind):
    pref,_=NotificationPreference.objects.get_or_create(user=user);return getattr(pref,kind,True)
def notify_user(user,type,title,message,url="",metadata=None,dedupe_minutes=0):
    if dedupe_minutes and Notification.objects.filter(user=user,type=type,title=title,created_at__gte=timezone.now()-timedelta(minutes=dedupe_minutes)).exists():return None
    return Notification.objects.create(user=user,type=type,title=title,message=message,url=url,metadata=metadata or {})
def notify_share(share,updated=False):
    if not enabled(share.shared_with,"sharing"):return
    item=share.item;name=getattr(item,"name",getattr(item,"display_name","item"));url=reverse("sharing:folder",args=[item.uuid]) if share.folder_id else reverse("files:preview",args=[item.uuid])
    notify_user(share.shared_with,"permission_changed" if updated else "shared","Permission updated" if updated else "Shared with you",f'{share.shared_by.get_full_name() or share.shared_by.username} gave you {share.get_permission_display()} access to “{name}”.',url)
def notify_access_removed(user,item,owner):
    if enabled(user,"sharing"):notify_user(user,"access_removed","Access removed",f'Your access to “{getattr(item,"name",getattr(item,"display_name","item"))}” was removed by {owner.get_full_name() or owner.username}.')
def notify_request_upload(request_obj,count):
    if enabled(request_obj.created_by,"upload_requests"):notify_user(request_obj.created_by,"request_upload","Files received",f'{count} file{"s" if count!=1 else ""} uploaded to “{request_obj.title}”.',reverse("files:folder",args=[request_obj.destination_folder.uuid]),{"request_uuid":str(request_obj.uuid),"count":count})
def notify_folder_upload(folder,actor,count):
    from apps.sharing.models import SharePermission
    recipients={};node=folder
    while node:
        for share in SharePermission.objects.filter(folder=node).select_related("shared_with"):recipients[share.shared_with_id]=share.shared_with
        node=node.parent
    if actor.id!=folder.owner_id:recipients[folder.owner_id]=folder.owner
    for user in recipients.values():
        if user.id!=actor.id and enabled(user,"shared_activity"):notify_user(user,"shared_upload","New files in shared folder",f'{actor.get_full_name() or actor.username} uploaded {count} file{"s" if count!=1 else ""} to “{folder.name}”.',reverse("sharing:folder",args=[folder.uuid]) if user.id!=folder.owner_id else reverse("files:folder",args=[folder.uuid]),dedupe_minutes=2)
def check_quota(user):
    p=user.profile;pct=p.storage_used/p.storage_quota*100 if p.storage_quota else 100
    threshold=100 if pct>=100 else 90 if pct>=90 else 80 if pct>=80 else None
    if threshold and enabled(user,"storage"):notify_user(user,"storage_warning",f"Storage {threshold}% full",f"You have used {pct:.1f}% of your storage quota.",reverse("coming_soon"),{"threshold":threshold},dedupe_minutes=1440)
