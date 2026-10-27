import json
import logging
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.utils import timezone
from apps.chat.models import Message, MessageReceipt, Room, RoomMembership
from apps.chat.presence import add_presence, get_active_users, remove_presence

logger = logging.getLogger(__name__)


@database_sync_to_async
def get_room_and_membership(room_slug: str, user):
    """Retrieve room and verify user membership."""
    try:
        room = Room.objects.get(slug=room_slug)
    except Room.DoesNotExist:
        # Create public room if it doesn't exist yet
        room = Room.objects.create(name=room_slug.capitalize(), slug=room_slug, is_direct=False)

    membership, _ = RoomMembership.objects.get_or_create(
        room=room,
        user=user,
        defaults={"role": RoomMembership.ROLE_MEMBER},
    )
    return room, membership


@database_sync_to_async
def save_message(room_id, sender, content: str, parent_id: str = None):
    """Persist message and initialize delivery receipts for active room members."""
    parent = None
    if parent_id:
        try:
            parent = Message.objects.get(id=parent_id, room_id=room_id)
        except Message.DoesNotExist:
            parent = None

    msg = Message.objects.create(
        room_id=room_id,
        sender=sender,
        content=content,
        parent_message=parent,
    )

    # Create receipts for other members
    memberships = RoomMembership.objects.filter(room_id=room_id).exclude(user=sender)
    receipts = [
        MessageReceipt(message=msg, user=m.user, status=MessageReceipt.STATUS_DELIVERED)
        for m in memberships
    ]
    if receipts:
        MessageReceipt.objects.bulk_create(receipts, ignore_conflicts=True)

    # Update sender's last read message
    RoomMembership.objects.filter(room_id=room_id, user=sender).update(last_read_message=msg)

    return {
        "id": str(msg.id),
        "room_id": str(msg.room_id),
        "sender": {
            "id": str(sender.id),
            "username": sender.username,
            "full_name": sender.full_name,
            "avatar_url": sender.avatar_url,
        },
        "content": msg.content,
        "parent_id": str(parent.id) if parent else None,
        "is_deleted": False,
        "created_at": msg.created_at.isoformat(),
    }


@database_sync_to_async
def execute_soft_delete(message_id: str, user):
    """Verify delete permission and soft-delete message."""
    try:
        msg = Message.objects.select_related("room").get(id=message_id)
    except Message.DoesNotExist:
        return None

    is_sender = msg.sender_id == user.id
    is_admin = RoomMembership.objects.filter(
        room=msg.room, user=user, role=RoomMembership.ROLE_ADMIN
    ).exists()

    if not (is_sender or is_admin):
        return None

    msg.soft_delete()
    return {
        "id": str(msg.id),
        "room_slug": msg.room.slug,
        "is_deleted": True,
        "content": msg.content,
        "updated_at": msg.updated_at.isoformat(),
    }


@database_sync_to_async
def execute_mark_read(message_id: str, user):
    """Mark message read in receipt and room membership."""
    try:
        msg = Message.objects.select_related("room").get(id=message_id)
    except Message.DoesNotExist:
        return None

    receipt, _ = MessageReceipt.objects.update_or_create(
        message=msg,
        user=user,
        defaults={"status": MessageReceipt.STATUS_READ, "read_at": timezone.now()},
    )
    RoomMembership.objects.filter(room=msg.room, user=user).update(last_read_message=msg)

    return {
        "message_id": str(msg.id),
        "room_slug": msg.room.slug,
        "reader": {
            "id": str(user.id),
            "username": user.username,
        },
        "read_at": receipt.read_at.isoformat(),
    }


class ChatConsumer(AsyncWebsocketConsumer):
    """High-throughput ASGI WebSocket Consumer for rooms, typing, and presence."""

    async def connect(self):
        self.user = self.scope.get("user")
        if not self.user or self.user.is_anonymous:
            # Strictly reject unauthenticated connections at handshake upgrade
            await self.close(code=4001)
            return

        self.room_slug = self.scope["url_route"]["kwargs"]["room_slug"]
        self.room_group_name = f"chat_{self.room_slug}"

        # Fetch room and ensure membership
        self.room, self.membership = await get_room_and_membership(self.room_slug, self.user)

        # Join Redis Channel Layer group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        # Update Redis presence and broadcast
        active_users = await add_presence(self.room_slug, self.user.id, self.user.username)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_presence",
                "user_id": str(self.user.id),
                "username": self.user.username,
                "status": "online",
                "active_users": active_users,
            },
        )

    async def disconnect(self, close_code):
        if hasattr(self, "room_group_name") and hasattr(self, "user") and not self.user.is_anonymous:
            active_users = await remove_presence(self.room_slug, self.user.id)
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat_presence",
                    "user_id": str(self.user.id),
                    "username": self.user.username,
                    "status": "offline",
                    "active_users": active_users,
                },
            )
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            return

        try:
            payload = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({"error": "Invalid JSON format"}))
            return

        action = payload.get("action")

        if action == "ping":
            await self.send(text_data=json.dumps({"type": "pong"}))
            return

        elif action == "send_message":
            content = payload.get("content", "").strip()
            if not content:
                return

            parent_id = payload.get("parent_id")
            msg_dict = await save_message(self.room.id, self.user, content, parent_id)

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat_message",
                    **msg_dict,
                },
            )

        elif action == "delete_message":
            message_id = payload.get("message_id")
            if not message_id:
                return

            deleted_dict = await execute_soft_delete(message_id, self.user)
            if deleted_dict:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "chat_message_deleted",
                        **deleted_dict,
                    },
                )

        elif action == "typing":
            is_typing = bool(payload.get("is_typing", False))
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat_typing",
                    "sender_id": str(self.user.id),
                    "username": self.user.username,
                    "is_typing": is_typing,
                },
            )

        elif action == "mark_read":
            message_id = payload.get("message_id")
            if not message_id:
                return

            receipt_dict = await execute_mark_read(message_id, self.user)
            if receipt_dict:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "chat_read_receipt",
                        **receipt_dict,
                    },
                )

    # --- Redis Channel Layer Broadcast Handlers ---

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event))

    async def chat_message_deleted(self, event):
        await self.send(text_data=json.dumps(event))

    async def chat_typing(self, event):
        # Do not echo typing state back to the user who sent it
        if event.get("sender_id") != str(self.user.id):
            await self.send(text_data=json.dumps(event))

    async def chat_presence(self, event):
        await self.send(text_data=json.dumps(event))

    async def chat_read_receipt(self, event):
        await self.send(text_data=json.dumps(event))
