from __future__ import annotations

import asyncio
from dataclasses import dataclass

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
