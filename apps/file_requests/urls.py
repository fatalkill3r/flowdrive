from django.urls import path
from . import views
app_name="file_requests"
urlpatterns=[path("",views.list_requests,name="list"),path("create/",views.create,name="create"),path("<uuid:value>/disable/",views.disable,name="disable"),path("<uuid:value>/regenerate/",views.regenerate_view,name="regenerate")]
