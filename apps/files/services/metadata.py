import os
DOCUMENTS={"pdf","doc","docx","xls","xlsx","ppt","pptx","txt","csv","md","json","xml","log","sh","py"}
IMAGES={"jpg","jpeg","png","gif","webp"}; VIDEOS={"mp4","webm"}; AUDIO={"mp3","wav","ogg","m4a"}; ARCHIVES={"zip","rar","7z","tar","gz"}
def category(extension):
    ext=extension.lower()
    if ext in DOCUMENTS:return "documents"
    if ext in IMAGES:return "images"
    if ext in VIDEOS:return "videos"
    if ext in AUDIO:return "audio"
    if ext in ARCHIVES:return "archives"
    return "other"
def unique_name(model, owner, container_field, container, desired, name_field, exclude=None):
    desired=desired.strip(); stem,ext=os.path.splitext(desired); candidate=desired; n=1
    qs=model.objects.active().filter(owner=owner, **{container_field:container})
    if exclude: qs=qs.exclude(pk=exclude.pk)
    while qs.filter(**{f"{name_field}__iexact":candidate}).exists(): candidate=f"{stem} ({n}){ext}"; n+=1
    return candidate
def valid_name(name): return bool(name and len(name)<=255 and name not in (".","..") and not any(x in name for x in ("/","\\","\0")))
