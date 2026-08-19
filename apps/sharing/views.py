from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404,redirect,render
from django.urls import reverse
from django.views.decorators.http import require_POST
from apps.files.models import File,Folder
from apps.files.services.storage import usage_summary
from .models import SharePermission,ShareLink
from .services.permissions import can_share,permission_for
from .services.sharing import share_item,remove_share,event
from .services.public_links import configure,regenerate

def _owned(user,kind,value):
    model=File if kind=="file" else Folder; return get_object_or_404(model.objects.active(),owner=user,uuid=value)
@login_required
def user_search(request):
    q=request.GET.get("q","").strip(); users=get_user_model().objects.none()
    if len(q)>=2: users=get_user_model().objects.filter(Q(username__icontains=q)|Q(first_name__icontains=q)|Q(last_name__icontains=q)|Q(email__icontains=q)).exclude(pk=request.user.pk)[:8]
    return JsonResponse({"users":[{"id":u.id,"name":u.get_full_name() or u.username,"email":u.email,"initials":((u.first_name[:1]+u.last_name[:1]) or u.username[:2]).upper()} for u in users]})
@login_required
def share_dialog(request,kind,item_uuid):
    item=_owned(request.user,kind,item_uuid)
    if request.method=="POST":
        recipient=get_object_or_404(get_user_model(),pk=request.POST.get("user_id")); permission=request.POST.get("permission")
        if permission not in dict(SharePermission.PERMISSIONS): return JsonResponse({"ok":False,"error":"Choose a valid permission."},status=400)
        try: share_item(request.user,item,recipient,permission)
        except ValidationError as exc:return JsonResponse({"ok":False,"error":exc.message},status=400)
        return JsonResponse({"ok":True,"message":f"Shared with {recipient.get_full_name() or recipient.username}"})
    shares=SharePermission.objects.filter(shared_by=request.user,**{kind:item}).select_related("shared_with")
    link=ShareLink.objects.filter(created_by=request.user,**{kind:item}).first()
    return render(request,"sharing/share_dialog.html",{"item":item,"kind":kind,"shares":shares,"link":link})
@login_required
@require_POST
def update_permission(request,share_uuid):
    share=get_object_or_404(SharePermission,uuid=share_uuid,shared_by=request.user); value=request.POST.get("permission")
    if value in dict(SharePermission.PERMISSIONS):
        old=share.permission;share.permission=value;share.save(update_fields=["permission","updated_at"]);event(request.user,"permission_change",share.item,{"recipient_id":share.shared_with_id,"old_permission":old,"new_permission":value});messages.success(request,"Permission updated")
        from apps.notifications.services.notifications import notify_share
        notify_share(share,updated=True)
    return redirect("sharing:by_me")
@login_required
@require_POST
def remove_access(request,share_uuid):
    share=get_object_or_404(SharePermission,uuid=share_uuid,shared_by=request.user); remove_share(request.user,share); messages.success(request,"Access removed"); return redirect(request.POST.get("next") or "sharing:by_me")
@login_required
def shared_with_me(request):
    shares=SharePermission.objects.filter(shared_with=request.user).select_related("shared_by","file","file__folder","folder","folder__parent")
    q=request.GET.get("q","").strip()
    if q: shares=shares.filter(Q(file__display_name__icontains=q)|Q(folder__name__icontains=q)|Q(shared_by__username__icontains=q)|Q(shared_by__first_name__icontains=q)|Q(file__extension__icontains=q))
    shares=list(shares.order_by("-created_at")); folder_ids={s.folder_id for s in shares if s.folder_id}
    def nested_under_shared(item):
        node=item.folder if item.file_id else item.folder.parent
        while node:
            if node.id in folder_ids:return True
            node=node.parent
        return False
    shares=[s for s in shares if not nested_under_shared(s)]
    return render(request,"sharing/with_me.html",{"shares":shares,"stats":usage_summary(request.user),"query":q})
@login_required
def shared_folder(request,folder_uuid):
    folder=get_object_or_404(Folder.objects.active().select_related("owner","parent"),uuid=folder_uuid)
    permission=permission_for(request.user,folder)
    if not permission or folder.owner_id==request.user.id:return redirect("files:folder",folder.uuid) if folder.owner_id==request.user.id else render(request,"errors/error.html",{"code":404,"title":"Not found","message":"This shared folder is unavailable."},status=404)
    folders=[x for x in folder.children.active() if permission_for(request.user,x)]; files=[x for x in folder.files.active() if permission_for(request.user,x)]
    return render(request,"sharing/folder.html",{"folder":folder,"folders":folders,"files":files,"permission":permission,"stats":usage_summary(request.user)})
@login_required
def shared_by_me(request):
    shares=SharePermission.objects.filter(shared_by=request.user).select_related("shared_with","file","folder").order_by("-created_at")
    return render(request,"sharing/by_me.html",{"shares":shares,"stats":usage_summary(request.user)})
@login_required
@require_POST
def configure_link(request,kind,item_uuid):
    item=_owned(request.user,kind,item_uuid)
    from apps.adminpanel.models import SystemSettings
    if not SystemSettings.load().public_sharing_enabled:return JsonResponse({"ok":False,"error":"Public sharing is disabled by an administrator."},status=403)
    require=request.POST.get("require_password")=="on"; supplied=request.POST.get("password",""); password=(supplied or None) if require else ""
    try: link=configure(request.user,item,request.POST.get("allow_download")=="on",request.POST.get("expires","never"),password)
    except ValidationError as exc:return JsonResponse({"ok":False,"error":exc.message},status=400)
    return JsonResponse({"ok":True,"message":"Public link created","url":request.build_absolute_uri(reverse("public_sharing:item",args=[link.token]))})
@login_required
@require_POST
def disable_link(request,link_uuid):
    link=get_object_or_404(ShareLink,uuid=link_uuid,created_by=request.user); link.is_active=False; link.save(update_fields=["is_active","updated_at"]); messages.success(request,"Public link disabled"); return redirect(request.POST.get("next") or "sharing:by_me")
@login_required
@require_POST
def regenerate_link(request,link_uuid):
    link=get_object_or_404(ShareLink,uuid=link_uuid,created_by=request.user); regenerate(request.user,link); messages.success(request,"A new public link was generated"); return redirect(request.POST.get("next") or "sharing:by_me")
