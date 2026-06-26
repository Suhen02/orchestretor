from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.auth import get_current_admin
from app.core.database import get_db
from app.models.job import Job, JobStatus
from app.queue.redis_queue import RedisJobQueue
from app.schemas.job import MetricsRead
from app.worker.heartbeat import HeartbeatMonitor


router = APIRouter(tags=["metrics"])


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "api"}


@router.get("/metrics", response_model=MetricsRead)
def metrics(db: Session = Depends(get_db), admin=Depends(get_current_admin)) -> MetricsRead:
    total = db.scalar(select(func.count()).select_from(Job)) or 0
    running = db.scalar(select(func.count()).select_from(Job).where(Job.status == JobStatus.RUNNING)) or 0
    completed = db.scalar(select(func.count()).select_from(Job).where(Job.status == JobStatus.COMPLETED)) or 0
    failed = db.scalar(select(func.count()).select_from(Job).where(Job.status == JobStatus.FAILED)) or 0
    retried = db.scalar(select(func.count()).select_from(Job).where(Job.retry_count > 0)) or 0
    last_minute = datetime.now(UTC) - timedelta(minutes=1)
    jobs_per_minute = (
        db.scalar(select(func.count()).select_from(Job).where(Job.created_at >= last_minute)) or 0
    )
    avg_seconds = db.scalar(
        select(func.avg(func.extract("epoch", Job.completed_at - Job.started_at))).where(
            Job.started_at.is_not(None), Job.completed_at.is_not(None)
        )
    ) or 0
    queue = RedisJobQueue()
    active_workers = len([w for w in HeartbeatMonitor(db, queue).list_workers() if w["status"] == "ALIVE"])
    return MetricsRead(
        total_jobs=total,
        running_jobs=running,
        completed_jobs=completed,
        failed_jobs=failed,
        success_rate=round((completed / total) * 100, 2) if total else 0.0,
        avg_execution_time_ms=round(float(avg_seconds) * 1000, 2),
        queue_depth=queue.queue_size(),
        active_workers=active_workers,
        jobs_per_minute=jobs_per_minute,
        dlq_size=queue.dlq_size(),
        retry_rate=round((retried / total) * 100, 2) if total else 0.0,
    )


@router.get("/metrics/throughput")
def throughput(db: Session = Depends(get_db), admin=Depends(get_current_admin)) -> dict:
    since = datetime.now(UTC) - timedelta(minutes=60)
    rows = db.execute(
        select(func.date_trunc("minute", Job.created_at).label("minute"), func.count(Job.id))
        .where(Job.created_at >= since)
        .group_by("minute")
        .order_by("minute")
    ).all()
    return {"points": [{"minute": row[0], "jobs": row[1]} for row in rows]}


@router.post("/config/rate-limit")
def update_rate_limit(admin=Depends(get_current_admin)) -> dict:
    return {"message": "Runtime rate limit updates require a shared config store in production"}
