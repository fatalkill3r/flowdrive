import secrets
from datetime import timedelta
from django.contrib.auth.hashers import make_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from apps.sharing.models import ShareLink
from .sharing import event
@transaction.atomic
def configure(owner,item,allow_download=False,expires="never",password=None):
    if item.owner_id!=owner.id: raise ValidationError("Only the owner can create public links.")
    kwargs={"folder":item} if hasattr(item,"name") else {"file":item}
    link=ShareLink.objects.filter(created_by=owner,**kwargs).first() or ShareLink(created_by=owner,**kwargs)
    days={"24h":1,"7d":7,"30d":30}.get(expires); link.expires_at=timezone.now()+timedelta(days=days) if days else None
    link.allow_download=allow_download
    if password is not None: link.password_hash=make_password(password) if password else ""
    link.is_active=True; link.save(); event(owner,"link_create",item,{"allow_download":allow_download,"expires":expires})
    from apps.audit.services.audit import record
    record("PUBLIC_LINK_CONFIGURED",owner,item,metadata={"allow_download":allow_download,"expires":expires});return link
@transaction.atomic
def regenerate(owner,link):
    if link.created_by_id!=owner.id: raise ValidationError("Only the owner can regenerate links.")
    link.token=secrets.token_urlsafe(32); link.is_active=True; link.save(update_fields=["token","is_active","updated_at"]); event(owner,"link_regenerate",link.item); return link
