import os
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from apps.accounts.models import Profile
from apps.activity.models import Activity
from apps.files.models import FileVersion
from .storage import save_file,copy_physical,physical_delete
def _event(user,action,file,metadata=None):Activity.objects.create(user=user,action=action,object_type="file",object_uuid=file.uuid,object_name=file.display_name,metadata=metadata or {})
def history(file):return file.versions.select_related("uploaded_by").order_by("-version_number")
@transaction.atomic
def replace_current(file,uploaded,user,comment=""):
    if file.owner_id!=user.id:
        from apps.sharing.services.permissions import can_edit
        if not can_edit(user,file):raise ValidationError("You cannot update this file.")
    token,path,checksum=save_file(uploaded,file.owner)
    FileVersion.objects.create(file=file,version_number=file.current_version_number,storage_path=file.storage_path,stored_name=file.stored_name,size=file.size,checksum=file.checksum,mime_type=file.mime_type,extension=file.extension,uploaded_by=user,comment="Previous current version")
    file.current_version_number+=1;file.storage_path=path;file.stored_name=token;file.size=uploaded.size;file.checksum=checksum;file.mime_type=uploaded.content_type or file.mime_type;file.extension=os.path.splitext(uploaded.name)[1].lstrip(".").lower()[:32] or file.extension;file.save()
    _event(user,"version_upload",file,{"version":file.current_version_number,"comment":comment[:200]})
    if user.id!=file.owner_id:
        from apps.notifications.services.notifications import notify_user
        notify_user(file.owner,"shared_activity","Shared file updated",f'{user.get_full_name() or user.username} uploaded Version {file.current_version_number} of “{file.display_name}”.')
    from apps.notifications.services.notifications import check_quota
    check_quota(file.owner);prune_versions(file);return file
@transaction.atomic
def restore_version(version,user):
    file=version.file
    if file.owner_id!=user.id:
        from apps.sharing.services.permissions import can_edit
        if not can_edit(user,file):raise ValidationError("You cannot restore versions.")
    token,path=copy_physical(version,file.owner)
    FileVersion.objects.create(file=file,version_number=file.current_version_number,storage_path=file.storage_path,stored_name=file.stored_name,size=file.size,checksum=file.checksum,mime_type=file.mime_type,extension=file.extension,uploaded_by=user,comment="Current before restore")
    file.current_version_number+=1;file.storage_path=path;file.stored_name=token;file.size=version.size;file.checksum=version.checksum;file.mime_type=version.mime_type;file.extension=version.extension;file.save()
    _event(user,"version_restore",file,{"restored_from":version.version_number,"new_version":file.current_version_number});prune_versions(file);return file
@transaction.atomic
def prune_versions(file,limit=None):
    if limit is None:
        try:
            from apps.adminpanel.models import SystemSettings
            limit=SystemSettings.load().max_file_versions
        except Exception:limit=settings.FILEBOX_MAX_FILE_VERSIONS
    old=list(file.versions.order_by("-version_number")[max(0,limit-1):])
    if not old:return 0
    profile=Profile.objects.select_for_update().get(user=file.owner)
    for version in old:physical_delete(version);profile.storage_used=max(0,profile.storage_used-version.size);version.delete()
    profile.save(update_fields=["storage_used"]);return len(old)
