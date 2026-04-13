import type { JobRunView, JsonObject } from '../types/controlPlane'
import type {
  MainCheckinAccountPayload,
  TaskCenterAccountView,
  TaskCenterIncidentView,
  TaskCenterMainConfigView,
  TaskCenterRunStats,
  TaskCenterSiteView,
} from '../types/taskCenter'

function toRecord(value: unknown): Record<string, unknown> {
  return (value && typeof value === 'object' && !Array.isArray(value)) ? value as Record<string, unknown> : {}
}

function sameLocalDay(left: Date, right: Date) {
  return left.getFullYear() === right.getFullYear()
    && left.getMonth() === right.getMonth()
    && left.getDate() === right.getDate()
}

export function normalizeMainConfig(payload?: Partial<TaskCenterMainConfigView>): TaskCenterMainConfigView {
  return {
    accounts: Array.isArray(payload?.accounts) ? payload?.accounts as MainCheckinAccountPayload[] : [],
    providers: toRecord(payload?.providers) as Record<string, JsonObject>,
    accounts_linux_do: Array.isArray(payload?.accounts_linux_do) ? payload.accounts_linux_do : [],
    accounts_github: Array.isArray(payload?.accounts_github) ? payload.accounts_github : [],
    proxy: (payload?.proxy && typeof payload.proxy === 'object' && !Array.isArray(payload.proxy)) ? payload.proxy : null,
  }
}

export function buildAccountViews(config: TaskCenterMainConfigView): TaskCenterAccountView[] {
  return config.accounts.map((item, index) => {
    const authModes: string[] = []
    if (item.cookies && typeof item.cookies === 'object') {
      authModes.push('Cookies')
    }
    if (item['linux.do']) {
      authModes.push('Linux.do')
    }
    if (item.github) {
      authModes.push('GitHub')
    }
    return {
      id: `account-${index + 1}`,
      name: typeof item.name === 'string' && item.name.trim() ? item.name.trim() : `账号 ${index + 1}`,
      provider: typeof item.provider === 'string' && item.provider.trim() ? item.provider.trim() : 'anyrouter',
      apiUser: typeof item.api_user === 'string' ? item.api_user : '',
      hasCookies: Boolean(item.cookies),
      authModes,
      proxyConfigured: Boolean(item.proxy && typeof item.proxy === 'object'),
      extraConfigured: Object.keys(stripKnownAccountFields(item)).length > 0,
      browserSensitive: Boolean(item['linux.do'] || item.github),
    }
  })
}

function stripKnownAccountFields(account: MainCheckinAccountPayload) {
  const extra = { ...account }
  delete extra.name
  delete extra.provider
  delete extra.api_user
  delete extra.cookies
  delete extra['linux.do']
  delete extra.github
  delete extra.proxy
  return extra
}

export function buildSiteViews(config: TaskCenterMainConfigView): TaskCenterSiteView[] {
  const accounts = buildAccountViews(config)
  const siteMap = new Map<string, TaskCenterSiteView>()

  for (const account of accounts) {
    const siteId = account.provider || 'anyrouter'
    const current = siteMap.get(siteId) || {
      id: siteId,
      name: siteId,
      accountCount: 0,
      cookieAccountCount: 0,
      oauthAccountCount: 0,
      browserSensitiveCount: 0,
      customProviderConfigured: Boolean(config.providers[siteId]),
    }
    current.accountCount += 1
    current.cookieAccountCount += account.hasCookies ? 1 : 0
    current.oauthAccountCount += account.authModes.filter((item) => item !== 'Cookies').length > 0 ? 1 : 0
    current.browserSensitiveCount += account.browserSensitive ? 1 : 0
    current.customProviderConfigured = current.customProviderConfigured || Boolean(config.providers[siteId])
    siteMap.set(siteId, current)
  }

  for (const providerName of Object.keys(config.providers)) {
    if (!siteMap.has(providerName)) {
      siteMap.set(providerName, {
        id: providerName,
        name: providerName,
        accountCount: 0,
        cookieAccountCount: 0,
        oauthAccountCount: 0,
        browserSensitiveCount: 0,
        customProviderConfigured: true,
      })
    }
  }

  return Array.from(siteMap.values()).sort((left, right) => left.name.localeCompare(right.name))
}

export function buildRunStats(runs: JobRunView[]): TaskCenterRunStats {
  const now = new Date()
  const todayRuns = runs.filter((item) => sameLocalDay(new Date(item.started_at), now))
  return {
    todayRunCount: todayRuns.length,
    todaySuccessCount: todayRuns.filter((item) => item.status === 'success').length,
    todayFailedCount: todayRuns.filter((item) => item.status === 'failed').length,
    todaySkippedCount: todayRuns.filter((item) => item.status === 'skipped').length,
    lastRunAt: runs[0]?.started_at || null,
  }
}

export function buildIncidentViews(runs: JobRunView[]): TaskCenterIncidentView[] {
  return runs
    .filter((item) => item.status === 'failed' || (item.status === 'skipped' && item.error_message))
    .map((item) => ({
      id: item.id,
      jobType: item.job_type,
      status: item.status,
      startedAt: item.started_at,
      errorMessage: item.error_message || '任务被跳过，需要人工复核',
      trigger: item.trigger,
    }))
}
