from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import permission_required
from django.contrib.auth.password_validation import validate_password
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.accounts.models import Profile
from apps.accounts.services.rbac import ROLE_DEFINITIONS, assign_roles, user_roles
from apps.activity.models import Activity
from apps.audit.models import AuditEvent
from apps.audit.services.audit import record
from apps.files.models import File, FileVersion, Folder
from apps.sharing.models import ShareLink, SharePermission
from .models import SystemSettings


def base_stats():
    return {"users": get_user_model().objects.count(), "active_users": get_user_model().objects.filter(is_active=True).count(), "files": File.objects.count(), "folders": Folder.objects.count(), "storage": Profile.objects.aggregate(v=Sum("storage_used"))["v"] or 0, "shares": SharePermission.objects.count(), "links": ShareLink.objects.filter(is_active=True).count()}


@permission_required("adminpanel.access_administration", raise_exception=True)
def overview(request):
    return render(request, "adminpanel/overview.html", {"admin_stats": base_stats()})


@permission_required("adminpanel.view_users", raise_exception=True)
def users(request):
    q = request.GET.get("q", "")
    qs = get_user_model().objects.select_related("profile").prefetch_related("groups").annotate(file_count=Count("files")).order_by("username")
    if q:
        qs = qs.filter(Q(username__icontains=q) | Q(email__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q))
    return render(request, "adminpanel/users.html", {"page": Paginator(qs, 25).get_page(request.GET.get("page"))})


@permission_required("adminpanel.manage_users", raise_exception=True)
def create_user(request):
    if request.method == "POST":
        username, email, password = request.POST.get("username", "").strip(), request.POST.get("email", "").strip(), request.POST.get("password", "")
        selected_roles = (request.POST.getlist("roles") or ["Member"]) if request.user.has_perm("adminpanel.manage_roles") else ["Member"]
        try:
            quota_bytes = int(float(request.POST.get("quota_gb", "10")) * 1024**3)
            if quota_bytes <= 0: raise ValueError
            if not username or not password: raise ValueError("Username and password are required.")
            if get_user_model().objects.filter(username__iexact=username).exists(): raise ValueError("That username already exists.")
            if email and get_user_model().objects.filter(email__iexact=email).exists(): raise ValueError("That email is already in use.")
            validate_password(password)
            user = get_user_model().objects.create_user(username=username, email=email, password=password, first_name=request.POST.get("first_name", "").strip(), last_name=request.POST.get("last_name", "").strip(), is_active=request.POST.get("is_active") == "on")
            user.profile.storage_quota = quota_bytes
            user.profile.save(update_fields=["storage_quota"])
            assign_roles(request.user, user, selected_roles)
            record("ADMIN_USER_CREATED", request.user, target_user=user, metadata={"quota": quota_bytes, "roles": user_roles(user)})
            messages.success(request, f"User {username} created")
            return redirect("adminpanel:user_detail", user.id)
        except Exception as exc:
            messages.error(request, str(exc) if isinstance(exc, ValueError) and str(exc) else "Unable to create user. Check the password, role, and quota values.")
    return render(request, "adminpanel/create_user.html", {"role_definitions": ROLE_DEFINITIONS})


@permission_required("adminpanel.view_users", raise_exception=True)
def user_detail(request, user_id):
    user = get_object_or_404(get_user_model().objects.select_related("profile").prefetch_related("groups"), pk=user_id)
    return render(request, "adminpanel/user_detail.html", {"account": user, "recent": Activity.objects.filter(user=user)[:20], "version_storage": FileVersion.objects.filter(file__owner=user).aggregate(v=Sum("size"))["v"] or 0, "quota_gb": round(user.profile.storage_quota / 1024**3, 2), "account_roles": user_roles(user), "role_definitions": ROLE_DEFINITIONS})


@permission_required("adminpanel.manage_quotas", raise_exception=True)
@require_POST
def set_quota(request, user_id):
    user = get_object_or_404(get_user_model(), pk=user_id); old = user.profile.storage_quota
    try:
        value = int(float(request.POST.get("quota_gb")) * 1024**3); assert value > 0
    except (ValueError, TypeError, AssertionError):
        messages.error(request, "Enter a valid positive quota."); return redirect("adminpanel:user_detail", user.id)
    user.profile.storage_quota = value; user.profile.save(update_fields=["storage_quota"])
    record("ADMIN_QUOTA_CHANGED", request.user, target_user=user, metadata={"old": old, "new": value}); messages.success(request, "Quota updated")
    return redirect("adminpanel:user_detail", user.id)


