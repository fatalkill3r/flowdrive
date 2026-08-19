from apps.files.models import File, Folder
from apps.sharing.models import SharePermission
RANK={"viewer":1,"downloader":2,"editor":3,"owner":4}

def _folder_chain(folder):
    chain=[]
    while folder: chain.append(folder); folder=folder.parent
    return chain
def permission_for(user,item):
    if not user or not user.is_authenticated:return None
    if not item.owner.is_active:return None
    if item.owner_id==user.id:return "owner"
    if isinstance(item,File):
        direct=SharePermission.objects.filter(shared_with=user,file=item).values_list("permission",flat=True).first()
        if direct:return direct
        folder=item.folder
    else: folder=item
    # Nearest explicit folder share wins, providing specific-over-inherited precedence.
    for ancestor in _folder_chain(folder):
        value=SharePermission.objects.filter(shared_with=user,folder=ancestor).values_list("permission",flat=True).first()
        if value:return value
    return None
def can_view(user,item): return permission_for(user,item) is not None and not item.is_deleted
def can_preview(user,item): return can_view(user,item)
def can_download(user,item): return RANK.get(permission_for(user,item),0)>=RANK["downloader"] and not item.is_deleted
def can_edit(user,item): return RANK.get(permission_for(user,item),0)>=RANK["editor"] and not item.is_deleted
def can_upload_to_folder(user,folder): return can_edit(user,folder)
def can_share(user,item): return bool(user.is_authenticated and item.owner_id==user.id and not item.is_deleted)
def can_delete(user,item): return bool(user.is_authenticated and item.owner_id==user.id and not item.is_deleted)
def shared_root(user,item):
    folder=item.folder if isinstance(item,File) else item; root=None
    for ancestor in reversed(_folder_chain(folder)):
        if SharePermission.objects.filter(shared_with=user,folder=ancestor).exists(): root=ancestor; break
    return root
def within_same_shared_tree(user,item,destination):
    root=shared_root(user,item); return bool(root and destination and root in _folder_chain(destination))
