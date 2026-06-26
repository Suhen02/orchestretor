# from datetime import UTC, datetime
# import socket
# import time
# from uuid import UUID, uuid4

# from loguru import logger
# from redis import Redis
# from sqlalchemy import select

# from app.core.config import get_settings
# from app.core.database import SessionLocal
# from app.executor.registry import registry
# from app.models.events import add_job_log
# from app.models.job import Job, JobStatus
# from app.queue.redis_queue import RedisJobQueue
# from app.worker.heartbeat import HeartbeatSender
# from app.worker.retry import calculate_delay


# class Worker:
#     def __init__(self, worker_id: str | None = None) -> None:
#         self.settings = get_settings()
#         self.worker_id = worker_id or f"{socket.gethostname()}-{uuid4()}"
#         self.redis = Redis.from_url(self.settings.redis_url, decode_responses=True)
#         self.queue = RedisJobQueue(self.redis)
#         self.heartbeat = HeartbeatSender(self.redis, self.worker_id)

#     def run_forever(self) -> None:
#         self.heartbeat.start()
#         logger.info("worker_started", worker_id=self.worker_id)
#         while True:
#             self.process_once()
#             time.sleep(self.settings.worker_poll_interval_seconds)

#     def process_once(self) -> bool:
#         job_id = self.queue.dequeue()
#         if job_id is None:
#             return False
#         with SessionLocal() as db:
#             job = db.scalar(select(Job).where(Job.id == UUID(job_id)))
#             if job is None or job.status in {JobStatus.CANCELLED, JobStatus.COMPLETED}:
#                 return False
#             self._mark_assigned(db, job)
#             try:
#                 self._run_job(db, job)
#             except Exception as exc:
#                 self._handle_failure(db, job, exc)
#         return True

#     def _mark_assigned(self, db, job: Job) -> None:
#         job.status = JobStatus.ASSIGNED
#         job.worker_id = self.worker_id
#         add_job_log(db, job.id, "WORKER_ASSIGNED", "Worker claimed job", {"worker_id": self.worker_id})
#         db.commit()

#     def _run_job(self, db, job: Job) -> None:
#         job.status = JobStatus.RUNNING
#         job.started_at = datetime.now(UTC)
#         add_job_log(db, job.id, "EXECUTION_STARTED", "Worker started execution")
#         db.commit()

#         started = time.perf_counter()
#         result = registry.get(job.type).execute(job)
#         duration_ms = round((time.perf_counter() - started) * 1000, 2)

#         job.status = JobStatus.COMPLETED
#         job.result = result
#         job.completed_at = datetime.now(UTC)
#         job.error_message = None
#         add_job_log(
#             db,
#             job.id,
#             "EXECUTION_COMPLETED",
#             "Job completed successfully",
#             {"worker_id": self.worker_id, "duration_ms": duration_ms},
#         )
#         db.commit()
#         logger.info("job_completed", worker_id=self.worker_id, job_id=str(job.id), duration_ms=duration_ms)

#     def _handle_failure(self, db, job: Job, exc: Exception) -> None:
#         job.retry_count += 1
#         job.error_message = str(exc)
#         add_job_log(
#             db,
#             job.id,
#             "EXECUTION_FAILED",
#             "Job execution failed",
#             {"worker_id": self.worker_id, "error": str(exc), "retry_count": job.retry_count},
#         )
#         if job.retry_count <= job.max_retries:
#             delay = calculate_delay(job.retry_count)
#             job.status = JobStatus.RETRYING
#             job.worker_id = None
#             self.queue.enqueue(job.id, job.priority, delay_seconds=delay)
#             add_job_log(
#                 db,
#                 job.id,
#                 "JOB_RETRYING",
#                 "Job re-enqueued with exponential backoff",
#                 {"delay_seconds": delay},
#             )
#         else:
#             job.status = JobStatus.DEAD
#             job.completed_at = datetime.now(UTC)
#             self.queue.move_to_dlq(job.id, "max_retries_exhausted", str(exc))
#             add_job_log(db, job.id, "JOB_DEAD", "Max retries exhausted; job moved to DLQ")
#         db.commit()
#         logger.error("job_failed", worker_id=self.worker_id, job_id=str(job.id), error=str(exc))


