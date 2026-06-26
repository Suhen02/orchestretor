from uuid import uuid4

from app.queue.redis_queue import RedisJobQueue


class FakeRedis:
    def __init__(self):
        self.zset = {}
        self.hashes = {}

    def zadd(self, key, mapping):
        self.zset.update(mapping)

    def zrangebyscore(self, key, min, max, start=0, num=None):
        items = [item for item in self.zset.items() if item[1] <= max]
        items.sort(key=lambda item: item[1])
        values = [item[0] for item in items]
        return values[start : start + num if num else None]

    def zrem(self, key, value):
        return 1 if self.zset.pop(value, None) is not None else 0

    def zrange(self, key, start, end, withscores=False):
        items = sorted(self.zset.items(), key=lambda item: item[1])
        if withscores:
            return items
        return [item[0] for item in items]

    def zcard(self, key):
        return len(self.zset)

    def zscore(self, key, value):
        return self.zset.get(value)


def test_queue_dequeues_high_priority_first():
    queue = RedisJobQueue(FakeRedis())
    low = uuid4()
    high = uuid4()
    queue.enqueue(low, priority=3)
    queue.enqueue(high, priority=1)
    assert queue.dequeue() == str(high)
    assert queue.dequeue() == str(low)
