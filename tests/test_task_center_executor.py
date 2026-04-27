from __future__ import annotations

import asyncio
from datetime import date

from control_plane.services.newapi_checkin_service import NewApiTaskExecutionResult
from control_plane.services.task_center_executor import TaskCenterTaskExecutor
from control_plane.storage.memory import MemoryStorage
from control_plane.task_center_models import AccountRecord, DailyTaskRecord, SiteRecord


class FakeCheckinService:
	def __init__(self, result: NewApiTaskExecutionResult) -> None:
		self._result = result
		self.calls: list[tuple[str, str]] = []

	async def run_account(self, site, account):
		self.calls.append((site.id, account.id))
		return self._result


def _seed_storage(tmp_path):
	storage = MemoryStorage(tmp_path / 'artifacts')
	site = SiteRecord(name='Primary', base_url='https://example.com')
	account = AccountRecord(site_id=site.id, username='alice', password='secret-pass')
	task = DailyTaskRecord(site_id=site.id, account_id=account.id, task_date=date(2026, 4, 13))
	storage.save_site(site)
	storage.save_account(account)
	storage.save_daily_task(task)
	return storage, site, account, task


def test_task_center_executor_persists_success_result(tmp_path):
	storage, site, account, task = _seed_storage(tmp_path)
	service = FakeCheckinService(
		NewApiTaskExecutionResult(
			task_status='success',
			account_status='success',
			quota_awarded=20,
			checkin_date='2026-04-13',
			total_checkins=6,
			total_quota_awarded=120,
			raw_status_payload={'stats': {'checked_in_today': False}},
			raw_checkin_payload={'data': {'quota_awarded': 20}},
		)
	)
	executor = TaskCenterTaskExecutor(storage, service)

	finished = asyncio.run(executor.execute_task(task.id))
	saved_task = storage.get_daily_task(task.id)
	saved_account = storage.get_account(account.id)
	saved_result = storage.get_checkin_result(task.id)

	assert finished.status == 'success'
	assert saved_task is not None and saved_task.finished_at is not None
	assert saved_account is not None and saved_account.last_checkin_status == 'success'
	assert saved_account.total_checkins == 6
	assert saved_result is not None and saved_result.quota_awarded == 20
	assert storage.list_incidents() == []
	assert service.calls == [(site.id, account.id)]


def test_task_center_executor_persists_blocked_incident(tmp_path):
	storage, _, account, task = _seed_storage(tmp_path)
	service = FakeCheckinService(
		NewApiTaskExecutionResult(
			task_status='blocked',
			account_status='blocked',
			error_code='turnstile_required',
			error_message='Turnstile token 为空',
			total_checkins=5,
			total_quota_awarded=100,
			raw_status_payload={'success': False},
		)
	)
	executor = TaskCenterTaskExecutor(storage, service)

	finished = asyncio.run(executor.execute_task(task.id))
	saved_account = storage.get_account(account.id)
	incidents = storage.list_incidents()

	assert finished.status == 'blocked'
	assert saved_account is not None and saved_account.last_checkin_status == 'blocked'
	assert incidents[0].type == 'turnstile_required'
	assert incidents[0].status == 'blocked'


def test_task_center_executor_merges_repeated_incident_by_dedupe_key(tmp_path):
	storage, _, account, task = _seed_storage(tmp_path)
	service = FakeCheckinService(
		NewApiTaskExecutionResult(
			task_status='failed',
			account_status='failed',
			error_code='login_failed',
			error_message='用户名或密码错误',
			total_checkins=5,
			total_quota_awarded=100,
		)
	)
	executor = TaskCenterTaskExecutor(storage, service)

	first = asyncio.run(executor.execute_task(task.id))
	retried = task.model_copy(update={'id': 'retry-task', 'trigger_type': 'retry'})
	storage.save_daily_task(retried)
	second = asyncio.run(executor.execute_task(retried.id))
	incidents = storage.list_incidents()

	assert first.status == 'failed'
	assert second.status == 'failed'
	assert len(incidents) == 1
	assert incidents[0].task_id == second.id
	assert incidents[0].dedupe_key == f'{account.id}:2026-04-13:login_failed'
