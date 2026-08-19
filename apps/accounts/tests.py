from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
class AccountSettingsTests(TestCase):
    def test_settings_is_functional_and_protected(self):
        self.assertEqual(self.client.get(reverse("accounts:settings")).status_code,302);user=get_user_model().objects.create_user("settingsuser",password="pass123456");self.client.force_login(user);response=self.client.get(reverse("accounts:settings"));self.assertEqual(response.status_code,200);self.assertContains(response,"Storage breakdown")
