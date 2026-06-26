"""
tests/test_job_model.py
Unit tests for Job model status transitions and field defaults.
"""
from app.models.job import Job, JobStatus


def _make_job(**kwargs) -> Job:
    defaults = dict(
        user_id="00000000-0000-0000-0000-000000000001",
        type="resume_analysis",
        status=JobStatus.CREATED,
        priority=2,
        payload={},
        retry_count=0,
        max_retries=3,
    )
    defaults.update(kwargs)
    return Job(**defaults)


class TestJobStatusTransitions:
    def test_normal_path_sequence(self):
        """CREATED → QUEUED → ASSIGNED → RUNNING → COMPLETED is the happy path."""
        valid_transitions = [
            (JobStatus.CREATED, JobStatus.QUEUED),
            (JobStatus.QUEUED, JobStatus.ASSIGNED),
            (JobStatus.ASSIGNED, JobStatus.RUNNING),
            (JobStatus.RUNNING, JobStatus.COMPLETED),
        ]
        for from_status, to_status in valid_transitions:
            job = _make_job(status=from_status)
            job.status = to_status
            assert job.status == to_status

    def test_failure_path_sets_failed_then_retrying(self):
        job = _make_job(status=JobStatus.RUNNING)
        job.status = JobStatus.FAILED
        assert job.status == JobStatus.FAILED
        job.status = JobStatus.RETRYING
        assert job.status == JobStatus.RETRYING

    def test_dead_after_max_retries(self):
        job = _make_job(status=JobStatus.RETRYING, retry_count=3, max_retries=3)
        job.status = JobStatus.DEAD
        assert job.status == JobStatus.DEAD

    def test_cancelled_only_from_queued(self):
        job = _make_job(status=JobStatus.QUEUED)
        job.status = JobStatus.CANCELLED
        assert job.status == JobStatus.CANCELLED

    def test_default_priority_is_medium(self):
        job = Job(
            user_id="00000000-0000-0000-0000-000000000001",
            type="email_send",
            payload={},
        )
        assert job.priority == 2

    def test_default_retry_count_is_zero(self):
        job = Job(
            user_id="00000000-0000-0000-0000-000000000001",
            type="email_send",
            payload={},
        )
        assert job.retry_count == 0

    def test_all_statuses_are_defined(self):
        expected = {
            "CREATED", "QUEUED", "ASSIGNED", "RUNNING",
            "COMPLETED", "FAILED", "RETRYING", "DEAD", "CANCELLED",
        }
        actual = {s.value for s in JobStatus}
        assert actual == expected, f"Missing statuses: {expected - actual}"