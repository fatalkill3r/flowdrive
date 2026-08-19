from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("apps.accounts.urls")),
    path("files/", include("apps.files.urls")),
    path("sharing/", include("apps.sharing.urls")),
    path("s/", include("apps.sharing.public_urls")),
    path("notifications/", include("apps.notifications.urls")),
    path("manage/", include("apps.adminpanel.urls")),
    path("requests/", include("apps.file_requests.urls")),
    path("r/", include("apps.file_requests.public_urls")),
    path("", include("apps.dashboard.urls")),
    path("coming-soon/", TemplateView.as_view(template_name="base/coming_soon.html"), name="coming_soon"),
]
handler403 = "apps.dashboard.views.error_403"; handler404 = "apps.dashboard.views.error_404"; handler500 = "apps.dashboard.views.error_500"
