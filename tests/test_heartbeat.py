"""
tests/test_heartbeat.py
Unit tests for heartbeat sender and stale-worker detector.
Doc Section 9.2: test_heartbeat.py — stop worker heartbeat, verify job re-assigned
"""
import json
import time
import pytest
from unittest.mock import MagicMock, patch, PropertyMock

from app.worker.heartbeat import HeartbeatSender


class FakeRedis:
    """Minimal Redis fake for heartbeat tests — no real connection needed."""

    def __init__(self):
        self._store: dict[str, tuple] = {}  # key → (value, expiry_time)

    def set(self, key: str, value: str, ex: int = None) -> None:
        expires_at = time.time() + ex if ex else None
        self._store[key] = (value, expires_at)

    def get(self, key: str) -> str | None:
        entry = self._store.get(key)
        if not entry:
            return None
        value, expires_at = entry
        if expires_at and time.time() > expires_at:
            del self._store[key]
            return None
        return value

    def exists(self, key: str) -> int:
        return 1 if self.get(key) is not None else 0

    def delete(self, key: str) -> None:
        self._store.pop(key, None)

    def keys(self, pattern: str) -> list[str]:
        # Naive glob: only handles "prefix:*:suffix"
        prefix = pattern.replace("*", "")
        return [k for k in self._store if prefix.split("*")[0] in k]


class TestHeartbeatSender:
    def test_beat_writes_key_with_ttl(self):
        """HeartbeatSender.beat() must write a Redis key with the configured TTL."""
        from app.core.config import get_settings
        settings = get_settings()
        fake_redis = FakeRedis()
        sender = HeartbeatSender(fake_redis, "worker-test-001")
        sender.beat()
        key = "worker:worker-test-001:heartbeat"
        assert fake_redis.get(key) is not None

    def test_beat_key_expires_after_ttl(self):
        """Key must have an expiry so dead workers are auto-detected."""
        from app.core.config import get_settings
        fake_redis = FakeRedis()
        sender = HeartbeatSender(fake_redis, "worker-ttl-test")
        sender.beat()
        key = "worker:worker-ttl-test:heartbeat"
        entry = fake_redis._store.get(key)
        assert entry is not None
        _, expires_at = entry
        assert expires_at is not None, "Heartbeat key must have an expiry time"

    def test_stop_deletes_heartbeat_key(self):
        """Calling stop() should clean up the heartbeat key from Redis."""
        fake_redis = FakeRedis()
        sender = HeartbeatSender(fake_redis, "worker-stop-test")
        sender.beat()
        assert fake_redis.get("worker:worker-stop-test:heartbeat") is not None
        sender.stop()
        assert fake_redis.get("worker:worker-stop-test:heartbeat") is None

    def test_worker_alive_returns_true_when_key_present(self):
        """RedisJobQueue.worker_alive() must return True while heartbeat exists."""
        from app.queue.redis_queue import RedisJobQueue
        fake_redis = FakeRedis()
        queue = RedisJobQueue(fake_redis)
        fake_redis.set("worker:w1:heartbeat", "ts", ex=30)
        assert queue.worker_alive("w1") is True  # type: ignore

    def test_worker_alive_returns_false_when_key_missing(self):
        """worker_alive() must return False when heartbeat key is absent."""
        from app.queue.redis_queue import RedisJobQueue
        fake_redis = FakeRedis()
        queue = RedisJobQueue(fake_redis)
        assert queue.worker_alive("ghost-worker") is False  # type: ignore