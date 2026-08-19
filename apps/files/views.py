import logging, mimetypes, os, tempfile, zipfile
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q,Count
from django.http import FileResponse, JsonResponse, HttpResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.decorators.clickjacking import xframe_options_sameorigin
from apps.activity.models import Activity
from .forms import FolderForm, UploadForm
from .models import File, Folder, Favorite,FileVersion
from .services.storage import QuotaExceeded, StorageError, delete_file as adjust_usage, open_file, save_file, usage_summary
from .services.file_operations import rename as rename_service, move as move_service, copy_file, copy_folder, restore as restore_service, permanent_delete, soft_delete, log
from .services.metadata import category, unique_name
from .services.preview import PreviewError, preview_kind, text_content, csv_rows, spreadsheet_sheets, document_content
from .services.versioning import replace_current,restore_version
from apps.sharing.services.permissions import can_view,can_preview,can_download,can_edit,can_upload_to_folder,within_same_shared_tree,permission_for
logger = logging.getLogger("filebox")

def _folder_for(user, value):
    if not value: return None
    return get_object_or_404(Folder.objects.active().select_related("parent"), uuid=value, owner=user)
def _destination(request):
    value=request.POST.get("folder_uuid") or None
    if not value:return None
    folder=get_object_or_404(Folder.objects.active(),uuid=value)
    if folder.owner_id!=request.user.id and not can_upload_to_folder(request.user,folder): raise Http404
    return folder
def _back(folder): return reverse("files:folder", args=[folder.uuid]) if folder else reverse("files:root")

@login_required
def browser(request, folder_uuid=None):
    folder = _folder_for(request.user, folder_uuid)
    folders = Folder.objects.active().filter(owner=request.user, parent=folder).select_related("owner").annotate(share_count=Count("share_permissions",distinct=True),link_count=Count("share_links",filter=Q(share_links__is_active=True),distinct=True))
    files = File.objects.active().filter(owner=request.user, folder=folder).select_related("owner", "folder").annotate(share_count=Count("share_permissions",distinct=True),link_count=Count("share_links",filter=Q(share_links__is_active=True),distinct=True))
    sort=request.GET.get("sort","name"); direction=request.GET.get("direction","asc"); prefix="-" if direction=="desc" else ""
    folder_sort={"name":"name","modified":"updated_at","created":"created_at"}.get(sort,"name"); file_sort={"name":"display_name","modified":"updated_at","created":"created_at","size":"size","type":"extension"}.get(sort,"display_name")
    folders=folders.order_by(prefix+folder_sort); files=files.order_by(prefix+file_sort)
    combined = [("folder", x) for x in folders] + [("file", x) for x in files]
    try: per_page=int(request.GET.get("per_page",request.session.get("per_page",50))); per_page=per_page if per_page in (25,50,100) else 50
    except ValueError: per_page=50
    request.session["per_page"]=per_page; page = Paginator(combined, per_page).get_page(request.GET.get("page"))
    favorites=set(Favorite.objects.filter(user=request.user).values_list("file__uuid",flat=True))|set(Favorite.objects.filter(user=request.user).values_list("folder__uuid",flat=True))
    return render(request, "files/browser.html", {"folder": folder, "breadcrumbs": folder.breadcrumbs() if folder else [], "page": page, "stats": usage_summary(request.user),"favorites":favorites,"sort":sort,"direction":direction,"per_page":per_page})

@login_required
@require_POST
def create_folder(request):
    parent = _destination(request); owner=parent.owner if parent else request.user; form = FolderForm(request.POST, owner=owner, parent=parent)
    if form.is_valid():
        item = form.save(commit=False); item.owner=owner; item.parent=parent; item.save()
        Activity.objects.create(user=request.user, action="folder_create", object_name=item.name, object_uuid=item.uuid)
        messages.success(request, "Folder created successfully")
    else: messages.error(request, next(iter(form.errors.values()))[0])
    return redirect(_back(parent))

