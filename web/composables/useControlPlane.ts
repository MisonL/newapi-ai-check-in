export function useControlPlane() {
  const authHeaders = import.meta.server ? useRequestHeaders(['cookie']) : undefined
  const request = <T>(url: string, options?: Record<string, any>) =>
    $fetch<T>(url, {
      ...options,
      headers: {
        ...authHeaders,
        ...(options?.headers || {})
      }
    })

  const getStatus = () => request('/api/ui/status')
  const getConfig = (domain: string) => request(`/api/ui/config/${domain}`)
  const saveConfig = (domain: string, payload: Record<string, any>) =>
    request(`/api/ui/config/${domain}`, { method: 'PUT', body: { domain, payload } })
  const listJobs = () => request('/api/ui/jobs')
  const getJob = (id: string) => request(`/api/ui/jobs/${id}`)
  const getJobLogs = (id: string) => request(`/api/ui/jobs/${id}/logs`)
  const runJob = (jobType: string) => request(`/api/ui/jobs/${jobType}/run`, { method: 'POST' })
  const listSchedules = () => request('/api/ui/schedules')
  const saveSchedule = (jobType: string, payload: Record<string, any>) =>
    request(`/api/ui/schedules/${jobType}`, { method: 'PUT', body: payload })
  const updateAdminPassword = (password: string) =>
    request('/api/ui/system/admin-password', { method: 'POST', body: { password } })
  return {
    getStatus,
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
