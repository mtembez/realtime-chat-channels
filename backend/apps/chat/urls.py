from django.urls import path
from apps.chat.views import (
    MarkMessageReadView,
    MessageListCreateView,
    MessageSoftDeleteView,
    RoomDetailView,
    RoomListCreateView,
    RoomMembersView,
)

app_name = "chat"

urlpatterns = [
    path("rooms", RoomListCreateView.as_view(), name="room-list-create"),
    path("rooms/<slug:slug>", RoomDetailView.as_view(), name="room-detail"),
    path("rooms/<slug:slug>/members", RoomMembersView.as_view(), name="room-members"),
    path("rooms/<slug:slug>/messages", MessageListCreateView.as_view(), name="message-list-create"),
    path("messages/<uuid:pk>/delete", MessageSoftDeleteView.as_view(), name="message-soft-delete"),
    path("messages/<uuid:pk>/read", MarkMessageReadView.as_view(), name="message-mark-read"),
]
