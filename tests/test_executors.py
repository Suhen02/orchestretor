from types import SimpleNamespace

from app.executor.email_send import EmailSendExecutor
from app.executor.resume_analysis import ResumeAnalysisExecutor


def test_resume_analysis_extracts_expected_fields():
    job = SimpleNamespace(
        payload={
            "text": "Backend Engineer with 5 years of Python, FastAPI, Redis and Docker. B.Tech."
        }
    )
    result = ResumeAnalysisExecutor().execute(job)
    assert "python" in result["skills"]
    assert "fastapi" in result["skills"]
    assert result["experience_years"] == 5
    assert result["score"] > 0


def test_email_send_dry_run_returns_message_id():
    job = SimpleNamespace(payload={"to": "a@example.com", "subject": "Hi", "body": "Hello"})
    result = EmailSendExecutor().execute(job)
    assert result["dry_run"] is True
    assert result["message_id"]
