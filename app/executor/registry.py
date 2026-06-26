from app.executor.base import BaseExecutor
from app.executor.email_send import EmailSendExecutor
from app.executor.pdf_summary import PdfSummaryExecutor
from app.executor.resume_analysis import ResumeAnalysisExecutor


class ExecutorRegistry:
    def __init__(self) -> None:
        self._executors: dict[str, type[BaseExecutor]] = {}

    def register(self, job_type: str, executor: type[BaseExecutor]) -> None:
        self._executors[job_type] = executor

    def get(self, job_type: str) -> BaseExecutor:
        executor_class = self._executors.get(job_type)
        if executor_class is None:
            raise ValueError(f"Unsupported job type: {job_type}")
        return executor_class()


registry = ExecutorRegistry()
registry.register("resume_analysis", ResumeAnalysisExecutor)
registry.register("pdf_summary", PdfSummaryExecutor)
registry.register("email_send", EmailSendExecutor)
