import tempfile
from datetime import timedelta
from pathlib import Path
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase,override_settings
from django.urls import reverse
from django.utils import timezone
from apps.files.models import File,Folder,Favorite
from apps.sharing.models import SharePermission,ShareLink
from apps.sharing.services.permissions import permission_for,can_view,can_download,can_edit
from django.conf import settings

class SharingTests(TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.over=override_settings(FILEBOX_STORAGE_ROOT=Path(self.temp.name));self.over.enable()
        U=get_user_model();self.owner=U.objects.create_user("owner",email="owner@example.com",password="pass123456",first_name="Olivia");self.member=U.objects.create_user("member",email="member@example.com",password="pass123456",first_name="Morgan");self.stranger=U.objects.create_user("stranger",password="pass123456")
        self.root=Folder.objects.create(owner=self.owner,name="Root");self.a=Folder.objects.create(owner=self.owner,parent=self.root,name="A");self.b=Folder.objects.create(owner=self.owner,parent=self.a,name="B");self.sibling=Folder.objects.create(owner=self.owner,parent=self.root,name="Private")
        self.client.force_login(self.owner);self.client.post(reverse("files:upload"),{"folder_uuid":str(self.b.uuid),"files":SimpleUploadedFile("diagram.png",b"image-bytes","image/png")});self.file=File.objects.get(display_name="diagram.png")
    def tearDown(self):self.over.disable();self.temp.cleanup()
    def share(self,item,permission="viewer"):
        return SharePermission.objects.create(shared_by=self.owner,shared_with=self.member,permission=permission,**({"folder":item} if isinstance(item,Folder) else {"file":item}))
    def test_direct_permission_levels(self):
        share=self.share(self.file,"viewer");self.assertTrue(can_view(self.member,self.file));self.assertFalse(can_download(self.member,self.file));self.assertFalse(can_edit(self.member,self.file));share.permission="downloader";share.save();self.assertTrue(can_download(self.member,self.file));self.assertFalse(can_edit(self.member,self.file));share.permission="editor";share.save();self.assertTrue(can_edit(self.member,self.file))
    def test_folder_inheritance_and_private_boundary(self):
        self.share(self.a,"viewer");self.assertTrue(can_view(self.member,self.a));self.assertTrue(can_view(self.member,self.b));self.assertTrue(can_view(self.member,self.file));self.assertFalse(can_view(self.member,self.root));self.assertFalse(can_view(self.member,self.sibling))
    def test_specific_override_wins(self):
        self.share(self.a,"viewer");self.share(self.b,"editor");self.assertEqual(permission_for(self.member,self.a),"viewer");self.assertEqual(permission_for(self.member,self.b),"editor");self.assertEqual(permission_for(self.member,self.file),"editor")
    def test_share_create_update_and_self_share(self):
        url=reverse("sharing:dialog",args=["file",self.file.uuid]);response=self.client.post(url,{"user_id":self.member.id,"permission":"viewer"});self.assertEqual(response.status_code,200);self.client.post(url,{"user_id":self.member.id,"permission":"editor"});self.assertEqual(SharePermission.objects.count(),1);self.assertEqual(SharePermission.objects.get().permission,"editor");self.assertEqual(self.client.post(url,{"user_id":self.owner.id,"permission":"viewer"}).status_code,400)
    def test_share_action_is_available_in_list_and_grid_markup(self):
        self.client.force_login(self.owner); response=self.client.get(reverse("files:folder",args=[self.b.uuid])); self.assertGreaterEqual(response.content.decode().count("share-trigger"),2)
    def test_right_click_share_command_is_wired(self):
        script=(settings.BASE_DIR/"static/js/app.js").read_text();self.assertIn("cmd==='share')row.querySelector('.share-trigger')?.click()",script)
    def test_owner_only_share_management(self):
        self.share(self.file);self.client.force_login(self.member);self.assertEqual(self.client.get(reverse("sharing:dialog",args=["file",self.file.uuid])).status_code,404)
    def test_viewer_preview_denied_download_and_edit(self):
        self.share(self.file,"viewer");self.client.force_login(self.member);self.assertEqual(self.client.get(reverse("files:preview",args=[self.file.uuid])).status_code,200);self.assertEqual(self.client.get(reverse("files:download",args=[self.file.uuid])).status_code,404);self.assertEqual(self.client.post(reverse("files:rename",args=["file",self.file.uuid]),{"name":"hacked.png"}).status_code,404)
    def test_downloader_can_download_not_edit(self):
        self.share(self.file,"downloader");self.client.force_login(self.member);self.assertEqual(self.client.get(reverse("files:download",args=[self.file.uuid])).status_code,200);self.assertEqual(self.client.post(reverse("files:rename",args=["file",self.file.uuid]),{"name":"hacked.png"}).status_code,404)
    def test_editor_can_rename_but_cannot_move_outside_tree(self):
        self.share(self.a,"editor");self.client.force_login(self.member);self.assertEqual(self.client.post(reverse("files:rename",args=["file",self.file.uuid]),{"name":"updated.png"}).status_code,302);self.file.refresh_from_db();self.assertEqual(self.file.display_name,"updated.png");self.assertEqual(self.client.post(reverse("files:move",args=["file",self.file.uuid]),{"destination":""}).status_code,404)
    def test_editor_upload_owned_by_folder_owner_and_uses_owner_quota(self):
        self.share(self.a,"editor");self.owner.profile.refresh_from_db();before=self.owner.profile.storage_used;self.client.force_login(self.member);response=self.client.post(reverse("files:upload"),{"folder_uuid":str(self.a.uuid),"files":SimpleUploadedFile("collab.txt",b"hello")});self.assertEqual(response.status_code,200);item=File.objects.get(display_name="collab.txt");self.assertEqual(item.owner,self.owner);self.owner.profile.refresh_from_db();self.member.profile.refresh_from_db();self.assertEqual(self.owner.profile.storage_used,before+5);self.assertEqual(self.member.profile.storage_used,0)
    def test_shared_search_and_per_user_star(self):
        self.share(self.a);self.client.force_login(self.member);self.assertContains(self.client.get(reverse("files:search"),{"q":"diagram"}),"diagram.png");self.client.post(reverse("files:star",args=["file",self.file.uuid]));self.assertTrue(Favorite.objects.filter(user=self.member,file=self.file).exists());self.assertFalse(Favorite.objects.filter(user=self.owner,file=self.file).exists())
    def test_shared_with_me_only_lists_top_level_grant(self):
        self.share(self.a);self.share(self.b,"editor");self.client.force_login(self.member);response=self.client.get(reverse("sharing:with_me"));self.assertContains(response,">A<");self.assertNotContains(response,">B<")
    def test_public_valid_invalid_expired_and_disabled(self):
        link=ShareLink.objects.create(file=self.file,created_by=self.owner);self.client.logout();self.assertEqual(self.client.get(reverse("public_sharing:item",args=[link.token])).status_code,200);self.assertEqual(self.client.get("/s/not-a-real-token/").status_code,404);link.expires_at=timezone.now()-timedelta(seconds=1);link.save();self.assertEqual(self.client.get(reverse("public_sharing:item",args=[link.token])).status_code,410);link.expires_at=None;link.is_active=False;link.save();self.assertEqual(self.client.get(reverse("public_sharing:item",args=[link.token])).status_code,410)
    def test_password_session_and_wrong_password(self):
        link=ShareLink.objects.create(file=self.file,created_by=self.owner,password_hash=make_password("secret"));self.client.logout();url=reverse("public_sharing:item",args=[link.token]);self.assertContains(self.client.post(url,{"password":"wrong"}),"incorrect");self.assertEqual(self.client.post(url,{"password":"secret"}).status_code,302);self.assertEqual(self.client.get(url).status_code,200)
    def test_public_download_flag_enforced(self):
        link=ShareLink.objects.create(file=self.file,created_by=self.owner,allow_download=False);self.client.logout();url=reverse("public_sharing:download",args=[link.token,self.file.uuid]);self.assertEqual(self.client.get(url).status_code,404);link.allow_download=True;link.save();self.assertEqual(self.client.get(url).status_code,200)
    def test_public_folder_containment(self):
        link=ShareLink.objects.create(folder=self.a,created_by=self.owner);self.client.logout();self.assertEqual(self.client.get(reverse("public_sharing:folder",args=[link.token,self.b.uuid])).status_code,200);self.assertEqual(self.client.get(reverse("public_sharing:folder",args=[link.token,self.sibling.uuid])).status_code,404)
    def test_revoke_and_regenerate(self):
        link=ShareLink.objects.create(file=self.file,created_by=self.owner);old=link.token;self.client.post(reverse("sharing:regenerate_link",args=[link.uuid]));link.refresh_from_db();self.assertNotEqual(link.token,old);self.client.logout();self.assertEqual(self.client.get(reverse("public_sharing:item",args=[old])).status_code,404);self.client.force_login(self.owner);self.client.post(reverse("sharing:disable_link",args=[link.uuid]));link.refresh_from_db();self.assertFalse(link.is_active)
