from django.contrib.auth.models import Group, Permission
from django.db import transaction

from apps.audit.services.audit import record


ROLE_DEFINITIONS = {
    "Member": {
        "description": "Standard workspace access; no administrative capabilities.",
        "permissions": [],
    },
    "Support Admin": {
        "description": "Read-only operational access to users and platform analytics.",
        "permissions": ["access_administration", "view_users", "view_storage_analytics", "view_file_analytics", "view_sharing_analytics"],
    },
    "User Admin": {
        "description": "Create, activate, deactivate, and inspect user accounts.",
        "permissions": ["access_administration", "view_users", "manage_users"],
    },
    "Storage Admin": {
        "description": "Inspect storage usage and manage user quotas.",
        "permissions": ["access_administration", "view_users", "manage_quotas", "view_storage_analytics"],
    },
    "Sharing Admin": {
        "description": "Inspect direct shares and public links.",
        "permissions": ["access_administration", "view_sharing_analytics"],
    },
    "Security Auditor": {
        "description": "Read-only access to security and administrative audit events.",
        "permissions": ["access_administration", "view_audit_log"],
    },
    "System Admin": {
        "description": "Full application administration, including roles and settings.",
        "permissions": ["access_administration", "view_users", "manage_users", "manage_quotas", "view_storage_analytics", "view_file_analytics", "view_sharing_analytics", "view_audit_log", "manage_system_settings", "manage_roles"],
    },
}


@transaction.atomic
def ensure_roles():
    permissions = Permission.objects.filter(content_type__app_label="adminpanel", codename__in={p for role in ROLE_DEFINITIONS.values() for p in role["permissions"]})
    by_codename = {permission.codename: permission for permission in permissions}
    for name, definition in ROLE_DEFINITIONS.items():
        group, _ = Group.objects.get_or_create(name=name)
        group.permissions.set([by_codename[codename] for codename in definition["permissions"] if codename in by_codename])


def user_roles(user):
    return list(user.groups.filter(name__in=ROLE_DEFINITIONS).values_list("name", flat=True).order_by("name"))


@transaction.atomic
def assign_roles(actor, user, role_names):
    requested = set(role_names)
    unknown = requested.difference(ROLE_DEFINITIONS)
    if unknown:
        raise ValueError(f"Unknown roles: {', '.join(sorted(unknown))}")
    ensure_roles()
    old = user_roles(user)
    user.groups.remove(*Group.objects.filter(name__in=ROLE_DEFINITIONS))
    user.groups.add(*Group.objects.filter(name__in=requested))
    new = user_roles(user)
    if old != new:
        record("ROLE_ASSIGNMENT_CHANGED", actor, target_user=user, metadata={"old_roles": old, "new_roles": new})
    return new
