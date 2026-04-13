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
                  "verified", "groups", "password",
                   "first_name", "last_name", "phone_number", 
                   "address", "city", "profile_picture"]
        extra_kwargs = {
            'password': {'write_only': True} # makes the password writable but not readable
        }

    def create(self, validated_data):
        user = CustomUser(**validated_data)
        user.set_password(validated_data['password'])
        user.save()

        return user

class CartUserSerializer(serializers.ModelSerializer):

    class Meta:
        model = CustomUser
        fields = [
                'email', 
                "first_name", 
                "last_name", 
                "phone_number", 
                "address", "city"
            ]

class UserCreateSerializer(serializers.ModelSerializer):
    """Serializer for user registration with proper OpenAPI schema documentation"""
    
    password = serializers.CharField(write_only=True, min_length=6)
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = CustomUser
        fields = ['email', 'password', 'password_confirm', 'first_name', 'last_name', 'phone_number']
    
    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError("Passwords do not match.")
        return data
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')  # Remove confirm password
        password = validated_data.pop('password')
        user = CustomUser(**validated_data)
        user.set_password(password)
        user.save()
        return user

class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile with proper OpenAPI schema documentation"""
    
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'phone_number', 'address', 'city', 'profile_picture']
        extra_kwargs = {
            'profile_picture': {'required': False}
        }

    

