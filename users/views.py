from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import authentication, permissions, status
from django.contrib.auth import get_user_model
from .serializers import UserSerializer
from django.conf import settings

from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import InvalidToken
from .permissions import IsVerifiedUser
    
from django.views.decorators.csrf import ensure_csrf_cookie
from django.http import JsonResponse

from .models import CustomUser

import pyotp
from django.core.mail import send_mail

def send_otp_to_user(user):
    secret = pyotp.random_base32()
    user.otp_secret = secret
    user.save()

    totp = pyotp.TOTP(secret, interval=300)
    otp = totp.now()

    send_mail(
        "Your verification code",
        f"Your OTP is: {otp}",
        "noreply@yourapp.com",
        [user.email],
    )

def verify_user_otp(user, otp_input):
    totp = pyotp.TOTP(user.otp_secret)
    if totp.verify(otp_input):
        user.verified = True
        user.otp_secret = None
        user.save()
        return True
    return False

class VerifyOTPView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        email = request.data.get("email")
        otp_input = request.data.get("otp")

        User = get_user_model()
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        if verify_user_otp(user, otp_input):
            refresh = RefreshToken.for_user(user)

            response = Response({"message": "User verified successfully"}, status=status.HTTP_200_OK)

            response.set_cookie(
                "access",
                str(refresh.access_token),
                httponly=True,
                secure=not settings.DEBUG,
                samesite="Lax",
                max_age=900,
                path="/",
            )
            response.set_cookie(
                "refresh",
                str(refresh),
                httponly=True,
                secure=not settings.DEBUG,
                samesite="Lax",
                max_age=604800,
                path="/auth/refresh/",
            )

            return response
        else:
            return Response({"error": "Invalid or expired OTP"}, status=status.HTTP_400_BAD_REQUEST)

class SignupUser(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()


            send_otp_to_user(user)

            return Response({"message": "User created successfully"}, status=status.HTTP_201_CREATED)
        else:
            return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

# only accessible to security managers


class CookieJWTLoginView(TokenObtainPairView):
    # serializer_class = MyTokenObtainPairSerializer
    
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    
    def post(self, request, *args, **kwargs):
        user_email = request.data.get("email", None)
        user = CustomUser.objects.get(email=user_email)

        group = user.groups.first()
        if group is not None:
            role = group.name
        else:
            role = "no-role"
        
        response = super().post(request, *args, **kwargs)
        data = response.data
        access_token = data.get("access")
        refresh_token = data.get("refresh")

        response.data.pop("access", None)
        response.data.pop("refresh", None)


        response.set_cookie(
            "access",
            access_token,
            httponly=True,
            secure=not settings.DEBUG,
            samesite="Lax",
            max_age=900,
            path="/",
        )
        response.set_cookie(
            "refresh",
            refresh_token,
            httponly=True,
            secure=not settings.DEBUG,
            samesite="Lax",
            max_age=604800,
            path="/",
        )

        response.set_cookie(
            "role",
            role,
            httponly=False,
            max_age=604800,
            path="/",
        )
        
    

        return response

from rest_framework_simplejwt.views import TokenRefreshView

class CookieTokenRefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        refresh_token = request.COOKIES.get("refresh")
        request.data['refresh'] = refresh_token
        

        try:
            response = super().post(request, *args, **kwargs)
        except InvalidToken:
            return Response({"detail": "Invalid refresh token."}, status=status.HTTP_401_UNAUTHORIZED)

        data = response.data
        access_token = data.get('access')

        response.data.pop('access', None)

        response.set_cookie(
            "access",
            access_token,
            httponly=True,
            secure=not settings.DEBUG,
            samesite="Lax",
            max_age=900,
            path="/",
        )

        return response

class GetUsersView(APIView):
    
    def get(self, request):
        users = get_user_model().objects.all()
        serializer = UserSerializer(users, many=True)
        return Response({"users": serializer.data}, status=status.HTTP_200_OK)

@ensure_csrf_cookie
def get_csrf(request):
    return JsonResponse({"detail": "CSRF cookie set"})

class UserProfileView(APIView):
    def get(self, request):
        user = request.user
        serializer = UserSerializer(user)
        return Response({"user": serializer.data}, status=status.HTTP_200_OK)

    def put(self, request):
        data = request.data
        user = request.user
        serializer = UserSerializer(user, data=data)
        if serializer.is_valid():
            serializer.save()
            return Response({"user": serializer.data}, status=status.HTTP_200_OK)
        else:
            return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request):
        data = request.data # get data coming from the request
        user = request.user # get the user from the request
        serializer = UserSerializer(user, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"user": serializer.data}, status=status.HTTP_200_OK)
        else:
            return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request):
        user = request.user
        user.delete()
        return Response({"message": "User deleted successfully"}, status=status.HTTP_204_NO_CONTENT)

class LogoutUserView(APIView):
    def post(self, request):
        response = Response({"message": "Logged out successfully"}, status=status.HTTP_200_OK)
        response.delete_cookie('access')
        response.delete_cookie('refresh')
        response.delete_cookie('role')
        return response