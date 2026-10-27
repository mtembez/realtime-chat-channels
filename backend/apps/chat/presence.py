import json
import logging
from django.conf import settings
import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

_redis_client = None


def get_redis_client():
    global _redis_client
    if _redis_client is None:
        redis_url = getattr(settings, "REDIS_URL", "redis://127.0.0.1:6379/0")
        _redis_client = aioredis.from_url(redis_url, decode_responses=True)
    return _redis_client


async def add_presence(room_slug: str, user_id: str, username: str) -> list:
    """Add user to room active presence set and return current online users."""
    try:
        client = get_redis_client()
        key = f"presence:room:{room_slug}"
        user_data = json.dumps({"user_id": str(user_id), "username": username})
        await client.hset(key, str(user_id), user_data)
        await client.expire(key, 86400)  # 24h TTL
        return await get_active_users(room_slug)
    except Exception as exc:
        logger.warning("Redis presence error on add: %s", exc)
        return [{"user_id": str(user_id), "username": username}]


async def remove_presence(room_slug: str, user_id: str) -> list:
    """Remove user from room active presence set and return remaining online users."""
    try:
        client = get_redis_client()
        key = f"presence:room:{room_slug}"
        await client.hdel(key, str(user_id))
        return await get_active_users(room_slug)
    except Exception as exc:
        logger.warning("Redis presence error on remove: %s", exc)
        return []


async def get_active_users(room_slug: str) -> list:
    """Fetch all currently online users for a given room."""
    try:
        client = get_redis_client()
        key = f"presence:room:{room_slug}"
        raw_items = await client.hvals(key)
        return [json.loads(item) for item in raw_items]
    except Exception as exc:
        logger.warning("Redis presence error on fetch: %s", exc)
        return []
