import uuid
from django.conf import settings
from django.db import models
class Notification(models.Model):
    uuid=models.UUIDField(default=uuid.uuid4,unique=True,editable=False);user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="notifications")
    type=models.CharField(max_length=40,db_index=True);title=models.CharField(max_length=160);message=models.CharField(max_length=500);url=models.CharField(max_length=500,blank=True);metadata=models.JSONField(default=dict,blank=True)
    is_read=models.BooleanField(default=False,db_index=True);created_at=models.DateTimeField(auto_now_add=True,db_index=True);read_at=models.DateTimeField(null=True,blank=True)
    class Meta:ordering=["-created_at"];indexes=[models.Index(fields=["user","is_read","created_at"])]
class NotificationPreference(models.Model):
    user=models.OneToOneField(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="notification_preferences")
    sharing=models.BooleanField(default=True);shared_activity=models.BooleanField(default=True);upload_requests=models.BooleanField(default=True);storage=models.BooleanField(default=True)
