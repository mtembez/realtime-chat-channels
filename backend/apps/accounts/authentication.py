import jwt
from rest_framework import authentication, exceptions
from apps.accounts.tokens import decode_token, get_user_from_token


class JWTAuthentication(authentication.BaseAuthentication):
    """DRF Authentication scheme using Bearer JWT tokens."""

    def authenticate_header(self, request):
        return 'Bearer realm="api"'

    def authenticate(self, request):
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return None

        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise exceptions.AuthenticationFailed("Invalid Authorization header format. Expected 'Bearer <token>'")

        raw_token = parts[1]
        try:
            user = get_user_from_token(raw_token)
            if user is None:
                raise exceptions.AuthenticationFailed("User not found or inactive")
            return (user, raw_token)
        except jwt.ExpiredSignatureError:
            raise exceptions.AuthenticationFailed("Token has expired")
        except (jwt.InvalidTokenError, ValueError) as exc:
            raise exceptions.AuthenticationFailed(f"Invalid token: {str(exc)}")
