from django.urls import path
from . import views
app_name = "files"
urlpatterns = [
 path("", views.browser, name="root"), path("folder/<uuid:folder_uuid>/", views.browser, name="folder"),
 path("folder/create/", views.create_folder, name="create_folder"), path("upload/", views.upload, name="upload"),
 path("file/<uuid:file_uuid>/download/", views.download, name="download"), path("file/<uuid:file_uuid>/details/", views.details, name="details"),
 path("file/<uuid:file_uuid>/delete/", views.delete_file_view, name="delete_file"), path("folder/<uuid:folder_uuid>/delete/", views.delete_folder, name="delete_folder"),
 path("search/", views.search, name="search"), path("starred/", views.starred, name="starred"), path("recent/", views.recent, name="recent"), path("trash/", views.trash, name="trash"),
 path("item/<str:kind>/<uuid:item_uuid>/rename/", views.rename_item, name="rename"), path("item/<str:kind>/<uuid:item_uuid>/move/", views.move_item, name="move"), path("item/<str:kind>/<uuid:item_uuid>/copy/", views.copy_item, name="copy"), path("item/<str:kind>/<uuid:item_uuid>/star/", views.toggle_star, name="star"),
 path("item/<str:kind>/<uuid:item_uuid>/restore/", views.restore_item, name="restore"), path("item/<str:kind>/<uuid:item_uuid>/permanent-delete/", views.permanent_delete_item, name="permanent_delete"),
 path("file/<uuid:file_uuid>/preview/", views.preview, name="preview"), path("file/<uuid:file_uuid>/content/", views.preview_content, name="preview_content"),
 path("bulk/", views.bulk_action, name="bulk"), path("trash/empty/", views.empty_trash, name="empty_trash"), path("folders/tree/", views.folder_tree, name="folder_tree"),
 path("file/<uuid:file_uuid>/version/upload/",views.upload_version,name="upload_version"),path("version/<uuid:version_uuid>/download/",views.download_version,name="download_version"),path("version/<uuid:version_uuid>/preview/",views.preview_version,name="preview_version"),path("version/<uuid:version_uuid>/restore/",views.restore_version_view,name="restore_version"),
]
