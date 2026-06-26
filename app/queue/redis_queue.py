from datetime import UTC, datetime
import json
import time
from uuid import UUID

from redis import Redis

from app.core.config import get_settings


QUEUE_KEY = "queue:jobs"
DLQ_KEY = "dlq:jobs"


class RedisJobQueue:
    def __init__(self, redis_client: Redis | None = None) -> None:
        settings = get_settings()
        self.redis = redis_client or Redis.from_url(settings.redis_url, decode_responses=True)

    def enqueue(self, job_id: UUID | str, priority: int, delay_seconds: float = 0) -> None:
        available_at_ms = int((time.time() + delay_seconds) * 1000)
        score = priority * 10_000_000_000_000 + available_at_ms
        self.redis.zadd(QUEUE_KEY, {str(job_id): score})

    def dequeue(self) -> str | None:
        now_ms = int(time.time() * 1000)
        max_score = 3 * 10_000_000_000_000 + now_ms
        item = self.redis.zrangebyscore(QUEUE_KEY, min=0, max=max_score, start=0, num=1)
        if not item:
            return None
        job_id = item[0]
        removed = self.redis.zrem(QUEUE_KEY, job_id)
        return job_id if removed else None

    def peek(self) -> str | None:
        item = self.redis.zrange(QUEUE_KEY, 0, 0)
        return item[0] if item else None

    def queue_size(self) -> int:
        return int(self.redis.zcard(QUEUE_KEY))

    def is_in_queue(self, job_id: UUID | str) -> bool:
        return self.redis.zscore(QUEUE_KEY, str(job_id)) is not None

    def remove(self, job_id: UUID | str) -> bool:
        return bool(self.redis.zrem(QUEUE_KEY, str(job_id)))

    def stats(self) -> dict[str, int]:
        members = self.redis.zrange(QUEUE_KEY, 0, -1, withscores=True)
        counts = {"high_priority": 0, "medium_priority": 0, "low_priority": 0}
        for _, score in members:
            priority = int(score // 10_000_000_000_000)
            if priority == 1:
                counts["high_priority"] += 1
            elif priority == 2:
                counts["medium_priority"] += 1
            elif priority == 3:
                counts["low_priority"] += 1
        counts["total_depth"] = len(members)
        return counts

    def move_to_dlq(self, job_id: UUID | str, failure_reason: str, final_error: str) -> None:
        payload = {
            "job_id": str(job_id),
            "failure_reason": failure_reason,
            "final_error": final_error,
            "moved_at": datetime.now(UTC).isoformat(),
        }
        self.redis.hset(DLQ_KEY, str(job_id), json.dumps(payload))

    def list_dlq(self) -> list[dict]:
        values = self.redis.hvals(DLQ_KEY)
        return [json.loads(value) for value in values]

    def remove_from_dlq(self, job_id: UUID | str) -> bool:
        return bool(self.redis.hdel(DLQ_KEY, str(job_id)))

    def dlq_size(self) -> int:
        return int(self.redis.hlen(DLQ_KEY))
