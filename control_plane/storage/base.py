from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from control_plane.models import ArtifactRef, ConfigDomain, JobLogLine, JobRun, JobType, ScheduleSpec
from control_plane.task_center_models import (
    AccountRecord,
    CheckinResultRecord,
    DailyTaskRecord,
    IncidentRecord,
    SiteRecord,
)


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
    def list_job_runs(self, job_type: JobType | None = None, limit: int | None = None) -> list[JobRun]:
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

    @abstractmethod
    def list_sites(self) -> list[SiteRecord]:
        raise NotImplementedError

    @abstractmethod
    def get_site(self, site_id: str) -> SiteRecord | None:
        raise NotImplementedError

    @abstractmethod
    def save_site(self, site: SiteRecord) -> None:
        raise NotImplementedError

    @abstractmethod
    def list_accounts(self, site_id: str | None = None) -> list[AccountRecord]:
        raise NotImplementedError

    @abstractmethod
    def get_account(self, account_id: str) -> AccountRecord | None:
        raise NotImplementedError

    @abstractmethod
    def save_account(self, account: AccountRecord) -> None:
        raise NotImplementedError

    @abstractmethod
    def list_daily_tasks(
        self,
        task_date: date | None = None,
        status: str | None = None,
        site_id: str | None = None,
        account_id: str | None = None,
    ) -> list[DailyTaskRecord]:
        raise NotImplementedError

    @abstractmethod
    def get_daily_task(self, task_id: str) -> DailyTaskRecord | None:
        raise NotImplementedError

    @abstractmethod
    def save_daily_task(self, task: DailyTaskRecord) -> None:
        raise NotImplementedError

    @abstractmethod
    def list_checkin_results(
        self,
        task_id: str | None = None,
        site_id: str | None = None,
        account_id: str | None = None,
    ) -> list[CheckinResultRecord]:
        raise NotImplementedError

    @abstractmethod
    def get_checkin_result(self, task_id: str) -> CheckinResultRecord | None:
        raise NotImplementedError

    @abstractmethod
    def save_checkin_result(self, result: CheckinResultRecord) -> None:
        raise NotImplementedError

    @abstractmethod
    def list_incidents(
        self,
        resolved: bool | None = None,
        site_id: str | None = None,
        account_id: str | None = None,
    ) -> list[IncidentRecord]:
        raise NotImplementedError

    @abstractmethod
    def save_incident(self, incident: IncidentRecord) -> None:
        raise NotImplementedError