@login_required
@require_POST
def upload(request):
    folder = _destination(request); form = UploadForm(request.POST, request.FILES)
    if not form.is_valid(): return JsonResponse({"ok": False, "error": next(iter(form.errors.values()))[0]}, status=400)
    created = []
    try:
        with transaction.atomic():
            for uploaded in form.cleaned_data["files"]:
                owner=folder.owner if folder else request.user
                existing=File.objects.active().filter(owner=owner,folder=folder,display_name__iexact=os.path.basename(uploaded.name)).first()
                if existing and request.POST.get("conflict")=="replace":replace_current(existing,uploaded,request.user,request.POST.get("comment",""));created.append(existing);continue
                token, path, checksum = save_file(uploaded, owner)
                name = unique_name(File,owner,"folder",folder,os.path.basename(uploaded.name),"display_name"); ext = os.path.splitext(name)[1].lstrip(".").lower()[:32]
                item = File.objects.create(owner=owner, folder=folder, display_name=name, stored_name=token, storage_path=path, mime_type=uploaded.content_type or mimetypes.guess_type(name)[0] or "application/octet-stream", extension=ext, size=uploaded.size, checksum=checksum)
                Activity.objects.create(user=request.user, action="upload", object_name=name, object_uuid=item.uuid); created.append(item)
    except (StorageError, QuotaExceeded) as exc: logger.warning("Upload rejected for user %s: %s", request.user.pk, exc); return JsonResponse({"ok": False, "error": str(exc)}, status=400)
    except Exception: logger.exception("Upload failed for user %s", request.user.pk); return JsonResponse({"ok": False, "error": "Upload failed. Please try again."}, status=500)
    from apps.notifications.services.notifications import check_quota
    if created:check_quota(created[0].owner)
    if created and folder:
        from apps.notifications.services.notifications import notify_folder_upload
        notify_folder_upload(folder,request.user,len(created))
    return JsonResponse({"ok": True, "message": f"{len(created)} file{'s' if len(created) != 1 else ''} uploaded", "redirect": _back(folder)})

@login_required
def download(request, file_uuid):
    item = get_object_or_404(File.objects.active(), uuid=file_uuid)
    if not can_download(request.user,item): raise Http404
    try: response = FileResponse(open_file(item), as_attachment=True, filename=item.display_name, content_type=item.mime_type)
    except (OSError, StorageError): logger.exception("Storage read failed for file %s", item.uuid); return render(request, "errors/error.html", {"code": 404, "title": "File unavailable", "message": "The stored file could not be found."}, status=404)
    Activity.objects.create(user=request.user, action="download", object_name=item.display_name, object_uuid=item.uuid); return response

@login_required
def details(request, file_uuid):
    item = get_object_or_404(File.objects.active().select_related("owner", "folder"), uuid=file_uuid)
    if not can_view(request.user,item): raise Http404
    is_partial = request.GET.get("partial") == "1" or request.headers.get("X-Requested-With") == "XMLHttpRequest"
    if not is_partial:return redirect("files:preview",item.uuid)
    activities=Activity.objects.filter(user=request.user,object_uuid=item.uuid)[:20]
    from apps.sharing.models import SharePermission,ShareLink
    shares=SharePermission.objects.filter(file=item).select_related("shared_with") if item.owner_id==request.user.id else SharePermission.objects.none()
    link=ShareLink.objects.filter(file=item,created_by=request.user,is_active=True).first()
    return render(request, "files/details.html", {"item": item,"activities":activities,"is_starred":Favorite.objects.filter(user=request.user,file=item).exists(),"shares":shares,"link":link,"access_permission":permission_for(request.user,item),"versions":item.versions.select_related("uploaded_by")})

@login_required
@require_POST
def delete_file_view(request, file_uuid):
    item = get_object_or_404(File.objects.active(), uuid=file_uuid, owner=request.user)
    with transaction.atomic():soft_delete(item,request.user)
    messages.success(request, "File moved to Trash")
    return redirect(_back(item.folder))

@login_required
@require_POST
def delete_folder(request, folder_uuid):
    item = get_object_or_404(Folder.objects.active(), uuid=folder_uuid, owner=request.user)
    with transaction.atomic():soft_delete(item,request.user)
    messages.success(request, "Folder moved to Trash")
    return redirect(_back(item.parent))

