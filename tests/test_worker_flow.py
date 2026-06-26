"""
tests/test_worker_flow.py
Unit tests for the Worker process_once loop.
Doc Section 9.2: test_worker_flow.py — submit job, start worker, verify completion
"""
import uuid
import pytest
from unittest.mock import MagicMock, patch, call

from app.models.job import Job, JobStatus


def _make_job(status=JobStatus.QUEUED, retry_count=0, max_retries=3) -> Job:
    j = Job.__new__(Job)
    j.id = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
    j.type = "email_send"
    j.status = status
    j.priority = 2
    j.payload = {"to": "x@y.com", "subject": "Hi", "body": "Hello"}
    j.result = None
    j.retry_count = retry_count
    j.max_retries = max_retries
    j.worker_id = None
    j.error_message = None
    j.started_at = None
    j.completed_at = None
    j.user_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    return j


class TestWorkerProcessOnce:
    def _make_worker(self):
        from app.worker.worker import Worker
        w = Worker.__new__(Worker)
        w.worker_id = "test-worker-1"
        w.queue = MagicMock()
        w.settings = MagicMock()
        return w

    def test_returns_false_when_queue_empty(self):
        w = self._make_worker()
        w.queue.dequeue.return_value = None
        result = w.process_once()
        assert result is False

    def test_skips_cancelled_job(self):
        """Worker must skip jobs that are already CANCELLED."""
        w = self._make_worker()
        job = _make_job(status=JobStatus.CANCELLED)
        w.queue.dequeue.return_value = str(job.id)

        mock_db = MagicMock()
        mock_db.__enter__ = MagicMock(return_value=mock_db)
        mock_db.__exit__ = MagicMock(return_value=False)
        mock_db.scalar.return_value = job

        with patch("app.worker.worker.SessionLocal", return_value=mock_db):
            result = w.process_once()

        assert result is False

    def test_successful_job_sets_completed(self):
        """Happy path: job executes, status becomes COMPLETED."""
        w = self._make_worker()
        job = _make_job(status=JobStatus.QUEUED)
        w.queue.dequeue.return_value = str(job.id)

        mock_db = MagicMock()
        mock_db.__enter__ = MagicMock(return_value=mock_db)
        mock_db.__exit__ = MagicMock(return_value=False)
        mock_db.scalar.return_value = job

        mock_executor = MagicMock()
        mock_executor.execute.return_value = {"delivered": True}

        with patch("app.worker.worker.SessionLocal", return_value=mock_db), \
             patch("app.worker.worker.registry") as mock_registry, \
             patch("app.worker.worker.add_job_log"):
            mock_registry.get.return_value = mock_executor
            result = w.process_once()

        assert result is True
        assert job.status == JobStatus.COMPLETED
        assert job.result == {"delivered": True}
        assert job.error_message is None

    def test_failed_job_increments_retry_count(self):
        """On exception, retry_count must increase by 1."""
        w = self._make_worker()
        job = _make_job(status=JobStatus.QUEUED, retry_count=0, max_retries=3)
        w.queue.dequeue.return_value = str(job.id)

        mock_db = MagicMock()
        mock_db.__enter__ = MagicMock(return_value=mock_db)
        mock_db.__exit__ = MagicMock(return_value=False)
        mock_db.scalar.return_value = job

        mock_executor = MagicMock()
        mock_executor.execute.side_effect = RuntimeError("executor error")

        with patch("app.worker.worker.SessionLocal", return_value=mock_db), \
             patch("app.worker.worker.registry") as mock_registry, \
             patch("app.worker.worker.add_job_log"), \
             patch("app.worker.worker.calculate_delay", return_value=1.0):
            mock_registry.get.return_value = mock_executor
            w.process_once()

        assert job.retry_count == 1

    def test_worker_id_assigned_during_execution(self):
        """Worker must stamp its worker_id on the job before executing."""
        w = self._make_worker()
        job = _make_job(status=JobStatus.QUEUED)
        w.queue.dequeue.return_value = str(job.id)

        mock_db = MagicMock()
        mock_db.__enter__ = MagicMock(return_value=mock_db)
        mock_db.__exit__ = MagicMock(return_value=False)
        mock_db.scalar.return_value = job

        mock_executor = MagicMock()
        mock_executor.execute.return_value = {}

        with patch("app.worker.worker.SessionLocal", return_value=mock_db), \
             patch("app.worker.worker.registry") as mock_registry, \
             patch("app.worker.worker.add_job_log"):
            mock_registry.get.return_value = mock_executor
            w.process_once()

        assert job.worker_id == "test-worker-1"