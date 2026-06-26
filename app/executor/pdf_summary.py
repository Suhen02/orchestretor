from pathlib import Path

import fitz
import httpx

from app.core.config import get_settings
from app.executor.base import BaseExecutor
from app.models.job import Job


class PdfSummaryExecutor(BaseExecutor):
    def execute(self, job: Job) -> dict:
        file_path = job.payload.get("file_path")
        if not file_path:
            raise ValueError("pdf_summary requires payload.file_path")
        max_length = int(job.payload.get("max_length", 220))
        text, pages = self._extract_text(file_path)
        summary = self._summarize(text, max_length)
        return {"summary": summary, "word_count": len(text.split()), "pages": pages}

    def _extract_text(self, file_path: str) -> tuple[str, int]:
        path = Path(file_path)
        if not path.exists():
            raise ValueError(f"PDF file not found: {file_path}")
        with fitz.open(path) as document:
            parts = [page.get_text() for page in document]
            return "\n".join(parts), document.page_count

    def _summarize(self, text: str, max_length: int) -> str:
        settings = get_settings()
        if settings.llm_provider == "openai" and settings.openai_api_key:
            return self._summarize_openai(text, max_length, settings.openai_api_key)
        if settings.llm_provider == "groq" and settings.groq_api_key:
            return self._summarize_groq(text, max_length, settings.groq_api_key)
        words = text.split()
        if not words:
            return ""
        return " ".join(words[:max_length])

    def _summarize_openai(self, text: str, max_length: int, api_key: str) -> str:
        response = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": "Summarize the PDF text concisely."},
                    {"role": "user", "content": text[:12000]},
                ],
                "max_tokens": max_length,
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

    def _summarize_groq(self, text: str, max_length: int, api_key: str) -> str:
        response = httpx.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "llama-3.1-8b-instant",
                "messages": [
                    {"role": "system", "content": "Summarize the PDF text concisely."},
                    {"role": "user", "content": text[:12000]},
                ],
                "max_tokens": max_length,
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
