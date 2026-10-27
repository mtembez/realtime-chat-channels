import logging
from collections import defaultdict
from datetime import timedelta
from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from apps.chat.models import MessageReceipt

logger = logging.getLogger(__name__)


@shared_task(name="apps.notifications.tasks.send_unread_message_digests")
def send_unread_message_digests():
    """Celery Beat task: Scans for users with unread messages older than 15 minutes,

    groups them by room, sends an email digest, and marks them as digest_sent.
    """
    cutoff = timezone.now() - timedelta(minutes=15)

    pending_receipts = (
        MessageReceipt.objects.filter(
            status=MessageReceipt.STATUS_DELIVERED,
            digest_sent=False,
            message__created_at__lte=cutoff,
            message__is_deleted=False,
            user__is_active=True,
        )
        .select_related("user", "message", "message__sender", "message__room")
        .order_by("user_id", "message__created_at")
    )

    if not pending_receipts.exists():
        logger.info("No pending unread digests found.")
        return {"processed_users": 0, "processed_messages": 0}

    # Group receipts by user -> room
    user_digests = defaultdict(lambda: defaultdict(list))
    receipts_to_update = []

    for receipt in pending_receipts:
        user = receipt.user
        room = receipt.message.room
        user_digests[user][room].append(receipt.message)
        receipts_to_update.append(receipt.id)

    emails_sent = 0

    for user, rooms_map in user_digests.items():
        if not user.email:
            continue

        total_unread = sum(len(msgs) for msgs in rooms_map.values())
        subject = f"You have {total_unread} unread message{'s' if total_unread > 1 else ''} in Realtime Chat"

        lines = [
            f"Hello {user.full_name or user.username},",
            "",
            f"You have {total_unread} unread message{'s' if total_unread > 1 else ''} waiting for you:",
            "",
        ]

        for room, messages in rooms_map.items():
            lines.append(f"--- Channel: #{room.name} ({len(messages)} unread) ---")
            for msg in messages[-3:]:  # Last 3 preview
                sender_name = msg.sender.full_name or msg.sender.username
                lines.append(f"  [{sender_name}]: {msg.content[:80]}")
            if len(messages) > 3:
                lines.append(f"  ... and {len(messages) - 3} more messages")
            lines.append("")

        lines.extend([
            "Log in to the dashboard to reply and view your conversations.",
            "",
            "— The Realtime Chat Team",
        ])

        email_body = "\n".join(lines)
        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@realtimechat.com")

        try:
            send_mail(
                subject=subject,
                message=email_body,
                from_email=from_email,
                recipient_list=[user.email],
                fail_silently=False,
            )
            emails_sent += 1
        except Exception as exc:
            logger.error("Failed to send digest email to %s: %s", user.email, exc)

    # Mark receipts as digest_sent=True
    MessageReceipt.objects.filter(id__in=receipts_to_update).update(digest_sent=True)

    logger.info(
        "Unread digest completed: %d emails sent across %d receipts",
        emails_sent,
        len(receipts_to_update),
    )
    return {
        "processed_users": len(user_digests),
        "processed_messages": len(receipts_to_update),
        "emails_sent": emails_sent,
    }
