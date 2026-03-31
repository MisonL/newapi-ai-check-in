from __future__ import annotations

from abc import ABC, abstractmethod

from control_plane.models import ArtifactRef, ConfigDomain, JobLogLine, JobRun, JobType, ScheduleSpec


class StorageBackend(ABC):
    @abstractmethod
    def load_config(self, domain: ConfigDomain) -> dict:
        raise NotImplementedError

    @abstractmethod
    def save_config(self, domain: ConfigDomain, payload: dict) -> None:
        raise NotImplementedError

    @abstractmethod
    def load_schedule(self, job_type: JobType) -> ScheduleSpec:
        raise NotImplementedError

    @abstractmethod
    def save_schedule(self, schedule: ScheduleSpec) -> None:
        raise NotImplementedError

    @abstractmethod
    def list_schedules(self) -> list[ScheduleSpec]:
        raise NotImplementedError

    @abstractmethod
    def create_job_run(self, run: JobRun) -> None:
        raise NotImplementedError

    @abstractmethod
    def update_job_run(self, run: JobRun) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_job_run(self, run_id: str) -> JobRun | None:
        raise NotImplementedError

    @abstractmethod
    def list_job_runs(self, job_type: JobType | None = None) -> list[JobRun]:
        raise NotImplementedError

    @abstractmethod
    def append_job_log(self, log_line: JobLogLine) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_job_logs(self, run_id: str) -> list[JobLogLine]:
        raise NotImplementedError

    @abstractmethod
    def save_artifact(self, run_id: str, artifact: ArtifactRef, content: bytes) -> ArtifactRef:
        raise NotImplementedError
