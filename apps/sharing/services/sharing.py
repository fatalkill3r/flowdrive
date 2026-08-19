from django.core.exceptions import ValidationError
from django.db import transaction
from apps.activity.models import Activity
from apps.sharing.models import SharePermission
def event(actor,action,item,metadata=None): Activity.objects.create(user=actor,action=action,object_type="folder" if hasattr(item,"name") else "file",object_uuid=item.uuid,object_name=getattr(item,"name",getattr(item,"display_name","")),metadata=metadata or {})
@transaction.atomic
def share_item(owner,item,recipient,permission):
    if item.owner_id!=owner.id: raise ValidationError("Only the owner can share this item.")
    if recipient.id==owner.id: raise ValidationError("You already own this item.")
    kwargs={"folder":item} if hasattr(item,"name") else {"file":item}
    share=SharePermission.objects.filter(shared_with=recipient,**kwargs).first()
    if share:
        old=share.permission;share.permission=permission;share.shared_by=owner;share.save(update_fields=["permission","shared_by","updated_at"]);event(owner,"permission_change",item,{"recipient_id":recipient.id,"old_permission":old,"new_permission":permission})
    else:
        share=SharePermission.objects.create(shared_with=recipient,shared_by=owner,permission=permission,**kwargs);event(owner,"share",item,{"recipient_id":recipient.id,"permission":permission})
    from apps.notifications.services.notifications import notify_share
    notify_share(share,updated=bool(locals().get("old")))
    from apps.audit.services.audit import record
    record("SHARE_PERMISSION_UPDATED" if locals().get("old") else "ITEM_SHARED",owner,item,target_user=recipient,metadata={"permission":permission});return share
@transaction.atomic
def remove_share(owner,share):
    if share.shared_by_id!=owner.id: raise ValidationError("Only the owner can remove access.")
    recipient=share.shared_with;item=share.item;event(owner,"unshare",item,{"recipient_id":share.shared_with_id});share.delete()
    from apps.notifications.services.notifications import notify_access_removed
    notify_access_removed(recipient,item,owner)
    from apps.audit.services.audit import record
    record("SHARE_ACCESS_REMOVED",owner,item,target_user=recipient)
