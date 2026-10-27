import urllib.parse
import jwt
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from apps.accounts.tokens import get_user_from_token


@database_sync_to_async
def get_user_async(token: str):
    try:
        user = get_user_from_token(token)
        return user or AnonymousUser()
    except Exception:
        return AnonymousUser()


class JwtAuthMiddleware:
    """ASGI middleware for authenticating WebSocket connections using JWT tokens.

    Extracts token from query string (?token=...) or Authorization header.
    If the connection is unauthenticated, it is rejected immediately at handshake
    with WebSocket close code 4001 (Unauthorized).
    """

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        if scope["type"] != "websocket":
            return await self.inner(scope, receive, send)

        # 1. Try query string: ?token=...
        token = None
        query_string = scope.get("query_string", b"").decode("utf-8")
        if query_string:
            query_params = urllib.parse.parse_qs(query_string)
            token = query_params.get("token", [None])[0]

        # 2. Try Authorization header: Bearer <token>
        if not token:
            headers = dict(scope.get("headers", []))
            auth_header = headers.get(b"authorization", b"").decode("utf-8")
            if auth_header.startswith("Bearer "):
                token = auth_header[7:].strip()

        # 3. Authenticate user
        if token:
            user = await get_user_async(token)
            scope["user"] = user
        else:
            scope["user"] = AnonymousUser()

        # 4. Strict Handshake Rejection: If unauthenticated, reject before consumer accept()
        if scope["user"].is_anonymous:
            event = await receive()
            if event["type"] == "websocket.connect":
                await send({"type": "websocket.close", "code": 4001})
                return

        return await self.inner(scope, receive, send)


def JwtAuthMiddlewareStack(inner):
    """Convenience wrapper for JwtAuthMiddleware."""
    return JwtAuthMiddleware(inner)
