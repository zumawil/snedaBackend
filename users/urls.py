from django.urls import path

from .views import ( SignupUser, CookieJWTLoginView, 
                    CookieTokenRefreshView, GetUsersView, 
                    VerifyOTPView, UserProfileView, LogoutUserView)

urlpatterns = [
    path("signup/", SignupUser.as_view(), name="signup"),
    path("login/", CookieJWTLoginView.as_view(), name="login"),
    path("refresh/", CookieTokenRefreshView.as_view(), name="token_refresh"),
    path("verify-otp/", VerifyOTPView.as_view(), name="verify_otp"),  # Placeholder for OTP verification view
    path("users/", GetUsersView.as_view(), name="get_users"),

    #porfile endpoints
    path("profile/", UserProfileView.as_view(), name="profile"),

    path("logout/", LogoutUserView.as_view(), name="logout"),
]