from django.urls import path
from . import public_views
app_name="public_requests"
urlpatterns=[path("<str:token>/",public_views.request_page,name="page")]
