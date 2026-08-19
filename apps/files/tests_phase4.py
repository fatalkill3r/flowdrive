import tempfile
from pathlib import Path
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase,override_settings
from django.urls import reverse
from apps.files.models import File,FileVersion
from apps.files.services.versioning import replace_current,restore_version,prune_versions
from apps.adminpanel.models import SystemSettings
class VersioningTests(TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.over=override_settings(FILEBOX_STORAGE_ROOT=Path(self.temp.name),FILEBOX_MAX_FILE_VERSIONS=3);self.over.enable();SystemSettings.objects.create(singleton=True,max_file_versions=3);U=get_user_model();self.owner=U.objects.create_user("versionowner",password="pass123456");self.other=U.objects.create_user("versionother",password="pass123456");self.client.force_login(self.owner);self.client.post(reverse("files:upload"),{"files":SimpleUploadedFile("doc.txt",b"v1")});self.file=File.objects.get()
    def tearDown(self):self.over.disable();self.temp.cleanup()
    def test_replace_creates_history_and_quota_includes_versions(self):
        replace_current(self.file,SimpleUploadedFile("doc.txt",b"version-two"),self.owner);self.file.refresh_from_db();self.owner.profile.refresh_from_db();self.assertEqual(self.file.current_version_number,2);self.assertEqual(self.file.versions.get().version_number,1);self.assertEqual(self.owner.profile.storage_used,2+11)
    def test_restore_creates_new_current_without_destroying_history(self):
        replace_current(self.file,SimpleUploadedFile("doc.txt",b"v2"),self.owner);old=self.file.versions.get(version_number=1);restore_version(old,self.owner);self.file.refresh_from_db();self.assertEqual(self.file.current_version_number,3);self.assertEqual(set(self.file.versions.values_list("version_number",flat=True)),{1,2});self.assertEqual(self.file.checksum,old.checksum)
    def test_version_access_is_owner_or_editor_only(self):
        replace_current(self.file,SimpleUploadedFile("doc.txt",b"v2"),self.owner);v=self.file.versions.get();self.client.force_login(self.other);self.assertEqual(self.client.get(reverse("files:download_version",args=[v.uuid])).status_code,404);self.assertEqual(self.client.post(reverse("files:restore_version",args=[v.uuid])).status_code,404)
    def test_quota_blocks_new_version(self):
        self.owner.profile.storage_quota=3;self.owner.profile.save();self.client.post(reverse("files:upload_version",args=[self.file.uuid]),{"file":SimpleUploadedFile("doc.txt",b"too-large")});self.assertFalse(FileVersion.objects.exists())
    def test_retention_prunes_oldest_and_releases_quota(self):
        for value in (b"v2",b"v3",b"v4"):replace_current(self.file,SimpleUploadedFile("doc.txt",value),self.owner)
        self.assertLessEqual(self.file.versions.count(),2);self.assertNotIn(1,self.file.versions.values_list("version_number",flat=True))
    def test_trash_counts_until_permanent_delete(self):
        self.owner.profile.refresh_from_db();before=self.owner.profile.storage_used;self.client.post(reverse("files:delete_file",args=[self.file.uuid]));self.owner.profile.refresh_from_db();self.assertEqual(self.owner.profile.storage_used,before);self.client.post(reverse("files:permanent_delete",args=["file",self.file.uuid]));self.owner.profile.refresh_from_db();self.assertEqual(self.owner.profile.storage_used,0)
