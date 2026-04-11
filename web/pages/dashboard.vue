<script setup lang="ts">
import type { DashboardResponse } from '../types/controlPlane'

const api = useControlPlane()
const { locale, t, formatDeployMode, formatJobStatus, formatJobType, formatTrigger } = useAppI18n()

const formatRunningState = (running: boolean) => t(running ? '运行中' : '空闲中')
const formatDateTime = (value: string | null) => {
  if (!value) {
    return t('未安排')
  }
  return new Intl.DateTimeFormat(locale.value, {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}

const { data: dashboardResponse, refresh: refreshDashboard } = await useAsyncData<DashboardResponse>('dashboard-data', () => api.getDashboard())
const status = computed(() => dashboardResponse.value?.status)
const recentJobs = computed(() => dashboardResponse.value?.recent_runs || [])
const totalRuns = computed(() => Number(dashboardResponse.value?.total_runs || 0))
const schedules = computed(() => dashboardResponse.value?.schedules || [])
const metrics = computed(() => dashboardResponse.value?.metrics)
const nextRuns = computed(() => dashboardResponse.value?.next_runs || {})
const runningEntries = computed(() => Object.entries(status.value?.running_jobs || {}))
const remainingRuns = computed(() => Math.max(totalRuns.value - recentJobs.value.length, 0))
const storageLabel = computed(() => `${t('存储模式')} ${status.value?.storage_mode || '-'}`)
const timezoneLabel = computed(() => `${t('时区')} ${status.value?.timezone || '-'}`)
const deployModeLabel = computed(() => `${t('部署模式')} ${formatDeployMode(status.value?.deploy_mode)}`)
const schedulerLabel = computed(() => `${t('本地调度')} ${t(status.value?.scheduler_enabled ? '已启用' : '已禁用')}`)
const enabledSchedulesLabel = computed(() => `${t('已启用调度')} ${metrics.value?.enabled_schedule_count || 0}`)
const enabledSchedulesState = computed(() => schedules.value.some((item) => item.enabled) ? 'enabled' : 'disabled')
const nextRunLabel = computed(() => `${t('下次调度')} ${formatDateTime(metrics.value?.next_run_at || null)}`)
const lastSuccessLabel = computed(() => `${t('最近成功')} ${formatDateTime(metrics.value?.last_success_at || null)}`)
const lastFailureLabel = computed(() => `${t('最近失败')} ${formatDateTime(metrics.value?.last_failure_at || null)}`)
const nextRunEntries = computed(() => Object.entries(nextRuns.value).filter(([, value]) => Boolean(value)))
const statItems = computed(() => [
  { label: '历史运行', value: String(totalRuns.value), icon: 'dashboard' },
  { label: '运行中任务', value: String(runningEntries.value.filter(([, value]) => Boolean(value)).length), icon: 'jobs' },
  {
    label: '已启用调度',
    value: String(metrics.value?.enabled_schedule_count || 0),
    icon: 'schedules'
  },
  {
    label: '连续失败',
    value: String(metrics.value?.consecutive_failures || 0),
    icon: 'settings'
  },
])
</script>

<template>
  <AppShell>
    <PageHeader
      title="仪表盘"
      description="查看运行状态、最近作业和系统健康度"
      eyebrow="工作台"
    >
      <template #actions>
        <div class="button-row">
          <button class="button button--secondary" @click="refreshDashboard()">{{ t('刷新面板') }}</button>
        </div>
      </template>
    </PageHeader>
    <div class="button-row page-summary-strip">
      <StatusBadge :label="storageLabel" state="neutral" />
      <StatusBadge :label="timezoneLabel" state="info" />
      <StatusBadge :label="deployModeLabel" :state="status?.deploy_mode === 'control_plane' ? 'enabled' : 'info'" />
      <StatusBadge :label="schedulerLabel" :state="status?.scheduler_enabled ? 'enabled' : 'failed'" />
      <StatusBadge :label="enabledSchedulesLabel" :state="enabledSchedulesState" />
      <StatusBadge :label="nextRunLabel" :state="metrics?.next_run_at ? 'info' : 'neutral'" />
      <StatusBadge :label="lastSuccessLabel" :state="metrics?.last_success_at ? 'success' : 'neutral'" />
      <StatusBadge :label="lastFailureLabel" :state="metrics?.last_failure_at ? 'failed' : 'neutral'" />
    </div>
    <div class="stat-grid">
      <section v-for="item in statItems" :key="item.label" class="card surface-card stat-card">
        <div class="stat-card__head">
          <p class="stat-card__label">{{ t(item.label) }}</p>
          <span class="stat-card__icon">
            <AppIcon :name="item.icon" :size="16" />
          </span>
        </div>
        <div class="stat-card__value">{{ item.value }}</div>
      </section>
    </div>
    <div class="panel-grid panel-grid--two dashboard-panels">
      <section class="card surface-card dashboard-panel dashboard-panel--status">
        <h2 class="card__title">{{ t('运行状态') }}</h2>
        <div class="status-list dashboard-scroll">
          <StatusBadge :label="t('存储模式：{value}', { value: status?.storage_mode || '-' })" state="neutral" />
          <StatusBadge :label="t('时区：{value}', { value: status?.timezone || '-' })" state="info" />
          <StatusBadge
            :label="t('部署模式：{value}', { value: formatDeployMode(status?.deploy_mode) })"
            :state="status?.deploy_mode === 'control_plane' ? 'enabled' : 'info'"
          />
          <StatusBadge
            :label="t('本地调度：{value}', { value: t(status?.scheduler_enabled ? '已启用' : '已禁用') })"
            :state="status?.scheduler_enabled ? 'enabled' : 'failed'"
          />
          <StatusBadge
            v-for="[jobType, nextRun] in nextRunEntries"
            :key="`next-${jobType}`"
            :label="t('{job} 下次：{value}', { job: formatJobType(jobType), value: formatDateTime(nextRun) })"
            state="info"
          />
          <StatusBadge
            v-for="[jobType, running] in runningEntries"
            :key="jobType"
            :label="t('{job}：{status}', { job: formatJobType(jobType), status: formatRunningState(Boolean(running)) })"
            :state="running ? 'running' : 'idle'"
          />
        </div>
      </section>
      <section class="card surface-card dashboard-panel dashboard-panel--runs">
        <h2 class="card__title">{{ t('最近运行') }}</h2>
        <div class="job-list dashboard-scroll">
          <div v-if="!recentJobs.length" class="dashboard-empty">
            <span class="dashboard-empty__icon">
              <AppIcon name="jobs" :size="18" />
            </span>
            <div class="dashboard-empty__copy">
              <strong>{{ t('暂无运行记录') }}</strong>
              <p class="muted">{{ t('可点击顶部“刷新面板”拉取最新状态') }}</p>
            </div>
          </div>
          <div v-for="job in recentJobs" :key="job.id" class="job-item">
            <strong>{{ formatJobType(job.job_type) }}</strong>
            <div class="job-item__meta">
              <StatusBadge :label="formatJobStatus(job.status)" :state="job.status" />
              <span>{{ formatTrigger(job.trigger) }}</span>
            </div>
          </div>
        </div>
        <p v-if="remainingRuns" class="muted">{{ t('还有 {count} 条更早记录未展开', { count: remainingRuns }) }}</p>
      </section>
    </div>
  </AppShell>
</template>
