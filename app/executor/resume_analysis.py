import re
from pathlib import Path

from app.executor.base import BaseExecutor
from app.models.job import Job


SKILL_KEYWORDS = {
    "python",
    "fastapi",
    "django",
    "flask",
    "sql",
    "postgresql",
    "redis",
    "docker",
    "kubernetes",
    "aws",
    "azure",
    "gcp",
    "machine learning",
    "nlp",
    "pytorch",
    "tensorflow",
    "react",
    "javascript",
    "typescript",
    "java",
    "spring",
    "celery",
}

EDUCATION_PATTERNS = [
    r"\bB\.?Tech\b",
    r"\bM\.?Tech\b",
    r"\bBachelor(?:'s)?\b",
    r"\bMaster(?:'s)?\b",
    r"\bB\.?E\.?\b",
    r"\bM\.?S\.?\b",
    r"\bPhD\b",
]

TITLE_PATTERNS = [
    r"software engineer",
    r"backend engineer",
    r"data scientist",
    r"machine learning engineer",
    r"devops engineer",
    r"full stack developer",
]


class ResumeAnalysisExecutor(BaseExecutor):
    def execute(self, job: Job) -> dict:
        text = self._load_text(job.payload)
        lowered = text.lower()
        skills = sorted(skill for skill in SKILL_KEYWORDS if skill in lowered)
        education = sorted(
            {match.group(0) for pattern in EDUCATION_PATTERNS for match in re.finditer(pattern, text, re.I)}
        )
        titles = sorted(
            {match.group(0).title() for pattern in TITLE_PATTERNS for match in re.finditer(pattern, text, re.I)}
        )
        experience_years = self._experience_years(text)
        score = min(100.0, round(len(skills) * 5 + experience_years * 4 + len(education) * 3, 2))
        return {
            "skills": skills,
            "experience_years": experience_years,
            "education": education,
            "job_titles": titles,
            "score": score,
        }

    def _load_text(self, payload: dict) -> str:
        if payload.get("text"):
            return str(payload["text"])
        file_path = payload.get("file_path")
        if not file_path:
            raise ValueError("resume_analysis requires payload.text or payload.file_path")
        path = Path(file_path)
        if not path.exists():
            raise ValueError(f"Resume file not found: {file_path}")
        return path.read_text(encoding="utf-8", errors="ignore")

    def _experience_years(self, text: str) -> int:
        matches = re.findall(r"(\d{1,2})\+?\s*(?:years|yrs)", text, flags=re.I)
        return max((int(match) for match in matches), default=0)
