from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import redirect,render
from apps.files.models import File,FileVersion
from apps.files.services.storage import usage_summary
@login_required
def settings_page(request):
    if request.method=="POST":
        request.user.first_name=request.POST.get("first_name","").strip();request.user.last_name=request.POST.get("last_name","").strip();request.user.email=request.POST.get("email","").strip();request.user.save(update_fields=["first_name","last_name","email"]);messages.success(request,"Account settings updated");return redirect("accounts:settings")
    active=File.objects.active().filter(owner=request.user).aggregate(v=Sum("size"))["v"] or 0;trash=File.objects.filter(owner=request.user,is_deleted=True).aggregate(v=Sum("size"))["v"] or 0;versions=FileVersion.objects.filter(file__owner=request.user).aggregate(v=Sum("size"))["v"] or 0
    return render(request,"accounts/settings.html",{"stats":usage_summary(request.user),"active_storage":active,"trash_storage":trash,"version_storage":versions})
