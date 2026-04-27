from __future__ import annotations

import asyncio

from control_plane.services.newapi_checkin_service import (
	NewApiCheckinService,
	NewApiPreflightResult,
	NewApiSiteProbeResult,
	NewApiTaskExecutionResult,
)
from control_plane.services.newapi_client import (
	NewApiAuthResult,
	NewApiCheckinActionResult,
	NewApiCheckinStatusResult,
)
from control_plane.task_center_models import AccountRecord, SiteRecord


class FakeClient:
	def __init__(self, auth_result, status_result=None, checkin_result=None) -> None:
		self.auth_result = auth_result
		self.status_result = status_result
		self.checkin_result = checkin_result
		self.closed = False
		self.calls: list[tuple[str, tuple]] = []

	def bootstrap_session(self, user_id: str, cookies: dict[str, str]) -> None:
		self.calls.append(('bootstrap_session', (user_id, cookies)))

	async def login(self, username: str, password: str, turnstile_token: str = ''):
		self.calls.append(('login', (username, password, turnstile_token)))
		return self.auth_result

	async def get_checkin_status(self, month: str = ''):
		self.calls.append(('get_checkin_status', (month,)))
		if isinstance(self.status_result, list):
			return self.status_result.pop(0)
		return self.status_result

	async def probe_checkin_endpoint(self):
		self.calls.append(('probe_checkin_endpoint', ()))
		if isinstance(self.status_result, list):
			return self.status_result.pop(0)
		return self.status_result

	async def do_checkin(self, turnstile_token: str = ''):
		self.calls.append(('do_checkin', (turnstile_token,)))
		if isinstance(self.checkin_result, list):
			return self.checkin_result.pop(0)
		return self.checkin_result

	async def aclose(self) -> None:
		self.closed = True


def _site_and_account():
	site = SiteRecord(name='Primary', base_url='https://example.com')
	account = AccountRecord(site_id=site.id, username='alice', password='secret-pass')
	return site, account


def test_newapi_checkin_service_probes_site_without_running_checkin():
	site, _ = _site_and_account()
	fake_client = FakeClient(
		auth_result=None,
		status_result=NewApiCheckinStatusResult(
			success=False,
			error_code='auth_contract_mismatch',
			message='未提供用户ID',
			raw_payload={'success': False, 'message': '未提供用户ID'},
		),
	)
	service = NewApiCheckinService(lambda _: fake_client)

	result = asyncio.run(service.probe_site(site))
	assert isinstance(result, NewApiSiteProbeResult)
	assert result.status == 'healthy'
	assert result.compatible is True
	assert result.reachable is True
	assert result.error_code == 'auth_contract_mismatch'
	assert [item[0] for item in fake_client.calls] == ['probe_checkin_endpoint']


def test_newapi_checkin_service_preflight_does_not_execute_checkin():
	site, account = _site_and_account()
	fake_client = FakeClient(
		auth_result=NewApiAuthResult(phase='login_success', success=True, user_id='1'),
		status_result=NewApiCheckinStatusResult(
			success=True,
			enabled=True,
			min_quota=10,
			max_quota=20,
			checked_in_today=False,
			total_checkins=5,
			total_quota=100,
			raw_payload={'data': {'enabled': True}},
		),
		checkin_result=NewApiCheckinActionResult(phase='success', success=True, quota_awarded=20),
	)
	service = NewApiCheckinService(lambda _: fake_client)

	result = asyncio.run(service.preflight_account(site, account))
	assert isinstance(result, NewApiPreflightResult)
	assert result.session_status == 'valid'
	assert result.checkin_status == 'pending'
	assert result.checkin_enabled is True
	assert result.min_quota == 10
	assert result.max_quota == 20
	assert result.total_checkins == 5
	assert [item[0] for item in fake_client.calls] == ['login', 'get_checkin_status']


