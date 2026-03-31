from __future__ import annotations

import hashlib
import json
from contextlib import redirect_stderr, redirect_stdout

from checkin_qaq_al.checkin import CheckIn
from control_plane.executors.common import notification_env
from control_plane.models import CheckinQaqAlConfig, JobSummary, NotificationConfig, SystemConfig
from control_plane.utils.env_scope import temporary_environ
from control_plane.utils.log_capture import LineCapture
from utils.balance_hash import load_balance_hash, save_balance_hash
from utils.notify import notify


BALANCE_HASH_FILE = "balance_hash_qaq_al.txt"


def _generate_checkin_hash(results: dict[str, dict]) -> str:
    if not results:
        return ""
    rewards = {account_key: info.get("reward_final", "0") for account_key, info in results.items() if info}
    payload = json.dumps(rewards, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


async def run_checkin_qaq_al(
    config: CheckinQaqAlConfig,
    notifications: NotificationConfig,
    system_config: SystemConfig,
    emit_log,
) -> JobSummary:
    if not config.accounts:
        raise ValueError("No qaq.al accounts configured")
    if not system_config.browser_enabled:
        raise ValueError("qaq.al check-in requires browser support. Enable browser execution first.")

    success_count = 0
    total_count = len(config.accounts)
    notification_lines: list[str] = []
    current_results: dict[str, dict] = {}

    with temporary_environ(notification_env(notifications)):
        last_hash = load_balance_hash(BALANCE_HASH_FILE)

        for index, sid in enumerate(config.accounts):
            account_name = f"account_{index + 1}"
            if notification_lines:
                notification_lines.append("\n-------------------------------")
            checkin = CheckIn(account_name, global_proxy=config.proxy)
            success, result = await checkin.execute(sid, tier=config.tier)
            if success:
                success_count += 1
                current_results[account_name] = result
                if result.get("already_signed"):
                    notification_lines.append(
                        f"  {account_name}: already_signed reward={result.get('reward_final', '?')} tier={result.get('tier_name', '')}"
                    )
                else:
                    notification_lines.append(
                        "  {name}: reward={reward} tier={tier} pow_elapsed={elapsed}s pow_hps={hps}".format(
                            name=account_name,
                            reward=result.get("reward_final", "?"),
                            tier=result.get("tier_name", ""),
                            elapsed=result.get("pow_elapsed", "?"),
                            hps=result.get("pow_hps", 0),
                        )
                    )
            else:
                notification_lines.append(f"  {account_name}: {result.get('error', 'Unknown error')}")

        current_hash = _generate_checkin_hash(current_results)
        need_notify = not last_hash or current_hash != last_hash or success_count != total_count
        if current_hash:
            save_balance_hash(BALANCE_HASH_FILE, current_hash)

        notification_sent = False
        if need_notify and notification_lines:
            summary_lines = [
                "Check-in result statistics:",
                f"Success: {success_count}/{total_count}",
                f"Failed: {total_count - success_count}/{total_count}",
            ]
            notify.push_message(
                "qaq.al Check-in Alert",
                "\n\n".join(["Check-in details:\n" + "\n".join(notification_lines), "\n".join(summary_lines)]),
                msg_type="text",
            )
            notification_sent = True
            emit_log("qaq.al notification dispatched")

    return JobSummary(
        success_count=success_count,
        total_count=total_count,
        notification_sent=notification_sent,
        extra={
            "checkin_hash": current_hash,
            "tier": config.tier,
            "accounts": current_results,
        },
    )


async def execute_checkin_qaq_al(
    config: CheckinQaqAlConfig,
    notifications: NotificationConfig,
    system_config: SystemConfig,
    emit_log,
) -> JobSummary:
    stdout_capture = LineCapture(lambda line: emit_log(line, "stdout"))
    stderr_capture = LineCapture(lambda line: emit_log(line, "stderr"))
    with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
        return await run_checkin_qaq_al(config, notifications, system_config, emit_log)
