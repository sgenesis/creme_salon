from rest_framework_simplejwt.authentication import JWTAuthentication
from django.contrib.auth.middleware import get_user

class JWTAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.jwt_auth = JWTAuthentication()

    def __call__(self, request):
        user = get_user(request)

        if not user.is_authenticated:

            # 1. Intentar leer el token del header
            header = self.jwt_auth.get_header(request)

            # 2. Si no viene en header, intentarlo desde cookie
            if not header and request.COOKIES.get("access"):
                header = f"Bearer {request.COOKIES['access']}".encode()

            # 3. Si encontramos header o cookie, validar token
            if header:
                try:
                    raw_token = self.jwt_auth.get_raw_token(header)
                    validated_token = self.jwt_auth.get_validated_token(raw_token)
                    user = self.jwt_auth.get_user(validated_token)
                    request.user = user
                except Exception as e:
                    print("❌ JWT Middleware Error:", e)

        return self.get_response(request)

