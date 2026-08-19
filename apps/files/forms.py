import os
from django import forms
from django.core.exceptions import ValidationError
from .models import Folder

class FolderForm(forms.ModelForm):
    class Meta: model = Folder; fields = ["name"]
    def __init__(self, *args, owner=None, parent=None, **kwargs): super().__init__(*args, **kwargs); self.owner=owner; self.parent=parent
    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        if name in (".", "..") or any(x in name for x in ("/", "\\", "\0")): raise ValidationError("Enter a valid folder name without slashes.")
        if self.owner and Folder.objects.active().filter(owner=self.owner, parent=self.parent, name__iexact=name).exists(): raise ValidationError("A folder with this name already exists here.")
        return name

class MultipleInput(forms.ClearableFileInput): allow_multiple_selected = True
class MultipleFileField(forms.FileField):
    def clean(self, data, initial=None):
        clean_one = super().clean
        return [clean_one(item, initial) for item in data] if isinstance(data, (list, tuple)) else [clean_one(data, initial)]
class UploadForm(forms.Form):
    files = MultipleFileField(widget=MultipleInput())
    def clean_files(self):
        uploaded = self.cleaned_data["files"]
        for item in uploaded:
            name = os.path.basename(item.name)
            if not name or len(name) > 255: raise ValidationError("Each filename must be between 1 and 255 characters.")
        return uploaded
