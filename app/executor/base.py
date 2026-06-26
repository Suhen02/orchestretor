from abc import ABC, abstractmethod

from app.models.job import Job


class BaseExecutor(ABC):
    @abstractmethod
    def execute(self, job: Job) -> dict:
        raise NotImplementedError
