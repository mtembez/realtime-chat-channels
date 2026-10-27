from datetime import timedelta
import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.utils import timezone
from apps.chat.models import Message, MessageReceipt, Room, RoomMembership
from apps.notifications.tasks import send_unread_message_digests

User = get_user_model()


@pytest.fixture
def users(db):
    alice = User.objects.create_user(
        email="alice@test.com", username="alice", password="Password123!", full_name="Alice Adams"
    )
    bob = User.objects.create_user(
        email="bob@test.com", username="bob", password="Password123!", full_name="Bob Brown"
    )
    return alice, bob


@pytest.fixture
def room(db, users):
    alice, bob = users
    room = Room.objects.create(name="Project Updates", slug="project-updates", is_direct=False)
    RoomMembership.objects.create(room=room, user=alice, role=RoomMembership.ROLE_ADMIN)
    RoomMembership.objects.create(room=room, user=bob, role=RoomMembership.ROLE_MEMBER)
    return room


@pytest.mark.django_db
class TestUnreadEmailDigest:
    def test_no_unread_messages(self):
        mail.outbox.clear()
        res = send_unread_message_digests()
        assert res["processed_users"] == 0
        assert res["processed_messages"] == 0
        assert len(mail.outbox) == 0

    def test_messages_younger_than_15_mins_skipped(self, users, room):
        alice, bob = users
        mail.outbox.clear()

        # Alice sends message 5 minutes ago
        msg = Message.objects.create(
            room=room,
            sender=alice,
            content="Recent urgent update",
            created_at=timezone.now() - timedelta(minutes=5),
        )
        MessageReceipt.objects.create(message=msg, user=bob, status=MessageReceipt.STATUS_DELIVERED)

        res = send_unread_message_digests()
        assert res["processed_messages"] == 0
        assert len(mail.outbox) == 0

    def test_messages_older_than_15_mins_triggers_digest(self, users, room):
        alice, bob = users
        mail.outbox.clear()

        # Alice sends message 25 minutes ago
        past_time = timezone.now() - timedelta(minutes=25)
        msg = Message.objects.create(
            room=room,
            sender=alice,
            content="Old unread announcement",
        )
        Message.objects.filter(id=msg.id).update(created_at=past_time)

        receipt = MessageReceipt.objects.create(
            message=msg,
            user=bob,
            status=MessageReceipt.STATUS_DELIVERED,
            digest_sent=False,
        )

        res = send_unread_message_digests()
        assert res["processed_users"] == 1
        assert res["processed_messages"] == 1
        assert res["emails_sent"] == 1

        # Check outbox
        assert len(mail.outbox) == 1
        email = mail.outbox[0]
        assert email.to == ["bob@test.com"]
        assert "unread message" in email.subject.lower()
        assert "Old unread announcement" in email.body
        assert "#Project Updates" in email.body

        # Verify receipt marked digest_sent=True
        receipt.refresh_from_db()
        assert receipt.digest_sent is True

        # Second invocation: should NOT send duplicate email
        mail.outbox.clear()
        res2 = send_unread_message_digests()
        assert res2["processed_messages"] == 0
        assert len(mail.outbox) == 0

    def test_deleted_messages_excluded_from_digest(self, users, room):
        alice, bob = users
        mail.outbox.clear()

        past_time = timezone.now() - timedelta(minutes=30)
        msg = Message.objects.create(
            room=room,
            sender=alice,
            content="Will be deleted",
            is_deleted=True,
        )
        Message.objects.filter(id=msg.id).update(created_at=past_time)

        MessageReceipt.objects.create(
            message=msg,
            user=bob,
            status=MessageReceipt.STATUS_DELIVERED,
            digest_sent=False,
        )

        res = send_unread_message_digests()
        assert res["processed_messages"] == 0
        assert len(mail.outbox) == 0
