from apps.sharing.models import SharePermission
def accessible_ids(user):
    file_ids=set();folder_ids=set()
    shares=SharePermission.objects.filter(shared_with=user).select_related("file","folder")
    def walk(folder):
        if folder.pk in folder_ids:return
        folder_ids.add(folder.pk);file_ids.update(folder.files.active().values_list("pk",flat=True))
        for child in folder.children.active():walk(child)
    for share in shares:
        if share.file_id:file_ids.add(share.file_id)
        elif share.folder_id:walk(share.folder)
    return file_ids,folder_ids
