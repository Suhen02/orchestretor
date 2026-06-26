from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.events import add_job_log
from app.models.job import Job, JobStatus
from app.models.user import User
from app.queue.redis_queue import RedisJobQueue
from app.schemas.job import JobCreate, JobLogRead, JobRead


router = APIRouter(prefix="/jobs", tags=["jobs"])
limiter = Limiter(key_func=get_remote_address)


def _get_owned_job(db: Session, user: User, job_id: UUID) -> Job:
    job = db.scalar(select(Job).where(Job.id == job_id, Job.user_id == user.id))
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job


@router.post("", response_model=JobRead, status_code=status.HTTP_201_CREATED)
@limiter.limit(lambda: get_settings().job_create_rate_limit)
def create_job(
    request: Request,
    payload: JobCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Job:
    job = Job(
        user_id=user.id,
        type=payload.type,
        payload=payload.payload,
        priority=payload.priority,
        max_retries=payload.max_retries,
        status=JobStatus.CREATED,
    )
    db.add(job)
    db.flush()
    add_job_log(db, job.id, "JOB_CREATED", "Job accepted by API", {"type": job.type})
    RedisJobQueue().enqueue(job.id, job.priority)
    job.status = JobStatus.QUEUED
    add_job_log(db, job.id, "JOB_QUEUED", "Job enqueued to Redis priority queue")
    db.commit()
    db.refresh(job)
    return job


@router.get("", response_model=list[JobRead])
def list_jobs(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[Job]:
    return list(
        db.scalars(select(Job).where(Job.user_id == user.id).order_by(Job.created_at.desc())).all()
    )


@router.get("/{job_id}", response_model=JobRead)
def get_job(job_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> Job:
    return _get_owned_job(db, user, job_id)


@router.delete("/{job_id}", response_model=JobRead)
def cancel_job(job_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> Job:
    job = _get_owned_job(db, user, job_id)
    if job.status != JobStatus.QUEUED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only queued jobs can be cancelled")
    RedisJobQueue().remove(job.id)
    job.status = JobStatus.CANCELLED
    add_job_log(db, job.id, "JOB_CANCELLED", "Queued job cancelled by user")
    db.commit()
    db.refresh(job)
    return job


@router.get("/{job_id}/logs", response_model=list[JobLogRead])
def job_logs(job_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    job = _get_owned_job(db, user, job_id)
    return job.logs


@router.post("/{job_id}/retry", response_model=JobRead)
def retry_job(job_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> Job:
    job = _get_owned_job(db, user, job_id)
    if job.status not in {JobStatus.FAILED, JobStatus.DEAD}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only failed or dead jobs can be retried")
    queue = RedisJobQueue()
    queue.remove_from_dlq(job.id)
    job.retry_count = 0
    job.error_message = None
    job.worker_id = None
    job.status = JobStatus.QUEUED
    queue.enqueue(job.id, job.priority)
    add_job_log(db, job.id, "JOB_MANUAL_RETRY", "Job manually requeued by user")
    db.commit()
    db.refresh(job)
    return job
