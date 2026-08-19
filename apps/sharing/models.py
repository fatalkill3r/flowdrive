import secrets, uuid
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone
from apps.files.models import File, Folder
def secure_token(): return secrets.token_urlsafe(32)

class SharePermission(models.Model):
    VIEWER="viewer"; DOWNLOADER="downloader"; EDITOR="editor"
    PERMISSIONS=[(VIEWER,"Viewer"),(DOWNLOADER,"Downloader"),(EDITOR,"Editor")]
    uuid=models.UUIDField(default=uuid.uuid4,unique=True,editable=False)
    shared_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="shares_created",db_index=True)
    shared_with=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="shares_received",db_index=True)
    file=models.ForeignKey(File,null=True,blank=True,on_delete=models.CASCADE,related_name="share_permissions")
    folder=models.ForeignKey(Folder,null=True,blank=True,on_delete=models.CASCADE,related_name="share_permissions")
    permission=models.CharField(max_length=16,choices=PERMISSIONS,db_index=True)
    created_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True)
    class Meta:
        constraints=[models.CheckConstraint(condition=(Q(file__isnull=False,folder__isnull=True)|Q(file__isnull=True,folder__isnull=False)),name="share_exactly_one_item"),models.UniqueConstraint(fields=["shared_with","file"],name="unique_user_file_share"),models.UniqueConstraint(fields=["shared_with","folder"],name="unique_user_folder_share")]
        indexes=[models.Index(fields=["shared_with","permission"]),models.Index(fields=["shared_by","created_at"])]
    @property
    def item(self): return self.file or self.folder
    def clean(self):
        if self.shared_by_id==self.shared_with_id: raise ValidationError("You already own this item.")
        if self.item and self.item.owner_id!=self.shared_by_id: raise ValidationError("Only the owner can share this item.")

class ShareLink(models.Model):
    uuid=models.UUIDField(default=uuid.uuid4,unique=True,editable=False)
    file=models.ForeignKey(File,null=True,blank=True,on_delete=models.CASCADE,related_name="share_links")
    folder=models.ForeignKey(Folder,null=True,blank=True,on_delete=models.CASCADE,related_name="share_links")
    token=models.CharField(max_length=86,unique=True,db_index=True,default=secure_token,editable=False)
    created_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="public_links")
    allow_download=models.BooleanField(default=False)
    password_hash=models.CharField(max_length=255,blank=True)
    expires_at=models.DateTimeField(null=True,blank=True,db_index=True)
    is_active=models.BooleanField(default=True,db_index=True)
    created_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True)
    last_accessed_at=models.DateTimeField(null=True,blank=True); access_count=models.PositiveBigIntegerField(default=0)
    class Meta:
        constraints=[models.CheckConstraint(condition=(Q(file__isnull=False,folder__isnull=True)|Q(file__isnull=True,folder__isnull=False)),name="link_exactly_one_item")]
        indexes=[models.Index(fields=["is_active","expires_at"])]
    @property
    def item(self): return self.file or self.folder
    @property
    def available(self): return self.is_active and self.created_by.is_active and (not self.expires_at or self.expires_at>timezone.now())
    def clean(self):
        if self.item and self.item.owner_id!=self.created_by_id: raise ValidationError("Only the owner can create a link.")
