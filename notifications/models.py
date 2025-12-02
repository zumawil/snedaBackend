from django.db import models
from users.models import CustomUser

# Create your models here.
class Notification(models.Model):
    user = models.ForeignKey(CustomUser, related_name='notifications', on_delete=models.CASCADE)
    message = models.TextField("notification message to be sent to user")
    date = models.DateTimeField(auto_now=True)
    is_read = models.BooleanField(default=False)
