from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from control_plane.models import JobType, TriggerType
from control_plane.services.job_service import JobService
from control_plane.storage.base import StorageBackend


class SchedulerService:
    def __init__(self, storage: StorageBackend, job_service: JobService) -> None:
        self._storage = storage
        self._job_service = job_service
        self._scheduler = AsyncIOScheduler(timezone="UTC")

    def start(self) -> None:
        if not self._scheduler.running:
            self._sync_jobs()
            self._scheduler.start()

    def shutdown(self) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)

    def sync(self) -> None:
        self._sync_jobs()

    def _sync_jobs(self) -> None:
        existing = {job.id for job in self._scheduler.get_jobs()}
        wanted = set()
        for schedule in self._storage.list_schedules():
            job_id = schedule.job_type.value
            wanted.add(job_id)
            if not schedule.enabled:
                if job_id in existing:
                    self._scheduler.remove_job(job_id)
                continue
            trigger = CronTrigger.from_crontab(schedule.cron, timezone=schedule.timezone)
            self._scheduler.add_job(
                self._scheduled_fire,
                trigger=trigger,
                id=job_id,
                replace_existing=True,
                args=[schedule.job_type],
            )
        for job_id in existing - wanted:
            self._scheduler.remove_job(job_id)

    def _scheduled_fire(self, job_type: JobType) -> None:
        self._job_service.start_job(job_type, TriggerType.SCHEDULED)
