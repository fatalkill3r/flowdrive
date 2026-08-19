from django.urls import path
from . import public_views
app_name="public_sharing"
urlpatterns=[path("<str:token>/",public_views.public_item,name="item"),path("<str:token>/folder/<uuid:folder_uuid>/",public_views.public_item,name="folder"),path("<str:token>/file/<uuid:file_uuid>/preview/",public_views.public_file,name="preview"),path("<str:token>/file/<uuid:file_uuid>/download/",public_views.public_file,name="download",kwargs={"download":True}),path("<str:token>/download-folder/",public_views.public_folder_zip,name="folder_zip")]
