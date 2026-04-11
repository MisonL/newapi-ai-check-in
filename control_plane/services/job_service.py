from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from uuid import uuid4

from control_plane.executors.checkin_996 import execute_checkin_996
from control_plane.executors.checkin_qaq_al import execute_checkin_qaq_al
from control_plane.executors.linuxdo_read import execute_linuxdo_read
from control_plane.executors.main_checkin import execute_main_checkin
from control_plane.models import (
    Checkin996Config,
    CheckinQaqAlConfig,
    ConfigDomain,
    JobLogLine,
    JobRun,
    JobStatus,
    JobType,
    LinuxDoReadConfig,
    MainCheckinConfig,
    NotificationConfig,
    ScheduleSpec,
    SystemConfig,
    TriggerType,
)
from control_plane.settings import settings
from control_plane.storage.base import StorageBackend


class JobService:
    def __init__(self, storage: StorageBackend) -> None:
        self._storage = storage
        self._locks: dict[str, asyncio.Lock] = {job_type.value: asyncio.Lock() for job_type in JobType}
        self._loop: asyncio.AbstractEventLoop | None = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def running_jobs(self) -> dict[str, bool]:
        return {job_type: lock.locked() for job_type, lock in self._locks.items()}

    def _last_run(self, job_type: JobType) -> JobRun | None:
        runs = self._storage.list_job_runs(job_type)
        return runs[0] if runs else None

    def _within_cooldown(self, schedule: ScheduleSpec, last_run: JobRun | None) -> bool:
        if schedule.cooldown_seconds <= 0 or last_run is None or last_run.finished_at is None:
            return False
        seconds = (datetime.now(timezone.utc) - last_run.finished_at).total_seconds()
        return seconds < schedule.cooldown_seconds

    def start_job(self, job_type: JobType, trigger: TriggerType) -> JobRun:
        schedule = self._storage.load_schedule(job_type)
        if trigger == TriggerType.SCHEDULED and (not schedule.enabled or self._within_cooldown(schedule, self._last_run(job_type))):
            run = self._build_run(job_type, trigger, JobStatus.SKIPPED)
            self._storage.create_job_run(run)
            return run
        lock = self._locks[job_type.value]
        if lock.locked():
            run = self._build_run(job_type, trigger, JobStatus.SKIPPED)
            run.error_code = "already_running"
            run.error_message = "A job of the same type is already running"
            self._storage.create_job_run(run)
            return run
        run = self._build_run(job_type, trigger, JobStatus.QUEUED)
        self._storage.create_job_run(run)
        self._dispatch_run(run)
        return run

    def _dispatch_run(self, run: JobRun) -> None:
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            current_loop = None

        target_loop = current_loop or self._loop
        if target_loop is None:
            raise RuntimeError("JobService event loop is not initialized")

        if current_loop is target_loop:
            asyncio.create_task(self._run_job(run))
            return

        asyncio.run_coroutine_threadsafe(self._run_job(run), target_loop)

    def _build_run(self, job_type: JobType, trigger: TriggerType, status: JobStatus) -> JobRun:
        return JobRun(id=uuid4().hex, job_type=job_type, trigger=trigger, status=status)

    def _summary_has_failures(self, job_type: JobType, summary) -> bool:
        failure_sensitive_jobs = {
            JobType.MAIN_CHECKIN,
            JobType.CHECKIN_996,
            JobType.CHECKIN_QAQ_AL,
            JobType.LINUXDO_READ,
        }
        if job_type not in failure_sensitive_jobs:
            return False
        return summary.total_count > 0 and summary.success_count < summary.total_count

    async def _run_job(self, run: JobRun) -> None:
        lock = self._locks[run.job_type.value]
        async with lock:
            current = self._storage.get_job_run(run.id) or run
            current.status = JobStatus.RUNNING
            current.started_at = datetime.now(timezone.utc)
            self._storage.update_job_run(current)
            try:
                notifications = NotificationConfig.model_validate(self._storage.load_config(ConfigDomain.NOTIFICATIONS))
                system_config = SystemConfig.model_validate(self._storage.load_config(ConfigDomain.SYSTEM))
                emit_log = lambda message, stream="system": self._append_log(current.id, message, stream)
                if current.job_type == JobType.MAIN_CHECKIN:
                    summary = await execute_main_checkin(
                        MainCheckinConfig.model_validate(self._storage.load_config(ConfigDomain.MAIN_CHECKIN)),
                        notifications,
                        system_config,
                        str(settings.storage_states_dir),
                        emit_log,
                    )
                elif current.job_type == JobType.CHECKIN_996:
                    summary = await execute_checkin_996(
                        Checkin996Config.model_validate(self._storage.load_config(ConfigDomain.CHECKIN_996)),
                        notifications,
                        emit_log,
                    )
                elif current.job_type == JobType.CHECKIN_QAQ_AL:
                    summary = await execute_checkin_qaq_al(
                        CheckinQaqAlConfig.model_validate(self._storage.load_config(ConfigDomain.CHECKIN_QAQ_AL)),
                        notifications,
                        system_config,
                        emit_log,
                    )
                elif current.job_type == JobType.LINUXDO_READ:
                    summary = await execute_linuxdo_read(
                        LinuxDoReadConfig.model_validate(self._storage.load_config(ConfigDomain.LINUXDO_READ)),
                        notifications,
                        system_config,
                        str(settings.storage_states_dir),
                        emit_log,
                    )
                else:
                    raise NotImplementedError(f"{current.job_type.value} is not wired yet")
                current.summary = summary
                if self._summary_has_failures(current.job_type, summary):
                    current.status = JobStatus.FAILED
                    current.exit_code = 1
                    current.error_code = "partial_failure"
                    current.error_message = (
                        f"{current.job_type.value} completed with failures: "
                        f"{summary.success_count}/{summary.total_count} succeeded"
                    )
                    self._append_log(current.id, current.error_message, "stderr")
                else:
                    current.status = JobStatus.SUCCESS
                    current.exit_code = 0
            except Exception as exc:
                current.status = JobStatus.FAILED
                current.exit_code = 1
                current.error_code = "execution_error"
                current.error_message = str(exc)
                self._append_log(current.id, f"Execution failed: {exc}", "stderr")
            current.finished_at = datetime.now(timezone.utc)
            self._storage.update_job_run(current)

    def _append_log(self, run_id: str, message: str, stream: str) -> None:
        self._storage.append_job_log(JobLogLine(run_id=run_id, message=message, stream=stream))
