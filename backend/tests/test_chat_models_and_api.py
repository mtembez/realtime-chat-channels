import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from apps.accounts.tokens import generate_tokens_for_user
from apps.chat.models import Message, MessageReceipt, Room, RoomMembership

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def auth_user(db):
    user = User.objects.create_user(
        email="simon@chat.com",
        username="simon",
        password="Pass12345678!",
        full_name="Simon Munyambu",
    )
    tokens = generate_tokens_for_user(user)
    return user, tokens["access_token"]


@pytest.fixture
def other_user(db):
    user = User.objects.create_user(
        email="colleague@chat.com",
        username="colleague",
        password="Pass12345678!",
        full_name="Colleague Developer",
    )
    tokens = generate_tokens_for_user(user)
    return user, tokens["access_token"]


@pytest.mark.django_db
class TestRoomAPI:
    def test_create_room(self, api_client, auth_user):
        user, token = auth_user
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        url = reverse("chat:room-list-create")
        payload = {
            "name": "General Engineering",
            "slug": "engineering",
            "topic": "High-throughput systems",
            "is_direct": False,
        }
        res = api_client.post(url, payload, format="json")
        assert res.status_code == status.HTTP_201_CREATED
        data = res.json()
        assert data["slug"] == "engineering"
        assert data["name"] == "General Engineering"

        # Verify creator is auto-added as admin
        room = Room.objects.get(slug="engineering")
        membership = RoomMembership.objects.get(room=room, user=user)
        assert membership.role == RoomMembership.ROLE_ADMIN

    def test_create_duplicate_slug_rejected(self, api_client, auth_user):
        user, token = auth_user
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        url = reverse("chat:room-list-create")
        payload = {"name": "Room One", "slug": "room-dup", "is_direct": False}
        api_client.post(url, payload, format="json")

        # Second creation with same slug
        res = api_client.post(url, payload, format="json")
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_list_user_rooms(self, api_client, auth_user, other_user):
        user1, token1 = auth_user
        user2, token2 = other_user
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token1}")

        # Create room as user1
        room = Room.objects.create(name="Devs", slug="devs", is_direct=False, created_by=user1)
        RoomMembership.objects.create(room=room, user=user1, role=RoomMembership.ROLE_ADMIN)

        url = reverse("chat:room-list-create")
        res = api_client.get(url)
        assert res.status_code == status.HTTP_200_OK
        slugs = [r["slug"] for r in res.json()]
        assert "devs" in slugs

        # User2 shouldn't see it until joined
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token2}")
        res2 = api_client.get(url)
        assert "devs" not in [r["slug"] for r in res2.json()]


@pytest.mark.django_db
class TestMessageAndThreadingAPI:
    def test_create_message_and_reply_thread(self, api_client, auth_user):
        user, token = auth_user
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        room = Room.objects.create(name="Random", slug="random", is_direct=False, created_by=user)
        RoomMembership.objects.create(room=room, user=user, role=RoomMembership.ROLE_ADMIN)

        # 1. Post parent message
        url = reverse("chat:message-list-create", kwargs={"slug": "random"})
        res = api_client.post(url, {"content": "First root message"}, format="json")
        assert res.status_code == status.HTTP_201_CREATED
        parent_id = res.json()["id"]

        # 2. Post threaded reply referencing parent_id
        res_reply = api_client.post(
            url,
            {"content": "Replying to root message", "parent_message": parent_id},
            format="json",
        )
        assert res_reply.status_code == status.HTTP_201_CREATED
        reply_data = res_reply.json()
        assert reply_data["parent_message"] == parent_id

        # 3. Verify reply count on parent
        res_list = api_client.get(url)
        assert res_list.status_code == status.HTTP_200_OK
        messages = res_list.json()
        root_msg = next(m for m in messages if m["id"] == parent_id)
        assert root_msg["reply_count"] == 1

    def test_soft_delete_message(self, api_client, auth_user, other_user):
        user1, token1 = auth_user
        user2, token2 = other_user
        room = Room.objects.create(name="General", slug="general", is_direct=False, created_by=user1)
        RoomMembership.objects.create(room=room, user=user1, role=RoomMembership.ROLE_ADMIN)
        RoomMembership.objects.create(room=room, user=user2, role=RoomMembership.ROLE_MEMBER)

        msg = Message.objects.create(room=room, sender=user1, content="Sensitive secret")

        # Non-sender non-admin (user2) cannot delete user1's message
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token2}")
        del_url = reverse("chat:message-soft-delete", kwargs={"pk": msg.id})
        res_forbidden = api_client.post(del_url)
        assert res_forbidden.status_code == status.HTTP_403_FORBIDDEN

        # Sender (user1) can delete
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token1}")
        res_ok = api_client.post(del_url)
        assert res_ok.status_code == status.HTTP_200_OK
        assert res_ok.json()["is_deleted"] is True
        assert res_ok.json()["content"] == "This message was deleted."

        # Verify DB persisted soft-delete
        msg.refresh_from_db()
        assert msg.is_deleted is True
        assert msg.content == "This message was deleted."

    def test_mark_message_read(self, api_client, other_user, auth_user):
        user1, token1 = auth_user
        user2, token2 = other_user
        room = Room.objects.create(name="Announcements", slug="announcements", created_by=user1)
        RoomMembership.objects.create(room=room, user=user1, role=RoomMembership.ROLE_ADMIN)
        membership2 = RoomMembership.objects.create(room=room, user=user2, role=RoomMembership.ROLE_MEMBER)

        msg = Message.objects.create(room=room, sender=user1, content="Hello all!")

        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token2}")
        read_url = reverse("chat:message-mark-read", kwargs={"pk": msg.id})
        res = api_client.post(read_url)
        assert res.status_code == status.HTTP_200_OK
        assert res.json()["status"] == "read"

        # Verify receipt created
        receipt = MessageReceipt.objects.get(message=msg, user=user2)
        assert receipt.status == MessageReceipt.STATUS_READ
        assert receipt.read_at is not None

        # Verify user2 membership last_read_message updated
        membership2.refresh_from_db()
        assert membership2.last_read_message_id == msg.id
