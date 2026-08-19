import logging
from django.contrib.auth.hashers import check_password
from django.shortcuts import get_object_or_404,render,redirect
from apps.files.forms import UploadForm
from .models import UploadRequest
from .services.requests import receive_files
from apps.files.services.storage import StorageError
logger=logging.getLogger("filebox")
def request_page(request,token):
    from apps.adminpanel.models import SystemSettings
    if not SystemSettings.load().upload_requests_enabled:return render(request,"file_requests/unavailable.html",status=410)
    obj=get_object_or_404(UploadRequest.objects.select_related("created_by","destination_folder"),token=token)
    if not obj.available:return render(request,"file_requests/unavailable.html",status=410)
    key=f"upload_request_{obj.uuid}"
    if obj.password_hash and not request.session.get(key):
        if request.method=="POST" and "password" in request.POST and check_password(request.POST.get("password",""),obj.password_hash):request.session[key]=True;return redirect(request.path)
        if request.method=="POST":
            from apps.audit.services.audit import record
            record("UPLOAD_REQUEST_PASSWORD_FAILED",obj=obj,result="denied")
        return render(request,"file_requests/password.html",{"invalid":request.method=="POST"})
    if request.method=="POST":
        form=UploadForm(request.POST,request.FILES);name=request.POST.get("uploader_name","").strip()
        if form.is_valid() and name:
            try:files=receive_files(obj,form.cleaned_data["files"],name,request.POST.get("uploader_email",""));return render(request,"file_requests/success.html",{"obj":obj,"count":len(files)})
            except StorageError as exc:return render(request,"file_requests/public.html",{"obj":obj,"error":str(exc)},status=400)
            except Exception:logger.exception("Anonymous request upload failed for request %s",obj.uuid);return render(request,"file_requests/public.html",{"obj":obj,"error":"Upload failed. Please try again."},status=500)
        return render(request,"file_requests/public.html",{"obj":obj,"error":"Enter your name and choose at least one file."},status=400)
    return render(request,"file_requests/public.html",{"obj":obj})
