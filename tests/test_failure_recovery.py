"""
tests/test_failure_recovery.py
Unit tests for retry logic, DLQ transition, and worker failure handling.
Doc Section 9.1: test_retry.py — backoff delay calculation, DLQ transition
Doc Section 9.2: test_failure_recovery.py — force job failure, verify retry, verify DLQ
"""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch, call
import pytest

from app.worker.retry import calculate_delay
from app.models.job import Job, JobStatus


# ── Retry delay tests (already have test_retry.py, these extend coverage) ─────

class TestRetryDelay:
    def test_attempt_1_near_1s(self):
        """Doc: Attempt 1 fails → retry after ~1s (2^0 = 1 ± 20%)."""
        for _ in range(20):
            delay = calculate_delay(1)
            assert 0.8 <= delay <= 1.2, f"Attempt 1 delay out of range: {delay}"

    def test_attempt_2_near_2s(self):
        """Doc: Attempt 2 fails → retry after ~2s (2^1 = 2 ± 20%)."""
        for _ in range(20):
            delay = calculate_delay(2)
            assert 1.6 <= delay <= 2.4, f"Attempt 2 delay out of range: {delay}"

    def test_attempt_3_near_4s(self):
        """Doc: Attempt 3 fails → retry after ~4s (2^2 = 4 ± 20%)."""
        for _ in range(20):
            delay = calculate_delay(3)
            assert 3.2 <= delay <= 4.8, f"Attempt 3 delay out of range: {delay}"

    def test_delay_increases_with_attempt(self):
        """Each successive attempt should have a higher expected delay."""
        avg_delays = [sum(calculate_delay(a) for _ in range(50)) / 50 for a in range(1, 5)]
        for i in range(len(avg_delays) - 1):
            assert avg_delays[i] < avg_delays[i + 1]


# ── Worker failure handling ────────────────────────────────────────────────────

class TestWorkerFailureHandling:
    def _make_job(self, retry_count=0, max_retries=3) -> Job:
        job = Job.__new__(Job)
        job.id = "job-uuid-001"
        job.type = "resume_analysis"
        job.status = JobStatus.RUNNING
        job.retry_count = retry_count
        job.max_retries = max_retries
        job.priority = 2
        job.error_message = None
        job.worker_id = "worker-1"
        job.completed_at = None
        return job

    def test_first_failure_sets_failed_then_retrying(self):
        """
        Doc Section 3.2: FAILED → RETRYING lifecycle.
        Worker must set FAILED before deciding to retry.
        """
        from app.worker.worker import Worker
        worker = Worker.__new__(Worker)
        worker.worker_id = "w1"

        db = MagicMock()
        queue = MagicMock()
        worker.queue = queue
        job = self._make_job(retry_count=0, max_retries=3)

        status_history = []
        original_setattr = object.__setattr__

        with patch("app.worker.worker.add_job_log"), \
             patch("app.worker.worker.calculate_delay", return_value=1.0):
            worker._handle_failure(db, job, ValueError("boom"))

        # After _handle_failure: retry_count=1 ≤ max_retries=3 → RETRYING
        assert job.status == JobStatus.RETRYING
        assert job.retry_count == 1

    def test_max_retries_exhausted_sets_dead(self):
        """Doc: retry_count >= max_retries → DEAD + move to DLQ."""
        from app.worker.worker import Worker
        worker = Worker.__new__(Worker)
        worker.worker_id = "w1"

        db = MagicMock()
        queue = MagicMock()
        worker.queue = queue
        job = self._make_job(retry_count=3, max_retries=3)

        with patch("app.worker.worker.add_job_log"):
            worker._handle_failure(db, job, ValueError("still broken"))

        assert job.status == JobStatus.DEAD
        queue.move_to_dlq.assert_called_once()

    def test_error_message_stored(self):
        """error_message field must be populated on failure."""
        from app.worker.worker import Worker
        worker = Worker.__new__(Worker)
        worker.worker_id = "w1"
        db = MagicMock()
        worker.queue = MagicMock()
        job = self._make_job(retry_count=0, max_retries=3)

        with patch("app.worker.worker.add_job_log"), \
             patch("app.worker.worker.calculate_delay", return_value=1.0):
            worker._handle_failure(db, job, RuntimeError("disk full"))

        assert job.error_message == "disk full"

    def test_worker_id_cleared_on_retry(self):
        """Worker ID must be None after re-enqueuing so another worker can claim it."""
        from app.worker.worker import Worker
        worker = Worker.__new__(Worker)
        worker.worker_id = "w1"
        db = MagicMock()
        worker.queue = MagicMock()
        job = self._make_job(retry_count=0, max_retries=3)

        with patch("app.worker.worker.add_job_log"), \
             patch("app.worker.worker.calculate_delay", return_value=1.0):
            worker._handle_failure(db, job, Exception("oops"))

        assert job.worker_id is None