def _item(user,kind,value,deleted=False):
    model=File if kind=="file" else Folder if kind=="folder" else None
    if not model: raise ValueError("Invalid item type")
    qs=model.objects.filter(owner=user,is_deleted=deleted)
    return get_object_or_404(qs,uuid=value)
def _editable_item(user,kind,value):
    model=File if kind=="file" else Folder if kind=="folder" else None
    if not model:raise ValueError("Invalid item type")
    item=get_object_or_404(model.objects.active(),uuid=value)
    if not can_edit(user,item):raise Http404
    return item

@login_required
@require_POST
def rename_item(request,kind,item_uuid):
    item=_editable_item(request.user,kind,item_uuid)
    try:
        with transaction.atomic(): rename_service(item,request.POST.get("name",""),request.user)
        messages.success(request,f"{kind.title()} renamed")
    except ValueError as exc: messages.error(request,str(exc))
    return redirect(request.POST.get("next") or _back(item.parent if kind=="folder" else item.folder))

@login_required
@require_POST
def move_item(request,kind,item_uuid):
    item=_editable_item(request.user,kind,item_uuid); dest_value=request.POST.get("destination") or None
    destination=get_object_or_404(Folder.objects.active(),uuid=dest_value) if dest_value else None
    if item.owner_id!=request.user.id and not within_same_shared_tree(request.user,item,destination):raise Http404
    if destination and destination.owner_id!=request.user.id and not can_edit(request.user,destination):raise Http404
    try:
        with transaction.atomic(): move_service(item,destination,request.user,request.POST.get("conflict")=="keep")
        messages.success(request,f"{kind.title()} moved successfully")
    except ValueError as exc: messages.error(request,str(exc))
    return redirect(request.POST.get("next") or "files:root")

@login_required
@require_POST
def copy_item(request,kind,item_uuid):
    item=_item(request.user,kind,item_uuid); destination=_folder_for(request.user,request.POST.get("destination") or None)
    try:
        with transaction.atomic(): copy_file(item,destination,request.user) if kind=="file" else copy_folder(item,destination,request.user)
        messages.success(request,f"{kind.title()} copied")
    except (ValueError,StorageError,OSError) as exc: messages.error(request,str(exc) or "Unable to copy item")
    return redirect(request.POST.get("next") or "files:root")

@login_required
@require_POST
def toggle_star(request,kind,item_uuid):
    model=File if kind=="file" else Folder; item=get_object_or_404(model.objects.active(),uuid=item_uuid)
    if not can_view(request.user,item):raise Http404
    kwargs={kind:item}; favorite=Favorite.objects.filter(user=request.user,**kwargs).first()
    if favorite: favorite.delete(); action="unstar"; message="Removed from Starred"
    else: Favorite.objects.create(user=request.user,**kwargs); action="star"; message="Added to Starred"
    log(request.user,action,item); messages.success(request,message); return redirect(request.POST.get("next") or _back(item.parent if kind=="folder" else item.folder))

@login_required
def starred(request):
    favs=Favorite.objects.filter(user=request.user).select_related("file","file__folder","folder","folder__parent")
    items=[("file",x.file) if x.file else ("folder",x.folder) for x in favs if (x.file and not x.file.is_deleted) or (x.folder and not x.folder.is_deleted)]
    return render(request,"files/collection.html",{"title":"Starred","subtitle":"Your favorite files and folders","items":items,"empty":"No starred files yet","stats":usage_summary(request.user)})

@login_required
def recent(request):
    activities=Activity.objects.filter(user=request.user).exclude(action__in=["star","unstar"])
    return render(request,"files/recent.html",{"activities":activities[:100],"stats":usage_summary(request.user)})

@login_required
def trash(request):
    folders=Folder.objects.filter(owner=request.user,is_deleted=True).filter(Q(parent__isnull=True)|Q(parent__is_deleted=False)).select_related("parent")
    files=File.objects.filter(owner=request.user,is_deleted=True).filter(Q(folder__isnull=True)|Q(folder__is_deleted=False)).select_related("folder")
    return render(request,"files/trash.html",{"items":[("folder",x) for x in folders]+[("file",x) for x in files],"stats":usage_summary(request.user)})

