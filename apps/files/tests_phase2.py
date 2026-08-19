import tempfile
from pathlib import Path
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from .models import File, Folder, Favorite

class Phase2Tests(TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.override=override_settings(FILEBOX_STORAGE_ROOT=Path(self.temp.name)); self.override.enable()
        U=get_user_model(); self.a=U.objects.create_user("phase2a",password="pass123456"); self.b=U.objects.create_user("phase2b",password="pass123456"); self.client.force_login(self.a)
        self.root=Folder.objects.create(owner=self.a,name="Projects"); self.child=Folder.objects.create(owner=self.a,name="Documents",parent=self.root)
    def tearDown(self): self.override.disable(); self.temp.cleanup()
    def upload(self,name="Architecture.pdf",content=b"phase two"):
        response=self.client.post(reverse("files:upload"),{"folder_uuid":str(self.root.uuid),"files":SimpleUploadedFile(name,content,"application/pdf")})
        self.assertEqual(response.status_code,200); return File.objects.active().filter(owner=self.a).latest("created_at")
    def test_file_rename(self):
        f=self.upload(); self.client.post(reverse("files:rename",args=["file",f.uuid]),{"name":"Final.pdf"}); f.refresh_from_db(); self.assertEqual(f.display_name,"Final.pdf"); self.assertEqual(f.extension,"pdf")
    def test_folder_rename(self):
        self.client.post(reverse("files:rename",args=["folder",self.child.uuid]),{"name":"Specs"}); self.child.refresh_from_db(); self.assertEqual(self.child.name,"Specs")
    def test_rename_duplicate_rejected(self):
        Folder.objects.create(owner=self.a,parent=self.root,name="Specs"); self.client.post(reverse("files:rename",args=["folder",self.child.uuid]),{"name":"Specs"}); self.child.refresh_from_db(); self.assertEqual(self.child.name,"Documents")
    def test_unauthorized_rename(self):
        foreign=Folder.objects.create(owner=self.b,name="Private"); self.assertEqual(self.client.post(reverse("files:rename",args=["folder",foreign.uuid]),{"name":"Hacked"}).status_code,404)
    def test_file_move(self):
        f=self.upload(); self.client.post(reverse("files:move",args=["file",f.uuid]),{"destination":str(self.child.uuid)}); f.refresh_from_db(); self.assertEqual(f.folder,self.child)
    def test_folder_move_and_circular_prevention(self):
        other=Folder.objects.create(owner=self.a,name="Other"); self.client.post(reverse("files:move",args=["folder",self.child.uuid]),{"destination":str(other.uuid)}); self.child.refresh_from_db(); self.assertEqual(self.child.parent,other)
        self.client.post(reverse("files:move",args=["folder",other.uuid]),{"destination":str(self.child.uuid)}); other.refresh_from_db(); self.assertIsNone(other.parent)
    def test_unauthorized_move_destination(self):
        f=self.upload(); foreign=Folder.objects.create(owner=self.b,name="Private"); response=self.client.post(reverse("files:move",args=["file",f.uuid]),{"destination":str(foreign.uuid)}); self.assertEqual(response.status_code,404)
    def test_file_copy_has_independent_storage(self):
        f=self.upload(); self.client.post(reverse("files:copy",args=["file",f.uuid]),{"destination":str(self.root.uuid)}); copies=File.objects.active().filter(owner=self.a); self.assertEqual(copies.count(),2); self.assertNotEqual(copies[0].storage_path,copies[1].storage_path); self.assertIn("(1)",copies.exclude(pk=f.pk).get().display_name)
    def test_recursive_folder_copy(self):
        self.client.post(reverse("files:upload"),{"folder_uuid":str(self.child.uuid),"files":SimpleUploadedFile("note.txt",b"hello")}); self.client.post(reverse("files:copy",args=["folder",self.root.uuid]),{}); copied=Folder.objects.get(owner=self.a,parent=None,name="Projects (1)"); self.assertEqual(copied.children.get().files.active().count(),1)
    def test_star_unstar_and_user_isolation(self):
        f=self.upload(); url=reverse("files:star",args=["file",f.uuid]); self.client.post(url); self.assertTrue(Favorite.objects.filter(user=self.a,file=f).exists()); self.assertFalse(Favorite.objects.filter(user=self.b,file=f).exists()); self.client.post(url); self.assertFalse(Favorite.objects.exists())
    def test_search_file_folder_filter_and_isolation(self):
        self.upload("Architecture.pdf"); Folder.objects.create(owner=self.b,name="Architecture Secret")
        response=self.client.get(reverse("files:search"),{"q":"Architecture"}); self.assertContains(response,"Architecture.pdf"); self.assertNotContains(response,"Secret")
        response=self.client.get(reverse("files:search"),{"q":"Projects","type":"folders"}); self.assertContains(response,"Projects")
    def test_authorized_preview_and_content(self):
        f=self.upload("notes.txt",b"safe <script>text</script>"); self.assertContains(self.client.get(reverse("files:preview",args=[f.uuid])),"notes.txt"); content=self.client.get(reverse("files:preview_content",args=[f.uuid])); self.assertContains(content,"&lt;script&gt;")
    def test_preview_idor(self):
        foreign=File.objects.create(owner=self.b,display_name="secret.txt",stored_name="foreign",storage_path="fo/foreign",mime_type="text/plain",extension="txt",size=1,checksum="x"*64); self.assertEqual(self.client.get(reverse("files:preview",args=[foreign.uuid])).status_code,404)
    def test_unauthorized_copy_restore_and_permanent_delete(self):
        foreign=File.objects.create(owner=self.b,display_name="secret.txt",stored_name="foreign2",storage_path="fo/foreign2",mime_type="text/plain",extension="txt",size=1,checksum="x"*64,is_deleted=True)
        self.assertEqual(self.client.post(reverse("files:copy",args=["file",foreign.uuid])).status_code,404); self.assertEqual(self.client.post(reverse("files:restore",args=["file",foreign.uuid])).status_code,404); self.assertEqual(self.client.post(reverse("files:permanent_delete",args=["file",foreign.uuid])).status_code,404)
    def test_restore_with_name_conflict(self):
        f=self.upload(); self.client.post(reverse("files:delete_file",args=[f.uuid])); self.upload(); self.client.post(reverse("files:restore",args=["file",f.uuid])); f.refresh_from_db(); self.assertFalse(f.is_deleted); self.assertIn("(1)",f.display_name)
    def test_permanent_delete_removes_bytes_and_record(self):
        f=self.upload(); path=Path(self.temp.name)/f.storage_path; self.client.post(reverse("files:delete_file",args=[f.uuid])); self.client.post(reverse("files:permanent_delete",args=["file",f.uuid])); self.assertFalse(File.objects.filter(pk=f.pk).exists()); self.assertFalse(path.exists())
    def test_empty_trash(self):
        f=self.upload(); self.client.post(reverse("files:delete_file",args=[f.uuid])); self.client.post(reverse("files:empty_trash")); self.assertFalse(File.objects.filter(pk=f.pk).exists())
    def test_bulk_move(self):
        f1=self.upload("a.txt"); f2=self.upload("b.txt"); self.client.post(reverse("files:bulk"),{"action":"move","destination":str(self.child.uuid),"items":[f"file:{f1.uuid}",f"file:{f2.uuid}"]}); self.assertEqual(File.objects.filter(folder=self.child,is_deleted=False).count(),2)
    def test_bulk_delete(self):
        f1=self.upload("a.txt"); f2=self.upload("b.txt"); self.client.post(reverse("files:bulk"),{"action":"delete","items":[f"file:{f1.uuid}",f"file:{f2.uuid}"]}); self.assertEqual(File.objects.filter(is_deleted=True).count(),2)
    def test_malicious_names_do_not_control_storage_path(self):
        f=self.upload("../../etc-passwd.txt"); self.assertNotIn("etc-passwd",f.storage_path); response=self.client.post(reverse("files:rename",args=["file",f.uuid]),{"name":"../escape.txt"}); f.refresh_from_db(); self.assertNotEqual(f.display_name,"../escape.txt")
