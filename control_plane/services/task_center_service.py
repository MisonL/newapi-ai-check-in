from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from control_plane.services.task_center_import import TaskCenterMainCheckinImporter
from control_plane.services.task_runtime import build_task_center_executor
from control_plane.settings import settings
from control_plane.storage.base import StorageBackend
from control_plane.task_center_models import (
	AccountRecord,
	DailyTaskRecord,
	IncidentRecord,
	SiteRecord,
	TaskCenterBatchExecutionResult,
	TaskCenterDayStats,
	TaskCenterImportResult,
	TaskCenterReportDay,
	TaskCenterReportPayload,
	TaskCenterReportSite,
	TaskCenterSummary,
	TaskCenterTaskGenerationResult,
	TaskCenterTodayPayload,
	TaskCenterTodayTaskView,
)


class TaskCenterService:
	def __init__(self, storage: StorageBackend) -> None:
		self._storage = storage

	def _account_identity(self, account: AccountRecord) -> tuple[str, str, str]:
		if account.auth_mode == "cookies":
			return (account.site_id, account.auth_mode, account.api_user)
		return (account.site_id, account.auth_mode, account.username)

	def _timezone(self) -> ZoneInfo:
		return ZoneInfo(settings.timezone)

	def _now(self) -> datetime:
		return datetime.now(timezone.utc)

	def _resolve_date(self, value: date | None = None) -> date:
		return value or datetime.now(self._timezone()).date()

	def list_sites(self) -> list[SiteRecord]:
		return self._storage.list_sites()

	def save_site(self, site: SiteRecord) -> SiteRecord:
		for existing in self._storage.list_sites():
			if existing.id != site.id and existing.base_url == site.base_url:
				raise ValueError("Site base URL already exists")
		site.updated_at = datetime.now(timezone.utc)
		self._storage.save_site(site)
		return site

	def list_accounts(self, site_id: str | None = None) -> list[AccountRecord]:
		return self._storage.list_accounts(site_id)

	def save_account(self, account: AccountRecord) -> AccountRecord:
		target_identity = self._account_identity(account)
		for existing in self._storage.list_accounts():
			if existing.id != account.id and self._account_identity(existing) == target_identity:
				raise ValueError("Account already exists for this site and auth mode")
		account.updated_at = datetime.now(timezone.utc)
		self._storage.save_account(account)
		return account

	def delete_account(self, account_id: str) -> dict[str, int | str | bool]:
		account = self._storage.get_account(account_id)
		if account is None:
			raise KeyError(account_id)
		task_count = 0
		for task in self._storage.list_daily_tasks(account_id=account_id):
			self._storage.delete_daily_task(task.id)
			task_count += 1
		result_count = 0
		for result in self._storage.list_checkin_results(account_id=account_id):
			self._storage.delete_checkin_result(result.id)
			result_count += 1
		incident_count = 0
		for incident in self._storage.list_incidents(account_id=account_id):
			self._storage.delete_incident(incident.id)
			incident_count += 1
		self._storage.delete_account(account_id)
		return {
			'deleted': True,
			'account_id': account_id,
			'daily_tasks_deleted': task_count,
			'checkin_results_deleted': result_count,
			'incidents_deleted': incident_count,
		}

	def delete_site(self, site_id: str) -> dict[str, int | str | bool]:
		site = self._storage.get_site(site_id)
		if site is None:
			raise KeyError(site_id)
		account_count = 0
		task_count = 0
		result_count = 0
		incident_count = 0
		for account in self._storage.list_accounts(site_id=site_id):
			account_result = self.delete_account(account.id)
			account_count += 1
			task_count += int(account_result['daily_tasks_deleted'])
			result_count += int(account_result['checkin_results_deleted'])
			incident_count += int(account_result['incidents_deleted'])
		for task in self._storage.list_daily_tasks(site_id=site_id):
			self._storage.delete_daily_task(task.id)
			task_count += 1
		for result in self._storage.list_checkin_results(site_id=site_id):
			self._storage.delete_checkin_result(result.id)
			result_count += 1
		for incident in self._storage.list_incidents(site_id=site_id):
			self._storage.delete_incident(incident.id)
			incident_count += 1
		self._storage.delete_site(site_id)
		return {
			'deleted': True,
			'site_id': site_id,
			'accounts_deleted': account_count,
			'daily_tasks_deleted': task_count,
			'checkin_results_deleted': result_count,
			'incidents_deleted': incident_count,
		}

	def import_from_main_checkin_config(self) -> TaskCenterImportResult:
		return TaskCenterMainCheckinImporter(self._storage).run()

	def generate_today_tasks(self, task_date: date | None = None) -> TaskCenterTaskGenerationResult:
		run_date = self._resolve_date(task_date)
		sites = {site.id: site for site in self.list_sites() if site.enabled}
		accounts = [account for account in self.list_accounts() if account.enabled and account.site_id in sites]
		existing_by_account = {task.account_id: task for task in self._storage.list_daily_tasks(task_date=run_date)}
		created_count = 0
		existing_count = 0
		for account in accounts:
			if account.id in existing_by_account:
				existing_count += 1
				continue
			self._storage.save_daily_task(
				DailyTaskRecord(
					site_id=account.site_id,
					account_id=account.id,
					task_date=run_date,
					status="pending",
					trigger_type="manual",
					attempt_count=0,
				)
			)
			created_count += 1
		return TaskCenterTaskGenerationResult(
			task_date=run_date,
			total_accounts=len(accounts),
			created_count=created_count,
			existing_count=existing_count,
		)

	def retry_task(self, task_id: str) -> DailyTaskRecord:
		task = self._storage.get_daily_task(task_id)
		if task is None:
			raise KeyError(task_id)
		retried = task.model_copy(
			update={
				"status": "pending",
				"trigger_type": "retry",
				"attempt_count": task.attempt_count + 1,
				"started_at": None,
				"finished_at": None,
				"error_code": "",
				"error_message": "",
				"updated_at": self._now(),
			}
		)
		self._storage.save_daily_task(retried)
		return retried

	async def execute_task(self, task_id: str) -> DailyTaskRecord:
		return await build_task_center_executor(self._storage).execute_task(task_id)

	async def execute_today_tasks(self, task_date: date | None = None) -> TaskCenterBatchExecutionResult:
		run_date = self._resolve_date(task_date)
		tasks = [
			task for task in self._storage.list_daily_tasks(task_date=run_date)
			if task.status == "pending"
		]
		result = TaskCenterBatchExecutionResult(task_date=run_date, total_selected=len(tasks))
		executor = build_task_center_executor(self._storage)
		for task in sorted(tasks, key=lambda item: item.created_at):
			finished = await executor.execute_task(task.id)
			result.executed_count += 1
			result.task_ids.append(finished.id)
			if finished.status == "success":
				result.success_count += 1
			elif finished.status == "skipped":
				result.skipped_count += 1
			elif finished.status == "blocked":
				result.blocked_count += 1
			else:
				result.failed_count += 1
		return result

	def today(self, task_date: date | None = None) -> TaskCenterTodayPayload:
		run_date = self._resolve_date(task_date)
		tasks = self._storage.list_daily_tasks(task_date=run_date)
		sites = {site.id: site for site in self.list_sites()}
		accounts = {account.id: account for account in self.list_accounts()}
		results = {result.task_id: result for result in self._storage.list_checkin_results()}
		task_views: list[TaskCenterTodayTaskView] = []
		payload = TaskCenterTodayPayload(task_date=run_date)
		for task in tasks:
			account = accounts.get(task.account_id)
			site = sites.get(task.site_id)
			result = results.get(task.id)
			task_views.append(
				TaskCenterTodayTaskView(
					id=task.id,
					site_id=task.site_id,
					site_name=site.name if site is not None else "Unknown Site",
					account_id=task.account_id,
					account_display_name=(account.display_name or account.username) if account is not None else task.account_id,
					username=account.username if account is not None else "",
					auth_mode=account.auth_mode if account is not None else "password",
					task_date=task.task_date,
					status=task.status,
					trigger_type=task.trigger_type,
					attempt_count=task.attempt_count,
					executor_type=task.executor_type,
					started_at=task.started_at,
					finished_at=task.finished_at,
					error_code=task.error_code,
					error_message=task.error_message,
					quota_awarded=result.quota_awarded if result is not None else 0,
					checked_in_today_before_run=result.checked_in_today_before_run if result is not None else False,
				)
			)
			payload.total_tasks += 1
			payload.total_quota_awarded += result.quota_awarded if result is not None else 0
			if task.status == "pending":
				payload.pending_tasks += 1
			elif task.status == "success":
				payload.success_tasks += 1
			elif task.status == "skipped":
				payload.skipped_tasks += 1
			elif task.status == "failed":
				payload.failed_tasks += 1
			elif task.status == "blocked":
				payload.blocked_tasks += 1
			else:
				payload.running_tasks += 1
		payload.tasks = task_views
		return payload

	def reports(self, date_from: date | None = None, date_to: date | None = None) -> TaskCenterReportPayload:
		end_date = self._resolve_date(date_to)
		start_date = date_from or (end_date - timedelta(days=29))
		all_tasks = [
			task for task in self._storage.list_daily_tasks()
			if start_date <= task.task_date <= end_date
		]
		results = {result.task_id: result for result in self._storage.list_checkin_results()}
		sites = {site.id: site for site in self.list_sites()}
		day_map: dict[date, TaskCenterReportDay] = {}
		site_map: dict[str, TaskCenterReportSite] = {}
		current = start_date
		while current <= end_date:
			day_map[current] = TaskCenterReportDay(task_date=current)
			current += timedelta(days=1)
		for task in all_tasks:
			day = day_map.setdefault(task.task_date, TaskCenterReportDay(task_date=task.task_date))
			site = sites.get(task.site_id)
			site_summary = site_map.setdefault(
				task.site_id,
				TaskCenterReportSite(
					site_id=task.site_id,
					site_name=site.name if site is not None else "Unknown Site",
				),
			)
			day.total_tasks += 1
			site_summary.total_tasks += 1
			if task.status == "success":
				day.success_tasks += 1
				site_summary.success_tasks += 1
			elif task.status == "skipped":
				day.skipped_tasks += 1
				site_summary.skipped_tasks += 1
			elif task.status == "failed":
				day.failed_tasks += 1
				site_summary.failed_tasks += 1
			elif task.status == "blocked":
				day.blocked_tasks += 1
				site_summary.blocked_tasks += 1
			result = results.get(task.id)
			if result is not None:
				day.total_quota_awarded += result.quota_awarded
				site_summary.total_quota_awarded += result.quota_awarded
		return TaskCenterReportPayload(
			date_from=start_date,
			date_to=end_date,
			days=[day_map[item] for item in sorted(day_map.keys())],
			sites=sorted(
				site_map.values(),
				key=lambda item: (-item.total_tasks, -item.total_quota_awarded, item.site_name.lower()),
			),
		)

	def incidents(self, resolved: bool | None = None) -> list[IncidentRecord]:
		stored = self._storage.list_incidents(resolved=resolved)
		if stored:
			return stored
		sites = {site.id: site for site in self.list_sites()}
		accounts = {account.id: account for account in self.list_accounts()}
		derived: list[IncidentRecord] = []
		for task in self._storage.list_daily_tasks():
			if task.status not in {"failed", "blocked"}:
				continue
			account = accounts.get(task.account_id)
			site = sites.get(task.site_id)
			derived.append(
				IncidentRecord(
					account_id=task.account_id,
					site_id=task.site_id,
					task_id=task.id,
					display_name=(account.display_name or account.username) if account is not None else task.account_id,
					site_name=site.name if site is not None else "Unknown Site",
					status="failed" if task.status == "failed" else "blocked",
					last_error_message=task.error_message or "Task requires review",
					type=task.error_code or task.status,
					severity="high" if task.status == "failed" else "medium",
					dedupe_key=f"{task.account_id}:{task.task_date}:{task.error_code or task.status}",
					first_seen_at=task.started_at or task.created_at,
					last_seen_at=task.finished_at or task.updated_at,
					detail=task.error_message,
					last_checkin_at=task.finished_at,
				)
			)
		return sorted(derived, key=lambda item: item.last_seen_at, reverse=True)

	def summary(self) -> TaskCenterSummary:
		sites = self.list_sites()
		accounts = self.list_accounts()
		site_names = {site.id: site.name for site in sites}
		today = datetime.now(ZoneInfo(settings.timezone)).date()
		today_tasks = self._storage.list_daily_tasks(task_date=today)
		if today_tasks:
			today_payload = self.today(today)
			return TaskCenterSummary(
				today=TaskCenterDayStats(
					total_sites=len(sites),
					enabled_sites=sum(1 for site in sites if site.enabled),
					total_accounts=len(accounts),
					enabled_accounts=sum(1 for account in accounts if account.enabled),
					today_success=today_payload.success_tasks,
					today_skipped=today_payload.skipped_tasks,
					today_failed=today_payload.failed_tasks,
					today_blocked=today_payload.blocked_tasks,
					today_pending=today_payload.pending_tasks + today_payload.running_tasks,
					today_quota_awarded=today_payload.total_quota_awarded,
				),
				recent_accounts=sorted(accounts, key=lambda item: item.updated_at, reverse=True)[:8],
				recent_incidents=self.incidents()[:8],
			)

		stats = TaskCenterDayStats(
			total_sites=len(sites),
			enabled_sites=sum(1 for site in sites if site.enabled),
			total_accounts=len(accounts),
			enabled_accounts=sum(1 for account in accounts if account.enabled),
		)
		recent_accounts = sorted(accounts, key=lambda item: item.updated_at, reverse=True)[:8]
		recent_incidents: list[IncidentRecord] = []

		for account in accounts:
			if not account.enabled:
				continue
			is_today = account.last_checkin_date == today
			if is_today and account.last_checkin_status == "success":
				stats.today_success += 1
				stats.today_quota_awarded += account.last_quota_awarded
			elif is_today and account.last_checkin_status == "skipped":
				stats.today_skipped += 1
			elif is_today and account.last_checkin_status == "failed":
				stats.today_failed += 1
			elif is_today and account.last_checkin_status == "blocked":
				stats.today_blocked += 1
			else:
				stats.today_pending += 1

			if account.last_checkin_status in {"failed", "blocked"}:
				recent_incidents.append(
					IncidentRecord(
						account_id=account.id,
						site_id=account.site_id,
						display_name=account.display_name or account.username,
						site_name=site_names.get(account.site_id, "Unknown Site"),
						status=account.last_checkin_status,
						last_error_message=account.last_error_message,
						last_checkin_at=account.last_checkin_at,
					)
				)

		recent_incidents.sort(
			key=lambda item: (item.last_checkin_at or datetime.min.replace(tzinfo=timezone.utc)).timestamp(),
			reverse=True,
		)
		return TaskCenterSummary(
			today=stats,
			recent_accounts=recent_accounts,
			recent_incidents=recent_incidents[:8],
		)
