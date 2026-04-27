import type {
  AccountRecordView,
  AccountPreflightResultView,
  AppStatus,
  ConfigEnvelope,
  DashboardResponse,
  IncidentRecordView,
  RelatedDeletionResultView,
  SiteProbeResultView,
  SiteRecordView,
  TaskCenterBatchExecutionResultView,
  TaskCenterImportResultView,
  TaskCenterReportResponse,
  TaskCenterSummaryResponse,
  TaskCenterTaskGenerationResultView,
  TaskCenterTodayResponse,
  JobLogLineView,
  JobRunView,
  ScheduleSpecView,
} from '../types/controlPlane'

export function useControlPlane() {
  const authHeaders = import.meta.server ? useRequestHeaders(['cookie']) : undefined
  const request = <T>(url: string, options?: Record<string, unknown>) =>
    $fetch<T>(url, {
      ...options,
      headers: {
        ...authHeaders,
        ...((options?.headers as Record<string, string> | undefined) || {})
      }
    })

  const getStatus = () => request<AppStatus>('/api/ui/status')
  const getDashboard = () => request<DashboardResponse>('/api/ui/dashboard')
  const getTaskCenterSummary = () => request<TaskCenterSummaryResponse>('/api/ui/task-center/summary')
  const getTaskCenterIncidents = (resolved?: boolean) =>
    request<IncidentRecordView[]>('/api/ui/task-center/incidents', { query: resolved === undefined ? {} : { resolved } })
  const resolveTaskCenterIncident = (incidentId: string) =>
    request<IncidentRecordView>(`/api/ui/task-center/incidents/${incidentId}/resolve`, { method: 'POST' })
  const getTaskCenterReports = (dateFrom?: string, dateTo?: string) =>
    request<TaskCenterReportResponse>('/api/ui/task-center/reports', {
      query: {
        ...(dateFrom ? { date_from: dateFrom } : {}),
        ...(dateTo ? { date_to: dateTo } : {}),
      }
    })
  const importMainCheckinToTaskCenter = () =>
    request<TaskCenterImportResultView>('/api/ui/task-center/imports/main-checkin', { method: 'POST' })
  const probeTaskCenterSite = (siteId: string) =>
    request<SiteProbeResultView>(`/api/ui/task-center/sites/${siteId}/probe`, { method: 'POST' })
  const preflightTaskCenterAccount = (accountId: string) =>
    request<AccountPreflightResultView>(`/api/ui/task-center/accounts/${accountId}/preflight`, { method: 'POST' })
  const getTaskCenterToday = (taskDate?: string) =>
    request<TaskCenterTodayResponse>('/api/ui/task-center/today', { query: taskDate ? { task_date: taskDate } : {} })
  const generateTaskCenterToday = (taskDate?: string) =>
    request<TaskCenterTaskGenerationResultView>('/api/ui/task-center/tasks/generate-today', {
      method: 'POST',
      query: taskDate ? { task_date: taskDate } : {}
    })
  const executeTaskCenterToday = (taskDate?: string) =>
    request<TaskCenterBatchExecutionResultView>('/api/ui/task-center/tasks/execute-today', {
      method: 'POST',
      query: taskDate ? { task_date: taskDate } : {}
    })
  const retryTaskCenterTask = (taskId: string) =>
    request(`/api/ui/task-center/tasks/${taskId}/retry`, { method: 'POST' })
  const executeTaskCenterTask = (taskId: string) =>
    request(`/api/ui/task-center/tasks/${taskId}/execute`, { method: 'POST' })
  const listSites = () => request<SiteRecordView[]>('/api/ui/sites')
  const createSite = (payload: Record<string, unknown>) => request<SiteRecordView>('/api/ui/sites', { method: 'POST', body: payload })
  const updateSite = (siteId: string, payload: Record<string, unknown>) =>
    request<SiteRecordView>(`/api/ui/sites/${siteId}`, { method: 'PUT', body: payload })
  const deleteSite = (siteId: string) =>
    request<RelatedDeletionResultView>(`/api/ui/sites/${siteId}`, { method: 'DELETE' })
  const listAccounts = (options?: { siteId?: string }) =>
    request<AccountRecordView[]>('/api/ui/accounts', { query: options?.siteId ? { site_id: options.siteId } : {} })
  const createAccount = (payload: Record<string, unknown>) =>
    request<AccountRecordView>('/api/ui/accounts', { method: 'POST', body: payload })
  const updateAccount = (accountId: string, payload: Record<string, unknown>) =>
    request<AccountRecordView>(`/api/ui/accounts/${accountId}`, { method: 'PUT', body: payload })
  const deleteAccount = (accountId: string) =>
    request<RelatedDeletionResultView>(`/api/ui/accounts/${accountId}`, { method: 'DELETE' })
  const getConfig = <TPayload = Record<string, unknown>>(domain: string) => request<ConfigEnvelope<TPayload>>(`/api/ui/config/${domain}`)
  const saveConfig = <TPayload = Record<string, unknown>>(domain: string, payload: TPayload) =>
    request<ConfigEnvelope<TPayload>>(`/api/ui/config/${domain}`, { method: 'PUT', body: { domain, payload } })
  const listJobs = (options?: { jobType?: string, limit?: number }) =>
    request<JobRunView[]>('/api/ui/jobs', {
      query: {
        ...(options?.jobType ? { job_type: options.jobType } : {}),
        ...(options?.limit ? { limit: options.limit } : {})
      }
    })
  const getJob = (id: string) => request<JobRunView>(`/api/ui/jobs/${id}`)
  const getJobLogs = (id: string) => request<JobLogLineView[]>(`/api/ui/jobs/${id}/logs`)
  const runJob = (jobType: string) => request<JobRunView>(`/api/ui/jobs/${jobType}/run`, { method: 'POST' })
  const listSchedules = () => request<ScheduleSpecView[]>('/api/ui/schedules')
  const saveSchedule = (jobType: string, payload: Record<string, unknown>) =>
    request<ScheduleSpecView>(`/api/ui/schedules/${jobType}`, { method: 'PUT', body: payload })
  const updateAdminPassword = (password: string) =>
    request<{ updated: boolean }>('/api/ui/system/admin-password', { method: 'POST', body: { password } })
  return {
    getStatus,
    getDashboard,
    getTaskCenterSummary,
    getTaskCenterIncidents,
    resolveTaskCenterIncident,
    getTaskCenterReports,
    importMainCheckinToTaskCenter,
    probeTaskCenterSite,
    preflightTaskCenterAccount,
    getTaskCenterToday,
    generateTaskCenterToday,
    executeTaskCenterToday,
    retryTaskCenterTask,
    executeTaskCenterTask,
    listSites,
    createSite,
    updateSite,
    deleteSite,
    listAccounts,
    createAccount,
    updateAccount,
    deleteAccount,
    getConfig,
    saveConfig,
    listJobs,
    getJob,
    getJobLogs,
    runJob,
    listSchedules,
    saveSchedule,
    updateAdminPassword
  }
}
