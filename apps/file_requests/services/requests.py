import mimetypes,os,secrets
from datetime import timedelta
from django.contrib.auth.hashers import make_password
from django.db import transaction
from django.utils import timezone
from apps.audit.services.audit import record
from apps.files.models import File
from apps.files.services.metadata import unique_name
from apps.files.services.storage import save_file
from apps.notifications.services.notifications import notify_request_upload
from apps.file_requests.models import UploadRequest,RequestUpload
@transaction.atomic
def create_request(user,folder,title,description="",days=7,password=""):
    if folder.owner_id!=user.id:raise ValueError("Choose a folder you own.")
    obj=UploadRequest.objects.create(created_by=user,destination_folder=folder,title=title,description=description,expires_at=timezone.now()+timedelta(days=min(days,30)) if days else None,password_hash=make_password(password) if password else "");record("UPLOAD_REQUEST_CREATED",user,obj);return obj
@transaction.atomic
def receive_files(obj,uploads,name,email=""):
    created=[]
    for upload in uploads:
        display=unique_name(File,obj.created_by,"folder",obj.destination_folder,os.path.basename(upload.name),"display_name");token,path,checksum=save_file(upload,obj.created_by);ext=os.path.splitext(display)[1].lstrip(".").lower()[:32]
        item=File.objects.create(owner=obj.created_by,folder=obj.destination_folder,display_name=display,stored_name=token,storage_path=path,mime_type=upload.content_type or mimetypes.guess_type(display)[0] or "application/octet-stream",extension=ext,size=upload.size,checksum=checksum);RequestUpload.objects.create(request=obj,file=item,uploader_name=name,uploader_email=email);created.append(item)
    obj.upload_count+=len(created);obj.last_upload_at=timezone.now();obj.save(update_fields=["upload_count","last_upload_at"]);notify_request_upload(obj,len(created));record("UPLOAD_REQUEST_USED",obj.created_by,obj,metadata={"count":len(created)});return created
def regenerate(obj,user):
    if obj.created_by_id!=user.id:raise ValueError("Not allowed")
    obj.token=secrets.token_urlsafe(32);obj.save(update_fields=["token"]);record("UPLOAD_REQUEST_REGENERATED",user,obj);return obj
