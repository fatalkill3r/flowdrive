import hashlib, os, uuid
from pathlib import Path
from django.conf import settings
from django.db import transaction
from apps.accounts.models import Profile

class StorageError(Exception): pass
class QuotaExceeded(StorageError): pass

def _safe_path(relative):
    root = Path(settings.FILEBOX_STORAGE_ROOT).resolve()
    path = (root / relative).resolve()
    if root not in path.parents: raise StorageError("Invalid storage path")
    return path

def save_file(uploaded, user):
    profile = Profile.objects.select_for_update().get(user=user)
    size = uploaded.size
    if size > settings.FILEBOX_MAX_UPLOAD_BYTES: raise StorageError("File exceeds the upload size limit.")
    if profile.storage_used + size > profile.storage_quota: raise QuotaExceeded("Storage limit exceeded. Delete some files or contact your administrator.")
    token = str(uuid.uuid4()); relative = str(Path(token[:2]) / token); target = _safe_path(relative)
    target.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    try:
        with target.open("xb") as output:
            for chunk in uploaded.chunks(): digest.update(chunk); output.write(chunk)
    except Exception:
        target.unlink(missing_ok=True); raise
    profile.storage_used += size; profile.save(update_fields=["storage_used"])
    return token, relative, digest.hexdigest()

def open_file(file_obj): return _safe_path(file_obj.storage_path).open("rb")
def physical_delete(file_obj): _safe_path(file_obj.storage_path).unlink(missing_ok=True)
def copy_physical(file_obj, user):
    import shutil
    profile = Profile.objects.select_for_update().get(user=user)
    if profile.storage_used + file_obj.size > profile.storage_quota: raise QuotaExceeded("Storage limit exceeded. Delete some files or contact your administrator.")
    token = str(uuid.uuid4()); relative = str(Path(token[:2]) / token); target = _safe_path(relative); target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(_safe_path(file_obj.storage_path), target)
    profile.storage_used += file_obj.size; profile.save(update_fields=["storage_used"])
    return token, relative
def delete_file(file_obj):
    # Soft deletion intentionally retains bytes for later Trash restoration.
    profile = Profile.objects.select_for_update().get(user=file_obj.owner)
    profile.storage_used = max(0, profile.storage_used - file_obj.size); profile.save(update_fields=["storage_used"])
def calculate_checksum(path):
    digest = hashlib.sha256()
    with _safe_path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""): digest.update(chunk)
    return digest.hexdigest()
def get_storage_usage(user): return user.profile.storage_used
def usage_summary(user):
    from apps.files.models import File, Folder
    p = user.profile; used = p.storage_used; quota = p.storage_quota
    return {"files": File.objects.active().filter(owner=user).count(), "folders": Folder.objects.active().filter(owner=user).count(), "used": used, "quota": quota, "remaining": max(0, quota-used), "percentage": min(100, round(used/quota*100, 1)) if quota else 100}
