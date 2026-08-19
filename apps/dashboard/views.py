from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from apps.files.models import File, Folder
from apps.files.services.storage import usage_summary

@login_required
def home(request):
    files = File.objects.active().filter(owner=request.user).select_related("folder")
    folders = Folder.objects.active().filter(owner=request.user)
    from apps.file_requests.models import UploadRequest
    from apps.sharing.models import SharePermission
    return render(request, "dashboard/home.html", {"recent_files": files.order_by("-updated_at")[:5], "recent_folders": folders.order_by("-updated_at")[:5], "stats": usage_summary(request.user),"pending_requests":UploadRequest.objects.filter(created_by=request.user,is_active=True).count(),"recent_notifications":request.user.notifications.all()[:3],"recent_shares":SharePermission.objects.filter(shared_with=request.user).select_related("shared_by")[:3]})
def error_403(request, exception=None): return render(request, "errors/error.html", {"code": 403, "title": "Access denied", "message": "You don't have access to this item."}, status=403)
def error_404(request, exception=None): return render(request, "errors/error.html", {"code": 404, "title": "Page not found", "message": "The item may have moved or no longer exists."}, status=404)
def error_500(request): return render(request, "errors/error.html", {"code": 500, "title": "Something went wrong", "message": "Please try again in a moment."}, status=500)