def test_newapi_checkin_service_success_path():
	site, account = _site_and_account()
	fake_client = FakeClient(
		auth_result=NewApiAuthResult(phase='login_success', success=True, user_id='1'),
		status_result=NewApiCheckinStatusResult(
			success=True,
			enabled=True,
			checked_in_today=False,
			total_checkins=5,
			total_quota=100,
			raw_payload={'stats': {'checked_in_today': False}},
		),
		checkin_result=NewApiCheckinActionResult(
			phase='success',
			success=True,
			quota_awarded=20,
			checkin_date='2026-04-13',
			raw_payload={'data': {'quota_awarded': 20}},
		),
	)
	service = NewApiCheckinService(lambda _: fake_client)

	result = asyncio.run(service.run_account(site, account))
	assert result.task_status == 'success'
	assert result.account_status == 'success'
	assert result.total_checkins == 6
	assert result.total_quota_awarded == 120
	assert fake_client.closed is True


def test_newapi_checkin_service_skips_when_already_checked_in_status():
	site, account = _site_and_account()
	fake_client = FakeClient(
		auth_result=NewApiAuthResult(phase='login_success', success=True, user_id='1'),
		status_result=NewApiCheckinStatusResult(
			success=True,
			enabled=True,
			checked_in_today=True,
			total_checkins=8,
			total_quota=233,
			raw_payload={'stats': {'checked_in_today': True}},
		),
	)
	service = NewApiCheckinService(lambda _: fake_client)

	result = asyncio.run(service.run_account(site, account))
	assert result.task_status == 'skipped'
	assert result.checked_in_today_before_run is True
	assert [item[0] for item in fake_client.calls] == ['login', 'get_checkin_status']


def test_newapi_checkin_service_blocks_when_two_factor_required():
	site, account = _site_and_account()
	fake_client = FakeClient(
		auth_result=NewApiAuthResult(
			phase='two_factor_required',
			success=False,
			message='需要两步验证',
		),
	)
	service = NewApiCheckinService(lambda _: fake_client)

	result = asyncio.run(service.run_account(site, account))
	assert result.task_status == 'blocked'
	assert result.error_code == 'two_factor_required'
	assert fake_client.closed is True


def test_newapi_checkin_service_blocks_when_login_needs_turnstile():
	site, account = _site_and_account()
	fake_client = FakeClient(
		auth_result=NewApiAuthResult(
			phase='login_failed',
			success=False,
			error_code='turnstile_required',
			message='Turnstile token 为空',
		),
	)
	service = NewApiCheckinService(lambda _: fake_client)

	result = asyncio.run(service.run_account(site, account))
	assert result.task_status == 'blocked'
	assert result.account_status == 'blocked'
	assert result.error_code == 'turnstile_required'
	assert fake_client.closed is True


def test_newapi_checkin_service_reconciles_duplicate_checkin_as_skipped():
	site, account = _site_and_account()
	fake_client = FakeClient(
		auth_result=NewApiAuthResult(phase='login_success', success=True, user_id='1'),
		status_result=[
			NewApiCheckinStatusResult(
				success=True,
				enabled=True,
				checked_in_today=False,
				total_checkins=0,
				total_quota=0,
				raw_payload={'stats': {'checked_in_today': False}},
			),
			NewApiCheckinStatusResult(
				success=True,
				enabled=True,
				checked_in_today=True,
				total_checkins=1,
				total_quota=5724,
				raw_payload={
					'data': {
						'stats': {
							'checked_in_today': True,
							'total_checkins': 1,
							'total_quota': 5724,
						}
					}
				},
			),
		],
		checkin_result=NewApiCheckinActionResult(
			phase='failed',
			success=False,
			error_code='unexpected_response',
			message='签到失败，请稍后重试',
			raw_payload={'message': '签到失败，请稍后重试', 'success': False},
		),
	)
	service = NewApiCheckinService(lambda _: fake_client)

	result = asyncio.run(service.run_account(site, account))
	assert result.task_status == 'skipped'
	assert result.account_status == 'skipped'
	assert result.error_code == 'already_checked'
	assert result.total_checkins == 1
	assert result.total_quota_awarded == 5724
	assert [item[0] for item in fake_client.calls] == [
		'login',
		'get_checkin_status',
		'do_checkin',
		'get_checkin_status',
	]


def test_newapi_checkin_service_blocks_when_site_checkin_disabled():
	site, account = _site_and_account()
	fake_client = FakeClient(
		auth_result=NewApiAuthResult(phase='login_success', success=True, user_id='1'),
		status_result=NewApiCheckinStatusResult(
			success=False,
			error_code='site_checkin_disabled',
			message='签到功能未启用',
			raw_payload={'message': '签到功能未启用', 'success': False},
		),
	)
	service = NewApiCheckinService(lambda _: fake_client)

	result = asyncio.run(service.run_account(site, account))
	assert result.task_status == 'blocked'
	assert result.account_status == 'blocked'
	assert result.error_code == 'site_checkin_disabled'


