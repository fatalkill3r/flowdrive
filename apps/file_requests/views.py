from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404,redirect,render
from django.views.decorators.http import require_POST
from apps.files.models import Folder
from apps.files.services.storage import usage_summary
from .models import UploadRequest
from .services.requests import create_request,regenerate
@login_required
def list_requests(request):return render(request,"file_requests/list.html",{"requests":UploadRequest.objects.filter(created_by=request.user).select_related("destination_folder"),"stats":usage_summary(request.user)})
@login_required
def create(request):
    from apps.adminpanel.models import SystemSettings
    if not SystemSettings.load().upload_requests_enabled:messages.error(request,"File requests are disabled by an administrator.");return redirect("file_requests:list")
    folders=Folder.objects.active().filter(owner=request.user)
    if request.method=="POST":
        folder=get_object_or_404(folders,uuid=request.POST.get("folder_uuid"))
        try:obj=create_request(request.user,folder,request.POST.get("title","").strip(),request.POST.get("description",""),int(request.POST.get("days",7)),request.POST.get("password",""));messages.success(request,"File request created");return redirect("file_requests:list")
        except (ValueError,TypeError) as exc:messages.error(request,str(exc))
    return render(request,"file_requests/create.html",{"folders":folders,"stats":usage_summary(request.user)})
@login_required
@require_POST
def disable(request,value):obj=get_object_or_404(UploadRequest,uuid=value,created_by=request.user);obj.is_active=False;obj.save(update_fields=["is_active"]);messages.success(request,"File request disabled");return redirect("file_requests:list")
@login_required
@require_POST
def regenerate_view(request,value):obj=get_object_or_404(UploadRequest,uuid=value,created_by=request.user);regenerate(obj,request.user);messages.success(request,"New request link generated");return redirect("file_requests:list")
