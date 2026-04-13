from __future__ import annotations

import io
from contextlib import redirect_stdout

from checkin import CheckIn
from control_plane.models import ConfigDomain, MainCheckinConfig, SystemConfig
from control_plane.services.newapi_checkin_service import NewApiTaskExecutionResult
from control_plane.settings import settings
from control_plane.storage.base import StorageBackend
from control_plane.task_center_models import AccountRecord, SiteRecord
from utils.config import AccountConfig, AppConfig, OAuthAccountConfig, ProviderConfig


class LegacyOAuthExecutor:
    def __init__(self, storage: StorageBackend) -> None:
        self._storage = storage

    async def run(self, site: SiteRecord, account: AccountRecord) -> NewApiTaskExecutionResult:
        system_config = SystemConfig.model_validate(self._storage.load_config(ConfigDomain.SYSTEM))
        if not system_config.browser_enabled:
            return NewApiTaskExecutionResult(
                task_status='blocked',
                account_status='blocked',
                executor_type='legacy_plugin',
                error_code='browser_auth_disabled',
                error_message='OAuth 兼容执行需要启用浏览器能力',
            )
        provider = self._resolve_provider(site)
        if provider is None:
            return NewApiTaskExecutionResult(
                task_status='failed',
                account_status='failed',
                executor_type='legacy_plugin',
                error_code='provider_not_found',
                error_message='未找到站点对应的 provider 配置',
            )
        account_config = self._build_account_config(site, account)
        checkin = CheckIn(
            account.display_name or account.username,
            account_config,
            provider,
            global_proxy=self._main_config().proxy,
            storage_state_dir=str(settings.storage_states_dir),
        )
        results = await checkin.execute()
        if not results:
            return NewApiTaskExecutionResult(
                task_status='failed',
                account_status='failed',
                executor_type='legacy_plugin',
                error_code='unexpected_response',
                error_message='Legacy OAuth executor returned no result',
            )
        auth_method, success, user_info = results[0]
        payload = user_info or {}
        if success:
            return NewApiTaskExecutionResult(
                task_status='success',
                account_status='success',
                executor_type='legacy_plugin',
                raw_checkin_payload={'auth_method': auth_method, 'user_info': payload},
            )
        return NewApiTaskExecutionResult(
            task_status='failed',
            account_status='failed',
            executor_type='legacy_plugin',
            error_code='legacy_oauth_failed',
            error_message=str(payload.get('error', 'Legacy OAuth authentication failed')),
            raw_checkin_payload={'auth_method': auth_method, 'user_info': payload},
        )

    def _main_config(self) -> MainCheckinConfig:
        return MainCheckinConfig.model_validate(self._storage.load_config(ConfigDomain.MAIN_CHECKIN))

    def _provider_catalog(self) -> dict[str, ProviderConfig]:
        with redirect_stdout(io.StringIO()):
            providers = AppConfig._load_providers('__TASK_CENTER_OAUTH_UNUSED__')
        main_config = self._main_config()
        for name, payload in main_config.providers.items():
            try:
                providers[name] = ProviderConfig.from_dict(name, payload, is_customize=True)
            except Exception:
                continue
        return providers

    def _resolve_provider(self, site: SiteRecord) -> ProviderConfig | None:
        providers = self._provider_catalog()
        provider = providers.get(site.name)
        if provider is not None:
            return provider
        for item in providers.values():
            if item.origin.rstrip('/') == site.base_url.rstrip('/'):
                return item
        return None

    def _build_account_config(self, site: SiteRecord, account: AccountRecord) -> AccountConfig:
        provider_name = site.name
        if account.auth_mode == 'github_oauth':
            return AccountConfig(
                provider=provider_name,
                name=account.display_name or account.username,
                github=[OAuthAccountConfig(username=account.username, password=account.password)],
            )
        if account.auth_mode == 'linuxdo_oauth':
            return AccountConfig(
                provider=provider_name,
                name=account.display_name or account.username,
                linux_do=[OAuthAccountConfig(username=account.username, password=account.password)],
            )
        raise ValueError(f'Unsupported auth mode: {account.auth_mode}')
