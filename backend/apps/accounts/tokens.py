import jwt
from datetime import datetime, timedelta, timezone
from django.conf import settings
from django.contrib.auth import get_user_model


def generate_tokens_for_user(user) -> dict:
    """Generate access and refresh JWT tokens for an authenticated user."""
    now = datetime.now(timezone.utc)
    access_expiry = now + timedelta(minutes=getattr(settings, "JWT_ACCESS_EXPIRATION_MINUTES", 60))
    refresh_expiry = now + timedelta(days=getattr(settings, "JWT_REFRESH_EXPIRATION_DAYS", 30))

    access_payload = {
        "user_id": str(user.id),
        "username": user.username,
        "email": user.email,
        "token_type": "access",
        "iat": int(now.timestamp()),
        "exp": int(access_expiry.timestamp()),
    }

    refresh_payload = {
        "user_id": str(user.id),
        "token_type": "refresh",
        "iat": int(now.timestamp()),
        "exp": int(refresh_expiry.timestamp()),
    }

    algorithm = getattr(settings, "JWT_ALGORITHM", "HS256")
    secret_key = getattr(settings, "JWT_SECRET_KEY", settings.SECRET_KEY)

    access_token = jwt.encode(access_payload, secret_key, algorithm=algorithm)
    refresh_token = jwt.encode(refresh_payload, secret_key, algorithm=algorithm)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "Bearer",
        "expires_in": int(getattr(settings, "JWT_ACCESS_EXPIRATION_MINUTES", 60) * 60),
    }


def decode_token(token: str, expected_type: str = "access") -> dict:
    """Decode and validate a JWT token."""
    if not token:
        raise ValueError("Token is required")

    algorithm = getattr(settings, "JWT_ALGORITHM", "HS256")
    secret_key = getattr(settings, "JWT_SECRET_KEY", settings.SECRET_KEY)

    payload = jwt.decode(token, secret_key, algorithms=[algorithm])
    if payload.get("token_type") != expected_type:
        raise ValueError(f"Invalid token type: expected {expected_type}")

    return payload


def get_user_from_token(token: str):
    """Retrieve an active User instance from a valid access JWT token."""
    payload = decode_token(token, expected_type="access")
    user_id = payload.get("user_id")
    if not user_id:
        return None

    User = get_user_model()
    try:
        user = User.objects.get(id=user_id, is_active=True)
        return user
    except User.DoesNotExist:
        return None
