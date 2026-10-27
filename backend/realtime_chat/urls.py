"""Root URL configuration for realtime_chat."""

from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse

def health_check(request):
    return JsonResponse({"status": "ok", "service": "realtime-chat-channels"})

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/health", health_check, name="health-check"),
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/chat/", include("apps.chat.urls")),
]
