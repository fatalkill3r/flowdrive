from django.contrib.auth import views
from . import views as account_views
from django.urls import path
app_name = "accounts"
urlpatterns = [path("login/", views.LoginView.as_view(template_name="accounts/login.html", redirect_authenticated_user=True), name="login"), path("logout/", views.LogoutView.as_view(), name="logout"),path("settings/",account_views.settings_page,name="settings")]