from datetime import UTC, datetime
import socket
import time
from uuid import UUID, uuid4

from loguru import logger
from redis import Redis
from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.executor.registry import registry
from app.models.events import add_job_log
from app.models.job import Job, JobStatus
from app.queue.redis_queue import RedisJobQueue
from app.worker.heartbeat import HeartbeatSender
from app.worker.retry import calculate_delay


class Worker:
    def __init__(self, worker_id: str | None = None) -> None:
        self.settings = get_settings()
        self.worker_id = worker_id or f"{socket.gethostname()}-{uuid4()}"
        self.redis = Redis.from_url(self.settings.redis_url, decode_responses=True)
        self.queue = RedisJobQueue(self.redis)
        self.heartbeat = HeartbeatSender(self.redis, self.worker_id)

    def run_forever(self) -> None:
        self.heartbeat.start()
        logger.info("worker_started", worker_id=self.worker_id)
        while True:
            self.process_once()
            time.sleep(self.settings.worker_poll_interval_seconds)

    def process_once(self) -> bool:
        job_id = self.queue.dequeue()
        if job_id is None:
            return False
        with SessionLocal() as db:
            job = db.scalar(select(Job).where(Job.id == UUID(job_id)))
            if job is None or job.status in {JobStatus.CANCELLED, JobStatus.COMPLETED}:
                return False
            self._mark_assigned(db, job)
            try:
                self._run_job(db, job)
            except Exception as exc:
                self._handle_failure(db, job, exc)
        return True

    def _mark_assigned(self, db, job: Job) -> None:
        job.status = JobStatus.ASSIGNED
        job.worker_id = self.worker_id
        add_job_log(db, job.id, "WORKER_ASSIGNED", "Worker claimed job", {"worker_id": self.worker_id})
        db.commit()

    def _run_job(self, db, job: Job) -> None:
        job.status = JobStatus.RUNNING
        job.started_at = datetime.now(UTC)
        add_job_log(db, job.id, "EXECUTION_STARTED", "Worker started execution")
        db.commit()

        started = time.perf_counter()
        result = registry.get(job.type).execute(job)
        duration_ms = round((time.perf_counter() - started) * 1000, 2)

        job.status = JobStatus.COMPLETED
        job.result = result
        job.completed_at = datetime.now(UTC)
        job.error_message = None
        add_job_log(
            db,
            job.id,
            "EXECUTION_COMPLETED",
            "Job completed successfully",
            {"worker_id": self.worker_id, "duration_ms": duration_ms},
        )
        db.commit()
        logger.info("job_completed", worker_id=self.worker_id, job_id=str(job.id), duration_ms=duration_ms)

    def _handle_failure(self, db, job: Job, exc: Exception) -> None:
        job.retry_count += 1
        job.error_message = str(exc)

        # ── FIX: always set FAILED first so the lifecycle state is recorded ──
        job.status = JobStatus.FAILED
        add_job_log(
            db,
            job.id,
            "EXECUTION_FAILED",
            "Job execution failed",
            {"worker_id": self.worker_id, "error": str(exc), "retry_count": job.retry_count},
        )

        if job.retry_count <= job.max_retries:
            # ── FIX: doc says delay = 2^(attempt-1): attempt1→1s, attempt2→2s,
            #         attempt3→4s.  Pass retry_count (already incremented) so
            #         calculate_delay(1)→~1s, (2)→~2s, (3)→~4s ─────────────
            delay = calculate_delay(job.retry_count)
            job.status = JobStatus.RETRYING
            job.worker_id = None
            self.queue.enqueue(job.id, job.priority, delay_seconds=delay)
            add_job_log(
                db,
                job.id,
                "JOB_RETRYING",
                "Job re-enqueued with exponential backoff",
                {"delay_seconds": delay},
            )
        else:
            job.status = JobStatus.DEAD
            job.completed_at = datetime.now(UTC)
            self.queue.move_to_dlq(job.id, "max_retries_exhausted", str(exc))
            add_job_log(db, job.id, "JOB_DEAD", "Max retries exhausted; job moved to DLQ")

        db.commit()
        logger.error("job_failed", worker_id=self.worker_id, job_id=str(job.id), error=str(exc))