@login_required
@require_POST
def restore_item(request,kind,item_uuid):
    item=_item(request.user,kind,item_uuid,True)
    with transaction.atomic(): restore_service(item,request.user)
    messages.success(request,"Restored from Trash"); return redirect("files:trash")

@login_required
@require_POST
def permanent_delete_item(request,kind,item_uuid):
    item=_item(request.user,kind,item_uuid,True)
    with transaction.atomic(): permanent_delete(item,request.user)
    messages.success(request,"Deleted permanently"); return redirect("files:trash")

@login_required
@require_POST
def empty_trash(request):
    with transaction.atomic():
        for item in File.objects.filter(owner=request.user,is_deleted=True): permanent_delete(item,request.user)
        for item in Folder.objects.filter(owner=request.user,is_deleted=True).filter(Q(parent__isnull=True)|Q(parent__is_deleted=False)): permanent_delete(item,request.user)
    messages.success(request,"Trash emptied"); return redirect("files:trash")

@login_required
def search(request):
    query=request.GET.get("q","").strip(); type_filter=request.GET.get("type","all"); modified=request.GET.get("modified","any")
    owned_files=File.objects.active().filter(owner=request.user); owned_folders=Folder.objects.active().filter(owner=request.user)
    from apps.sharing.selectors.shared_items import accessible_ids
    shared_file_ids,shared_folder_ids=accessible_ids(request.user)
    files=File.objects.active().filter(Q(owner=request.user)|Q(pk__in=shared_file_ids)); folders=Folder.objects.active().filter(Q(owner=request.user)|Q(pk__in=shared_folder_ids))
    if query: files=files.filter(Q(display_name__icontains=query)|Q(extension__icontains=query)|Q(mime_type__icontains=query)); folders=folders.filter(name__icontains=query)
    if type_filter=="folders": files=files.none()
    elif type_filter!="all": files=[f for f in files if category(f.extension)==type_filter]; folders=folders.none()
    if modified!="any":
        from datetime import timedelta
        days={"today":1,"7":7,"30":30}.get(modified); cutoff=timezone.now()-timedelta(days=days) if days else None
        if cutoff: files=[f for f in files if f.updated_at>=cutoff]; folders=folders.filter(updated_at__gte=cutoff)
    items=[("folder",x) for x in folders]+[("file",x) for x in files]
    return render(request,"files/search.html",{"query":query,"items":items,"type_filter":type_filter,"modified":modified,"stats":usage_summary(request.user)})

@login_required
def preview(request,file_uuid):
    item=get_object_or_404(File.objects.active(),uuid=file_uuid)
    if not can_preview(request.user,item):raise Http404
    log(request.user,"view",item)
    return render(request,"files/preview.html",{"item":item,"kind":preview_kind(item),"stats":usage_summary(request.user)})

@login_required
@xframe_options_sameorigin
def preview_content(request,file_uuid):
    item=get_object_or_404(File.objects.active(),uuid=file_uuid)
    if not can_preview(request.user,item):raise Http404
    kind=preview_kind(item)
    if kind in ("image","pdf","audio","video"):
        try:return FileResponse(open_file(item),content_type=item.mime_type)
        except OSError:return HttpResponse(status=404)
    try:
        if kind=="csv": return render(request,"files/csv_preview.html",{"rows":csv_rows(item)})
        if kind=="spreadsheet":return render(request,"files/spreadsheet_preview.html",{"sheets":spreadsheet_sheets(item)})
        if kind=="document":return render(request,"files/text_preview.html",{"content":document_content(item),"document":True})
        if kind in ("json","text"): return render(request,"files/text_preview.html",{"content":text_content(item)})
    except PreviewError as exc:return render(request,"files/preview_error.html",{"message":str(exc)},status=422)
    return HttpResponse(status=415)

@login_required
def folder_tree(request):
    folders=Folder.objects.active().filter(owner=request.user).values("uuid","name","parent_id")
    return JsonResponse({"folders":list(folders)})

