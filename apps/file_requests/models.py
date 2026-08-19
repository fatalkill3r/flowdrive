import secrets,uuid
from django.conf import settings
from django.db import models
from django.utils import timezone
from apps.files.models import File,Folder
def request_token():return secrets.token_urlsafe(32)
class UploadRequest(models.Model):
    uuid=models.UUIDField(default=uuid.uuid4,unique=True,editable=False);token=models.CharField(max_length=86,unique=True,db_index=True,default=request_token,editable=False);created_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="upload_requests");destination_folder=models.ForeignKey(Folder,on_delete=models.CASCADE,related_name="upload_requests")
    title=models.CharField(max_length=160);description=models.TextField(blank=True);password_hash=models.CharField(max_length=255,blank=True);expires_at=models.DateTimeField(null=True,blank=True,db_index=True);is_active=models.BooleanField(default=True,db_index=True);created_at=models.DateTimeField(auto_now_add=True);upload_count=models.PositiveIntegerField(default=0);last_upload_at=models.DateTimeField(null=True,blank=True)
    class Meta:ordering=["-created_at"];indexes=[models.Index(fields=["token","is_active","expires_at"])]
    @property
    def available(self):return self.is_active and self.created_by.is_active and (not self.expires_at or self.expires_at>timezone.now())
class RequestUpload(models.Model):
    request=models.ForeignKey(UploadRequest,on_delete=models.CASCADE,related_name="submissions");file=models.ForeignKey(File,on_delete=models.CASCADE,related_name="request_upload_metadata");uploader_name=models.CharField(max_length=160);uploader_email=models.EmailField(blank=True);created_at=models.DateTimeField(auto_now_add=True)
