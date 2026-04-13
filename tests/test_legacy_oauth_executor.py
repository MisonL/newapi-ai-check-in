from __future__ import annotations

import asyncio

from control_plane.models import ConfigDomain
from control_plane.services.legacy_oauth_executor import LegacyOAuthExecutor
from control_plane.storage.memory import MemoryStorage
from control_plane.task_center_models import AccountRecord, SiteRecord


def test_legacy_oauth_executor_blocks_when_browser_disabled(tmp_path):
    storage = MemoryStorage(tmp_path / 'artifacts')
    storage.save_config(
        ConfigDomain.SYSTEM,
        {
            'debug': False,
            'browser_strategy': 'legacy',
            'browser_enabled': False,
            'main_checkin_engine': 'legacy',
            'admin_password_hash': '',
        },
    )
    storage.save_config(ConfigDomain.MAIN_CHECKIN, {'providers': {}, 'accounts': []})
    site = SiteRecord(name='custom-provider', base_url='https://example.com')
    account = AccountRecord(
        site_id=site.id,
        username='octocat',
        auth_mode='github_oauth',
        password='oauth-pass',
    )

    result = asyncio.run(LegacyOAuthExecutor(storage).run(site, account))
    assert result.task_status == 'blocked'
    assert result.error_code == 'browser_auth_disabled'


def test_legacy_oauth_executor_resolves_provider_and_maps_failure(monkeypatch, tmp_path):
    storage = MemoryStorage(tmp_path / 'artifacts')
    storage.save_config(
        ConfigDomain.SYSTEM,
        {
            'debug': False,
            'browser_strategy': 'legacy',
            'browser_enabled': True,
            'main_checkin_engine': 'legacy',
            'admin_password_hash': '',
        },
    )
    storage.save_config(
        ConfigDomain.MAIN_CHECKIN,
        {
            'providers': {'custom-provider': {'origin': 'https://example.com', 'linuxdo_client_id': 'abc'}},
            'accounts': [],
        },
    )
    site = SiteRecord(name='custom-provider', base_url='https://example.com')
    account = AccountRecord(
        site_id=site.id,
        username='octocat',
        auth_mode='linuxdo_oauth',
        password='oauth-pass',
    )

    async def fake_execute(self):
        return [('linux.do', False, {'error': 'OAuth callback failed'})]

    monkeypatch.setattr('checkin.CheckIn.execute', fake_execute)

    result = asyncio.run(LegacyOAuthExecutor(storage).run(site, account))
    assert result.task_status == 'failed'
    assert result.executor_type == 'legacy_plugin'
    assert result.error_code == 'legacy_oauth_failed'
