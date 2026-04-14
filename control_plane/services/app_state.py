from __future__ import annotations

from control_plane.models import (
    AppStatus,
    Checkin996Config,
    CheckinQaqAlConfig,
    ConfigDomain,
    DashboardMetrics,
    DashboardPayload,
    JobRun,
    JobStatus,
    JobType,
    LinuxDoReadConfig,
    MainCheckinConfig,
    NotificationConfig,
    SystemConfig,
)
from control_plane.services.job_service import JobService
from control_plane.services.scheduler_service import SchedulerService
from control_plane.services.task_center_service import TaskCenterService
from control_plane.settings import settings
from control_plane.storage.base import StorageBackend
from control_plane.storage.factory import create_storage

SYSTEM_DEFAULTS_VERSION = 2


class AppState:
    def __init__(self, storage: StorageBackend) -> None:
        self.storage = storage
        self.job_service = JobService(storage)
        self.scheduler_service = SchedulerService(storage, self.job_service, enabled=settings.scheduler_enabled)
        self.task_center_service = TaskCenterService(storage)
        self._ensure_defaults()

    def _ensure_defaults(self) -> None:
        defaults = {
            ConfigDomain.SYSTEM: SystemConfig.model_validate(settings.default_system_config()).model_dump(),
            ConfigDomain.MAIN_CHECKIN: MainCheckinConfig().model_dump(),
            ConfigDomain.CHECKIN_996: Checkin996Config().model_dump(),
            ConfigDomain.CHECKIN_QAQ_AL: CheckinQaqAlConfig().model_dump(),
            ConfigDomain.LINUXDO_READ: LinuxDoReadConfig().model_dump(),
            ConfigDomain.NOTIFICATIONS: NotificationConfig().model_dump(),
        }
        config_models = {
            ConfigDomain.SYSTEM: SystemConfig,
            ConfigDomain.MAIN_CHECKIN: MainCheckinConfig,
            ConfigDomain.CHECKIN_996: Checkin996Config,
            ConfigDomain.CHECKIN_QAQ_AL: CheckinQaqAlConfig,
            ConfigDomain.LINUXDO_READ: LinuxDoReadConfig,
            ConfigDomain.NOTIFICATIONS: NotificationConfig,
        }
        for domain, default_payload in defaults.items():
            current_payload = self.storage.load_config(domain)
            if not current_payload:
                self.storage.save_config(domain, default_payload)
                continue
            if domain == ConfigDomain.SYSTEM:
                merged_payload = self._merge_system_payload(default_payload, current_payload)
            else:
                merged_payload = config_models[domain].model_validate({**default_payload, **current_payload}).model_dump()
            if merged_payload != current_payload:
                self.storage.save_config(domain, merged_payload)
        existing_schedule_ids = {item.job_type.value for item in self.storage.list_schedules()}
        for job_type in JobType:
            schedule = self.storage.load_schedule(job_type)
            if schedule.job_type == job_type and schedule.job_type.value not in existing_schedule_ids:
                self.storage.save_schedule(schedule)
                existing_schedule_ids.add(schedule.job_type.value)

    def _merge_system_payload(self, default_payload: dict, current_payload: dict) -> dict:
        merged_payload = SystemConfig.model_validate({**default_payload, **current_payload}).model_dump()
        current_version = int(current_payload.get("defaults_version", 1))

        if current_version < SYSTEM_DEFAULTS_VERSION:
            if merged_payload["browser_strategy"] == "legacy":
                merged_payload["browser_strategy"] = default_payload["browser_strategy"]
            if merged_payload["main_checkin_engine"] == "legacy":
                merged_payload["main_checkin_engine"] = default_payload["main_checkin_engine"]

        merged_payload["defaults_version"] = SYSTEM_DEFAULTS_VERSION
        return merged_payload

    def status(self) -> AppStatus:
        system_config = SystemConfig.model_validate(self.storage.load_config(ConfigDomain.SYSTEM))
        return AppStatus(
            storage_mode=settings.storage_mode,
            timezone=settings.timezone,
            deploy_mode=settings.deploy_mode,
            running_jobs=self.job_service.running_jobs(),
            scheduler_enabled=settings.scheduler_enabled,
            admin_password_configured=bool(system_config.admin_password_hash),
            bootstrap_password_enabled=not bool(system_config.admin_password_hash) and bool(settings.bootstrap_admin_password),
        )

    def dashboard(self) -> DashboardPayload:
        job_runs = self.storage.list_job_runs()
        schedules = self.storage.list_schedules()
        next_runs = self.scheduler_service.next_run_times()
        next_run_values = [value for value in next_runs.values() if value is not None]
        metrics = DashboardMetrics(
            enabled_schedule_count=sum(1 for schedule in schedules if schedule.enabled),
            next_run_at=min(next_run_values) if next_run_values else None,
            last_run_at=job_runs[0].started_at if job_runs else None,
            last_success_at=next((run.finished_at for run in job_runs if run.status == JobStatus.SUCCESS), None),
            last_failure_at=next((run.finished_at for run in job_runs if run.status == JobStatus.FAILED), None),
            consecutive_failures=self._consecutive_failures(job_runs),
        )
        return DashboardPayload(
            status=self.status(),
            recent_runs=job_runs[:8],
            total_runs=len(job_runs),
            schedules=schedules,
            metrics=metrics,
            next_runs=next_runs,
        )

    def _consecutive_failures(self, runs: list[JobRun]) -> int:
        failures = 0
        for run in runs:
            if run.status == JobStatus.FAILED:
                failures += 1
                continue
            if run.status == JobStatus.SUCCESS:
                break
        return failures


def build_app_state() -> AppState:
    return AppState(create_storage())
