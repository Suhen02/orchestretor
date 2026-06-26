from datetime import UTC, datetime
import threading
import time

from redis import Redis
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.events import add_job_log
from app.models.job import Job, JobStatus
from app.queue.redis_queue import RedisJobQueue


class HeartbeatSender:
    def __init__(self, redis_client: Redis, worker_id: str) -> None:
        self.redis = redis_client
        self.worker_id = worker_id
        self.settings = get_settings()
        self._stop = threading.Event()

    def start(self) -> threading.Thread:
        thread = threading.Thread(target=self.run, daemon=True)
        thread.start()
        return thread

    def stop(self) -> None:
        self._stop.set()

    def run(self) -> None:
        while not self._stop.is_set():
            self.beat()
            self._stop.wait(self.settings.worker_heartbeat_interval_seconds)

    def beat(self) -> None:
        key = f"worker:{self.worker_id}:heartbeat"
        self.redis.setex(
            key,
            self.settings.worker_heartbeat_ttl_seconds,
            datetime.now(UTC).isoformat(),
        )


class HeartbeatMonitor:
    def __init__(self, db: Session, queue: RedisJobQueue | None = None) -> None:
        self.db = db
        self.queue = queue or RedisJobQueue()

    def recover_dead_worker_jobs(self) -> int:
        workers = self.list_workers()
        alive_ids = {worker["worker_id"] for worker in workers if worker["status"] == "ALIVE"}
        running_jobs = self.db.scalars(select(Job).where(Job.status == JobStatus.RUNNING)).all()
        recovered = 0
        for job in running_jobs:
            if job.worker_id and job.worker_id not in alive_ids:
                job.status = JobStatus.QUEUED
                job.worker_id = None
                self.queue.enqueue(job.id, job.priority)
                add_job_log(
                    self.db,
                    job.id,
                    "WORKER_CRASH_DETECTED",
                    "Running job was requeued after stale worker heartbeat",
                )
                recovered += 1
        self.db.commit()
        return recovered

    def list_workers(self) -> list[dict]:
        workers = []
        for raw_key in self.queue.redis.scan_iter("worker:*:heartbeat"):
            key = raw_key if isinstance(raw_key, str) else raw_key.decode()
            worker_id = key.removeprefix("worker:").removesuffix(":heartbeat")
            value = self.queue.redis.get(key)
            last_seen = datetime.fromisoformat(value) if value else None
            ttl = self.queue.redis.ttl(key)
            current_job = self.db.scalar(
                select(Job).where(Job.worker_id == worker_id, Job.status == JobStatus.RUNNING)
            )
            workers.append(
                {
                    "worker_id": worker_id,
                    "last_seen": last_seen,
                    "status": "ALIVE" if ttl > 0 else "DEAD",
                    "current_job_id": current_job.id if current_job else None,
                }
            )
        return workers
