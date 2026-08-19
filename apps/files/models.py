import uuid
from django.conf import settings
from django.db import models

class ActiveManager(models.Manager):
    def active(self): return self.get_queryset().filter(is_deleted=False)

class Folder(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=255)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="folders", db_index=True)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.CASCADE, related_name="children", db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    objects = ActiveManager()
    class Meta:
        ordering = ["name"]
        constraints = [models.UniqueConstraint(fields=["owner", "parent", "name"], condition=models.Q(is_deleted=False), name="unique_active_folder_name")]
        indexes = [models.Index(fields=["owner", "parent", "is_deleted"])]
    def __str__(self): return self.name
    def breadcrumbs(self):
        result, node = [], self
        while node: result.append(node); node = node.parent
        return list(reversed(result))

class File(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="files", db_index=True)
    folder = models.ForeignKey(Folder, null=True, blank=True, on_delete=models.CASCADE, related_name="files", db_index=True)
    display_name = models.CharField(max_length=255)
    stored_name = models.CharField(max_length=80, unique=True)
    storage_path = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=255, blank=True)
    extension = models.CharField(max_length=32, blank=True)
    size = models.PositiveBigIntegerField()
    checksum = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    current_version_number = models.PositiveIntegerField(default=1)
    objects = ActiveManager()
    class Meta:
        ordering = ["display_name"]
        indexes = [models.Index(fields=["owner", "folder", "is_deleted"]), models.Index(fields=["owner", "display_name"]), models.Index(fields=["owner", "extension"]), models.Index(fields=["owner", "updated_at"])]
    @property
    def type_label(self): return self.extension.upper() if self.extension else "FILE"
    @property
    def icon(self):
        ext = self.extension.lower()
        if ext == "pdf": return "file-earmark-pdf"
        if ext in ("doc", "docx"): return "file-earmark-word"
        if ext in ("xls", "xlsx", "csv"): return "file-earmark-excel"
        if ext in ("ppt", "pptx"): return "file-earmark-ppt"
        if ext in ("png", "jpg", "jpeg", "gif", "webp", "svg"): return "file-earmark-image"
        if ext in ("mp3", "wav", "ogg"): return "file-earmark-music"
        if ext in ("mp4", "mov", "webm"): return "file-earmark-play"
        if ext in ("zip", "rar", "7z", "tar", "gz"): return "file-earmark-zip"
        if ext in ("py", "sh", "js", "html", "css", "json"): return "file-earmark-code"
        return "file-earmark"

class FileVersion(models.Model):
    uuid=models.UUIDField(default=uuid.uuid4,unique=True,editable=False)
    file=models.ForeignKey(File,on_delete=models.CASCADE,related_name="versions",db_index=True)
    version_number=models.PositiveIntegerField()
    storage_path=models.CharField(max_length=255)
    stored_name=models.CharField(max_length=80,unique=True)
    size=models.PositiveBigIntegerField();checksum=models.CharField(max_length=64)
    mime_type=models.CharField(max_length=255,blank=True);extension=models.CharField(max_length=32,blank=True)
    uploaded_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,related_name="file_versions")
    created_at=models.DateTimeField(auto_now_add=True,db_index=True);comment=models.CharField(max_length=500,blank=True)
    class Meta:
        ordering=["-version_number"]
        constraints=[models.UniqueConstraint(fields=["file","version_number"],name="unique_file_version_number")]
        indexes=[models.Index(fields=["file","version_number"])]

class Favorite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favorites")
    file = models.ForeignKey(File, null=True, blank=True, on_delete=models.CASCADE, related_name="favorites")
    folder = models.ForeignKey(Folder, null=True, blank=True, on_delete=models.CASCADE, related_name="favorites")
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [
            models.CheckConstraint(condition=(models.Q(file__isnull=False, folder__isnull=True) | models.Q(file__isnull=True, folder__isnull=False)), name="favorite_exactly_one_item"),
            models.UniqueConstraint(fields=["user", "file"], name="unique_file_favorite"),
            models.UniqueConstraint(fields=["user", "folder"], name="unique_folder_favorite"),
        ]
