import uuid
from django.conf import settings
from django.db import models


class Room(models.Model):
    """Chat room supporting both multi-user group channels and 1-on-1 direct messaging."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True, db_index=True)
    is_direct = models.BooleanField(default=False, help_text="True for 1-on-1 direct message, False for group")
    topic = models.TextField(blank=True, default="")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_rooms",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "rooms"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Room({self.slug}, is_direct={self.is_direct})"


class RoomMembership(models.Model):
    """Membership mapping connecting Users to Rooms with roles and mute state."""

    ROLE_ADMIN = "admin"
    ROLE_MEMBER = "member"
    ROLE_CHOICES = (
        (ROLE_ADMIN, "Admin"),
        (ROLE_MEMBER, "Member"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="room_memberships")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_MEMBER)
    last_read_message = models.ForeignKey(
        "Message",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    is_muted = models.BooleanField(default=False)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "room_memberships"
        unique_together = ("room", "user")
        indexes = [
            models.Index(fields=["room", "user"]),
        ]

    def __str__(self):
        return f"{self.user} in {self.room.slug} ({self.role})"


class Message(models.Model):
    """Message entity supporting soft-delete, threaded replies, and PostgreSQL time-series indexing."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="messages", db_index=True)
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_messages", db_index=True)
    content = models.TextField()
    parent_message = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="replies",
    )
    is_deleted = models.BooleanField(default=False, help_text="Soft-delete flag preserving message history & threads")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "messages"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["room", "created_at"]),
            models.Index(fields=["room", "parent_message"]),
        ]

    def __str__(self):
        status_suffix = " [DELETED]" if self.is_deleted else ""
        return f"Msg {self.id} from {self.sender} in {self.room.slug}{status_suffix}"

    def soft_delete(self):
        """Perform soft delete by masking content and marking is_deleted."""
        self.is_deleted = True
        self.content = "This message was deleted."
        self.save(update_fields=["is_deleted", "content", "updated_at"])


class MessageReceipt(models.Model):
    """Per-user message delivery and read receipts."""

    STATUS_DELIVERED = "delivered"
    STATUS_READ = "read"
    STATUS_CHOICES = (
        (STATUS_DELIVERED, "Delivered"),
        (STATUS_READ, "Read"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="receipts")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="message_receipts")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DELIVERED)
    read_at = models.DateTimeField(null=True, blank=True)
    digest_sent = models.BooleanField(default=False, db_index=True)

    class Meta:
        db_table = "message_receipts"
        unique_together = ("message", "user")
        indexes = [
            models.Index(fields=["message", "user"]),
            models.Index(fields=["user", "status"]),
            models.Index(fields=["status", "digest_sent"]),
        ]

    def __str__(self):
        return f"Receipt({self.message_id}, {self.user_id}, {self.status})"
