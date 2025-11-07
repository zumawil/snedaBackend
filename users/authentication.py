from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.authentication import JWTAuthentication


class CookieJWTAuthentication(JWTAuthentication):
    
    def authenticate(self, request):
        access = request.COOKIES.get("access")

        if not access:
            # optionally fall back to header:
            return super().authenticate(request)
        
        validated_token = self.get_validated_token(access)
        user = self.get_user(validated_token)

        return (user, validated_token)