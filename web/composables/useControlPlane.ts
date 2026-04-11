import type {
  AppStatus,
  ConfigEnvelope,
  DashboardResponse,
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
