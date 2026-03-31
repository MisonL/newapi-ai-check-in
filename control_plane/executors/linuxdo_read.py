from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout

from control_plane.executors.common import notification_env
from control_plane.models import JobSummary, LinuxDoReadConfig, NotificationConfig, SystemConfig
from control_plane.utils.env_scope import temporary_environ
from control_plane.utils.log_capture import LineCapture
from linuxdo_read_posts import LinuxDoReadPosts
from utils.mask_utils import mask_username
from utils.notify import notify


def _linuxdo_env(config: LinuxDoReadConfig, notifications: NotificationConfig) -> dict[str, str]:
    env = notification_env(notifications)
    if config.base_topic_id is not None:
        env["LINUXDO_BASE_TOPIC_ID"] = str(config.base_topic_id)
    env["LINUXDO_MAX_POSTS"] = str(config.max_posts)
    return env


async def run_linuxdo_read(
    config: LinuxDoReadConfig,
    notifications: NotificationConfig,
    system_config: SystemConfig,
    storage_states_dir: str,
    emit_log,
) -> JobSummary:
    if not config.accounts:
        raise ValueError("No Linux.do read accounts configured")
    if not system_config.browser_enabled:
        raise ValueError("Linux.do read requires browser support. Enable browser execution first.")

    seen_usernames: set[str] = set()
    unique_accounts = []
    for account in config.accounts:
        if account.username in seen_usernames:
            emit_log(f"Skip duplicate Linux.do account: {mask_username(account.username)}")
            continue
        seen_usernames.add(account.username)
        unique_accounts.append(account)

    success_count = 0
    results: list[dict[str, object]] = []
    total_read_count = 0

    with temporary_environ(_linuxdo_env(config, notifications)):
        for account in unique_accounts:
            reader = LinuxDoReadPosts(
                username=account.username,
                password=account.password,
                storage_state_dir=storage_states_dir,
            )
            success, result = await reader.run()
            if success:
                success_count += 1
                total_read_count += int(result.get("read_count", 0))
            results.append(
                {
                    "username": account.username,
                    "success": success,
                    "result": result,
                }
            )

        notification_sent = False
        if results:
            notification_lines = []
            for item in results:
                masked_username = mask_username(str(item["username"]))
                result = item["result"] if isinstance(item["result"], dict) else {}
                if item["success"]:
                    notification_lines.append(
                        f"{masked_username}: read_count={result.get('read_count', 0)} "
                        f"last_topic_id={result.get('last_topic_id', 'unknown')}"
                    )
                else:
                    notification_lines.append(f"{masked_username}: {result.get('error', 'Unknown error')}")
            notification_lines.append(f"Total read: {total_read_count}")
            notify.push_message("Linux.do Read Posts", "\n".join(notification_lines), msg_type="text")
            notification_sent = True
            emit_log("Linux.do notification dispatched")

    return JobSummary(
        success_count=success_count,
        total_count=len(unique_accounts),
        notification_sent=notification_sent,
        extra={
            "total_read_count": total_read_count,
            "results": results,
        },
    )


async def execute_linuxdo_read(
    config: LinuxDoReadConfig,
    notifications: NotificationConfig,
    system_config: SystemConfig,
    storage_states_dir: str,
    emit_log,
) -> JobSummary:
    stdout_capture = LineCapture(lambda line: emit_log(line, "stdout"))
    stderr_capture = LineCapture(lambda line: emit_log(line, "stderr"))
    with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
        return await run_linuxdo_read(config, notifications, system_config, storage_states_dir, emit_log)
