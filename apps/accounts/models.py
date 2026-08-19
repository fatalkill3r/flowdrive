from django.conf import settings
from django.db import models
class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    storage_quota = models.PositiveBigIntegerField(default=settings.FILEBOX_DEFAULT_QUOTA_BYTES)
    storage_used = models.PositiveBigIntegerField(default=0)
    avatar_color = models.CharField(max_length=7, default="#4f46e5")
    def __str__(self): return f"{self.user.username}'s profile"
