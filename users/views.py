from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import authentication, permissions, status
from django.contrib.auth import get_user_model
from .serializers import UserSerializer, UserCreateSerializer, UserProfileUpdateSerializer
from django.conf import settings

from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import InvalidToken
from .permissions import IsVerifiedUser, IsAdminUser
    
from django.views.decorators.csrf import ensure_csrf_cookie
from django.http import JsonResponse
from utils.normalize_errors import normalize_errors

from .models import CustomUser

import pyotp
from utils.sendEmail import send_otp_email

from dotenv import load_dotenv
import os
from utils.apiResponse import api_response

load_dotenv()

def send_otp_to_user(user):
    secret = pyotp.random_base32()
    user.otp_secret = secret
    user.save()

    totp = pyotp.TOTP(secret, interval=300)
    otp = totp.now()

    from utils.email_templates import get_otp_email_html
    otp_html = get_otp_email_html(otp)
    
    r = send_otp_email(
        user.email,
        "Your verification code from Sneda Ecommerce",
        otp_html,
    )
    print(r)

    return otp

def verify_user_otp(user, otp_input):
    if not user.otp_secret:
        return False
    totp = pyotp.TOTP(user.otp_secret, interval=300)
    if totp.verify(otp_input):
        user.verified = True
        user.otp_secret = None
        user.save()
        return True
    return False

class VerifyOTPView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_scope = 'sensitive'

    def post(self, request):
        email = request.data.get("email")
        otp_input = request.data.get("otp")

        User = get_user_model()

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return api_response(
                success=False,
                data=None,
                error="User not found",
                message="User with this email does not exist",
                status_code=status.HTTP_404_NOT_FOUND
            )

        if verify_user_otp(user, otp_input):
            refresh = RefreshToken.for_user(user)

            response = api_response(
                success=True,
                data=None,
                message="User verified successfully",
                status_code=status.HTTP_200_OK
            )

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
            return api_response(
                success=False,
                data=None,
                error="Invalid OTP",
                message="Invalid or expired OTP code",
                status_code=status.HTTP_400_BAD_REQUEST
            )

class SignupUser(APIView):

    """
       sigunu user endpoint , 
       has a sensitive throttling mechanism which allows 
       5 request in a minutes 
    """

    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_scope = 'sensitive'

    def post(self, request):
        serializer = UserCreateSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()

            otp = send_otp_to_user(user)

            return api_response(
                success=True,
                data={'otp':otp},
                message="User created successfully",
                status_code=status.HTTP_201_CREATED
            )
        else:
            return api_response(
                success=False,
                data=None,
                error="Validation failed",
                message=normalize_errors(serializer.errors),
                status_code=status.HTTP_400_BAD_REQUEST
            )

# only accessible to security managers

# chnaged it ancestor to return general response  (TokenViewBase)
class CookieJWTLoginView(TokenObtainPairView):
    # serializer_class = MyTokenObtainPairSerializer
    
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_scope = 'sensitive'
    
    def post(self, request, *args, **kwargs):
        user_email = request.data.get("email", None)
        user = CustomUser.objects.get(email=user_email)
        
        response = super().post(request, *args, **kwargs)
        data = response.data
        access_token = data.get("access")
        refresh_token = data.get("refresh")

        response.data.pop("access", None)
        response.data.pop("refresh", None)

        # set access token in cookies
        response.set_cookie(
            "access",
            access_token,
            httponly=True,
            secure=not settings.DEBUG,
            samesite="Lax",
            max_age=900,
            path="/",
        )
         # set refresh token in cookies
        response.set_cookie(
            "refresh",
            refresh_token,
            httponly=True,
            secure=not settings.DEBUG,
            samesite="Lax",
            max_age=604800,
            path="/",
        )


        # For Swagger compatibility, include tokens in response if requested
        if request.GET.get('include_tokens') == 'true':
            response.data['access'] = access_token
            response.data['refresh'] = refresh_token

        return response

from rest_framework_simplejwt.views import TokenRefreshView

