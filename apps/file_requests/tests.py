import tempfile
from datetime import timedelta
from pathlib import Path
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase,override_settings
from django.urls import reverse
from django.utils import timezone
from apps.files.models import File,Folder
from .models import UploadRequest
class UploadRequestTests(TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.over=override_settings(FILEBOX_STORAGE_ROOT=Path(self.temp.name));self.over.enable();self.user=get_user_model().objects.create_user("requester",password="pass123456");self.folder=Folder.objects.create(owner=self.user,name="Incoming");self.obj=UploadRequest.objects.create(created_by=self.user,destination_folder=self.folder,title="Documents")
    def tearDown(self):self.over.disable();self.temp.cleanup()
    def post(self,name="report.txt",content=b"hello",**extra):return self.client.post(reverse("public_requests:page",args=[self.obj.token]),{"uploader_name":"External","files":SimpleUploadedFile(name,content),**extra})
    def test_valid_upload_uses_bound_destination_and_owner_quota(self):
        self.assertEqual(self.post().status_code,200);item=File.objects.get();self.assertEqual(item.folder,self.folder);self.assertEqual(item.owner,self.user);self.user.profile.refresh_from_db();self.assertEqual(self.user.profile.storage_used,5)
    def test_invalid_expired_disabled_tokens_denied(self):
        self.assertEqual(self.client.get("/r/invalid-token/").status_code,404);self.obj.expires_at=timezone.now()-timedelta(seconds=1);self.obj.save();self.assertEqual(self.post().status_code,410);self.obj.expires_at=None;self.obj.is_active=False;self.obj.save();self.assertEqual(self.post().status_code,410)
    def test_password_session(self):
        self.obj.password_hash=make_password("secret");self.obj.save();url=reverse("public_requests:page",args=[self.obj.token]);self.assertContains(self.client.post(url,{"password":"bad"}),"incorrect");self.assertEqual(self.client.post(url,{"password":"secret"}).status_code,302);self.assertEqual(self.post().status_code,200)
    def test_quota_and_malicious_filename(self):
        self.user.profile.storage_quota=3;self.user.profile.save();self.assertEqual(self.post(content=b"1234").status_code,400);self.user.profile.storage_quota=100;self.user.profile.save();self.post(name="../../etc/passwd");item=File.objects.get();self.assertNotIn("passwd",item.storage_path);self.assertEqual(item.folder,self.folder)
    def test_duplicate_names_keep_both(self):self.post();self.post();self.assertEqual(set(File.objects.values_list("display_name",flat=True)),{"report.txt","report (1).txt"})
