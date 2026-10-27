from rest_framework import serializers
from apps.accounts.serializers import UserSerializer
from apps.chat.models import Message, MessageReceipt, Room, RoomMembership


class MessageReceiptSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = MessageReceipt
        fields = ("id", "message", "user", "status", "read_at")
        read_only_fields = ("id", "read_at")


class MessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)
    room_slug = serializers.CharField(source="room.slug", read_only=True)
    reply_count = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = (
            "id",
            "room_slug",
            "sender",
            "content",
            "parent_message",
            "is_deleted",
            "created_at",
            "updated_at",
            "reply_count",
        )
        read_only_fields = ("id", "is_deleted", "created_at", "updated_at", "reply_count")

    def get_reply_count(self, obj):
        return obj.replies.count()


class CreateMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ("content", "parent_message")

    def validate_parent_message(self, value):
        if value:
            # Parent message must belong to the same room
            room = self.context.get("room")
            if room and value.room_id != room.id:
                raise serializers.ValidationError("Parent message belongs to a different room.")
        return value


class RoomMembershipSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = RoomMembership
        fields = ("id", "user", "role", "is_muted", "joined_at")
        read_only_fields = ("id", "joined_at")


class RoomSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)
    member_count = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = Room
        fields = (
            "id",
            "name",
            "slug",
            "is_direct",
            "topic",
            "created_by",
            "member_count",
            "last_message",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at", "member_count", "last_message")

    def get_member_count(self, obj):
        return obj.memberships.count()

    def get_last_message(self, obj):
        last_msg = obj.messages.order_by("-created_at").first()
        if last_msg:
            return MessageSerializer(last_msg).data
        return None


class CreateRoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = ("name", "slug", "is_direct", "topic")

    def validate_slug(self, value):
        slug = value.strip().lower()
        if Room.objects.filter(slug=slug).exists():
            raise serializers.ValidationError("A room with this slug already exists.")
        return slug