@permission_required("adminpanel.manage_users", raise_exception=True)
@require_POST
def toggle_user(request, user_id):
    user = get_object_or_404(get_user_model(), pk=user_id)
    if user == request.user: messages.error(request, "You cannot disable your own account.")
    else:
        user.is_active = not user.is_active; user.save(update_fields=["is_active"])
        record("ADMIN_USER_STATUS_CHANGED", request.user, target_user=user, metadata={"is_active": user.is_active})
    return redirect("adminpanel:user_detail", user.id)


@permission_required("adminpanel.manage_roles", raise_exception=True)
@require_POST
def set_roles(request, user_id):
    user = get_object_or_404(get_user_model(), pk=user_id)
    try:
        assign_roles(request.user, user, request.POST.getlist("roles") or ["Member"]); messages.success(request, "Roles updated")
    except ValueError as exc: messages.error(request, str(exc))
    return redirect("adminpanel:user_detail", user.id)


@permission_required("adminpanel.manage_roles", raise_exception=True)
def roles(request):
    counts = {row["groups__name"]: row["user_count"] for row in get_user_model().objects.filter(groups__name__in=ROLE_DEFINITIONS).values("groups__name").annotate(user_count=Count("id"))}
    rows = [{"name": name, "description": definition["description"], "permissions": definition["permissions"], "user_count": counts.get(name, 0)} for name, definition in ROLE_DEFINITIONS.items()]
    return render(request, "adminpanel/roles.html", {"roles": rows})


@permission_required("adminpanel.view_storage_analytics", raise_exception=True)
def storage(request):
    return render(request, "adminpanel/storage.html", {"by_user": Profile.objects.select_related("user").order_by("-storage_used")[:10], "versions": FileVersion.objects.aggregate(v=Sum("size"))["v"] or 0, "trash": File.objects.filter(is_deleted=True).aggregate(v=Sum("size"))["v"] or 0, "admin_stats": base_stats()})


@permission_required("adminpanel.view_file_analytics", raise_exception=True)
def files_report(request):
    return render(request, "adminpanel/files.html", {"largest": File.objects.select_related("owner").order_by("-size")[:25], "extensions": File.objects.values("extension").annotate(count=Count("id"), size=Sum("size")).order_by("-size")[:20]})


@permission_required("adminpanel.view_sharing_analytics", raise_exception=True)
def sharing_report(request):
    return render(request, "adminpanel/sharing.html", {"shares": SharePermission.objects.select_related("shared_by", "shared_with")[:50], "links": ShareLink.objects.select_related("created_by").order_by("-created_at")[:50]})


@permission_required("adminpanel.view_audit_log", raise_exception=True)
def audit(request):
    q = request.GET.get("q", ""); qs = AuditEvent.objects.select_related("actor", "target_user")
    if q: qs = qs.filter(Q(event_type__icontains=q) | Q(object_name__icontains=q) | Q(actor__username__icontains=q))
    return render(request, "adminpanel/audit.html", {"page": Paginator(qs, 50).get_page(request.GET.get("page"))})


@permission_required("adminpanel.manage_system_settings", raise_exception=True)
def system_settings(request):
    obj = SystemSettings.load()
    if request.method == "POST":
        old = {"max_versions": obj.max_file_versions, "trash_days": obj.trash_retention_days}
        obj.max_file_versions = int(request.POST.get("max_file_versions", obj.max_file_versions)); obj.trash_retention_days = int(request.POST.get("trash_retention_days", obj.trash_retention_days)); obj.public_sharing_enabled = request.POST.get("public_sharing_enabled") == "on"; obj.upload_requests_enabled = request.POST.get("upload_requests_enabled") == "on"; obj.save()
        record("ADMIN_SETTINGS_CHANGED", request.user, metadata={"old": old}); messages.success(request, "Settings updated")
    return render(request, "adminpanel/settings.html", {"settings_obj": obj})
