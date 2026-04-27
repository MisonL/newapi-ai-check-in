from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from control_plane.task_center_models import AccountRecord, SiteRecord


@dataclass(slots=True)
class NewApiTaskExecutionResult:
	task_status: str
	account_status: str
	executor_type: str = 'standard_newapi'
	error_code: str = ''
	error_message: str = ''
	checked_in_today_before_run: bool = False
	quota_awarded: int = 0
	checkin_date: str = ''
	total_checkins: int = 0
	total_quota_awarded: int = 0
	raw_status_payload: dict[str, Any] = field(default_factory=dict)
	raw_checkin_payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class NewApiSiteProbeResult:
	site_id: str
	status: str
	reachable: bool
	compatible: bool
	checkin_enabled: bool | None = None
	min_quota: int | None = None
	max_quota: int | None = None
	error_code: str = ''
	message: str = ''


@dataclass(slots=True)
class NewApiPreflightResult:
	site_id: str
	account_id: str
	session_status: str
	checkin_status: str
	checkin_enabled: bool | None = None
	checked_in_today: bool = False
	min_quota: int | None = None
	max_quota: int | None = None
	total_checkins: int = 0
	total_quota_awarded: int = 0
	error_code: str = ''
	message: str = ''


class NewApiClientProtocol(Protocol):
	def bootstrap_session(self, user_id: str, cookies: dict[str, str]) -> None: ...

	async def login(self, username: str, password: str, turnstile_token: str = ''): ...

	async def probe_checkin_endpoint(self): ...

	async def get_checkin_status(self, month: str = ''): ...

	async def do_checkin(self, turnstile_token: str = ''): ...

	async def aclose(self) -> None: ...


