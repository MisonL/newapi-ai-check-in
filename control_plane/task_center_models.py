from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator

SiteCompatibility = Literal["standard", "browser", "legacy", "unsupported"]
SiteProbeStatus = Literal["unknown", "healthy", "degraded", "unreachable", "unsupported"]
AccountSessionStatus = Literal["unknown", "valid", "expired", "invalid"]
AccountCheckinStatus = Literal["pending", "success", "skipped", "failed", "blocked", "unknown"]
AccountAuthMode = Literal["password", "cookies", "github_oauth", "linuxdo_oauth"]
DailyTaskStatus = Literal["pending", "probing", "logging_in", "checking", "checking_in", "success", "skipped", "failed", "blocked"]
TaskTriggerType = Literal["manual", "scheduled", "retry"]
TaskExecutorType = Literal["standard_newapi", "browser_fallback", "legacy_plugin"]
IncidentSeverity = Literal["low", "medium", "high"]


def utc_now() -> datetime:
	return datetime.now(timezone.utc)


class SiteRecord(BaseModel):
	id: str = Field(default_factory=lambda: uuid4().hex)
	name: str = Field(min_length=1)
	base_url: str = Field(min_length=1)
	enabled: bool = True
	compatibility_level: SiteCompatibility = "standard"
	last_probe_status: SiteProbeStatus = "unknown"
	checkin_enabled_detected: bool | None = None
	checkin_min_quota_detected: int | None = Field(default=None, ge=0)
	checkin_max_quota_detected: int | None = Field(default=None, ge=0)
	notes: str = ""
	created_at: datetime = Field(default_factory=utc_now)
	updated_at: datetime = Field(default_factory=utc_now)

	@field_validator("name", "base_url", "notes")
	@classmethod
	def normalize_strings(cls, value: str) -> str:
		return value.strip()

	@field_validator("base_url")
	@classmethod
	def trim_trailing_slash(cls, value: str) -> str:
		return value.rstrip("/")


class AccountRecord(BaseModel):
	id: str = Field(default_factory=lambda: uuid4().hex)
	site_id: str = Field(min_length=1)
	display_name: str = ""
	username: str = Field(min_length=1)
	auth_mode: AccountAuthMode = "password"
	password: str = ""
	api_user: str = ""
	session_cookies: dict[str, str] = Field(default_factory=dict)
	enabled: bool = True
	session_status: AccountSessionStatus = "unknown"
	last_checkin_status: AccountCheckinStatus = "pending"
	last_checkin_date: date | None = None
	last_checkin_at: datetime | None = None
	last_quota_awarded: int = Field(default=0, ge=0)
	total_checkins: int = Field(default=0, ge=0)
	total_quota_awarded: int = Field(default=0, ge=0)
	last_error_message: str = ""
	created_at: datetime = Field(default_factory=utc_now)
	updated_at: datetime = Field(default_factory=utc_now)

	@field_validator("site_id", "display_name", "username", "password", "last_error_message")
	@classmethod
	def normalize_strings(cls, value: str) -> str:
		return value.strip()

	@model_validator(mode="after")
	def validate_auth_mode(self) -> "AccountRecord":
		if self.auth_mode in {"password", "github_oauth", "linuxdo_oauth"}:
			if not self.password:
				raise ValueError(f"{self.auth_mode} auth mode requires password")
			return self
		if not self.api_user:
			raise ValueError("cookies auth mode requires api_user")
		if not self.session_cookies:
			raise ValueError("cookies auth mode requires session_cookies")
		return self


class IncidentRecord(BaseModel):
	id: str = Field(default_factory=lambda: uuid4().hex)
	account_id: str
	site_id: str
	display_name: str
	site_name: str
	status: AccountCheckinStatus
	last_error_message: str
	task_id: str | None = None
	type: str = ""
	severity: IncidentSeverity = "high"
	resolved: bool = False
	resolution_action: str = ""
	dedupe_key: str = ""
	first_seen_at: datetime = Field(default_factory=utc_now)
	last_seen_at: datetime = Field(default_factory=utc_now)
	detail: str = ""
	last_checkin_at: datetime | None = None

	@field_validator("account_id", "site_id", "display_name", "site_name", "last_error_message", "type", "resolution_action", "dedupe_key", "detail")
	@classmethod
	def normalize_strings(cls, value: str) -> str:
		return value.strip()