def test_newapi_checkin_service_blocks_when_turnstile_required():
	site, account = _site_and_account()
	fake_client = FakeClient(
		auth_result=NewApiAuthResult(phase='login_success', success=True, user_id='1'),
		status_result=NewApiCheckinStatusResult(
			success=True,
			enabled=True,
			checked_in_today=False,
			total_checkins=0,
			total_quota=0,
			raw_payload={'stats': {'checked_in_today': False}},
		),
		checkin_result=NewApiCheckinActionResult(
			phase='turnstile_required',
			success=False,
			error_code='turnstile_required',
			message='Turnstile token 为空',
			raw_payload={'message': 'Turnstile token 为空', 'success': False},
		),
	)
	service = NewApiCheckinService(lambda _: fake_client)

	result = asyncio.run(service.run_account(site, account))
	assert result.task_status == 'blocked'
	assert result.account_status == 'blocked'
	assert result.error_code == 'turnstile_required'


def test_newapi_checkin_service_fails_on_auth_contract_mismatch():
	site, account = _site_and_account()
	fake_client = FakeClient(
		auth_result=NewApiAuthResult(phase='login_success', success=True, user_id='1'),
		status_result=NewApiCheckinStatusResult(
			success=False,
			error_code='auth_contract_mismatch',
			message='Missing New-Api-User context',
			raw_payload={'success': False},
		),
	)
	service = NewApiCheckinService(lambda _: fake_client)

	result = asyncio.run(service.run_account(site, account))
	assert result.task_status == 'failed'
	assert result.account_status == 'failed'
	assert result.error_code == 'auth_contract_mismatch'


def test_newapi_checkin_service_supports_cookie_auth_mode():
	site = SiteRecord(name='Primary', base_url='https://example.com')
	account = AccountRecord(
		site_id=site.id,
		display_name='Cookie Account',
		username='cookie-42',
		auth_mode='cookies',
		api_user='42',
		session_cookies={'session': 'abc'},
	)
	fake_client = FakeClient(
		auth_result=None,
		status_result=NewApiCheckinStatusResult(
			success=True,
			enabled=True,
			checked_in_today=True,
			total_checkins=3,
			total_quota=99,
			raw_payload={'stats': {'checked_in_today': True}},
		),
	)
	service = NewApiCheckinService(lambda _: fake_client)

	result = asyncio.run(service.run_account(site, account))
	assert result.task_status == 'skipped'
	assert [item[0] for item in fake_client.calls] == ['bootstrap_session', 'get_checkin_status']


def test_newapi_checkin_service_blocks_oauth_auth_mode():
	site = SiteRecord(name='Primary', base_url='https://example.com')
	account = AccountRecord(
		site_id=site.id,
		display_name='GitHub Account',
		username='octocat',
		auth_mode='github_oauth',
		password='oauth-pass',
	)
	fake_client = FakeClient(auth_result=None)
	service = NewApiCheckinService(lambda _: fake_client)

	result = asyncio.run(service.run_account(site, account))
	assert result.task_status == 'blocked'
	assert result.error_code == 'browser_auth_required'
	assert fake_client.calls == []


def test_newapi_checkin_service_uses_oauth_executor_when_present():
	site = SiteRecord(name='Primary', base_url='https://example.com')
	account = AccountRecord(
		site_id=site.id,
		display_name='GitHub Account',
		username='octocat',
		auth_mode='github_oauth',
		password='oauth-pass',
	)
	fake_client = FakeClient(auth_result=None)

	async def fake_oauth_executor(current_site, current_account):
		assert current_site.id == site.id
		assert current_account.id == account.id
		return NewApiTaskExecutionResult(
			task_status='success',
			account_status='success',
			executor_type='legacy_plugin',
		)

	service = NewApiCheckinService(lambda _: fake_client, oauth_executor=fake_oauth_executor)

	result = asyncio.run(service.run_account(site, account))
	assert result.task_status == 'success'
	assert result.executor_type == 'legacy_plugin'
	assert fake_client.calls == []
