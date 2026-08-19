from django.contrib.auth.signals import user_logged_in,user_logged_out,user_login_failed
from django.dispatch import receiver
from .services.audit import record
@receiver(user_logged_in)
def login(sender,request,user,**kwargs):record("LOGIN",actor=user)
@receiver(user_logged_out)
def logout(sender,request,user,**kwargs):record("LOGOUT",actor=user)
@receiver(user_login_failed)
def failed(sender,credentials,request,**kwargs):record("LOGIN_FAILED",metadata={"username":str(credentials.get("username",""))[:100]},result="denied")