@login_required
@require_POST
def bulk_action(request):
    action=request.POST.get("action"); refs=request.POST.getlist("items"); selected=[]
    for ref in refs:
        try: kind,value=ref.split(":",1); selected.append((kind,_item(request.user,kind,value,action in ("restore","permanent_delete"))))
        except (ValueError,TypeError): continue
    if action=="download":
        temp=tempfile.TemporaryFile()
        with zipfile.ZipFile(temp,"w",zipfile.ZIP_DEFLATED) as archive:
            def add(kind,item,prefix=""):
                if kind=="file":
                    with open_file(item) as stream: archive.write(stream.name,prefix+item.display_name)
                else:
                    for f in item.files.active(): add("file",f,prefix+item.name+"/")
                    for child in item.children.active(): add("folder",child,prefix+item.name+"/")
            for pair in selected:add(*pair)
        temp.seek(0); return FileResponse(temp,as_attachment=True,filename=f"selected-files-{timezone.now():%Y-%m-%d}.zip")
    destination=_folder_for(request.user,request.POST.get("destination") or None) if action in ("move","copy") else None
    success=0
    with transaction.atomic():
        for kind,item in selected:
            try:
                if action=="delete": soft_delete(item,request.user)
                elif action=="move": move_service(item,destination,request.user,True)
                elif action=="copy": copy_file(item,destination,request.user) if kind=="file" else copy_folder(item,destination,request.user)
                elif action in ("star","unstar"):
                    kwargs={kind:item}
                    if action=="star": Favorite.objects.get_or_create(user=request.user,**kwargs)
                    else: Favorite.objects.filter(user=request.user,**kwargs).delete()
                elif action=="restore": restore_service(item,request.user)
                elif action=="permanent_delete": permanent_delete(item,request.user)
                success+=1
            except Exception: logger.exception("Bulk %s failed",action)
    messages.success(request,f"{success} item{'s' if success!=1 else ''} {action}d") if success else messages.error(request,"No items were changed")
    return redirect(request.POST.get("next") or "files:root")

@login_required
@require_POST
def upload_version(request,file_uuid):
    item=get_object_or_404(File.objects.active(),uuid=file_uuid)
    if not can_edit(request.user,item):raise Http404
    uploaded=request.FILES.get("file")
    if not uploaded:return JsonResponse({"ok":False,"error":"Choose a file."},status=400)
    try:replace_current(item,uploaded,request.user,request.POST.get("comment",""));messages.success(request,"New version uploaded")
    except Exception as exc:messages.error(request,str(exc))
    return redirect(request.POST.get("next") or reverse("files:preview",args=[item.uuid]))
@login_required
def download_version(request,version_uuid):
    version=get_object_or_404(FileVersion.objects.select_related("file","file__owner"),uuid=version_uuid)
    if permission_for(request.user,version.file) not in ("owner","editor"):raise Http404
    log(request.user,"version_download",version.file,{"version":version.version_number});return FileResponse(open_file(version),as_attachment=True,filename=f"v{version.version_number}_{version.file.display_name}",content_type=version.mime_type)
@login_required
def preview_version(request,version_uuid):
    version=get_object_or_404(FileVersion.objects.select_related("file"),uuid=version_uuid)
    if permission_for(request.user,version.file) not in ("owner","editor"):raise Http404
    if preview_kind(version) not in ("image","pdf","audio","video"):return render(request,"files/version_preview.html",{"version":version,"unsupported":True,"stats":usage_summary(request.user)})
    return FileResponse(open_file(version),content_type=version.mime_type)
@login_required
@require_POST
def restore_version_view(request,version_uuid):
    version=get_object_or_404(FileVersion.objects.select_related("file"),uuid=version_uuid)
    if permission_for(request.user,version.file) not in ("owner","editor"):raise Http404
    try:restore_version(version,request.user);messages.success(request,f"Version {version.version_number} restored as a new version")
    except Exception as exc:messages.error(request,str(exc))
    return redirect(request.POST.get("next") or reverse("files:preview",args=[version.file.uuid]))
