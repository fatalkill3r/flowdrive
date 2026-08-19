from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from .models import Notification
class NotificationTests(TestCase):
    def setUp(self):U=get_user_model();self.a=U.objects.create_user("notifya",password="pass123456");self.b=U.objects.create_user("notifyb",password="pass123456");self.note=Notification.objects.create(user=self.b,type="shared",title="Shared",message="A file")
    def test_isolation(self):self.client.force_login(self.a);self.assertEqual(self.client.get(reverse("notifications:read",args=[self.note.uuid])).status_code,404)
    def test_read_and_mark_all(self):
        self.client.force_login(self.b);self.client.get(reverse("notifications:read",args=[self.note.uuid]));self.note.refresh_from_db();self.assertTrue(self.note.is_read);Notification.objects.create(user=self.b,type="x",title="X",message="X");self.client.post(reverse("notifications:read_all"));self.assertFalse(Notification.objects.filter(user=self.b,is_read=False).exists())
