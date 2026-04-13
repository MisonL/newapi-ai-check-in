export type JobStatus = 'queued' | 'running' | 'success' | 'failed' | 'skipped'
export type TriggerType = 'manual' | 'scheduled'
export type StorageMode = 'memory' | 'persistent'

export type JsonObject = Record<string, unknown>

export interface AppStatus {
  storage_mode: StorageMode
  timezone: string
  deploy_mode: 'control_plane' | 'github_actions'
  running_jobs: Record<string, boolean>
  scheduler_enabled: boolean
  admin_password_configured: boolean
  bootstrap_password_enabled: boolean
}

export interface JobSummary {
  success_count: number
  total_count: number
  notification_sent: boolean
  balances: Record<string, unknown>
  extra: Record<string, unknown>
}

export interface JobRunView {
  id: string
  job_type: string
  trigger: TriggerType
  status: JobStatus
  started_at: string
  finished_at: string | null
  exit_code: number | null
  summary: JobSummary | null
  error_code: string | null
  error_message: string | null
}

export interface JobLogLineView {
  run_id: string
  created_at: string
  stream: 'stdout' | 'stderr' | 'system'
  message: string
}

export interface ScheduleSpecView {
  job_type: string
  enabled: boolean
  cron: string
  timezone: string
  cooldown_seconds: number
}

export interface DashboardMetricsView {
  enabled_schedule_count: number
  next_run_at: string | null
  last_run_at: string | null
  last_success_at: string | null
  last_failure_at: string | null
  consecutive_failures: number
}

export interface DashboardResponse {
  status: AppStatus
  recent_runs: JobRunView[]
  total_runs: number
  schedules: ScheduleSpecView[]
  metrics: DashboardMetricsView
  next_runs: Record<string, string | null>
}

export interface SiteRecordView {
  id: string
  name: string
  base_url: string
  enabled: boolean
  compatibility_level: 'standard' | 'browser' | 'legacy' | 'unsupported'
  last_probe_status: 'unknown' | 'healthy' | 'degraded' | 'unreachable' | 'unsupported'
  checkin_enabled_detected: boolean | null
  checkin_min_quota_detected: number | null
  checkin_max_quota_detected: number | null
  notes: string
  created_at: string
  updated_at: string
}

export interface AccountRecordView {
  id: string
  site_id: string
  display_name: string
  username: string
  auth_mode: 'password' | 'cookies' | 'github_oauth' | 'linuxdo_oauth'
  password: string
  api_user: string
  session_cookies: Record<string, string>
  enabled: boolean
  session_status: 'unknown' | 'valid' | 'expired' | 'invalid'
  last_checkin_status: 'pending' | 'success' | 'skipped' | 'failed' | 'blocked' | 'unknown'
  last_checkin_date: string | null
  last_checkin_at: string | null
  last_quota_awarded: number
  total_checkins: number
  total_quota_awarded: number
  last_error_message: string
  created_at: string
  updated_at: string
}

export interface IncidentRecordView {
  id: string
  account_id: string
  site_id: string
  display_name: string
  site_name: string
  status: 'pending' | 'success' | 'skipped' | 'failed' | 'blocked' | 'unknown'
  last_error_message: string
  task_id?: string | null
  type?: string
  severity?: 'low' | 'medium' | 'high'
  resolved?: boolean
  resolution_action?: string
  dedupe_key?: string
  first_seen_at?: string
  last_seen_at?: string
  detail?: string
  last_checkin_at: string | null
}

export interface TaskCenterDayStatsView {
  total_sites: number
  enabled_sites: number
  total_accounts: number
  enabled_accounts: number
  today_success: number
  today_skipped: number
  today_failed: number
  today_blocked: number
  today_pending: number
  today_quota_awarded: number
}

export interface TaskCenterSummaryResponse {
  today: TaskCenterDayStatsView
  recent_accounts: AccountRecordView[]
  recent_incidents: IncidentRecordView[]
}

export interface TaskCenterTaskGenerationResultView {
  task_date: string
  total_accounts: number
  created_count: number
  existing_count: number
}

export interface TaskCenterBatchExecutionResultView {
  task_date: string
  total_selected: number
  executed_count: number
  success_count: number
  skipped_count: number
  failed_count: number
  blocked_count: number
  task_ids: string[]
}

export interface TaskCenterImportResultView {
  source: string
  total_providers: number
  total_accounts: number
  created_sites: number
  updated_sites: number
  created_accounts: number
  updated_accounts: number
  skipped_accounts: number
  messages: string[]
}

export interface TaskCenterTodayTaskView {
  id: string
  site_id: string
  site_name: string
  account_id: string
  account_display_name: string
  username: string
  auth_mode: 'password' | 'cookies' | 'github_oauth' | 'linuxdo_oauth'
  task_date: string
  status: 'pending' | 'probing' | 'logging_in' | 'checking' | 'checking_in' | 'success' | 'skipped' | 'failed' | 'blocked'
  trigger_type: 'manual' | 'scheduled' | 'retry'
  attempt_count: number
  executor_type: 'standard_newapi' | 'browser_fallback' | 'legacy_plugin'
  started_at: string | null
  finished_at: string | null
  error_code: string
  error_message: string
  quota_awarded: number
  checked_in_today_before_run: boolean
}

export interface TaskCenterTodayResponse {
  task_date: string
  total_tasks: number
  pending_tasks: number
  success_tasks: number
  skipped_tasks: number
  failed_tasks: number
  blocked_tasks: number
  running_tasks: number
  total_quota_awarded: number
  tasks: TaskCenterTodayTaskView[]
}

export interface TaskCenterReportDayView {
  task_date: string
  total_tasks: number
  success_tasks: number
  skipped_tasks: number
  failed_tasks: number
  blocked_tasks: number
  total_quota_awarded: number
}

export interface TaskCenterReportSiteView {
  site_id: string
  site_name: string
  total_tasks: number
  success_tasks: number
  skipped_tasks: number
  failed_tasks: number
  blocked_tasks: number
  total_quota_awarded: number
}

export interface TaskCenterReportResponse {
  date_from: string
  date_to: string
  days: TaskCenterReportDayView[]
  sites: TaskCenterReportSiteView[]
}

export interface ConfigEnvelope<TPayload = JsonObject> {
  domain: string
  payload: TPayload
}

export interface SystemConfigView {
  debug: boolean
  browser_strategy: 'legacy' | 'http_only'
  browser_enabled: boolean
  admin_password_hash?: string
}

export interface NotificationConfigView {
  dingding_webhook: string
  email_user: string
  email_pass: string
  email_to: string
  custom_smtp_server: string
  pushplus_token: string
  server_push_key: string
  feishu_webhook: string
  weixin_webhook: string
  telegram_bot_token: string
  telegram_chat_id: string
}

export interface MainCheckinConfigView {
  accounts: JsonObject[]
  providers: Record<string, JsonObject>
  accounts_linux_do: Array<{ username: string; password: string }>
  accounts_github: Array<{ username: string; password: string }>
  proxy: JsonObject | null
}

export interface Checkin996ConfigView {
  accounts: string[]
  proxy: JsonObject | null
}

export interface CheckinQaqAlConfigView {
  accounts: string[]
  proxy: JsonObject | null
  tier: number
}

export interface LinuxDoReadConfigView {
  accounts: Array<{ username: string; password: string }>
  base_topic_id: number | null
  max_posts: number
}
