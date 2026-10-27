"""ASGI config for Real-Time Chat & Channels System.

Exposes the ASGI callable as a module-level variable named ``application``.
"""

import os
import django
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "realtime_chat.settings")
django.setup()

from channels.routing import ProtocolTypeRouter, URLRouter
from apps.accounts.middleware import JwtAuthMiddlewareStack
import apps.chat.routing

django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": JwtAuthMiddlewareStack(
            URLRouter(apps.chat.routing.websocket_urlpatterns)
        ),
    }
)
