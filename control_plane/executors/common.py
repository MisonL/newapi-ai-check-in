from __future__ import annotations

from control_plane.models import NotificationConfig

NOTIFICATION_ENV_MAP = {
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


def notification_env(notifications: NotificationConfig) -> dict[str, str]:
    env: dict[str, str] = {}
    for key, value in notifications.model_dump().items():
        if value:
            env[NOTIFICATION_ENV_MAP[key]] = value
    return env
