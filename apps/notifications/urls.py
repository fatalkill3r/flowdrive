from django.urls import path
from . import views
app_name="notifications"
urlpatterns=[path("",views.center,name="center"),path("<uuid:value>/read/",views.mark_read,name="read"),path("read-all/",views.mark_all,name="read_all"),path("preferences/",views.preferences,name="preferences")]
