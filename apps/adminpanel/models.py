from django.conf import settings
from django.db import models
class SystemSettings(models.Model):
    singleton=models.BooleanField(default=True,unique=True);default_quota=models.PositiveBigIntegerField(default=settings.FILEBOX_DEFAULT_QUOTA_BYTES);max_upload_size=models.PositiveBigIntegerField(default=settings.FILEBOX_MAX_UPLOAD_BYTES);max_file_versions=models.PositiveIntegerField(default=settings.FILEBOX_MAX_FILE_VERSIONS);trash_retention_days=models.PositiveIntegerField(default=settings.FILEBOX_TRASH_RETENTION_DAYS);public_sharing_enabled=models.BooleanField(default=True);max_public_link_days=models.PositiveIntegerField(default=90);upload_requests_enabled=models.BooleanField(default=True);max_request_days=models.PositiveIntegerField(default=settings.FILEBOX_MAX_REQUEST_DAYS);updated_at=models.DateTimeField(auto_now=True)
    @classmethod
    def load(cls):return cls.objects.get_or_create(singleton=True)[0]
    class Meta:
        verbose_name_plural="system settings"
        permissions=[
            ("access_administration","Can access application administration"),
            ("view_users","Can view user accounts"),
            ("manage_users","Can create, activate, and deactivate users"),
            ("manage_quotas","Can manage user storage quotas"),
            ("view_storage_analytics","Can view storage analytics"),
            ("view_file_analytics","Can view file analytics"),
            ("view_sharing_analytics","Can view sharing analytics"),
            ("view_audit_log","Can view the audit log"),
            ("manage_system_settings","Can manage system settings"),
            ("manage_roles","Can assign platform roles"),
        ]
