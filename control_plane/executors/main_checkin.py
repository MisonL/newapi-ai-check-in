from __future__ import annotations

import asyncio
import hashlib
import json
from contextlib import redirect_stderr, redirect_stdout

from checkin import CheckIn
from control_plane.models import JobSummary, MainCheckinConfig, NotificationConfig, SystemConfig
from control_plane.utils.env_scope import temporary_environ
from control_plane.utils.log_capture import LineCapture
from utils.balance_hash import load_balance_hash, save_balance_hash
from utils.config import AppConfig
from utils.notify import notify


BALANCE_HASH_FILE = "balance_hash.txt"


def _generate_balance_hash(balances: dict) -> str:
    simple_balances = {}
    for account_key, account_balances in balances.items():
        quota_list = [balance_info["quota"] for balance_info in account_balances.values()]
        simple_balances[account_key] = quota_list
    balance_json = json.dumps(simple_balances, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(balance_json.encode("utf-8")).hexdigest()[:16]


def _to_env(config: MainCheckinConfig, notifications: NotificationConfig, system: SystemConfig) -> dict[str, str]:
    env = {
        "ACCOUNTS": json.dumps(config.accounts, ensure_ascii=False),
        "PROVIDERS": json.dumps(config.providers, ensure_ascii=False),
        "ACCOUNTS_LINUX_DO": json.dumps(config.accounts_linux_do, ensure_ascii=False),
        "ACCOUNTS_GITHUB": json.dumps(config.accounts_github, ensure_ascii=False),
        "DEBUG": "true" if system.debug else "false",
        "BROWSER_ENABLED": "true" if system.browser_enabled else "false",
        "BROWSER_STRATEGY": system.browser_strategy,
    }
    if config.proxy:
        env["PROXY"] = json.dumps(config.proxy, ensure_ascii=False)
    notification_env_map = {
        "dingding_webhook": "DINGDING_WEBHOOK",
        "email_user": "EMAIL_USER",
        "email_pass": "EMAIL_PASS",
        "email_to": "EMAIL_TO",
        "custom_smtp_server": "CUSTOM_SMTP_SERVER",
        "pushplus_token": "PUSHPLUS_TOKEN",
        "server_push_key": "SERVERPUSHKEY",
        "feishu_webhook": "FEISHU_WEBHOOK",
        "weixin_webhook": "WEIXIN_WEBHOOK",
        "telegram_bot_token": "TELEGRAM_BOT_TOKEN",
        "telegram_chat_id": "TELEGRAM_CHAT_ID",
    }
    for key, value in notifications.model_dump().items():
        if value:
            env[notification_env_map[key]] = value
    return env


async def run_main_checkin(
    main_config: MainCheckinConfig,
    notifications: NotificationConfig,
    system_config: SystemConfig,
    storage_states_dir: str,
    emit_log,
) -> JobSummary:
    env = _to_env(main_config, notifications, system_config)
    with temporary_environ(env):
        app_config = AppConfig.load_from_env()
        if not app_config.accounts:
            raise ValueError("No account configuration available")
        if not system_config.browser_enabled:
            for account in app_config.accounts:
                provider = app_config.get_provider(account.provider)
                if provider is None:
                    continue
                needs_browser = bool(account.linux_do or account.github)
                needs_browser = needs_browser or provider.aliyun_captcha
                needs_browser = needs_browser or provider.needs_waf_cookies()
                needs_browser = needs_browser or provider.needs_cf_clearance()
                if needs_browser:
                    raise ValueError(
                        f"Provider {account.provider} requires browser support. "
                        "Enable browser execution or switch to cookie-only accounts."
                    )

        last_balance_hash = load_balance_hash(BALANCE_HASH_FILE)
        success_count = 0
        total_count = 0
        notification_content: list[str] = []
        current_balances: dict[str, dict] = {}
        need_notify = False

        for index, account_config in enumerate(app_config.accounts):
            account_key = f"account_{index + 1}"
            account_name = account_config.get_display_name(index)
            if notification_content:
                notification_content.append("\n-------------------------------")
            provider_config = app_config.get_provider(account_config.provider)
            if provider_config is None:
                need_notify = True
                notification_content.append(f"[FAIL] {account_name}: provider not found")
                continue
            checkin = CheckIn(
                account_name,
                account_config,
                provider_config,
                global_proxy=app_config.global_proxy,
                storage_state_dir=storage_states_dir,
            )
            results = await checkin.execute()
            total_count += len(results)
            account_success = False
            successful_methods: list[str] = []
            failed_methods: list[str] = []
            this_account_balances: dict[str, dict] = {}
            account_result = f"{account_name} Summary:\n"
            for auth_method, success, user_info in results:
                status = "SUCCESS" if success else "FAILED"
                account_result += f"  {status} with {auth_method}\n"
                if success and user_info and user_info.get("success"):
                    account_success = True
                    success_count += 1
                    successful_methods.append(auth_method)
                    account_result += f"    {user_info['display']}\n"
                    this_account_balances[auth_method] = {
                        "quota": user_info["quota"],
                        "used": user_info["used_quota"],
                        "bonus": user_info["bonus_quota"],
                    }
                else:
                    failed_methods.append(auth_method)
                    error_message = user_info.get("error", "Unknown error") if user_info else "Unknown error"
                    account_result += f"    {error_message}\n"
            if account_success:
                current_balances[account_key] = this_account_balances
            if failed_methods:
                need_notify = True
            account_result += f"\nStatistics: {len(successful_methods)}/{len(results)} methods successful"
            notification_content.append(account_result)

        current_balance_hash = _generate_balance_hash(current_balances) if current_balances else None
        if current_balance_hash:
            if last_balance_hash is None or current_balance_hash != last_balance_hash:
                need_notify = True
            save_balance_hash(BALANCE_HASH_FILE, current_balance_hash)

        notification_sent = False
        if need_notify and notification_content:
            body = "\n\n".join(notification_content)
            notify.push_message("Check-in Alert", body, msg_type="text")
            notification_sent = True
            emit_log("Notification sent")

        return JobSummary(
            success_count=success_count,
            total_count=total_count,
            notification_sent=notification_sent,
            balances=current_balances,
            extra={"balance_hash": current_balance_hash or ""},
        )


async def execute_main_checkin(
    main_config: MainCheckinConfig,
    notifications: NotificationConfig,
    system_config: SystemConfig,
    storage_states_dir: str,
    emit_log,
) -> JobSummary:
    stdout_capture = LineCapture(lambda line: emit_log(line, "stdout"))
    stderr_capture = LineCapture(lambda line: emit_log(line, "stderr"))
    with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
        return await run_main_checkin(main_config, notifications, system_config, storage_states_dir, emit_log)
