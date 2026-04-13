from __future__ import annotations

from datetime import date, datetime, timezone

from control_plane.services.newapi_checkin_service import NewApiCheckinService, NewApiTaskExecutionResult
from control_plane.storage.base import StorageBackend
from control_plane.task_center_models import CheckinResultRecord, DailyTaskRecord, IncidentRecord


class TaskCenterTaskExecutor:
    def __init__(self, storage: StorageBackend, checkin_service: NewApiCheckinService) -> None:
        self._storage = storage
        self._checkin_service = checkin_service

    async def execute_task(self, task_id: str) -> DailyTaskRecord:
        task = self._storage.get_daily_task(task_id)
        if task is None:
            raise KeyError(task_id)
        site = self._storage.get_site(task.site_id)
        account = self._storage.get_account(task.account_id)
        if site is None or account is None:
            raise KeyError(task_id)
        started_at = datetime.now(timezone.utc)
        running_task = task.model_copy(
            update={
                'status': 'logging_in',
                'started_at': started_at,
                'updated_at': started_at,
                'error_code': '',
                'error_message': '',
            }
        )
        self._storage.save_daily_task(running_task)
        result = await self._checkin_service.run_account(site, account)
        finished_at = datetime.now(timezone.utc)
        finished_task = running_task.model_copy(
            update={
                'status': result.task_status,
                'executor_type': result.executor_type,
                'finished_at': finished_at,
                'updated_at': finished_at,
                'error_code': result.error_code,
                'error_message': result.error_message,
            }
        )
        self._storage.save_daily_task(finished_task)
        self._storage.save_account(self._updated_account(account, task.task_date, finished_at, result))
        self._storage.save_checkin_result(self._checkin_result(finished_task, result))
        if result.task_status in {'failed', 'blocked'}:
            self._storage.save_incident(self._incident(site.name, account, finished_task, finished_at, result))
        return finished_task

    def _updated_account(
        self,
        account,
        task_date: date,
        finished_at: datetime,
        result: NewApiTaskExecutionResult,
    ):
        return account.model_copy(
            update={
                'last_checkin_status': result.account_status,
                'last_checkin_date': task_date,
                'last_checkin_at': finished_at,
                'last_quota_awarded': result.quota_awarded,
                'total_checkins': result.total_checkins,
                'total_quota_awarded': result.total_quota_awarded,
                'last_error_message': result.error_message,
                'updated_at': finished_at,
            }
        )

    def _checkin_result(self, task: DailyTaskRecord, result: NewApiTaskExecutionResult) -> CheckinResultRecord:
        checkin_date = None
        if result.checkin_date:
            checkin_date = date.fromisoformat(result.checkin_date)
        return CheckinResultRecord(
            task_id=task.id,
            site_id=task.site_id,
            account_id=task.account_id,
            checked_in_today_before_run=result.checked_in_today_before_run,
            quota_awarded=result.quota_awarded,
            checkin_date=checkin_date,
            total_checkins=result.total_checkins,
            total_quota_awarded=result.total_quota_awarded,
            raw_status_payload=result.raw_status_payload,
            raw_checkin_payload=result.raw_checkin_payload,
        )

    def _incident(
        self,
        site_name: str,
        account,
        task: DailyTaskRecord,
        finished_at: datetime,
        result: NewApiTaskExecutionResult,
    ) -> IncidentRecord:
        display_name = account.display_name or account.username
        return IncidentRecord(
            account_id=account.id,
            site_id=task.site_id,
            task_id=task.id,
            display_name=display_name,
            site_name=site_name,
            status=result.account_status,
            last_error_message=result.error_message or result.error_code,
            type=result.error_code,
            severity='high' if result.task_status == 'failed' else 'medium',
            dedupe_key=f'{account.id}:{task.task_date}:{result.error_code or result.task_status}',
            first_seen_at=finished_at,
            last_seen_at=finished_at,
            detail=result.error_message,
            last_checkin_at=finished_at,
        )
