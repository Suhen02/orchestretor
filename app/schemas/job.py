from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.job import JobStatus


class JobCreate(BaseModel):
    type: str = Field(min_length=1, max_length=50)
    payload: dict[str, Any]
    priority: int = Field(default=2, ge=1, le=3)
    max_retries: int = Field(default=3, ge=0, le=10)


class JobRead(BaseModel):
    id: UUID
    user_id: UUID
    type: str
    status: JobStatus
    priority: int
    payload: dict[str, Any]
    result: dict[str, Any] | None
    retry_count: int
    max_retries: int
    worker_id: str | None
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class JobLogRead(BaseModel):
    id: UUID
    job_id: UUID
    event: str
    message: str
    metadata_: dict[str, Any] = Field(alias="metadata")
    created_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class QueueStats(BaseModel):
    total_depth: int
    high_priority: int
    medium_priority: int
    low_priority: int


class WorkerRead(BaseModel):
    worker_id: str
    last_seen: datetime | None
    status: str
    current_job_id: UUID | None = None


class MetricsRead(BaseModel):
    total_jobs: int
    running_jobs: int
    completed_jobs: int
    failed_jobs: int
    success_rate: float
    avg_execution_time_ms: float
    queue_depth: int
    active_workers: int
    jobs_per_minute: int
    dlq_size: int
    retry_rate: float
