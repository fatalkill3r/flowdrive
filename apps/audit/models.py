import uuid
from django.conf import settings
from django.db import models
class AuditEvent(models.Model):
    uuid=models.UUIDField(default=uuid.uuid4,unique=True,editable=False);actor=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,on_delete=models.SET_NULL,related_name="audit_events",db_index=True)
    event_type=models.CharField(max_length=64,db_index=True);object_type=models.CharField(max_length=32,blank=True);object_uuid=models.UUIDField(null=True,blank=True);object_name=models.CharField(max_length=255,blank=True);target_user=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,blank=True,on_delete=models.SET_NULL,related_name="targeted_audit_events")
    metadata=models.JSONField(default=dict,blank=True);result=models.CharField(max_length=16,default="success",db_index=True);created_at=models.DateTimeField(auto_now_add=True,db_index=True)
    class Meta:ordering=["-created_at"];indexes=[models.Index(fields=["actor","event_type","created_at"])]
