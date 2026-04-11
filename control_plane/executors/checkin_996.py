from __future__ import annotations

import hashlib
import json
from contextlib import redirect_stderr, redirect_stdout

from checkin_996.checkin import CheckIn
from control_plane.executors.common import notification_env
from control_plane.models import Checkin996Config, JobSummary, NotificationConfig
from control_plane.utils.env_scope import temporary_environ
from control_plane.utils.log_capture import LineCapture
from utils.balance_hash import load_balance_hash, save_balance_hash
from utils.notify import notify

BALANCE_HASH_FILE = "balance_hash_996.txt"


def _generate_checkin_hash(checkin_results: dict[str, dict]) -> str:
    if not checkin_results:
        return ""
    all_rewards = {account_key: info.get("total_rewards_usd", "0") for account_key, info in checkin_results.items() if info}
    rewards_json = json.dumps(all_rewards, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(rewards_json.encode("utf-8")).hexdigest()[:16]


async def run_checkin_996(config: Checkin996Config, notifications: NotificationConfig, emit_log) -> JobSummary:
    if not config.accounts:
        raise ValueError("No 996 accounts configured")

    success_count = 0
    total_count = len(config.accounts)
    notification_lines: list[str] = []
    current_results: dict[str, dict] = {}

    with temporary_environ(notification_env(notifications)):
        last_hash = load_balance_hash(BALANCE_HASH_FILE)

        for index, token in enumerate(config.accounts):
            account_name = f"account_{index + 1}"
            if notification_lines:
                notification_lines.append("\n-------------------------------")
            checkin = CheckIn(account_name, global_proxy=config.proxy)
            success, result = await checkin.execute(token)
            if success:
                success_count += 1
                current_results[account_name] = result
                notification_lines.append(
                    "  {name}: continuous_days={days} total_checkins={count} total_rewards_usd={reward}".format(
                        name=account_name,
                        days=result.get("continuous_days", 0),
                        count=result.get("total_checkins", 0),
                        reward=result.get("total_rewards_usd", "0"),
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
                "996 hub Check-in Alert",
                "\n\n".join(["Check-in details:\n" + "\n".join(notification_lines), "\n".join(summary_lines)]),
                msg_type="text",
            )
            notification_sent = True
            emit_log("996 notification dispatched")

    return JobSummary(
        success_count=success_count,
        total_count=total_count,
        notification_sent=notification_sent,
        extra={
            "checkin_hash": current_hash,
            "accounts": current_results,
        },
    )


async def execute_checkin_996(config: Checkin996Config, notifications: NotificationConfig, emit_log) -> JobSummary:
    stdout_capture = LineCapture(lambda line: emit_log(line, "stdout"))
    stderr_capture = LineCapture(lambda line: emit_log(line, "stderr"))
    with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
        return await run_checkin_996(config, notifications, emit_log)
