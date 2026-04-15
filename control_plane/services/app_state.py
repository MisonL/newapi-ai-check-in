from __future__ import annotations

from datetime import datetime, timezone

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
from control_plane.task_center_models import (
    AccountRecord,
    CheckinResultRecord,
    DailyTaskRecord,
    IncidentRecord,
    SiteRecord,
)

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
        self._repair_task_center_data()

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

    def _repair_task_center_data(self) -> None:
        site_redirects = self._repair_sites()
        account_redirects = self._repair_accounts(site_redirects)
        task_redirects = self._repair_tasks(site_redirects, account_redirects)
        self._repair_checkin_results(site_redirects, account_redirects, task_redirects)
        self._repair_incidents(site_redirects, account_redirects, task_redirects)

    def _repair_sites(self) -> dict[str, str]:
        redirects: dict[str, str] = {}
        canonical_by_url: dict[str, SiteRecord] = {}
        ordered_sites = sorted(
            self.storage.list_sites(),
            key=lambda item: (item.updated_at, item.created_at, item.id),
            reverse=True,
        )
        for site in ordered_sites:
            normalized = SiteRecord.model_validate(site.model_dump())
            canonical = canonical_by_url.get(normalized.base_url)
            if canonical is None:
                canonical_by_url[normalized.base_url] = normalized
                if normalized != site:
                    self.storage.save_site(normalized)
                continue
            merged = canonical.model_copy(
                update={
                    "notes": canonical.notes or normalized.notes,
                    "checkin_enabled_detected": canonical.checkin_enabled_detected
                    if canonical.checkin_enabled_detected is not None else normalized.checkin_enabled_detected,
                    "checkin_min_quota_detected": canonical.checkin_min_quota_detected
                    if canonical.checkin_min_quota_detected is not None else normalized.checkin_min_quota_detected,
                    "checkin_max_quota_detected": canonical.checkin_max_quota_detected
                    if canonical.checkin_max_quota_detected is not None else normalized.checkin_max_quota_detected,
                    "created_at": min(canonical.created_at, normalized.created_at),
                    "updated_at": max(canonical.updated_at, normalized.updated_at),
                }
            )
            if merged != canonical:
                self.storage.save_site(merged)
                canonical_by_url[normalized.base_url] = merged
            redirects[normalized.id] = canonical.id
            self.storage.delete_site(normalized.id)
        return redirects

    def _repair_accounts(self, site_redirects: dict[str, str]) -> dict[str, str]:
        redirects: dict[str, str] = {}
        canonical_by_identity: dict[tuple[str, str, str], AccountRecord] = {}
        ordered_accounts = sorted(
            self.storage.list_accounts(),
            key=lambda item: (item.updated_at, item.created_at, item.id),
            reverse=True,
        )
        for account in ordered_accounts:
            normalized = account.model_copy(update={"site_id": site_redirects.get(account.site_id, account.site_id)})
            identity = self.task_center_service._account_identity(normalized)
            canonical = canonical_by_identity.get(identity)
            if canonical is None:
                canonical_by_identity[identity] = normalized
                if normalized != account:
                    self.storage.save_account(normalized)
                continue
            latest_source = normalized if self._account_event_at(normalized) > self._account_event_at(canonical) else canonical
            merged = canonical.model_copy(
                update={
                    "display_name": canonical.display_name or normalized.display_name,
                    "password": canonical.password or normalized.password,
                    "api_user": canonical.api_user or normalized.api_user,
                    "session_cookies": canonical.session_cookies or normalized.session_cookies,
                    "session_status": canonical.session_status if canonical.session_status != "unknown" else normalized.session_status,
                    "last_checkin_status": latest_source.last_checkin_status,
                    "last_checkin_date": latest_source.last_checkin_date,
                    "last_checkin_at": latest_source.last_checkin_at,
                    "last_quota_awarded": latest_source.last_quota_awarded,
                    "total_checkins": max(canonical.total_checkins, normalized.total_checkins),
                    "total_quota_awarded": max(canonical.total_quota_awarded, normalized.total_quota_awarded),
                    "last_error_message": latest_source.last_error_message or canonical.last_error_message or normalized.last_error_message,
                    "created_at": min(canonical.created_at, normalized.created_at),
                    "updated_at": max(canonical.updated_at, normalized.updated_at),
                }
            )
            if merged != canonical:
                self.storage.save_account(merged)
                canonical_by_identity[identity] = merged
            redirects[normalized.id] = canonical.id
            self.storage.delete_account(normalized.id)
        return redirects

    def _repair_tasks(self, site_redirects: dict[str, str], account_redirects: dict[str, str]) -> dict[str, str]:
        redirects: dict[str, str] = {}
        canonical_by_key: dict[tuple[str, object], DailyTaskRecord] = {}
        ordered_tasks = sorted(
            self.storage.list_daily_tasks(),
            key=self._task_sort_key,
            reverse=True,
        )
        for task in ordered_tasks:
            normalized = task.model_copy(
                update={
                    "site_id": site_redirects.get(task.site_id, task.site_id),
                    "account_id": account_redirects.get(task.account_id, task.account_id),
                }
            )
            task_key = (normalized.account_id, normalized.task_date)
            canonical = canonical_by_key.get(task_key)
            if canonical is None:
                canonical_by_key[task_key] = normalized
                if normalized != task:
                    self.storage.save_daily_task(normalized)
                continue
            merged = canonical.model_copy(
                update={
                    "attempt_count": max(canonical.attempt_count, normalized.attempt_count),
                    "created_at": min(canonical.created_at, normalized.created_at),
                    "updated_at": max(canonical.updated_at, normalized.updated_at),
                }
            )
            if merged != canonical:
                self.storage.save_daily_task(merged)
                canonical_by_key[task_key] = merged
            redirects[normalized.id] = canonical.id
            self.storage.delete_daily_task(normalized.id)
        return redirects

    def _repair_checkin_results(
        self,
        site_redirects: dict[str, str],
        account_redirects: dict[str, str],
        task_redirects: dict[str, str],
    ) -> None:
        canonical_by_task: dict[str, CheckinResultRecord] = {}
        ordered_results = sorted(
            self.storage.list_checkin_results(),
            key=lambda item: (item.quota_awarded, item.created_at, item.id),
            reverse=True,
        )
        for result in ordered_results:
            normalized = result.model_copy(
                update={
                    "site_id": site_redirects.get(result.site_id, result.site_id),
                    "account_id": account_redirects.get(result.account_id, result.account_id),
                    "task_id": task_redirects.get(result.task_id, result.task_id),
                }
            )
            canonical = canonical_by_task.get(normalized.task_id)
            if canonical is None:
                canonical_by_task[normalized.task_id] = normalized
                if normalized != result:
                    self.storage.save_checkin_result(normalized)
                continue
            merged = canonical.model_copy(
                update={
                    "checked_in_today_before_run": canonical.checked_in_today_before_run or normalized.checked_in_today_before_run,
                    "quota_awarded": max(canonical.quota_awarded, normalized.quota_awarded),
                    "checkin_date": canonical.checkin_date or normalized.checkin_date,
                    "total_checkins": max(canonical.total_checkins, normalized.total_checkins),
                    "total_quota_awarded": max(canonical.total_quota_awarded, normalized.total_quota_awarded),
                    "raw_status_payload": canonical.raw_status_payload or normalized.raw_status_payload,
                    "raw_checkin_payload": canonical.raw_checkin_payload or normalized.raw_checkin_payload,
                    "created_at": min(canonical.created_at, normalized.created_at),
                }
            )
            if merged != canonical:
                self.storage.save_checkin_result(merged)
                canonical_by_task[normalized.task_id] = merged
            self.storage.delete_checkin_result(normalized.id)

    def _repair_incidents(
        self,
        site_redirects: dict[str, str],
        account_redirects: dict[str, str],
        task_redirects: dict[str, str],
    ) -> None:
        severity_rank = {"high": 3, "medium": 2, "low": 1}
        canonical_by_key: dict[tuple[str, str, str, str, str], IncidentRecord] = {}
        ordered_incidents = sorted(
            self.storage.list_incidents(),
            key=lambda item: (item.last_seen_at, severity_rank.get(item.severity, 0), item.id),
            reverse=True,
        )
        for incident in ordered_incidents:
            normalized = incident.model_copy(
                update={
                    "site_id": site_redirects.get(incident.site_id, incident.site_id),
                    "account_id": account_redirects.get(incident.account_id, incident.account_id),
                    "task_id": task_redirects.get(incident.task_id, incident.task_id) if incident.task_id else incident.task_id,
                }
            )
            dedupe_key = (
                normalized.account_id,
                normalized.site_id,
                normalized.task_id or "",
                normalized.type,
                normalized.last_error_message,
            )
            canonical = canonical_by_key.get(dedupe_key)
            if canonical is None:
                canonical_by_key[dedupe_key] = normalized
                if normalized != incident:
                    self.storage.save_incident(normalized)
                continue
            merged = canonical.model_copy(
                update={
                    "severity": canonical.severity
                    if severity_rank.get(canonical.severity, 0) >= severity_rank.get(normalized.severity, 0)
                    else normalized.severity,
                    "resolved": canonical.resolved and normalized.resolved,
                    "resolution_action": canonical.resolution_action or normalized.resolution_action,
                    "first_seen_at": min(canonical.first_seen_at, normalized.first_seen_at),
                    "last_seen_at": max(canonical.last_seen_at, normalized.last_seen_at),
                    "detail": canonical.detail or normalized.detail,
                    "last_checkin_at": self._max_datetime(canonical.last_checkin_at, normalized.last_checkin_at),
                }
            )
            if merged != canonical:
                self.storage.save_incident(merged)
                canonical_by_key[dedupe_key] = merged
            self.storage.delete_incident(normalized.id)

    def _account_event_at(self, account: AccountRecord) -> datetime:
        return account.last_checkin_at or account.updated_at

    def _task_sort_key(self, task: DailyTaskRecord) -> tuple[int, datetime, int, datetime]:
        status_rank = {
            "success": 7,
            "skipped": 6,
            "blocked": 5,
            "failed": 4,
            "checking_in": 3,
            "checking": 2,
            "logging_in": 1,
            "probing": 1,
            "pending": 0,
        }
        event_at = self._max_datetime(task.finished_at, task.started_at, task.updated_at, task.created_at)
        return (status_rank.get(task.status, 0), event_at, task.attempt_count, task.updated_at)

    def _max_datetime(self, *values: datetime | None) -> datetime:
        normalized = [value for value in values if value is not None]
        if normalized:
            return max(normalized)
        return datetime.min.replace(tzinfo=timezone.utc)

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
