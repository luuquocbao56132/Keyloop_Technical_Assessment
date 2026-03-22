"""Redis distributed lock for preventing double-booking.

Uses SET NX EX with a Lua compare-and-delete script for safe release,
exactly as specified in §8 of the System Design document.
"""

import uuid
from typing import Optional

import redis as redis_sync

from app.config import REDIS_URL, LOCK_TTL_SECONDS


def get_redis_client() -> redis_sync.Redis:
    """Return a synchronous Redis client."""
    return redis_sync.from_url(REDIS_URL, decode_responses=True)


# Lua script for atomic compare-and-delete (safe release)
_RELEASE_LOCK_LUA = """
if redis.call("GET", KEYS[1]) == ARGV[1] then
    return redis.call("DEL", KEYS[1])
else
    return 0
end
"""


def _lock_key(dealership_id: int, start_iso: str, end_iso: str) -> str:
    """Build the Redis lock key per the design document format."""
    return f"lock:dealership:{dealership_id}:slot:{start_iso}:{end_iso}"


def acquire_booking_lock(
    redis_client: redis_sync.Redis,
    dealership_id: int,
    start_time: str,
    end_time: str,
    timeout: int = LOCK_TTL_SECONDS,
) -> Optional[str]:
    """Attempt to acquire a distributed lock for the booking slot.

    Returns the lock_id (UUID) on success, ``None`` if the lock is already held.
    """
    key = _lock_key(dealership_id, start_time, end_time)
    lock_id = str(uuid.uuid4())
    acquired = redis_client.set(key, lock_id, nx=True, ex=timeout)
    return lock_id if acquired else None


def release_booking_lock(
    redis_client: redis_sync.Redis,
    dealership_id: int,
    start_time: str,
    end_time: str,
    lock_id: str,
) -> None:
    """Release the lock only if we are the owner (compare lock_id)."""
    key = _lock_key(dealership_id, start_time, end_time)
    redis_client.eval(_RELEASE_LOCK_LUA, 1, key, lock_id)
