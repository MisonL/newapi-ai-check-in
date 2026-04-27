from __future__ import annotations

import asyncio
from dataclasses import dataclass

from curl_cffi import requests

from control_plane.services.newapi_client import NewApiClient


class FakeCookieJar:
	def __init__(self) -> None:
		self.items: list[tuple[str, str, str, str]] = []

	def set(self, key: str, value: str, domain: str = '', path: str = '/'):
		self.items.append((key, value, domain, path))


@dataclass
class FakeResponse:
	payload: dict

	def json(self):
		return self.payload


class FakeSession:
	def __init__(self, responses: list[FakeResponse]) -> None:
		self._responses = responses
		self.calls: list[tuple[str, str, dict | None, dict[str, str]]] = []
		self.cookies = FakeCookieJar()

	async def get(self, url: str, headers: dict[str, str] | None = None):
		self.calls.append(('GET', url, None, headers or {}))
		return self._responses.pop(0)

	async def post(self, url: str, json: dict | None = None, headers: dict[str, str] | None = None):
		self.calls.append(('POST', url, json, headers or {}))
		return self._responses.pop(0)

	async def close(self):
		return None


class FallbackSession(FakeSession):
	def __init__(self, responses: list[FakeResponse]) -> None:
		super().__init__(responses)
		self.failed_once = False

	async def post(self, url: str, json: dict | None = None, headers: dict[str, str] | None = None):
		self.calls.append(('POST', url, json, headers or {}))
		if not self.failed_once and '127.0.0.1' in url:
			self.failed_once = True
			raise requests.exceptions.ConnectionError('connect failed')
		if not self._responses:
			raise requests.exceptions.ConnectionError('connect failed')
		return self._responses.pop(0)


def test_newapi_client_login_and_status_attach_new_api_user_header():
	session = FakeSession(
		[
			FakeResponse(
				{
					'success': True,
					'message': '',
					'data': {'id': 42, 'username': 'alice', 'display_name': 'Alice'},
				}
			),
			FakeResponse(
				{
					'success': True,
					'message': '',
					'data': {
						'enabled': True,
						'min_quota': 10,
						'max_quota': 20,
						'stats': {
							'total_quota': 1234,
							'total_checkins': 5,
							'checkin_count': 2,
							'checked_in_today': True,
							'records': [],
						},
					},
				}
			),
		]
	)

	async def run():
		client = NewApiClient('https://example.com', session=session)
		auth = await client.login('alice', 'secret-pass')
		status = await client.get_checkin_status('2026-04')
		await client.aclose()
		return auth, status

	auth, status = asyncio.run(run())
	assert auth.phase == 'login_success'
	assert auth.user_id == '42'
	assert status.success is True
	assert status.checked_in_today is True
	assert session.calls[1][3]['New-Api-User'] == '42'
	assert session.calls[1][1] == 'https://example.com/api/user/checkin?month=2026-04'


def test_newapi_client_login_returns_two_factor_required():
	session = FakeSession(
		[
			FakeResponse(
				{
					'success': True,
					'message': '需要两步验证',
					'data': {'require_2fa': True},
				}
			),
			FakeResponse(
				{
					'success': True,
					'message': '',
					'data': {'id': 7, 'username': 'bob', 'display_name': 'Bob'},
				}
			),
		]
	)

	async def run():
		client = NewApiClient('https://example.com', session=session)
		first = await client.login('bob', 'secret-pass')
		second = await client.verify_two_factor('123456')
		return first, second

	first, second = asyncio.run(run())
	assert first.phase == 'two_factor_required'
	assert first.success is False
	assert second.phase == 'login_success'
	assert second.user_id == '7'


def test_newapi_client_checkin_maps_already_checked_and_turnstile():
	session = FakeSession(
		[
			FakeResponse({'success': False, 'message': '今日已签到'}),
			FakeResponse({'success': False, 'message': 'Turnstile token 为空'}),
		]
	)

	async def run():
		client = NewApiClient('https://example.com', session=session)
		client._user_id = '99'
		first = await client.do_checkin()
		second = await client.do_checkin('token-1')
		return first, second

	first, second = asyncio.run(run())
	assert first.phase == 'already_checked'
	assert first.error_code == 'already_checked'
	assert second.phase == 'turnstile_required'
	assert 'turnstile=token-1' in session.calls[1][1]


def test_newapi_client_checkin_maps_site_disabled():
	session = FakeSession([FakeResponse({'success': False, 'message': '签到功能未启用'})])

	async def run():
		client = NewApiClient('https://example.com', session=session)
		client._user_id = '99'
		return await client.do_checkin()

	result = asyncio.run(run())
	assert result.phase == 'site_checkin_disabled'
	assert result.error_code == 'site_checkin_disabled'


def test_newapi_client_rejects_missing_new_api_user_context():
	session = FakeSession([])

	async def run():
		client = NewApiClient('https://example.com', session=session)
		return await client.get_checkin_status()

	result = asyncio.run(run())
	assert result.success is False
	assert result.error_code == 'auth_contract_mismatch'


def test_newapi_client_can_bootstrap_cookie_session():
	session = FakeSession([])
	client = NewApiClient('https://example.com', session=session)

	client.bootstrap_session('42', {'session': 'abc'})

	assert client.user_id == '42'
	assert session.cookies.items == [('session', 'abc', 'example.com', '/')]


def test_newapi_client_retries_loopback_host_with_host_docker_internal():
	session = FallbackSession(
		[
			FakeResponse(
				{
					'success': True,
					'message': '',
					'data': {'id': 42, 'username': 'alice', 'display_name': 'Alice'},
				}
			),
			FakeResponse(
				{
					'success': True,
					'message': '',
					'data': {
						'enabled': True,
						'min_quota': 10,
						'max_quota': 20,
						'stats': {
							'total_quota': 1234,
							'total_checkins': 5,
							'checkin_count': 0,
							'checked_in_today': False,
							'records': [],
						},
					},
				}
			),
		]
	)

	async def run():
		client = NewApiClient('http://127.0.0.1:3001', session=session)
		auth = await client.login('alice', 'secret-pass')
		status = await client.get_checkin_status()
		await client.aclose()
		return auth, status

	auth, status = asyncio.run(run())
	assert auth.success is True
	assert status.success is True
	assert session.calls[0][1] == 'http://127.0.0.1:3001/api/user/login'
	assert session.calls[1][1] == 'http://host.docker.internal:3001/api/user/login'
	assert session.calls[2][1] == 'http://host.docker.internal:3001/api/user/checkin'


def test_newapi_client_returns_site_unreachable_when_loopback_remains_unreachable():
	session = FallbackSession([])

	async def run():
		client = NewApiClient('http://127.0.0.1:3001', session=session)
		return await client.login('alice', 'secret-pass')

	auth = asyncio.run(run())
	assert auth.success is False
	assert auth.error_code == 'site_unreachable'
	assert 'Docker 容器内' in auth.message


def test_newapi_client_probe_checkin_endpoint_accepts_auth_contract_response():
	session = FakeSession([FakeResponse({'success': False, 'message': '未提供用户ID'})])

	async def run():
		client = NewApiClient('https://example.com', session=session)
		result = await client.probe_checkin_endpoint()
		await client.aclose()
		return result

	result = asyncio.run(run())
	assert result.success is False
	assert result.error_code == 'auth_contract_mismatch'
	assert session.calls[0][0] == 'GET'
	assert session.calls[0][1] == 'https://example.com/api/user/checkin'
