from django.urls import path
from apps.accounts.views import LoginView, MeView, RefreshTokenView, RegisterView

app_name = "accounts"

urlpatterns = [
    path("register", RegisterView.as_view(), name="register"),
    path("login", LoginView.as_view(), name="login"),
    path("refresh", RefreshTokenView.as_view(), name="refresh"),
    path("me", MeView.as_view(), name="me"),
]
