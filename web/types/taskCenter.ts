import type { JobRunView, JsonObject } from './controlPlane'

export interface TaskCenterAccountView {
  id: string
  name: string
  provider: string
  apiUser: string
  hasCookies: boolean
  authModes: string[]
  proxyConfigured: boolean
  extraConfigured: boolean
  browserSensitive: boolean
}

export interface TaskCenterSiteView {
  id: string
  name: string
  accountCount: number
  cookieAccountCount: number
  oauthAccountCount: number
  browserSensitiveCount: number
  customProviderConfigured: boolean
}

export interface TaskCenterRunStats {
  todayRunCount: number
  todaySuccessCount: number
  todayFailedCount: number
  todaySkippedCount: number
  lastRunAt: string | null
}

export interface TaskCenterIncidentView {
  id: string
  jobType: string
  status: string
  startedAt: string
  errorMessage: string
  trigger: string
}

export type MainCheckinAccountPayload = JsonObject & {
  name?: string
  provider?: string
  api_user?: string
  cookies?: JsonObject
  proxy?: JsonObject
  github?: boolean | { username?: string; password?: string }
  'linux.do'?: boolean | { username?: string; password?: string }
}

export interface TaskCenterMainConfigView {
  accounts: MainCheckinAccountPayload[]
  providers: Record<string, JsonObject>
  accounts_linux_do: Array<{ username: string; password: string }>
  accounts_github: Array<{ username: string; password: string }>
  proxy: JsonObject | null
}

export type TaskCenterJobRunView = JobRunView
