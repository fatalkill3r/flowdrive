from django.urls import path
from . import views
app_name="adminpanel"
urlpatterns=[path("",views.overview,name="overview"),path("users/",views.users,name="users"),path("users/create/",views.create_user,name="create_user"),path("users/<int:user_id>/",views.user_detail,name="user_detail"),path("users/<int:user_id>/quota/",views.set_quota,name="quota"),path("users/<int:user_id>/toggle/",views.toggle_user,name="toggle"),path("users/<int:user_id>/roles/",views.set_roles,name="set_roles"),path("roles/",views.roles,name="roles"),path("storage/",views.storage,name="storage"),path("files/",views.files_report,name="files"),path("sharing/",views.sharing_report,name="sharing"),path("audit/",views.audit,name="audit"),path("settings/",views.system_settings,name="settings")]
