import type { JobRunView, MainCheckinConfigView } from '../types/controlPlane'
import type {
  TaskCenterAccountView,
  TaskCenterIncidentView,
  TaskCenterOverview,
  TaskCenterReadModelInput,
  TaskCenterSiteView,
  TaskCenterTodayView,
} from '../types/taskCenter'

function isToday(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return false
  }
  const now = new Date()
  return date.getFullYear() === now.getFullYear()
    && date.getMonth() === now.getMonth()
    && date.getDate() === now.getDate()
}

function getAuthModes(account: Record<string, any>) {
  const modes: string[] = []
  if (account.cookies) {
    modes.push('cookies')
  }
  if (account['linux.do']) {
    modes.push('linux.do')
  }
  if (account.github) {
    modes.push('github')
  }
  return modes
}

function getProviderName(account: Record<string, any>) {
  return String(account.provider || 'default')
}

export function useTaskCenter() {
  const deriveSites = (config?: MainCheckinConfigView | null): TaskCenterSiteView[] => {
    const accounts = (config?.accounts || []) as Record<string, any>[]
    const providers = config?.providers || {}
    const providerNames = new Set<string>(Object.keys(providers))

    for (const account of accounts) {
      providerNames.add(getProviderName(account))
    }

    return [...providerNames]
      .sort((left, right) => left.localeCompare(right))
      .map((providerName) => {
        const providerAccounts = accounts.filter((account) => getProviderName(account) === providerName)
        const authModes = new Set<string>()
        let cookieAccountCount = 0
        let oauthAccountCount = 0

        for (const account of providerAccounts) {
          const modes = getAuthModes(account)
          if (modes.includes('cookies')) {
            cookieAccountCount += 1
          }
          if (modes.some((mode) => mode !== 'cookies')) {
            oauthAccountCount += 1
          }
          for (const mode of modes) {
            authModes.add(mode)
          }
        }

        const providerConfigured = Boolean(providers[providerName])
        return {
          id: providerName,
          name: providerName,
          accountCount: providerAccounts.length,
          cookieAccountCount,
          oauthAccountCount,
          providerConfigured,
          authModes: [...authModes],
          status: providerConfigured && providerAccounts.length > 0 ? 'configured' : 'partial'
        }
      })
  }

  const deriveAccounts = (config?: MainCheckinConfigView | null): TaskCenterAccountView[] => {
    const accounts = (config?.accounts || []) as Record<string, any>[]
    return accounts.map((account, index) => {
      const authModes = getAuthModes(account)
      const displayName = String(account.name || `${getProviderName(account)} ${index + 1}`)
      const hasApiUser = Boolean(String(account.api_user || '').trim())
      const hasProxy = Boolean(account.proxy)
      const status = authModes.length > 0 && (account.cookies ? hasApiUser : true) ? 'configured' : 'partial'
      return {
        id: `${getProviderName(account)}-${index}`,
        name: displayName,
        provider: getProviderName(account),
        hasApiUser,
        authModes,
        hasProxy,
        status,
      }
    })
  }

  const deriveIncidents = ({ mainConfig, jobs }: TaskCenterReadModelInput): TaskCenterIncidentView[] => {
    const incidents: TaskCenterIncidentView[] = []
    const accounts = (mainConfig?.accounts || []) as Record<string, any>[]

    if (!accounts.length) {
      incidents.push({
        id: 'config-no-accounts',
        title: '未配置任何签到账号',
        detail: '当前还没有纳管任何 new-api 账号，今日签到任务无法生成。',
        severity: 'high',
        source: 'config',
        createdAt: null,
      })
    }

    for (const run of jobs) {
      if (run.status !== 'failed') {
        continue
      }
      incidents.push({
        id: run.id,
        title: `${run.job_type} 执行失败`,
        detail: run.error_message || '最近一次批次执行失败，请检查站点、账号或浏览器策略。',
        severity: 'high',
        source: 'run',
        createdAt: run.finished_at || run.started_at,
      })
    }

    return incidents.slice(0, 8)
  }

  const deriveOverview = ({ dashboard, mainConfig, jobs }: TaskCenterReadModelInput): TaskCenterOverview => ({
    siteCount: deriveSites(mainConfig).length,
    accountCount: deriveAccounts(mainConfig).length,
    runningJobCount: Object.values(dashboard?.status.running_jobs || {}).filter(Boolean).length,
    enabledScheduleCount: Number(dashboard?.metrics.enabled_schedule_count || 0),
    incidentCount: deriveIncidents({ dashboard, mainConfig, jobs }).length,
    todayRunCount: jobs.filter((job) => isToday(job.started_at)).length,
  })

  const deriveToday = (jobs: JobRunView[]): TaskCenterTodayView => {
    const todayJobs = jobs.filter((job) => isToday(job.started_at))
    return {
      total: todayJobs.length,
      running: todayJobs.filter((job) => job.status === 'running').length,
      success: todayJobs.filter((job) => job.status === 'success').length,
      failed: todayJobs.filter((job) => job.status === 'failed').length,
      skipped: todayJobs.filter((job) => job.status === 'skipped').length,
    }
  }

  const getAuthModeLabel = (mode: string) => {
    if (mode === 'cookies') {
      return 'Cookies'
    }
    if (mode === 'linux.do') {
      return 'Linux.do'
    }
    if (mode === 'github') {
      return 'GitHub'
    }
    return mode
  }

  return {
    deriveSites,
    deriveAccounts,
    deriveIncidents,
    deriveOverview,
    deriveToday,
    getAuthModeLabel,
  }
}
