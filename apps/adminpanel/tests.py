from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.accounts.services.rbac import assign_roles, ensure_roles, user_roles
from apps.audit.models import AuditEvent


class AdminPanelRBACTests(TestCase):
    def setUp(self):
        ensure_roles()
        User = get_user_model()
        self.member = User.objects.create_user("normal", password="pass123456")
        self.legacy_staff = User.objects.create_user("staff", password="pass123456", is_staff=True)
        self.admin = User.objects.create_user("systemadmin", password="pass123456")
        self.auditor = User.objects.create_user("auditor", password="pass123456")
        self.user_admin = User.objects.create_user("useradmin", password="pass123456")
        assign_roles(None, self.member, ["Member"])
        assign_roles(None, self.admin, ["System Admin"])
        assign_roles(None, self.auditor, ["Security Auditor"])
        assign_roles(None, self.user_admin, ["User Admin"])

    def test_staff_flag_does_not_grant_administration(self):
        self.client.force_login(self.legacy_staff)
        self.assertEqual(self.client.get(reverse("adminpanel:overview")).status_code, 403)

    def test_system_admin_has_all_application_capabilities(self):
        self.client.force_login(self.admin)
        for name in ("overview", "users", "roles", "storage", "files", "sharing", "audit", "settings"):
            self.assertEqual(self.client.get(reverse(f"adminpanel:{name}")).status_code, 200, name)

    def test_auditor_can_only_access_audit_administration(self):
        self.client.force_login(self.auditor)
        self.assertEqual(self.client.get(reverse("adminpanel:overview")).status_code, 200)
        self.assertEqual(self.client.get(reverse("adminpanel:audit")).status_code, 200)
        self.assertEqual(self.client.get(reverse("adminpanel:users")).status_code, 403)
        self.assertEqual(self.client.get(reverse("adminpanel:settings")).status_code, 403)

    def test_quota_change_requires_quota_capability_and_is_audited(self):
        self.client.force_login(self.user_admin)
        self.assertEqual(self.client.post(reverse("adminpanel:quota", args=[self.member.id]), {"quota_gb": "20"}).status_code, 403)
        self.client.force_login(self.admin)
        self.client.post(reverse("adminpanel:quota", args=[self.member.id]), {"quota_gb": "20"})
        self.member.profile.refresh_from_db()
        self.assertEqual(self.member.profile.storage_quota, 20 * 1024**3)
        self.assertTrue(AuditEvent.objects.filter(event_type="ADMIN_QUOTA_CHANGED", target_user=self.member).exists())

    def test_role_assignment_requires_capability_and_is_audited(self):
        self.client.force_login(self.user_admin)
        self.assertEqual(self.client.post(reverse("adminpanel:set_roles", args=[self.member.id]), {"roles": "Security Auditor"}).status_code, 403)
        self.client.force_login(self.admin)
        self.client.post(reverse("adminpanel:set_roles", args=[self.member.id]), {"roles": "Security Auditor"})
        self.assertEqual(user_roles(self.member), ["Security Auditor"])
        self.assertTrue(AuditEvent.objects.filter(event_type="ROLE_ASSIGNMENT_CHANGED", actor=self.admin, target_user=self.member).exists())

    def test_user_admin_creates_member_but_cannot_escalate_roles(self):
        self.client.force_login(self.user_admin)
        response = self.client.post(reverse("adminpanel:create_user"), {"username": "newperson", "email": "new@example.com", "password": "A-strong-temporary-password-42", "quota_gb": "25", "roles": "Member", "is_active": "on"})
        self.assertEqual(response.status_code, 302)
        created = get_user_model().objects.get(username="newperson")
        self.assertEqual(user_roles(created), ["Member"])
        self.assertTrue(AuditEvent.objects.filter(event_type="ADMIN_USER_CREATED", target_user=created).exists())
