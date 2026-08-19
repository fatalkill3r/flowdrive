from apps.audit.models import AuditEvent
def record(event_type,actor=None,obj=None,target_user=None,result="success",metadata=None):
    return AuditEvent.objects.create(actor=actor,event_type=event_type,object_type=obj.__class__.__name__.lower() if obj else "",object_uuid=getattr(obj,"uuid",None),object_name=getattr(obj,"name",getattr(obj,"display_name","")) if obj else "",target_user=target_user,result=result,metadata=metadata or {})
