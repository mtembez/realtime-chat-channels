import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from apps.accounts.tokens import generate_tokens_for_user

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def create_user(db):
    def _create(email="simon@example.com", username="simon", password="StrongPassword123!", full_name="Simon Munyambu"):
        return User.objects.create_user(
            email=email,
            username=username,
            password=password,
            full_name=full_name,
        )
    return _create


@pytest.mark.django_db
class TestUserRegistration:
    def test_register_success(self, api_client):
        url = reverse("accounts:register")
        payload = {
            "email": "developer@jifunze.org",
            "username": "devsimon",
            "password": "SecurePassword2026!",
            "full_name": "Simon Developer",
        }
        res = api_client.post(url, payload, format="json")
        assert res.status_code == status.HTTP_201_CREATED
        data = res.json()
        assert data["user"]["email"] == "developer@jifunze.org"
        assert data["user"]["username"] == "devsimon"
        assert "tokens" in data
        assert "access_token" in data["tokens"]
        assert "refresh_token" in data["tokens"]

    def test_register_duplicate_email(self, api_client, create_user):
        create_user(email="dup@test.com", username="user1")
        url = reverse("accounts:register")
        res = api_client.post(
            url,
            {"email": "dup@test.com", "username": "user2", "password": "Password123!", "full_name": "User Two"},
            format="json",
        )
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert "email" in res.json()

    def test_register_short_password(self, api_client):
        url = reverse("accounts:register")
        res = api_client.post(
            url,
            {"email": "short@test.com", "username": "shortpass", "password": "123", "full_name": "Short"},
            format="json",
        )
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert "password" in res.json()


@pytest.mark.django_db
class TestUserLogin:
    def test_login_with_email_success(self, api_client, create_user):
        create_user(email="simon@domain.com", username="simonm", password="TargetPassword99!")
        url = reverse("accounts:login")
        res = api_client.post(
            url,
            {"login": "simon@domain.com", "password": "TargetPassword99!"},
            format="json",
        )
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert data["user"]["email"] == "simon@domain.com"
        assert "access_token" in data["tokens"]

    def test_login_with_username_success(self, api_client, create_user):
        create_user(email="simon2@domain.com", username="simonm2", password="TargetPassword99!")
        url = reverse("accounts:login")
        res = api_client.post(
            url,
            {"login": "simonm2", "password": "TargetPassword99!"},
            format="json",
        )
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert data["user"]["username"] == "simonm2"

    def test_login_wrong_password(self, api_client, create_user):
        create_user(email="simon3@domain.com", username="simonm3", password="CorrectPass123!")
        url = reverse("accounts:login")
        res = api_client.post(
            url,
            {"login": "simon3@domain.com", "password": "WrongPassword!"},
            format="json",
        )
        assert res.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestTokenRefreshAndMe:
    def test_refresh_token_success(self, api_client, create_user):
        user = create_user()
        tokens = generate_tokens_for_user(user)

        url = reverse("accounts:refresh")
        res = api_client.post(url, {"refresh_token": tokens["refresh_token"]}, format="json")
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert "access_token" in data
        assert "refresh_token" in data

    def test_refresh_token_invalid(self, api_client):
        url = reverse("accounts:refresh")
        res = api_client.post(url, {"refresh_token": "invalid.jwt.token"}, format="json")
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_me_endpoint_authenticated(self, api_client, create_user):
        user = create_user()
        tokens = generate_tokens_for_user(user)

        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access_token']}")
        url = reverse("accounts:me")
        res = api_client.get(url)
        assert res.status_code == status.HTTP_200_OK
        assert res.json()["id"] == str(user.id)

    def test_me_endpoint_unauthenticated(self, api_client):
        url = reverse("accounts:me")
        res = api_client.get(url)
        assert res.status_code == status.HTTP_401_UNAUTHORIZED
