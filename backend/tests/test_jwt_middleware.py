import pytest
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from apps.accounts.tokens import generate_tokens_for_user
from realtime_chat.asgi import application

User = get_user_model()


@pytest.fixture
def test_user(db):
    return User.objects.create_user(
        email="websocket_tester@domain.com",
        username="wstester",
        password="TestPassword123!",
        full_name="WS Tester",
    )


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_websocket_valid_token_query_param(test_user):
    tokens = generate_tokens_for_user(test_user)
    token = tokens["access_token"]

    communicator = WebsocketCommunicator(
        application,
        f"/ws/chat/general/?token={token}",
    )
    connected, subprotocol = await communicator.connect()
    assert connected is True

    # Send a ping frame
    await communicator.send_json_to({"action": "ping"})
    response = await communicator.receive_json_from()
    assert response == {"type": "pong"}

    await communicator.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_websocket_valid_token_header(test_user):
    tokens = generate_tokens_for_user(test_user)
    token = tokens["access_token"]

    communicator = WebsocketCommunicator(
        application,
        "/ws/chat/general/",
        headers=[(b"authorization", f"Bearer {token}".encode("utf-8"))],
    )
    connected, subprotocol = await communicator.connect()
    assert connected is True

    await communicator.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_websocket_rejects_missing_token():
    communicator = WebsocketCommunicator(
        application,
        "/ws/chat/general/",
    )
    connected, close_code = await communicator.connect()
    assert connected is False
    assert close_code == 4001


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_websocket_rejects_invalid_token():
    communicator = WebsocketCommunicator(
        application,
        "/ws/chat/general/?token=tampered_or_invalid_token",
    )
    connected, close_code = await communicator.connect()
    assert connected is False
    assert close_code == 4001
