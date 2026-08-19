import os
from django.db import transaction
from django.utils import timezone
from apps.activity.models import Activity
from apps.accounts.models import Profile
from apps.files.models import File, Folder
from .metadata import unique_name, valid_name
from .storage import copy_physical, physical_delete

def log(user, action, item, metadata=None):
    Activity.objects.create(user=user, action=action, object_type="folder" if isinstance(item,Folder) else "file", object_uuid=item.uuid, object_name=item.name if isinstance(item,Folder) else item.display_name, metadata=metadata or {})
def rename(item,new_name,user):
    if not valid_name(new_name): raise ValueError("Enter a valid name without slashes.")
    field="name" if isinstance(item,Folder) else "display_name"; container="parent" if isinstance(item,Folder) else "folder"
    model=type(item); value=getattr(item,container)
    if model.objects.active().filter(owner=item.owner,**{container:value,f"{field}__iexact":new_name}).exclude(pk=item.pk).exists(): raise ValueError("An item with this name already exists here.")
    old=getattr(item,field); setattr(item,field,new_name.strip())
    if isinstance(item,File): item.extension=os.path.splitext(new_name)[1].lstrip(".").lower()[:32]
    item.save(); log(user,"rename",item,{"old_name":old,"new_name":new_name})
def descendants(folder):
    found=[]
    for child in folder.children.active(): found.append(child); found.extend(descendants(child))
    return found
def move(item,destination,user,keep_both=False):
    if isinstance(item,Folder):
        if destination and (destination.pk==item.pk or destination in descendants(item)): raise ValueError("A folder cannot be moved into itself or one of its subfolders.")
        field,container="name","parent"
    else: field,container="display_name","folder"
    name=getattr(item,field); model=type(item)
    if model.objects.active().filter(owner=item.owner,**{container:destination,f"{field}__iexact":name}).exclude(pk=item.pk).exists():
        if keep_both: setattr(item,field,unique_name(model,item.owner,container,destination,name,field,item))
        else: raise ValueError("An item with this name already exists in the destination.")
    setattr(item,container,destination); item.save(); log(user,"move",item,{"destination":str(destination.uuid) if destination else "root"})
def copy_file(item,destination,user):
    name=unique_name(File,user,"folder",destination,item.display_name,"display_name")
    token,path=copy_physical(item,user)
    copied=File.objects.create(owner=user,folder=destination,display_name=name,stored_name=token,storage_path=path,mime_type=item.mime_type,extension=item.extension,size=item.size,checksum=item.checksum)
    log(user,"copy",copied,{"source_uuid":str(item.uuid)}); return copied
def copy_folder(item,destination,user):
    name=unique_name(Folder,user,"parent",destination,item.name,"name")
    copied=Folder.objects.create(owner=user,parent=destination,name=name); log(user,"copy",copied,{"source_uuid":str(item.uuid)})
    for file in item.files.active(): copy_file(file,copied,user)
    for child in item.children.active(): copy_folder(child,copied,user)
    return copied
def restore(item,user):
    if isinstance(item,Folder):
        parent=item.parent if item.parent and not item.parent.is_deleted else None; item.name=unique_name(Folder,user,"parent",parent,item.name,"name",item); item.parent=parent
        def restore_tree(folder):
            folder.is_deleted=False; folder.deleted_at=None; folder.save()
            for f in folder.files.filter(is_deleted=True): f.is_deleted=False; f.deleted_at=None; f.save()
            for child in folder.children.filter(is_deleted=True): restore_tree(child)
        restore_tree(item)
    else:
        folder=item.folder if item.folder and not item.folder.is_deleted else None; item.display_name=unique_name(File,user,"folder",folder,item.display_name,"display_name",item); item.folder=folder; item.is_deleted=False; item.deleted_at=None; item.save()
    log(user,"restore",item)
def permanent_delete(item,user):
    if isinstance(item,Folder):
        for f in list(item.files.all()): permanent_delete(f,user)
        for child in item.children.all(): permanent_delete(child,user)
    else:
        total=item.size+sum(item.versions.values_list("size",flat=True));physical_delete(item)
        for version in item.versions.all():physical_delete(version)
        profile=Profile.objects.select_for_update().get(user=item.owner);profile.storage_used=max(0,profile.storage_used-total);profile.save(update_fields=["storage_used"])
    log(user,"permanent_delete",item)
    from apps.audit.services.audit import record
    record("FILE_PERMANENTLY_DELETED",user,item);item.delete()
def soft_delete(item,user):
    from .storage import delete_file as adjust_usage
    if isinstance(item,Folder):
        for f in item.files.active(): soft_delete(f,user)
        for child in item.children.active(): soft_delete(child,user)
    item.is_deleted=True; item.deleted_at=timezone.now(); item.save(update_fields=["is_deleted","deleted_at","updated_at"]); log(user,"delete",item)
