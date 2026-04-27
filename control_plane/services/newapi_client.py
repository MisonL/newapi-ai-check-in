from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal
from urllib.parse import urlencode, urlparse, urlsplit, urlunsplit

from curl_cffi import requests

AuthPhase = Literal['login_success', 'two_factor_required', 'login_failed']
CheckinPhase = Literal['success', 'already_checked', 'site_checkin_disabled', 'turnstile_required', 'failed']


@dataclass(slots=True)
class NewApiAuthResult:
	phase: AuthPhase
	success: bool
	error_code: str = ''
	message: str = ''
	user_id: str = ''
	username: str = ''
	display_name: str = ''
	raw_payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class NewApiCheckinStatusResult:
	success: bool
	error_code: str = ''
	message: str = ''
	enabled: bool = False
	min_quota: int | None = None
	max_quota: int | None = None
	checked_in_today: bool = False
	total_checkins: int = 0
	total_quota: int = 0
	raw_payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class NewApiCheckinActionResult:
	phase: CheckinPhase
	success: bool
	error_code: str = ''
	message: str = ''
	quota_awarded: int = 0
	checkin_date: str = ''
	raw_payload: dict[str, Any] = field(default_factory=dict)


class NewApiClient:
	def __init__(self, base_url: str, session: requests.AsyncSession | Any | None = None) -> None:
		self._base_url = base_url.rstrip('/')
		self._session = session or requests.AsyncSession()
		self._owns_session = session is None
		self._user_id = ''
		self._resolved_base_url = ''

	@property
	def user_id(self) -> str:
		return self._user_id

	async def aclose(self) -> None:
		if self._owns_session:
			await self._session.close()

	def bootstrap_session(self, user_id: str, cookies: dict[str, str]) -> None:
		self._user_id = str(user_id).strip()
		cookie_jar = getattr(self._session, 'cookies', None)
		if cookie_jar is None:
			return
		for base_url in self._candidate_base_urls():
			parsed = urlparse(base_url)
			domain = parsed.hostname or ''
			for key, value in cookies.items():
				if hasattr(cookie_jar, 'set'):
					cookie_jar.set(key, value, domain=domain, path='/')

	async def login(self, username: str, password: str, turnstile_token: str = '') -> NewApiAuthResult:
		payload = await self._request(
			'POST',
			'/api/user/login',
			json={'username': username, 'password': password},
			turnstile_token=turnstile_token,
		)
		message = self._message(payload)
		if not payload.get('success'):
			return NewApiAuthResult(
				phase='login_failed',
				success=False,
				error_code=self._classify_auth_error(payload),
				message=message,
				raw_payload=payload,
			)
		data = payload.get('data') or {}
		if data.get('require_2fa') is True:
			return NewApiAuthResult(
				phase='two_factor_required',
				success=False,
				message=message,
				raw_payload=payload,
			)
		user_id = self._extract_user_id(data)
		if not user_id:
			return NewApiAuthResult(
				phase='login_failed',
				success=False,
				error_code='unexpected_response',
				message=message or '登录响应缺少用户标识',
				raw_payload=payload,
			)
		self._user_id = user_id
		return NewApiAuthResult(
			phase='login_success',
			success=True,
			message=message,
			user_id=user_id,
			username=self._as_text(data.get('username')),
			display_name=self._as_text(data.get('display_name')),
			raw_payload=payload,
		)

	async def verify_two_factor(self, code: str) -> NewApiAuthResult:
		payload = await self._request('POST', '/api/user/login/2fa', json={'code': code})
		message = self._message(payload)
		if not payload.get('success'):
			return NewApiAuthResult(
				phase='login_failed',
				success=False,
				error_code=self._classify_auth_error(payload),
				message=message,
				raw_payload=payload,
			)
		data = payload.get('data') or {}
		user_id = self._extract_user_id(data)
		if not user_id:
			return NewApiAuthResult(
				phase='login_failed',
				success=False,
				error_code='unexpected_response',
				message=message or '2FA 响应缺少用户标识',
				raw_payload=payload,
			)
		self._user_id = user_id
		return NewApiAuthResult(
			phase='login_success',
			success=True,
			message=message,
			user_id=user_id,
			username=self._as_text(data.get('username')),
			display_name=self._as_text(data.get('display_name')),
			raw_payload=payload,
		)

	async def get_checkin_status(self, month: str = '') -> NewApiCheckinStatusResult:
		params = {'month': month} if month else None
		payload = await self._request('GET', '/api/user/checkin', params=params, include_user_header=True)
		return self._checkin_status_from_payload(payload)

	async def probe_checkin_endpoint(self) -> NewApiCheckinStatusResult:
		payload = await self._request('GET', '/api/user/checkin')
		return self._checkin_status_from_payload(payload)

	def _checkin_status_from_payload(self, payload: dict[str, Any]) -> NewApiCheckinStatusResult:
		message = self._message(payload)
		if not payload.get('success'):
			return NewApiCheckinStatusResult(
				success=False,
				error_code=self._classify_checkin_error(payload),
				message=message,
				raw_payload=payload,
			)
		data = payload.get('data') or {}
		stats = data.get('stats') or {}
		return NewApiCheckinStatusResult(
			success=True,
			message=message,
			enabled=bool(data.get('enabled')),
			min_quota=self._as_int(data.get('min_quota')),
			max_quota=self._as_int(data.get('max_quota')),
			checked_in_today=bool(stats.get('checked_in_today')),
			total_checkins=self._as_int(stats.get('total_checkins')) or 0,
			total_quota=self._as_int(stats.get('total_quota')) or 0,
			raw_payload=payload,
		)

	async def do_checkin(self, turnstile_token: str = '') -> NewApiCheckinActionResult:
		payload = await self._request(
			'POST',
			'/api/user/checkin',
			include_user_header=True,
			turnstile_token=turnstile_token,
		)
		message = self._message(payload)
		if not payload.get('success'):
			error_code = self._classify_checkin_error(payload)
			return NewApiCheckinActionResult(
				phase=self._error_phase(error_code),
				success=False,
				error_code=error_code,
				message=message,
				raw_payload=payload,
			)
		data = payload.get('data') or {}
		return NewApiCheckinActionResult(
			phase='success',
			success=True,
			message=message,
			quota_awarded=self._as_int(data.get('quota_awarded')) or 0,
			checkin_date=self._as_text(data.get('checkin_date')),
			raw_payload=payload,
		)

	async def _request(
		self,
		method: str,
		path: str,
		json: dict[str, Any] | None = None,
		params: dict[str, Any] | None = None,
		include_user_header: bool = False,
		turnstile_token: str = '',
	) -> dict[str, Any]:
		headers: dict[str, str] = {}
		if include_user_header:
			if not self._user_id:
				return {
					'success': False,
					'message': 'Missing New-Api-User context',
					'error_code': 'auth_contract_mismatch',
				}
			headers['New-Api-User'] = self._user_id
		query = dict(params or {})
		if turnstile_token:
			query['turnstile'] = turnstile_token
		last_exception: Exception | None = None
		response = None
		for base_url in self._candidate_base_urls():
			url = f'{base_url}{path}'
			if query:
				url = f'{url}?{urlencode(query)}'
			try:
				response = await self._dispatch(method, url, json, headers)
			except requests.exceptions.RequestException as exc:
				last_exception = exc
				continue
			self._resolved_base_url = base_url
			break
		if response is None:
			return {
				'success': False,
				'message': self._connection_error_message(last_exception),
				'error_code': 'site_unreachable',
			}
		try:
			payload = response.json()
		except Exception as exc:
			return {'success': False, 'message': f'Invalid JSON response: {exc}', 'error_code': 'unexpected_response'}
		if isinstance(payload, dict):
			return payload
		return {'success': False, 'message': 'Unexpected response payload', 'error_code': 'unexpected_response'}

	def _candidate_base_urls(self) -> list[str]:
		if self._resolved_base_url:
			return [self._resolved_base_url]
		candidates = [self._base_url]
		parsed = urlsplit(self._base_url)
		hostname = (parsed.hostname or '').strip().lower()
		if hostname not in {'127.0.0.1', 'localhost', '::1'}:
			return candidates
		alternate_netloc = 'host.docker.internal'
		if parsed.port is not None:
			alternate_netloc = f'{alternate_netloc}:{parsed.port}'
		alternate = urlunsplit((parsed.scheme, alternate_netloc, parsed.path, '', ''))
		if alternate.rstrip('/') not in candidates:
			candidates.append(alternate.rstrip('/'))
		return candidates

	def _connection_error_message(self, exc: Exception | None) -> str:
		parsed = urlsplit(self._base_url)
		hostname = (parsed.hostname or '').strip().lower()
		if hostname in {'127.0.0.1', 'localhost', '::1'}:
			return (
				f'无法连接站点 {self._base_url}。当前控制面运行在 Docker 容器内，'
				'127.0.0.1/localhost 指向容器本身；请改用 host.docker.internal 或宿主机实际地址。'
			)
		if exc is None:
			return f'无法连接站点 {self._base_url}'
		return f'无法连接站点 {self._base_url}: {exc}'

	async def _dispatch(
		self,
		method: str,
		url: str,
		json: dict[str, Any] | None,
		headers: dict[str, str],
	):
		if method == 'GET':
			return await self._session.get(url, headers=headers)
		return await self._session.post(url, json=json, headers=headers)

	def _classify_auth_error(self, payload: dict[str, Any]) -> str:
		message = self._message(payload)
		if self._is_turnstile_message(message):
			return 'turnstile_required'
		if '会话' in message:
			return 'session_save_failed'
		return payload.get('error_code') or 'login_failed'

	def _classify_checkin_error(self, payload: dict[str, Any]) -> str:
		explicit = self._as_text(payload.get('error_code'))
		if explicit:
			return explicit
		message = self._message(payload)
		if self._is_auth_contract_message(message):
			return 'auth_contract_mismatch'
		if self._is_turnstile_message(message):
			return 'turnstile_required'
		if '今日已签到' in message:
			return 'already_checked'
		if '签到功能未启用' in message:
			return 'site_checkin_disabled'
		return 'unexpected_response'

	def _error_phase(self, error_code: str) -> CheckinPhase:
		if error_code == 'already_checked':
			return 'already_checked'
		if error_code == 'site_checkin_disabled':
			return 'site_checkin_disabled'
		if error_code == 'turnstile_required':
			return 'turnstile_required'
		return 'failed'

	def _extract_user_id(self, data: dict[str, Any]) -> str:
		raw_user_id = data.get('id')
		if raw_user_id is None:
			return ''
		return str(raw_user_id).strip()

	def _message(self, payload: dict[str, Any]) -> str:
		return self._as_text(payload.get('message'))

	def _is_turnstile_message(self, message: str) -> bool:
		return 'Turnstile' in message or 'turnstile' in message

	def _is_auth_contract_message(self, message: str) -> bool:
		normalized = message.lower()
		return (
			'user id' in normalized
			or 'not logged in' in normalized
			or 'missing new-api-user' in normalized
			or '未提供用户id' in normalized
			or '用户id' in normalized
			or '未登录' in normalized
			or '无权' in normalized
		)

	def _as_text(self, value: Any) -> str:
		if value is None:
			return ''
		return str(value).strip()

	def _as_int(self, value: Any) -> int | None:
		if value is None or value == '':
			return None
		try:
			return int(value)
		except (TypeError, ValueError):
			return None
