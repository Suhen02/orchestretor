from sqlalchemy.orm import Session

from app.models.job_log import JobLog


def add_job_log(
    db: Session,
    job_id,
    event: str,
    message: str,
    metadata: dict | None = None,
) -> JobLog:
    log = JobLog(job_id=job_id, event=event, message=message, metadata_=metadata or {})
    db.add(log)
    return log
