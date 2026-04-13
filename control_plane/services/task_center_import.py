from __future__ import annotations

import io
from contextlib import redirect_stdout
from datetime import datetime, timezone
from typing import Any

from control_plane.models import ConfigDomain, MainCheckinConfig
from control_plane.storage.base import StorageBackend
from control_plane.task_center_models import AccountRecord, SiteRecord, TaskCenterImportResult
from utils.config import AppConfig, OAuthAccountConfig, ProviderConfig


class TaskCenterMainCheckinImporter:
    def __init__(self, storage: StorageBackend) -> None:
        self._storage = storage

    def run(self) -> TaskCenterImportResult:
        config = MainCheckinConfig.model_validate(self._storage.load_config(ConfigDomain.MAIN_CHECKIN))
        provider_catalog, provider_messages = self._provider_catalog(config)
        provider_names = self._provider_names(config)
        result = TaskCenterImportResult(
            total_providers=len(provider_names),
            total_accounts=len(config.accounts),
            messages=provider_messages,
        )
        global_github_accounts = self._normalize_oauth_accounts(config.accounts_github)
        global_linuxdo_accounts = self._normalize_oauth_accounts(config.accounts_linux_do)
        existing_sites = self._storage.list_sites()
        sites_by_base_url = {site.base_url: site for site in existing_sites}
        sites_by_name = {site.name: site for site in existing_sites}
        provider_site_ids: dict[str, str] = {}
        for provider_name in sorted(provider_names):
            provider = provider_catalog.get(provider_name)
            if provider is None:
                result.messages.append(f"Provider {provider_name} 无法解析，已跳过站点导入")
                continue
            site, created, updated = self._upsert_site(provider_name, provider, sites_by_base_url, sites_by_name)
            provider_site_ids[provider_name] = site.id
            result.created_sites += int(created)
            result.updated_sites += int(updated)
            sites_by_base_url[site.base_url] = site
            sites_by_name[site.name] = site
        accounts_by_key = {self._account_key(account): account for account in self._storage.list_accounts()}
        for index, payload in enumerate(config.accounts, start=1):
            provider_name = self._account_provider(payload)
            site_id = provider_site_ids.get(provider_name)
            display_name = self._account_display_name(payload, index)
            if site_id is None:
                result.skipped_accounts += 1
                result.messages.append(f"账号 {display_name} 未找到 provider {provider_name} 对应站点，已跳过")
                continue
            account_payloads = self._build_account_payloads(
                payload,
                site_id,
                index,
                global_github_accounts,
                global_linuxdo_accounts,
            )
            if not account_payloads:
                result.skipped_accounts += 1
                result.messages.append(f"账号 {display_name} 缺少可导入的认证信息，已跳过")
                continue
            for account_payload in account_payloads:
                existing = accounts_by_key.get(self._account_key_from_payload(account_payload))
                if existing is None:
                    account = AccountRecord(**account_payload)
                    self._storage.save_account(account)
                    accounts_by_key[self._account_key(account)] = account
                    result.created_accounts += 1
                    continue
                updates: dict[str, Any] = {}
                for key in ("display_name", "auth_mode", "password", "api_user", "session_cookies"):
                    if existing.model_dump().get(key) != account_payload.get(key):
                        updates[key] = account_payload.get(key)
                if updates:
                    updates["updated_at"] = datetime.now(timezone.utc)
                    updated_account = existing.model_copy(update=updates)
                    self._storage.save_account(updated_account)
                    accounts_by_key[self._account_key(updated_account)] = updated_account
                    result.updated_accounts += 1
        return result

    def _provider_catalog(self, config: MainCheckinConfig) -> tuple[dict[str, ProviderConfig], list[str]]:
        with redirect_stdout(io.StringIO()):
            providers = AppConfig._load_providers("__TASK_CENTER_IMPORT_UNUSED__")
        messages: list[str] = []
        for name, payload in config.providers.items():
            try:
                providers[name] = ProviderConfig.from_dict(name, payload, is_customize=True)
            except Exception as exc:
                messages.append(f"Provider {name} 配置无效: {exc}")
        return providers, messages

    def _provider_names(self, config: MainCheckinConfig) -> set[str]:
        names = set(config.providers.keys())
        for payload in config.accounts:
            names.add(self._account_provider(payload))
        return {name for name in names if name}

    def _account_provider(self, payload: dict[str, Any]) -> str:
        provider_name = payload.get("provider", "anyrouter")
        if not isinstance(provider_name, str):
            return "anyrouter"
        return provider_name.strip() or "anyrouter"

    def _account_display_name(self, payload: dict[str, Any], index: int) -> str:
        name = payload.get("name")
        if isinstance(name, str) and name.strip():
            return name.strip()
        return f"{self._account_provider(payload)} {index}"

    def _build_account_payloads(
        self,
        payload: dict[str, Any],
        site_id: str,
        index: int,
        global_github_accounts: list[OAuthAccountConfig],
        global_linuxdo_accounts: list[OAuthAccountConfig],
    ) -> list[dict[str, Any]]:
        display_name = self._account_display_name(payload, index)
        account_payloads: list[dict[str, Any]] = []
        username = payload.get("username")
        password = payload.get("password")
        if isinstance(username, str) and isinstance(password, str):
            normalized_username = username.strip()
            normalized_password = password.strip()
            if normalized_username and normalized_password:
                account_payloads.append({
                    "site_id": site_id,
                    "display_name": display_name,
                    "username": normalized_username,
                    "auth_mode": "password",
                    "password": normalized_password,
                })
        cookies = payload.get("cookies")
        api_user = payload.get("api_user")
        if isinstance(cookies, dict) and isinstance(api_user, str):
            normalized_api_user = api_user.strip()
            normalized_cookies = {
                str(key).strip(): str(value).strip()
                for key, value in cookies.items()
                if str(key).strip() and str(value).strip()
            }
            if normalized_api_user and normalized_cookies:
                account_payloads.append({
                    "site_id": site_id,
                    "display_name": display_name,
                    "username": f"cookie-{normalized_api_user}",
                    "auth_mode": "cookies",
                    "api_user": normalized_api_user,
                    "session_cookies": normalized_cookies,
                })
        account_payloads.extend(
            self._build_oauth_payloads(
                payload.get("github"),
                global_github_accounts,
                site_id,
                display_name,
                "github_oauth",
                "github",
            )
        )
        account_payloads.extend(
            self._build_oauth_payloads(
                payload.get("linux.do"),
                global_linuxdo_accounts,
                site_id,
                display_name,
                "linuxdo_oauth",
                "linux.do",
            )
        )
        return account_payloads

    def _build_oauth_payloads(
        self,
        config_value: Any,
        global_accounts: list[OAuthAccountConfig],
        site_id: str,
        display_name: str,
        auth_mode: str,
        label: str,
    ) -> list[dict[str, Any]]:
        oauth_accounts = self._resolve_oauth_accounts(config_value, global_accounts)
        payloads: list[dict[str, Any]] = []
        for account in oauth_accounts:
            payloads.append(
                {
                    "site_id": site_id,
                    "display_name": f"{display_name} [{label}:{account.username}]",
                    "username": account.username,
                    "auth_mode": auth_mode,
                    "password": account.password,
                }
            )
        return payloads

    def _normalize_oauth_accounts(self, items: list[dict[str, str]]) -> list[OAuthAccountConfig]:
        accounts: list[OAuthAccountConfig] = []
        for item in items:
            username = str(item.get("username", "")).strip()
            password = str(item.get("password", "")).strip()
            if username and password:
                accounts.append(OAuthAccountConfig(username=username, password=password))
        return accounts

    def _resolve_oauth_accounts(
        self,
        config_value: Any,
        global_accounts: list[OAuthAccountConfig],
    ) -> list[OAuthAccountConfig]:
        if isinstance(config_value, bool):
            return list(global_accounts) if config_value else []
        if isinstance(config_value, dict):
            normalized = self._normalize_oauth_accounts([config_value])
            return normalized
        if isinstance(config_value, list):
            normalized = self._normalize_oauth_accounts(config_value)
            return normalized
        return []

    def _account_key(self, account: AccountRecord) -> tuple[str, str, str]:
        if account.auth_mode == "cookies":
            return (account.site_id, account.auth_mode, account.api_user)
        return (account.site_id, account.auth_mode, account.username)

    def _account_key_from_payload(self, payload: dict[str, Any]) -> tuple[str, str, str]:
        auth_mode = str(payload.get("auth_mode", "password"))
        identity_key = "api_user" if auth_mode == "cookies" else "username"
        return (str(payload["site_id"]), auth_mode, str(payload.get(identity_key, "")).strip())

    def _upsert_site(
        self,
        provider_name: str,
        provider: ProviderConfig,
        sites_by_base_url: dict[str, SiteRecord],
        sites_by_name: dict[str, SiteRecord],
    ) -> tuple[SiteRecord, bool, bool]:
        note = f"Legacy provider key: {provider_name}"
        compatibility = self._compatibility_level(provider)
        existing = sites_by_base_url.get(provider.origin) or sites_by_name.get(provider_name)
        if existing is None:
            site = SiteRecord(
                name=provider_name,
                base_url=provider.origin,
                compatibility_level=compatibility,
                notes=note,
            )
            self._storage.save_site(site)
            return site, True, False
        updates: dict[str, Any] = {}
        if existing.name != provider_name:
            updates["name"] = provider_name
        if existing.base_url != provider.origin:
            updates["base_url"] = provider.origin
        if existing.compatibility_level != compatibility:
            updates["compatibility_level"] = compatibility
        if not existing.notes:
            updates["notes"] = note
        if not updates:
            return existing, False, False
        updates["updated_at"] = datetime.now(timezone.utc)
        site = existing.model_copy(update=updates)
        self._storage.save_site(site)
        return site, False, True

    def _compatibility_level(self, provider: ProviderConfig) -> str:
        if provider.aliyun_captcha or provider.needs_waf_cookies() or provider.needs_cf_clearance():
            return "browser"
        if provider.check_in_path == "/api/user/checkin" and provider.check_in_status is True:
            return "standard"
        return "legacy"
