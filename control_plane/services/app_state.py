from __future__ import annotations

from control_plane.models import (
    AppStatus,
    Checkin996Config,
    CheckinQaqAlConfig,
    ConfigDomain,
    JobType,
    LinuxDoReadConfig,
    MainCheckinConfig,
    NotificationConfig,
    SystemConfig,
)
from control_plane.services.job_service import JobService
from control_plane.services.scheduler_service import SchedulerService
from control_plane.settings import settings
from control_plane.storage.base import StorageBackend
from control_plane.storage.factory import create_storage


class AppState:
    def __init__(self, storage: StorageBackend) -> None:
        self.storage = storage
        self.job_service = JobService(storage)
        self.scheduler_service = SchedulerService(storage, self.job_service)
        self._ensure_defaults()

    def _ensure_defaults(self) -> None:
        defaults = {
            ConfigDomain.SYSTEM: SystemConfig().model_dump(),
            ConfigDomain.MAIN_CHECKIN: MainCheckinConfig().model_dump(),
            ConfigDomain.CHECKIN_996: Checkin996Config().model_dump(),
            ConfigDomain.CHECKIN_QAQ_AL: CheckinQaqAlConfig().model_dump(),
            ConfigDomain.LINUXDO_READ: LinuxDoReadConfig().model_dump(),
            ConfigDomain.NOTIFICATIONS: NotificationConfig().model_dump(),
        }
        for domain, payload in defaults.items():
            if not self.storage.load_config(domain):
                self.storage.save_config(domain, payload)
        existing_schedule_ids = {item.job_type.value for item in self.storage.list_schedules()}
        for job_type in JobType:
            schedule = self.storage.load_schedule(job_type)
            if schedule.job_type == job_type and schedule.job_type.value not in existing_schedule_ids:
                self.storage.save_schedule(schedule)
                existing_schedule_ids.add(schedule.job_type.value)

    def status(self) -> AppStatus:
        system_config = SystemConfig.model_validate(self.storage.load_config(ConfigDomain.SYSTEM))
        return AppStatus(
            storage_mode=settings.storage_mode,
            timezone=settings.timezone,
            running_jobs=self.job_service.running_jobs(),
            admin_password_configured=bool(system_config.admin_password_hash),
            bootstrap_password_enabled=not bool(system_config.admin_password_hash) and bool(settings.bootstrap_admin_password),
        )


def build_app_state() -> AppState:
    return AppState(create_storage())
