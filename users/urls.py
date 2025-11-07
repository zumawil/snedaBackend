from django.urls import path

from .views import SignupUser, CookieJWTLoginView, CookieTokenRefreshView, CreateClientView, CreateSecurityPersonnelView, GetUsersView

urlpatterns = [
    path("signup/", SignupUser.as_view(), name="signup"),
    path("login/", CookieJWTLoginView.as_view(), name="login"),
    path("refresh/", CookieTokenRefreshView.as_view(), name="token_refresh"),
    path("verify-otp/", CookieTokenRefreshView.as_view(), name="verify_otp"),  # Placeholder for OTP verification view
    path("clients/create/", CreateClientView.as_view(), name="create_client"),
    path("security-personnel/create/", CreateSecurityPersonnelView.as_view(), name="create_security"),
    path("users/", GetUsersView.as_view(), name="get_users")
]