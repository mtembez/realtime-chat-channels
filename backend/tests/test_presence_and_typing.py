import pytest
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from apps.accounts.tokens import generate_tokens_for_user
from apps.chat.presence import add_presence, get_active_users, remove_presence
from realtime_chat.asgi import application

User = get_user_model()


@pytest.fixture
def chat_user(db):
    return User.objects.create_user(
        email="presence_user@test.com",
        username="presenceman",
        password="Password123!",
        full_name="Presence Man",
    )


@pytest.mark.asyncio
async def test_redis_presence_crud():
    room_slug = "test-presence-room"
    user_id = "11111111-1111-1111-1111-111111111111"
    username = "simon_online"

    # 1. Add presence
    active = await add_presence(room_slug, user_id, username)
    user_ids = [u["user_id"] for u in active]
    assert user_id in user_ids

    # 2. Get active users
    active_now = await get_active_users(room_slug)
    assert any(u["username"] == username for u in active_now)

    # 3. Remove presence
    remaining = await remove_presence(room_slug, user_id)
    rem_ids = [u["user_id"] for u in remaining]
    assert user_id not in rem_ids


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_websocket_presence_and_typing(chat_user):
    tokens = generate_tokens_for_user(chat_user)
    token = tokens["access_token"]

    communicator = WebsocketCommunicator(
        application,
        f"/ws/chat/engineering/?token={token}",
    )
    connected, _ = await communicator.connect()
    assert connected is True

    # On connect, client receives presence broadcast
    presence_msg = await communicator.receive_json_from()
    assert presence_msg["type"] == "chat_presence"
    assert presence_msg["status"] == "online"
    assert presence_msg["username"] == "presenceman"

    # Send typing event
    await communicator.send_json_to({"action": "typing", "is_typing": True})

    # Note: Typing event is not echoed to self (prevent self-noise)
    # Ping-pong to verify channel is healthy
    await communicator.send_json_to({"action": "ping"})
    pong = await communicator.receive_json_from()
    assert pong == {"type": "pong"}

    await communicator.disconnect()
