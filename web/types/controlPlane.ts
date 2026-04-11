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