class DailyTaskRecord(BaseModel):
	id: str = Field(default_factory=lambda: uuid4().hex)
	site_id: str = Field(min_length=1)
	account_id: str = Field(min_length=1)
	task_date: date
	status: DailyTaskStatus = "pending"
	trigger_type: TaskTriggerType = "manual"
	attempt_count: int = Field(default=0, ge=0)
	executor_type: TaskExecutorType = "standard_newapi"
	started_at: datetime | None = None
	finished_at: datetime | None = None
	error_code: str = ""
	error_message: str = ""
	created_at: datetime = Field(default_factory=utc_now)
	updated_at: datetime = Field(default_factory=utc_now)

	@field_validator("site_id", "account_id", "error_code", "error_message")
	@classmethod
	def normalize_strings(cls, value: str) -> str:
		return value.strip()


class CheckinResultRecord(BaseModel):
	id: str = Field(default_factory=lambda: uuid4().hex)
	task_id: str = Field(min_length=1)
	site_id: str = Field(min_length=1)
	account_id: str = Field(min_length=1)
	checked_in_today_before_run: bool = False
	quota_awarded: int = Field(default=0, ge=0)
	checkin_date: date | None = None
	total_checkins: int = Field(default=0, ge=0)
	total_quota_awarded: int = Field(default=0, ge=0)
	raw_status_payload: dict = Field(default_factory=dict)
	raw_checkin_payload: dict = Field(default_factory=dict)
	created_at: datetime = Field(default_factory=utc_now)

	@field_validator("task_id", "site_id", "account_id")
	@classmethod
	def normalize_strings(cls, value: str) -> str:
		return value.strip()


class TaskCenterDayStats(BaseModel):
	total_sites: int = 0
	enabled_sites: int = 0
	total_accounts: int = 0
	enabled_accounts: int = 0
	today_success: int = 0
	today_skipped: int = 0
	today_failed: int = 0
	today_blocked: int = 0
	today_pending: int = 0
	today_quota_awarded: int = 0


class TaskCenterSummary(BaseModel):
	today: TaskCenterDayStats = Field(default_factory=TaskCenterDayStats)
	recent_accounts: list[AccountRecord] = Field(default_factory=list)
	recent_incidents: list[IncidentRecord] = Field(default_factory=list)


class TaskCenterTodayTaskView(BaseModel):
	id: str
	site_id: str
	site_name: str
	account_id: str
	account_display_name: str
	username: str
	auth_mode: AccountAuthMode
	task_date: date
	status: DailyTaskStatus
	trigger_type: TaskTriggerType
	attempt_count: int
	executor_type: TaskExecutorType
	started_at: datetime | None = None
	finished_at: datetime | None = None
	error_code: str = ""
	error_message: str = ""
	quota_awarded: int = 0
	checked_in_today_before_run: bool = False


class TaskCenterTodayPayload(BaseModel):
	task_date: date
	total_tasks: int = 0
	pending_tasks: int = 0
	success_tasks: int = 0
	skipped_tasks: int = 0
	failed_tasks: int = 0
	blocked_tasks: int = 0
	running_tasks: int = 0
	total_quota_awarded: int = 0
	tasks: list[TaskCenterTodayTaskView] = Field(default_factory=list)


class TaskCenterReportDay(BaseModel):
	task_date: date
	total_tasks: int = 0
	success_tasks: int = 0
	skipped_tasks: int = 0
	failed_tasks: int = 0
	blocked_tasks: int = 0
	total_quota_awarded: int = 0


class TaskCenterReportSite(BaseModel):
	site_id: str
	site_name: str
	total_tasks: int = 0
	success_tasks: int = 0
	skipped_tasks: int = 0
	failed_tasks: int = 0
	blocked_tasks: int = 0
	total_quota_awarded: int = 0


class TaskCenterReportPayload(BaseModel):
	date_from: date
	date_to: date
	days: list[TaskCenterReportDay] = Field(default_factory=list)
	sites: list[TaskCenterReportSite] = Field(default_factory=list)


class TaskCenterTaskGenerationResult(BaseModel):
	task_date: date
	total_accounts: int = 0
	created_count: int = 0
	existing_count: int = 0


class TaskCenterImportResult(BaseModel):
	source: str = "main_checkin"
	total_providers: int = 0
	total_accounts: int = 0
	created_sites: int = 0
	updated_sites: int = 0
	created_accounts: int = 0
	updated_accounts: int = 0
	skipped_accounts: int = 0
	messages: list[str] = Field(default_factory=list)


class TaskCenterBatchExecutionResult(BaseModel):
	task_date: date
	total_selected: int = 0
	executed_count: int = 0
	success_count: int = 0
	skipped_count: int = 0
	failed_count: int = 0
	blocked_count: int = 0
	task_ids: list[str] = Field(default_factory=list)
