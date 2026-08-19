from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404,redirect,render
from django.utils import timezone
from django.views.decorators.http import require_POST
from apps.files.services.storage import usage_summary
from .models import Notification,NotificationPreference
@login_required
def center(request):
    qs=Notification.objects.filter(user=request.user);qs=qs.filter(is_read=False) if request.GET.get("filter")=="unread" else qs
    return render(request,"notifications/center.html",{"page":Paginator(qs,25).get_page(request.GET.get("page")),"stats":usage_summary(request.user)})
@login_required
def mark_read(request,value):
    item=get_object_or_404(Notification,uuid=value,user=request.user);item.is_read=True;item.read_at=timezone.now();item.save(update_fields=["is_read","read_at"]);return redirect(item.url or "notifications:center")
@login_required
@require_POST
def mark_all(request):Notification.objects.filter(user=request.user,is_read=False).update(is_read=True,read_at=timezone.now());return redirect("notifications:center")
@login_required
def preferences(request):
    pref,_=NotificationPreference.objects.get_or_create(user=request.user)
    if request.method=="POST":
        for field in ("sharing","shared_activity","upload_requests","storage"):setattr(pref,field,request.POST.get(field)=="on")
        pref.save();return redirect("notifications:preferences")
    return render(request,"notifications/preferences.html",{"pref":pref,"stats":usage_summary(request.user)})