class CookieTokenRefreshView(TokenRefreshView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        refresh_token = request.COOKIES.get("refresh")
        request.data['refresh'] = refresh_token
        

        try:
            response = super().post(request, *args, **kwargs)
        except InvalidToken:
            return api_response(
                success=False,
                data=None,
                error="Invalid refresh token",
                message="Invalid refresh token",
                status_code=status.HTTP_401_UNAUTHORIZED
            )

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

    permission_classes = [IsAdminUser]

    def get(self, request):
        users = get_user_model().objects.all()
        serializer = UserSerializer(users, many=True)
        return api_response(
            success=True,
            data={"users": serializer.data},
            message="Users retrieved successfully",
            status_code=status.HTTP_200_OK
        )

@ensure_csrf_cookie
def get_csrf(request):
    return JsonResponse({"detail": "CSRF cookie set"})

class UserProfileView(APIView):
    permission_classes = [IsVerifiedUser]

    def get(self, request):
        user = request.user
        serializer = UserSerializer(user)
        return api_response(
            success=True,
            data={"user": serializer.data},
            message="User profile retrieved successfully",
            status_code=status.HTTP_200_OK
        )

    def put(self, request):
        data = request.data
        user = request.user
        serializer = UserSerializer(user, data=data)
        if serializer.is_valid():
            serializer.save()
            return api_response(
                success=True,
                data={"user": serializer.data},
                message="User profile updated successfully",
                status_code=status.HTTP_200_OK
            )
        else:
            return api_response(
                success=False,
                data=None,
                error="Validation failed",
                message="Invalid user data",
                status_code=status.HTTP_400_BAD_REQUEST
            )

    def patch(self, request):
        data = request.data # get data coming from the request
        user = request.user # get the user from the request
        serializer = UserProfileUpdateSerializer(user, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return api_response(
                success=True,
                data={"user": serializer.data},
                message="User profile updated successfully",
                status_code=status.HTTP_200_OK
            )
        else:
            return api_response(
                success=False,
                data=None,
                error="Validation failed",
                message="Invalid user data",
                status_code=status.HTTP_400_BAD_REQUEST
            )
    
    def delete(self, request):
        user = request.user
        user.delete()
        return api_response(
            success=True,
            data=None,
            message="User deleted successfully",
            status_code=status.HTTP_204_NO_CONTENT
        )

class LogoutUserView(APIView):
    permission_classes = [IsVerifiedUser]

    def post(self, request):
        response = api_response(
            success=True,
            data=None,
            message="Logged out successfully",
            status_code=status.HTTP_200_OK
        )
        if response.cookies.get('access'):
            response.delete_cookie('access')
            response.delete_cookie('refresh')
            return api_response(
                success=True,
                message='logged out successfully',
                status_code=status.HTTP_200_OK
            )
        else:
            return api_response(
                success=False,
                data=None,
                error="No active session",
                message="User is not logged in",
                status_code=status.HTTP_400_BAD_REQUEST
            )


class RequestOTPView(APIView):
    """
    View to manually request a new OTP.
    Throttled to 5 requests per minute.
    """
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_scope = 'sensitive'

    def post(self, request):
        email = request.data.get("email")
        if not email:
            return api_response(
                success=False,
                data=None,
                error="Missing email",
                message="Email field is required",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        User = get_user_model()
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return api_response(
                success=False,
                data=None,
                error="User not found",
                message="User with this email does not exist",
                status_code=status.HTTP_404_NOT_FOUND
            )

        if user.verified:
            return api_response(
                success=True,
                data=None,
                message="User is already verified",
                status_code=status.HTTP_200_OK
            )

        otp = send_otp_to_user(user)

        return api_response(
            success=True,
            data={'otp': otp},
            message="OTP sent successfully",
            status_code=status.HTTP_200_OK
        )


from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.core.cache import cache

# token generator class
import secrets

class TokenGenerator:
    
    def __init__(self, bytes=32):
        self.bytes = bytes
        self.token = None
        
    def get_url_safe_bytes(self):
        self.token = secrets.token_urlsafe(self.bytes)
        return self.token

    def store_password_token(self, user_pk, expiry_minutes=15):
        """Store the token in cache for a user with expiry"""
        if not self.token:
            raise ValueError("Token not generated yet. Call generate_token() first.")
        cache.set(f'password_token_{user_pk}', self.token, expiry_minutes * 60)

    @staticmethod
    def check_token(user_pk, token):
        """Check if the token matches the cached token"""
        cached_token = cache.get(f'password_token_{user_pk}')
        return cached_token == token

class ChangePasswordRequestView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_scope = 'sensitive'

    def post(self, request):
        email  = request.data.get('email')
        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            return api_response(
                success=False,
                data=None,
                error="User not found",
                message="User with this email does not exist",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        ## generate user uid
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        ## generate the token for the url
        token = TokenGenerator()
        url_token = token.get_url_safe_bytes()
        
        token.store_password_token(user.pk) # 15 min

        app_url = os.environ.get("APP_URL", "http://localhost:3000")
        password_reset_url = f"{app_url.rstrip('/')}/users/reset-password-confirm/?uid={uid}&token={url_token}"
        from utils.email_templates import get_password_reset_html
        reset_html = get_password_reset_html(password_reset_url)

        send_otp_email(
            [user.email],
            "You requested for a password change",
            reset_html,
        )

        return api_response(
            success=True,
            data={'link': password_reset_url},
            message='Password reset link has been sent to your email',
            status_code=status.HTTP_202_ACCEPTED
        )

# checks if uid and token are valid when user clicks
#  the link sent from change password request view
class ResetPasswordConfirmView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_scope = 'sensitive'

    def get(self, request):
        uid = request.query_params.get('uid')
        token = request.query_params.get('token')

        user_id = urlsafe_base64_decode(uid).decode()
        user = get_object_or_404(CustomUser,pk=user_id)
        
        is_token_valid = TokenGenerator.check_token(user.id, token)
        
        if is_token_valid:
            return api_response(
                success=True,
                data={'token': token, 'uid': uid},
                message='Token is valid',
                status_code=status.HTTP_200_OK
            )
        else:
            return api_response(
                success=False,
                data=None,
                error='Invalid token',
                message='Invalid or expired token',
                status_code=status.HTTP_400_BAD_REQUEST
            )
# user actually send new password along with uid and token
class ResetPasswordView(APIView):   
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        new_password = request.data.get('new_password')
        confirm_password = request.data.get('confirm_password')
        uid = request.data.get('uid')
        token = request.data.get('token')

        user_id = urlsafe_base64_decode(uid).decode()
        try:
            user = get_object_or_404(CustomUser, pk=user_id)
        except CustomUser.DoesNotExist():
            return api_response(
                success=False,
                data=None,
                error="User not found",
                message="User account not found",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        if not TokenGenerator.check_token(user_id, token):
            return api_response(
                success=False,
                data=None,
                error="Invalid token",
                message="Invalid or expired token",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        if new_password == confirm_password and new_password and confirm_password:
            user.set_password(new_password)
            user.save()
            return api_response(
                success=True,
                data=None,
                message="Password reset successful",
                status_code=status.HTTP_200_OK
            )
        else:
            return api_response(
                success=False,
                data=None,
                error="Password mismatch",
                message="Passwords do not match or are empty",
                status_code=status.HTTP_400_BAD_REQUEST
            )

class GetUserSession(APIView):

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        session_count = request.session.get('count', 0)
        session_count += 1
        request.session['count'] = session_count
        session_data = request.session.items()
        return api_response(
            success=True,
            data={"session_data": dict(session_data)},
            message="Session data retrieved successfully",
            status_code=status.HTTP_200_OK
        )

from rest_framework.pagination import PageNumberPagination
from django.db.models import Q

class SearchUsers(APIView):

    permissions_class = [IsAdminUser]
    pagination_class = PageNumberPagination

    def get(self, request):
        search_query = request.query_params.get('q', '')
        users = CustomUser.objects.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )
        
        if users:
            paginator = self.pagination_class()
            paginated_users = paginator.paginate_queryset(users, request)
            
            serializer = UserSerializer(paginated_users, many=True)
            data = paginator.get_paginated_response(serializer.data).data

            return api_response(
                success=True,
                data=data,
                message="Users retrieved successfully",
                status_code=status.HTTP_200_OK
            )
        
        return api_response(
            success=False,
            data=None,
            message="No Users found from query",
            status_code=status.HTTP_200_OK,
            error=True
        )