class NewApiCheckinService:
	def __init__(self, client_factory, oauth_executor=None) -> None:
		self._client_factory = client_factory
		self._oauth_executor = oauth_executor

	async def probe_site(self, site: SiteRecord) -> NewApiSiteProbeResult:
		client: NewApiClientProtocol = self._client_factory(site)
		try:
			status_result = await client.probe_checkin_endpoint()
			if status_result.success:
				return NewApiSiteProbeResult(
					site_id=site.id,
					status='healthy' if status_result.enabled else 'degraded',
					reachable=True,
					compatible=True,
					checkin_enabled=status_result.enabled,
					min_quota=status_result.min_quota,
					max_quota=status_result.max_quota,
					message=status_result.message,
				)
			if status_result.error_code == 'auth_contract_mismatch':
				return NewApiSiteProbeResult(
					site_id=site.id,
					status='healthy',
					reachable=True,
					compatible=True,
					error_code=status_result.error_code,
					message=status_result.message,
				)
			if status_result.error_code == 'site_checkin_disabled':
				return NewApiSiteProbeResult(
					site_id=site.id,
					status='degraded',
					reachable=True,
					compatible=True,
					checkin_enabled=False,
					error_code=status_result.error_code,
					message=status_result.message,
				)
			if status_result.error_code == 'site_unreachable':
				return NewApiSiteProbeResult(
					site_id=site.id,
					status='unreachable',
					reachable=False,
					compatible=False,
					error_code=status_result.error_code,
					message=status_result.message,
				)
			return NewApiSiteProbeResult(
				site_id=site.id,
				status='unsupported',
				reachable=True,
				compatible=False,
				error_code=status_result.error_code or 'unexpected_response',
				message=status_result.message,
			)
		finally:
			await client.aclose()

	async def preflight_account(self, site: SiteRecord, account: AccountRecord) -> NewApiPreflightResult:
		if account.auth_mode in {'github_oauth', 'linuxdo_oauth'}:
			return NewApiPreflightResult(
				site_id=site.id,
				account_id=account.id,
				session_status='unknown',
				checkin_status='blocked',
				error_code='browser_auth_required',
				message='OAuth 登录当前需要浏览器执行链',
			)
		client: NewApiClientProtocol = self._client_factory(site)
		try:
			if account.auth_mode == 'cookies':
				client.bootstrap_session(account.api_user, account.session_cookies)
			else:
				auth_result = await client.login(account.username, account.password)
				if auth_result.phase == 'two_factor_required':
					return self._preflight_blocked(site, account, 'two_factor_required', auth_result.message)
				if auth_result.error_code == 'turnstile_required':
					return self._preflight_blocked(site, account, 'turnstile_required', auth_result.message)
				if not auth_result.success:
					return NewApiPreflightResult(
						site_id=site.id,
						account_id=account.id,
						session_status='invalid',
						checkin_status='failed',
						error_code=auth_result.error_code or 'login_failed',
						message=auth_result.message,
					)
			status_result = await client.get_checkin_status()
			if not status_result.success:
				return self._preflight_status_error(site, account, status_result.error_code, status_result.message)
			return NewApiPreflightResult(
				site_id=site.id,
				account_id=account.id,
				session_status='valid',
				checkin_status='skipped' if status_result.checked_in_today else 'pending',
				checkin_enabled=status_result.enabled,
				checked_in_today=status_result.checked_in_today,
				min_quota=status_result.min_quota,
				max_quota=status_result.max_quota,
				total_checkins=status_result.total_checkins,
				total_quota_awarded=status_result.total_quota,
				message=status_result.message,
			)
		finally:
			await client.aclose()

	async def run_account(self, site: SiteRecord, account: AccountRecord) -> NewApiTaskExecutionResult:
		if account.auth_mode in {'github_oauth', 'linuxdo_oauth'}:
			if self._oauth_executor is None:
				return self._blocked('browser_auth_required', 'OAuth 登录当前需要浏览器执行链')
			return await self._oauth_executor(site, account)
		client: NewApiClientProtocol = self._client_factory(site)
		try:
			if account.auth_mode == 'cookies':
				client.bootstrap_session(account.api_user, account.session_cookies)
			else:
				auth_result = await client.login(account.username, account.password)
				if auth_result.phase == 'two_factor_required':
					return self._blocked('two_factor_required', auth_result.message)
				if auth_result.error_code == 'turnstile_required':
					return self._blocked('turnstile_required', auth_result.message)
				if not auth_result.success:
					return self._failed(auth_result.error_code or 'login_failed', auth_result.message)

			status_result = await client.get_checkin_status()
			if not status_result.success:
				return self._from_status_error(
					status_result.error_code, status_result.message, status_result.raw_payload
				)

			if status_result.checked_in_today:
				return NewApiTaskExecutionResult(
					task_status='skipped',
					account_status='skipped',
					checked_in_today_before_run=True,
					total_checkins=status_result.total_checkins,
					total_quota_awarded=status_result.total_quota,
					raw_status_payload=status_result.raw_payload,
				)

			checkin_result = await client.do_checkin()
			if checkin_result.success:
				return NewApiTaskExecutionResult(
					task_status='success',
					account_status='success',
					checked_in_today_before_run=False,
					quota_awarded=checkin_result.quota_awarded,
					checkin_date=checkin_result.checkin_date,
					total_checkins=status_result.total_checkins + 1,
					total_quota_awarded=status_result.total_quota + checkin_result.quota_awarded,
					raw_status_payload=status_result.raw_payload,
					raw_checkin_payload=checkin_result.raw_payload,
				)

			if checkin_result.error_code == 'already_checked':
				return NewApiTaskExecutionResult(
					task_status='skipped',
					account_status='skipped',
					error_code='already_checked',
					error_message=checkin_result.message,
					checked_in_today_before_run=True,
					total_checkins=status_result.total_checkins,
					total_quota_awarded=status_result.total_quota,
					raw_status_payload=status_result.raw_payload,
					raw_checkin_payload=checkin_result.raw_payload,
				)
			if checkin_result.error_code in {'turnstile_required', 'site_checkin_disabled'}:
				return NewApiTaskExecutionResult(
					task_status='blocked',
					account_status='blocked',
					error_code=checkin_result.error_code,
					error_message=checkin_result.message,
					checked_in_today_before_run=False,
					total_checkins=status_result.total_checkins,
					total_quota_awarded=status_result.total_quota,
					raw_status_payload=status_result.raw_payload,
					raw_checkin_payload=checkin_result.raw_payload,
				)
			reconciled = await self._reconcile_failed_checkin(client, status_result, checkin_result)
			if reconciled is not None:
				return reconciled
			return NewApiTaskExecutionResult(
				task_status='failed',
				account_status='failed',
				error_code=checkin_result.error_code or 'unexpected_response',
				error_message=checkin_result.message,
				checked_in_today_before_run=False,
				total_checkins=status_result.total_checkins,
				total_quota_awarded=status_result.total_quota,
				raw_status_payload=status_result.raw_payload,
				raw_checkin_payload=checkin_result.raw_payload,
			)
		finally:
			await client.aclose()

	async def _reconcile_failed_checkin(
		self,
		client: NewApiClientProtocol,
		status_result,
		checkin_result,
	) -> NewApiTaskExecutionResult | None:
		refreshed_status = await client.get_checkin_status()
		if not refreshed_status.success or not refreshed_status.checked_in_today:
			return None
		return NewApiTaskExecutionResult(
			task_status='skipped',
			account_status='skipped',
			error_code='already_checked',
			error_message=checkin_result.message,
			checked_in_today_before_run=False,
			total_checkins=refreshed_status.total_checkins,
			total_quota_awarded=refreshed_status.total_quota,
			raw_status_payload=refreshed_status.raw_payload,
			raw_checkin_payload=checkin_result.raw_payload,
		)

	def _from_status_error(
		self, error_code: str, message: str, raw_payload: dict[str, Any]
	) -> NewApiTaskExecutionResult:
		if error_code in {'turnstile_required', 'site_checkin_disabled', 'two_factor_required'}:
			result = self._blocked(error_code, message)
		else:
			result = self._failed(error_code or 'unexpected_response', message)
		result.raw_status_payload = raw_payload
		return result

	def _blocked(self, error_code: str, message: str) -> NewApiTaskExecutionResult:
		return NewApiTaskExecutionResult(
			task_status='blocked',
			account_status='blocked',
			error_code=error_code,
			error_message=message,
		)

	def _preflight_blocked(
		self,
		site: SiteRecord,
		account: AccountRecord,
		error_code: str,
		message: str,
	) -> NewApiPreflightResult:
		return NewApiPreflightResult(
			site_id=site.id,
			account_id=account.id,
			session_status='unknown',
			checkin_status='blocked',
			error_code=error_code,
			message=message,
		)

	def _preflight_status_error(
		self,
		site: SiteRecord,
		account: AccountRecord,
		error_code: str,
		message: str,
	) -> NewApiPreflightResult:
		session_status = (
			'expired' if error_code == 'auth_contract_mismatch' and account.auth_mode == 'cookies' else 'valid'
		)
		checkin_status = 'blocked' if error_code in {'turnstile_required', 'site_checkin_disabled'} else 'failed'
		return NewApiPreflightResult(
			site_id=site.id,
			account_id=account.id,
			session_status=session_status,
			checkin_status=checkin_status,
			checkin_enabled=False if error_code == 'site_checkin_disabled' else None,
			error_code=error_code or 'unexpected_response',
			message=message,
		)

	def _failed(self, error_code: str, message: str) -> NewApiTaskExecutionResult:
		return NewApiTaskExecutionResult(
			task_status='failed',
			account_status='failed',
			error_code=error_code,
			error_message=message,
		)
