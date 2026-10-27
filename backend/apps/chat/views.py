from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.chat.models import Message, MessageReceipt, Room, RoomMembership
from apps.chat.serializers import (
    CreateMessageSerializer,
    CreateRoomSerializer,
    MessageSerializer,
    RoomMembershipSerializer,
    RoomSerializer,
)


class RoomListCreateView(generics.ListCreateAPIView):
    """List joined rooms or create a new room."""

    permission_classes = (permissions.IsAuthenticated,)

    def get_serializer_class(self):
        if self.request.method == "POST":
            return CreateRoomSerializer
        return RoomSerializer

    def get_queryset(self):
        return Room.objects.filter(memberships__user=self.request.user).distinct()

    def perform_create(self, serializer):
        room = serializer.save(created_by=self.request.user)
        # Automatically make creator the admin
        RoomMembership.objects.create(
            room=room,
            user=self.request.user,
            role=RoomMembership.ROLE_ADMIN,
        )


class RoomDetailView(generics.RetrieveAPIView):
    """Retrieve room details by slug."""

    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = RoomSerializer
    lookup_field = "slug"
    lookup_url_kwarg = "slug"

    def get_queryset(self):
        return Room.objects.all()


class RoomMembersView(generics.ListAPIView):
    """List members of a room."""

    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = RoomMembershipSerializer

    def get_queryset(self):
        room = get_object_or_404(Room, slug=self.kwargs["slug"])
        return room.memberships.select_related("user").all()


class MessageListCreateView(generics.ListCreateAPIView):
    """List messages for a room or create a new message."""

    permission_classes = (permissions.IsAuthenticated,)

    def get_serializer_class(self):
        if self.request.method == "POST":
            return CreateMessageSerializer
        return MessageSerializer

    def get_queryset(self):
        room = get_object_or_404(Room, slug=self.kwargs["slug"])
        return Message.objects.filter(room=room).select_related("sender", "room").prefetch_related("replies")

    def perform_create(self, serializer):
        room = get_object_or_404(Room, slug=self.kwargs["slug"])
        # Ensure user is a member of the room
        membership, _ = RoomMembership.objects.get_or_create(room=room, user=self.request.user)
        msg = serializer.save(room=room, sender=self.request.user)
        # Update last_read_message for sender
        membership.last_read_message = msg
        membership.save(update_fields=["last_read_message"])
        return msg

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={"room": get_object_or_404(Room, slug=self.kwargs["slug"])})
        serializer.is_valid(raise_exception=True)
        msg = self.perform_create(serializer)
        return Response(MessageSerializer(msg).data, status=status.HTTP_201_CREATED)


class MessageSoftDeleteView(APIView):
    """Soft-delete a message. Only sender or room admin can soft-delete."""

    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, pk):
        msg = get_object_or_404(Message, pk=pk)
        is_sender = msg.sender_id == request.user.id
        is_admin = RoomMembership.objects.filter(
            room=msg.room,
            user=request.user,
            role=RoomMembership.ROLE_ADMIN,
        ).exists()

        if not (is_sender or is_admin):
            return Response(
                {"detail": "You do not have permission to delete this message."},
                status=status.HTTP_403_FORBIDDEN,
            )

        msg.soft_delete()
        return Response(MessageSerializer(msg).data, status=status.HTTP_200_OK)


class MarkMessageReadView(APIView):
    """Mark a message as read by the current user."""

    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, pk):
        msg = get_object_or_404(Message, pk=pk)
        receipt, _ = MessageReceipt.objects.update_or_create(
            message=msg,
            user=request.user,
            defaults={"status": MessageReceipt.STATUS_READ, "read_at": timezone.now()},
        )
        # Also update user's room membership last_read_message
        RoomMembership.objects.filter(room=msg.room, user=request.user).update(last_read_message=msg)

        return Response(
            {
                "status": "read",
                "message_id": str(msg.id),
                "user_id": str(request.user.id),
                "read_at": receipt.read_at.isoformat(),
            },
            status=status.HTTP_200_OK,
        )
