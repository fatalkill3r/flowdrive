import tempfile,zipfile
from django.contrib.auth.hashers import check_password
from django.db.models import F
from django.http import FileResponse,Http404
from django.shortcuts import get_object_or_404,render,redirect
from django.utils import timezone
from apps.files.models import File,Folder
from apps.files.services.preview import preview_kind
from apps.files.services.storage import open_file
from .models import ShareLink
from apps.activity.models import Activity
def _public_event(link,action,item): Activity.objects.create(user=link.created_by,action=action,object_type="folder" if isinstance(item,Folder) else "file",object_uuid=item.uuid,object_name=getattr(item,"name",getattr(item,"display_name","")),metadata={"public":True})

def _link(token):
    link=get_object_or_404(ShareLink.objects.select_related("file","folder","created_by"),token=token)
    if not link.available:return None
    return link
def _unlocked(request,link): return not link.password_hash or request.session.get(f"share_link_{link.uuid}") is True
def public_item(request,token,folder_uuid=None):
    link=_link(token)
    if not link:return render(request,"sharing/link_unavailable.html",status=410)
    if not _unlocked(request,link):
        if request.method=="POST" and check_password(request.POST.get("password",""),link.password_hash): request.session[f"share_link_{link.uuid}"]=True; return redirect(request.path)
        if request.method=="POST":
            from apps.audit.services.audit import record
            record("PUBLIC_LINK_PASSWORD_FAILED",obj=link.item,result="denied")
        return render(request,"sharing/password.html",{"invalid":request.method=="POST"})
    ShareLink.objects.filter(pk=link.pk).update(access_count=F("access_count")+1,last_accessed_at=timezone.now())
    _public_event(link,"public_access",link.item)
    if link.file:return render(request,"sharing/public_file.html",{"link":link,"item":link.file,"kind":preview_kind(link.file)})
    root=link.folder; folder=root
    if folder_uuid:
        folder=get_object_or_404(Folder.objects.active(),uuid=folder_uuid)
        node=folder; contained=False
        while node:
            if node.pk==root.pk:contained=True;break
            node=node.parent
        if not contained:raise Http404
    return render(request,"sharing/public_folder.html",{"link":link,"root":root,"folder":folder,"folders":folder.children.active(),"files":folder.files.active()})
def public_file(request,token,file_uuid,download=False):
    link=_link(token)
    if not link or not _unlocked(request,link):raise Http404
    item=get_object_or_404(File.objects.active(),uuid=file_uuid); allowed=item.pk==link.file_id if link.file_id else False
    if link.folder_id:
        node=item.folder
        while node:
            if node.pk==link.folder_id:allowed=True;break
            node=node.parent
    if not allowed or (download and not link.allow_download):raise Http404
    safe_preview=preview_kind(item) in ("image","pdf","audio","video")
    if not download and not safe_preview:raise Http404
    if download:_public_event(link,"public_download",item)
    return FileResponse(open_file(item),as_attachment=download,filename=item.display_name if download else None,content_type=item.mime_type)
def public_folder_zip(request,token):
    link=_link(token)
    if not link or not link.folder_id or not link.allow_download or not _unlocked(request,link):raise Http404
    temp=tempfile.TemporaryFile()
    with zipfile.ZipFile(temp,"w",zipfile.ZIP_DEFLATED) as archive:
        def add(folder,prefix=""):
            for item in folder.files.active():
                with open_file(item) as stream:archive.write(stream.name,prefix+item.display_name)
            for child in folder.children.active():add(child,prefix+child.name+"/")
        add(link.folder,link.folder.name+"/")
    temp.seek(0);return FileResponse(temp,as_attachment=True,filename=f"{link.folder.name}.zip")
