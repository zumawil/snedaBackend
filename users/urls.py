from django.urls import path

from .views import ( SignupUser, CookieJWTLoginView, 
                    CookieTokenRefreshView,
                    VerifyOTPView, RequestOTPView, UserProfileView, LogoutUserView,
                    ChangePasswordRequestView, ResetPasswordConfirmView, ResetPasswordView,
                     GetUsersView, GetUserSession, SearchUsers, GuessSessionView)

urlpatterns = [
    path("signup/", SignupUser.as_view(), name="signup"),
    path("login/", CookieJWTLoginView.as_view(), name="login"),
    path("refresh/", CookieTokenRefreshView.as_view(), name="token_refresh"),
    path("verify-otp/", VerifyOTPView.as_view(), name="verify_otp"),
    path("request-otp/", RequestOTPView.as_view(), name="request_otp"),
    path("users/", GetUsersView.as_view(), name="get_users"),

    #porfile endpoints
    path("profile/", UserProfileView.as_view(), name="profile"),

    path("logout/", LogoutUserView.as_view(), name="logout"),
    path('change-password/', ChangePasswordRequestView.as_view(), name="request_passsword_change"),
    # expects uid, token, new password and new password as query params
    path('reset-password/', ResetPasswordView.as_view(), name="reset_passsord"),
    path('reset-password-confirm/', ResetPasswordConfirmView.as_view(), name='confirm_password_reset'),
    path('session/', GetUserSession.as_view(), name='get_user_session'),
    path('search/', SearchUsers.as_view(), name='search_users'),

    # guest views
    path('guest-session/', GuessSessionView.as_view(), name='guest_session'),
]