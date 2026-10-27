import pytest
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from apps.accounts.tokens import generate_tokens_for_user
from apps.chat.models import Message
from realtime_chat.asgi import application

User = get_user_model()


@pytest.fixture
def chat_author(db):
    return User.objects.create_user(
        email="author@domain.com",
        username="author",
        password="SecurePassword999!",
        full_name="Author Person",
    )


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_websocket_chat_lifecycle(chat_author):
    tokens = generate_tokens_for_user(chat_author)
    token = tokens["access_token"]

    communicator = WebsocketCommunicator(
        application,
        f"/ws/chat/general/?token={token}",
    )
    connected, _ = await communicator.connect()
    assert connected is True

    # 1. Discard the initial presence broadcast on connect
    pres = await communicator.receive_json_from()
    assert pres["type"] == "chat_presence"

    # 2. Send real-time message
    await communicator.send_json_to({
        "action": "send_message",
        "content": "Hello Realtime World!",
    })
    msg_broadcast = await communicator.receive_json_from()
    assert msg_broadcast["type"] == "chat_message"
    assert msg_broadcast["content"] == "Hello Realtime World!"
    assert msg_broadcast["sender"]["username"] == "author"
    assert msg_broadcast["parent_id"] is None
    msg_id = msg_broadcast["id"]

    # 3. Send threaded reply
    await communicator.send_json_to({
        "action": "send_message",
        "content": "A threaded reply to root",
        "parent_id": msg_id,
    })
    reply_broadcast = await communicator.receive_json_from()
    assert reply_broadcast["type"] == "chat_message"
    assert reply_broadcast["content"] == "A threaded reply to root"
    assert reply_broadcast["parent_id"] == msg_id

    # 4. Mark message as read
    await communicator.send_json_to({
        "action": "mark_read",
        "message_id": msg_id,
    })
    read_broadcast = await communicator.receive_json_from()
    assert read_broadcast["type"] == "chat_read_receipt"
    assert read_broadcast["message_id"] == msg_id

    # 5. Soft-delete message
    await communicator.send_json_to({
        "action": "delete_message",
        "message_id": msg_id,
    })
    del_broadcast = await communicator.receive_json_from()
    assert del_broadcast["type"] == "chat_message_deleted"
    assert del_broadcast["id"] == msg_id
    assert del_broadcast["is_deleted"] is True
    assert del_broadcast["content"] == "This message was deleted."

    await communicator.disconnect()
