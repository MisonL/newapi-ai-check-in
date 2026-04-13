from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from apscheduler.triggers.cron import CronTrigger
from pydantic import BaseModel, Field, field_validator


class ConfigDomain(str, Enum):
    SYSTEM = "system"
    MAIN_CHECKIN = "main_checkin"
    CHECKIN_996 = "checkin_996"
    CHECKIN_QAQ_AL = "checkin_qaq_al"
    LINUXDO_READ = "linuxdo_read"
    NOTIFICATIONS = "notifications"


class JobType(str, Enum):
    MAIN_CHECKIN = "main_checkin"
    CHECKIN_996 = "checkin_996"
    CHECKIN_QAQ_AL = "checkin_qaq_al"
    LINUXDO_READ = "linuxdo_read"


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class TriggerType(str, Enum):
    MANUAL = "manual"
    SCHEDULED = "scheduled"


class SystemConfig(BaseModel):
    debug: bool = False
    browser_strategy: Literal["legacy", "http_only"] = "legacy"
    browser_enabled: bool = False
    main_checkin_engine: Literal["legacy", "task_center"] = "legacy"
    admin_password_hash: str = ""


class MainCheckinConfig(BaseModel):
    accounts: list[dict[str, Any]] = Field(default_factory=list)
    providers: dict[str, dict[str, Any]] = Field(default_factory=dict)
    accounts_linux_do: list[dict[str, str]] = Field(default_factory=list)
    accounts_github: list[dict[str, str]] = Field(default_factory=list)
    proxy: dict[str, Any] | None = None


class NotificationConfig(BaseModel):
    dingding_webhook: str = ""
    email_user: str = ""
    email_pass: str = ""
    email_to: str = ""
    custom_smtp_server: str = ""
    pushplus_token: str = ""
    server_push_key: str = ""
    feishu_webhook: str = ""
    weixin_webhook: str = ""
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""


class Checkin996Config(BaseModel):
    accounts: list[str] = Field(default_factory=list)
    proxy: dict[str, Any] | None = None


class CheckinQaqAlConfig(BaseModel):
    accounts: list[str] = Field(default_factory=list)
    proxy: dict[str, Any] | None = None
    tier: int = Field(default=4, ge=1, le=4)


class LinuxDoReadAccount(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class LinuxDoReadConfig(BaseModel):
    accounts: list[LinuxDoReadAccount] = Field(default_factory=list)
    base_topic_id: int | None = Field(default=None, ge=1)
    max_posts: int = Field(default=100, ge=1)


class AppStatus(BaseModel):
    storage_mode: Literal["memory", "persistent"]
    timezone: str
    deploy_mode: Literal["control_plane", "github_actions"]
    running_jobs: dict[str, bool]
    scheduler_enabled: bool
    admin_password_configured: bool
    bootstrap_password_enabled: bool


class DashboardMetrics(BaseModel):
    enabled_schedule_count: int = 0
    next_run_at: datetime | None = None
    last_run_at: datetime | None = None
    last_success_at: datetime | None = None
    last_failure_at: datetime | None = None
    consecutive_failures: int = 0


class DashboardPayload(BaseModel):
    status: AppStatus
    recent_runs: list["JobRun"] = Field(default_factory=list)
    total_runs: int = 0
    schedules: list["ScheduleSpec"] = Field(default_factory=list)
    metrics: DashboardMetrics = Field(default_factory=DashboardMetrics)
    next_runs: dict[str, datetime | None] = Field(default_factory=dict)


class ConfigEnvelope(BaseModel):
    domain: ConfigDomain
    payload: dict[str, Any]


class AdminLoginRequest(BaseModel):
    password: str


class AdminPasswordUpdateRequest(BaseModel):
    password: str = Field(min_length=8)


class ScheduleSpec(BaseModel):
    job_type: JobType
    enabled: bool = False
    cron: str = "0 */8 * * *"
    timezone: str = "Asia/Shanghai"
    cooldown_seconds: int = 0

    @field_validator("cron")
    @classmethod
    def validate_cron(cls, value: str) -> str:
        CronTrigger.from_crontab(value)
        return value

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"Unknown timezone: {value}") from exc
        return value


class ArtifactRef(BaseModel):
    kind: str
    path: str
    content_type: str
    size: int


class JobSummary(BaseModel):
    success_count: int = 0
    total_count: int = 0
    notification_sent: bool = False
    balances: dict[str, Any] = Field(default_factory=dict)
    extra: dict[str, Any] = Field(default_factory=dict)


class JobRun(BaseModel):
    id: str
    job_type: JobType
    trigger: TriggerType
    status: JobStatus
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime | None = None
    exit_code: int | None = None
    summary: JobSummary | None = None
    error_code: str | None = None
    error_message: str | None = None
    artifacts: list[ArtifactRef] = Field(default_factory=list)


class JobLogLine(BaseModel):
    run_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    stream: Literal["stdout", "stderr", "system"] = "stdout"
    message: str
