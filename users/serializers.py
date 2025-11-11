from rest_framework import serializers
from users.models import CustomUser
# from django.contrib.auth.models import Group
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


# JWT serializer

# class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
#     @classmethod
#     def get_token(cls, user):
#         token = super().get_token(user)

#         # add user role to token
#         group = user.groups.first()
#         if group:
#             token['role'] = group.name
#         else:
#             token['role'] = 'NoRole'

#         return token

class UserSerializer(serializers.ModelSerializer):

    class Meta:
        model = CustomUser
        fields = ['date_joined',
                  'email', 'id', 'is_active',
                  'is_staff', "is_superuser",
                  "last_login","user_permissions",
                  "verified", "groups", "password"]
        extra_kwargs = {
            'password': {'write_only': True} # makes the password writable but not readable
        }

    def create(self, validated_data):
        user = CustomUser(**validated_data)
        user.set_password(validated_data['password'])
        user.save()

        return user

    

