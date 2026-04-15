from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from datetime import date
from pathlib import Path

from control_plane.models import ArtifactRef, ConfigDomain, JobLogLine, JobRun, JobType, ScheduleSpec
from control_plane.storage.base import StorageBackend
from control_plane.task_center_models import (
    AccountRecord,
    CheckinResultRecord,
    DailyTaskRecord,
    IncidentRecord,
    SiteRecord,
)


class MemoryStorage(StorageBackend):
    def __init__(self, artifact_root: Path) -> None:
        self._configs: dict[str, dict] = {}
        self._schedules: dict[str, ScheduleSpec] = {}
        self._runs: dict[str, JobRun] = {}
        self._logs: dict[str, list[JobLogLine]] = defaultdict(list)
        self._sites: dict[str, SiteRecord] = {}
        self._accounts: dict[str, AccountRecord] = {}
        self._daily_tasks: dict[str, DailyTaskRecord] = {}
        self._checkin_results: dict[str, CheckinResultRecord] = {}
        self._incidents: dict[str, IncidentRecord] = {}
        self._artifact_root = artifact_root
        self._artifact_root.mkdir(parents=True, exist_ok=True)

    def load_config(self, domain: ConfigDomain) -> dict:
        return deepcopy(self._configs.get(domain.value, {}))

    def save_config(self, domain: ConfigDomain, payload: dict) -> None:
        self._configs[domain.value] = deepcopy(payload)

    def load_schedule(self, job_type: JobType) -> ScheduleSpec:
        return self._schedules.get(job_type.value, ScheduleSpec(job_type=job_type))

    def save_schedule(self, schedule: ScheduleSpec) -> None:
        self._schedules[schedule.job_type.value] = schedule

    def list_schedules(self) -> list[ScheduleSpec]:
        return list(self._schedules.values())

    def create_job_run(self, run: JobRun) -> None:
        self._runs[run.id] = run

    def update_job_run(self, run: JobRun) -> None:
        self._runs[run.id] = run

    def get_job_run(self, run_id: str) -> JobRun | None:
        return self._runs.get(run_id)

    def list_job_runs(self, job_type: JobType | None = None, limit: int | None = None) -> list[JobRun]:
        runs = list(self._runs.values())
        if job_type is not None:
            runs = [run for run in runs if run.job_type == job_type]
        ordered = sorted(runs, key=lambda item: item.started_at, reverse=True)
        return ordered[:limit] if limit is not None else ordered

    def append_job_log(self, log_line: JobLogLine) -> None:
        self._logs[log_line.run_id].append(log_line)

    def get_job_logs(self, run_id: str) -> list[JobLogLine]:
        return list(self._logs.get(run_id, []))

    def save_artifact(self, run_id: str, artifact: ArtifactRef, content: bytes) -> ArtifactRef:
        run_dir = self._artifact_root / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        target = run_dir / Path(artifact.path).name
        target.write_bytes(content)
        saved = artifact.model_copy(update={"path": str(target), "size": target.stat().st_size})
        run = self._runs.get(run_id)
        if run is not None:
            run.artifacts.append(saved)
        return saved

    def list_sites(self) -> list[SiteRecord]:
        return sorted((deepcopy(item) for item in self._sites.values()), key=lambda item: item.updated_at, reverse=True)

    def get_site(self, site_id: str) -> SiteRecord | None:
        site = self._sites.get(site_id)
        return deepcopy(site) if site is not None else None

    def save_site(self, site: SiteRecord) -> None:
        self._sites[site.id] = deepcopy(site)

    def delete_site(self, site_id: str) -> None:
        self._sites.pop(site_id, None)

    def list_accounts(self, site_id: str | None = None) -> list[AccountRecord]:
        items = [deepcopy(item) for item in self._accounts.values()]
        if site_id is not None:
            items = [item for item in items if item.site_id == site_id]
        return sorted(items, key=lambda item: item.updated_at, reverse=True)

    def get_account(self, account_id: str) -> AccountRecord | None:
        account = self._accounts.get(account_id)
        return deepcopy(account) if account is not None else None

    def save_account(self, account: AccountRecord) -> None:
        self._accounts[account.id] = deepcopy(account)

    def delete_account(self, account_id: str) -> None:
        self._accounts.pop(account_id, None)

    def list_daily_tasks(
        self,
        task_date: date | None = None,
        status: str | None = None,
        site_id: str | None = None,
        account_id: str | None = None,
    ) -> list[DailyTaskRecord]:
        items = [deepcopy(item) for item in self._daily_tasks.values()]
        if task_date is not None:
            items = [item for item in items if item.task_date == task_date]
        if status is not None:
            items = [item for item in items if item.status == status]
        if site_id is not None:
            items = [item for item in items if item.site_id == site_id]
        if account_id is not None:
            items = [item for item in items if item.account_id == account_id]
        return sorted(items, key=lambda item: (item.task_date, item.updated_at), reverse=True)

    def get_daily_task(self, task_id: str) -> DailyTaskRecord | None:
        task = self._daily_tasks.get(task_id)
        return deepcopy(task) if task is not None else None

    def save_daily_task(self, task: DailyTaskRecord) -> None:
        duplicate_ids = [
            item.id for item in self._daily_tasks.values()
            if item.account_id == task.account_id and item.task_date == task.task_date and item.id != task.id
        ]
        for duplicate_id in duplicate_ids:
            del self._daily_tasks[duplicate_id]
        self._daily_tasks[task.id] = deepcopy(task)

    def delete_daily_task(self, task_id: str) -> None:
        self._daily_tasks.pop(task_id, None)

    def list_checkin_results(
        self,
        task_id: str | None = None,
        site_id: str | None = None,
        account_id: str | None = None,
    ) -> list[CheckinResultRecord]:
        items = [deepcopy(item) for item in self._checkin_results.values()]
        if task_id is not None:
            items = [item for item in items if item.task_id == task_id]
        if site_id is not None:
            items = [item for item in items if item.site_id == site_id]
        if account_id is not None:
            items = [item for item in items if item.account_id == account_id]
        return sorted(items, key=lambda item: item.created_at, reverse=True)

    def get_checkin_result(self, task_id: str) -> CheckinResultRecord | None:
        for item in self._checkin_results.values():
            if item.task_id == task_id:
                return deepcopy(item)
        return None

    def save_checkin_result(self, result: CheckinResultRecord) -> None:
        duplicate_ids = [item.id for item in self._checkin_results.values() if item.task_id == result.task_id and item.id != result.id]
        for duplicate_id in duplicate_ids:
            del self._checkin_results[duplicate_id]
        self._checkin_results[result.id] = deepcopy(result)

    def delete_checkin_result(self, result_id: str) -> None:
        self._checkin_results.pop(result_id, None)

    def list_incidents(
        self,
        resolved: bool | None = None,
        site_id: str | None = None,
        account_id: str | None = None,
    ) -> list[IncidentRecord]:
        items = [deepcopy(item) for item in self._incidents.values()]
        if resolved is not None:
            items = [item for item in items if item.resolved == resolved]
        if site_id is not None:
            items = [item for item in items if item.site_id == site_id]
        if account_id is not None:
            items = [item for item in items if item.account_id == account_id]
        return sorted(items, key=lambda item: item.last_seen_at, reverse=True)

    def save_incident(self, incident: IncidentRecord) -> None:
        self._incidents[incident.id] = deepcopy(incident)

    def delete_incident(self, incident_id: str) -> None:
        self._incidents.pop(incident_id, None)
