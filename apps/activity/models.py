from django.conf import settings
from django.db import models
class Activity(models.Model):
    ACTIONS = [(x, x.replace("_", " ").title()) for x in ("upload", "view", "download", "folder_create", "rename", "move", "copy", "star", "unstar", "delete", "restore", "permanent_delete", "share", "unshare", "permission_change", "link_create", "link_update", "link_disable", "link_regenerate", "public_access", "public_download", "version_upload", "version_restore", "version_download", "request_upload")]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="activities")
    action = models.CharField(max_length=32, choices=ACTIONS)
    object_name = models.CharField(max_length=255)
    object_uuid = models.UUIDField(null=True, blank=True)
    object_type = models.CharField(max_length=16, default="file")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    class Meta: ordering = ["-created_at"]
