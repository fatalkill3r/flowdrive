from django.urls import path
from . import views
app_name="sharing"
urlpatterns=[
 path("with-me/",views.shared_with_me,name="with_me"),path("folder/<uuid:folder_uuid>/",views.shared_folder,name="folder"),path("by-me/",views.shared_by_me,name="by_me"),
 path("dialog/<str:kind>/<uuid:item_uuid>/",views.share_dialog,name="dialog"),path("users/",views.user_search,name="user_search"),
 path("share/<uuid:share_uuid>/permission/",views.update_permission,name="update_permission"),path("share/<uuid:share_uuid>/remove/",views.remove_access,name="remove"),
 path("link/<str:kind>/<uuid:item_uuid>/configure/",views.configure_link,name="configure_link"),path("link/<uuid:link_uuid>/disable/",views.disable_link,name="disable_link"),path("link/<uuid:link_uuid>/regenerate/",views.regenerate_link,name="regenerate_link"),
]
