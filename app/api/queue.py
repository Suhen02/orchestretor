from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import get_current_admin
from app.core.database import get_db
from app.models.events import add_job_log
from app.models.job import Job, JobStatus
from app.queue.redis_queue import RedisJobQueue
from app.schemas.job import QueueStats, WorkerRead
from app.worker.heartbeat import HeartbeatMonitor


router = APIRouter(tags=["queue"])


@router.get("/queue/stats", response_model=QueueStats)
def queue_stats(admin=Depends(get_current_admin)) -> dict:
    return RedisJobQueue().stats()


@router.get("/workers", response_model=list[WorkerRead])
def workers(db: Session = Depends(get_db), admin=Depends(get_current_admin)) -> list[dict]:
    return HeartbeatMonitor(db).list_workers()


@router.get("/workers/{worker_id}", response_model=WorkerRead)
def worker(worker_id: str, db: Session = Depends(get_db), admin=Depends(get_current_admin)) -> dict:
    for item in HeartbeatMonitor(db).list_workers():
        if item["worker_id"] == worker_id:
            return item
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Worker not found")


@router.get("/dlq")
def dlq(admin=Depends(get_current_admin)) -> list[dict]:
    return RedisJobQueue().list_dlq()


@router.post("/dlq/{job_id}/requeue")
def requeue_dlq_job(
    job_id: UUID,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    job = db.scalar(select(Job).where(Job.id == job_id))
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    queue = RedisJobQueue()
    queue.remove_from_dlq(job.id)
    job.retry_count = 0
    job.status = JobStatus.QUEUED
    job.error_message = None
    job.worker_id = None
    queue.enqueue(job.id, job.priority)
    add_job_log(db, job.id, "DLQ_REQUEUED", "Job moved from DLQ back to main queue")
    db.commit()
    return {"job_id": job.id, "status": job.status}
