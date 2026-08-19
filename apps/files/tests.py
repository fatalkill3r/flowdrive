import hashlib, tempfile
from pathlib import Path
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from .models import File, Folder

class FileManagementTests(TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.settings = override_settings(FILEBOX_STORAGE_ROOT=Path(self.temp.name))
        self.settings.enable()
        User = get_user_model(); self.alice=User.objects.create_user("alice", password="strong-pass-123"); self.bob=User.objects.create_user("bob", password="strong-pass-123")
    def tearDown(self): self.settings.disable(); self.temp.cleanup()
    def test_authentication_required(self):
        self.assertRedirects(self.client.get(reverse("files:root")), f"{reverse('accounts:login')}?next={reverse('files:root')}")
    def test_folder_creation(self):
        self.client.force_login(self.alice); response=self.client.post(reverse("files:create_folder"), {"name":"Projects"})
        self.assertEqual(response.status_code, 302); self.assertTrue(Folder.objects.filter(owner=self.alice, name="Projects").exists())
    def test_dashboard_and_file_browser_render(self):
        self.client.force_login(self.alice)
        self.assertContains(self.client.get(reverse("dashboard:home")), "Good")
        self.assertContains(self.client.get(reverse("files:root")), "This folder is empty")
    def test_duplicate_folder_names_are_rejected_case_insensitively(self):
        Folder.objects.create(owner=self.alice, name="Projects"); self.client.force_login(self.alice); self.client.post(reverse("files:create_folder"), {"name":"projects"})
        self.assertEqual(Folder.objects.filter(owner=self.alice).count(), 1)
    def test_folder_idor_is_denied(self):
        secret=Folder.objects.create(owner=self.bob,name="Private"); self.client.force_login(self.alice)
        self.assertEqual(self.client.get(reverse("files:folder", args=[secret.uuid])).status_code,404)
    def test_upload_stores_checksum_and_private_name(self):
        self.client.force_login(self.alice); content=b"hello FlowDrive"
        response=self.client.post(reverse("files:upload"), {"files":SimpleUploadedFile("report.txt",content,"text/plain")})
        self.assertEqual(response.status_code,200); item=File.objects.get(); self.alice.profile.refresh_from_db(); self.assertEqual(item.checksum,hashlib.sha256(content).hexdigest()); self.assertNotIn("report",item.storage_path); self.assertEqual(self.alice.profile.storage_used,len(content))
    def test_file_download_idor_is_denied(self):
        item=File.objects.create(owner=self.bob,display_name="secret.txt",stored_name="abc",storage_path="ab/abc",mime_type="text/plain",extension="txt",size=1,checksum="x"*64)
        self.client.force_login(self.alice); self.assertEqual(self.client.get(reverse("files:download",args=[item.uuid])).status_code,404)
    def test_file_soft_delete_updates_usage(self):
        self.client.force_login(self.alice); self.client.post(reverse("files:upload"), {"files":SimpleUploadedFile("a.txt",b"hello")}); item=File.objects.get()
        self.client.post(reverse("files:delete_file",args=[item.uuid])); item.refresh_from_db(); self.alice.profile.refresh_from_db(); self.assertTrue(item.is_deleted); self.assertIsNotNone(item.deleted_at); self.assertEqual(self.alice.profile.storage_used,5)
    def test_upload_respects_quota(self):
        self.alice.profile.storage_quota=3; self.alice.profile.save(); self.client.force_login(self.alice)
        response=self.client.post(reverse("files:upload"), {"files":SimpleUploadedFile("large.txt",b"1234")})
        self.assertEqual(response.status_code,400); self.assertFalse(File.objects.exists())
