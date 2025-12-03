from .models import Notification
from rest_framework.serializers import ModelSerializer
from users.serializers import UserSerializer 


class NotificationSerializer(ModelSerializer):
    # user = UserSerializer(read_only=True)
    
    class Meta:
        model = Notification
        fields = ['id', 'user', 'message', 'date', 'is_read']
        read_only_fields = ['id', 'user', 'date']

