<script setup lang="ts">
import type { TaskCenterReportSiteView } from '../types/controlPlane'

const api = useControlPlane()
const { t } = useAppI18n()
const { formatDate, formatDateInput } = useUiDateTime()

const today = new Date()
const defaultDateTo = formatDateInput(today)
const defaultDateFrom = formatDateInput(new Date(today.getTime() - (29 * 24 * 60 * 60 * 1000)))

const dateFrom = ref(defaultDateFrom)
const dateTo = ref(defaultDateTo)
const siteFilter = ref('all')
const showEmptyDays = ref(false)
const reportBusy = ref(false)
const reportMessage = ref('')

const setQuickRange = async (days: number) => {
  const end = new Date()
  const start = new Date(end.getTime() - ((days - 1) * 24 * 60 * 60 * 1000))
  dateFrom.value = formatDateInput(start)
  dateTo.value = formatDateInput(end)
  await applyFilters(days === 7 ? '已切换到最近7天' : '已切换到最近30天')
}

const { data: reportsResponse, refresh: refreshReports } = await useAsyncData(
  'task-center-reports-real',
  () => api.getTaskCenterReports(dateFrom.value, dateTo.value)
)

const days = computed(() => reportsResponse.value?.days || [])
const siteSummaries = computed(() => (reportsResponse.value?.sites || []) as TaskCenterReportSiteView[])
const siteOptions = computed(() => [
  { label: t('全部站点'), value: 'all' },
  ...siteSummaries.value.map((item) => ({ label: item.site_name, value: item.site_id })),
])
const visibleSiteSummaries = computed(() => {
  return siteSummaries.value.filter((item) => (siteFilter.value === 'all' ? true : item.site_id === siteFilter.value))
})
const visibleDays = computed(() => {
  return [...days.value]
    .reverse()
    .filter((day) => (showEmptyDays.value ? true : day.total_tasks > 0))
})

const totals = computed(() => {
  return days.value.reduce(
    (result, day) => {
      result.totalTasks += day.total_tasks
      result.successTasks += day.success_tasks
      result.skippedTasks += day.skipped_tasks
      result.failedTasks += day.failed_tasks
      result.blockedTasks += day.blocked_tasks
      result.totalQuota += day.total_quota_awarded
      return result
    },
    {
      totalTasks: 0,
      successTasks: 0,
      skippedTasks: 0,
      failedTasks: 0,
      blockedTasks: 0,
      totalQuota: 0,
    }
  )
})

const successRate = computed(() => {
  if (!totals.value.totalTasks) {
    return '0%'
  }
  return `${Math.round(((totals.value.successTasks + totals.value.skippedTasks) / totals.value.totalTasks) * 100)}%`
})

const exportRows = computed(() => {
  const siteRows = visibleSiteSummaries.value.map((site) => ({
    section: 'site_summary',
    date: '',
    site_name: site.site_name,
    total_tasks: site.total_tasks,
    success_tasks: site.success_tasks,
    skipped_tasks: site.skipped_tasks,
    blocked_tasks: site.blocked_tasks,
    failed_tasks: site.failed_tasks,
    total_quota_awarded: site.total_quota_awarded,
  }))
  const dayRows = visibleDays.value.map((day) => ({
    section: 'daily_trend',
    date: day.task_date,
    site_name: '',
    total_tasks: day.total_tasks,
    success_tasks: day.success_tasks,
    skipped_tasks: day.skipped_tasks,
    blocked_tasks: day.blocked_tasks,
    failed_tasks: day.failed_tasks,
    total_quota_awarded: day.total_quota_awarded,
  }))
  return [...siteRows, ...dayRows]
})

const escapeCsv = (value: string | number) => {
  const text = String(value ?? '')
  if (text.includes('"') || text.includes(',') || text.includes('\n')) {
    return `"${text.replaceAll('"', '""')}"`
  }
  return text
}

const exportReport = () => {
  reportMessage.value = ''
  if (!exportRows.value.length) {
    reportMessage.value = t('当前没有可导出的报表数据')
    return
  }
  if (!import.meta.client) {
    return
  }
  const headers = [
    'section',
    'date',
    'site_name',
    'total_tasks',
    'success_tasks',
    'skipped_tasks',
    'blocked_tasks',
    'failed_tasks',
    'total_quota_awarded',
  ]
  const csv = [
    headers.join(','),
    ...exportRows.value.map((row) => headers.map((header) => escapeCsv((row as Record<string, string | number>)[header] ?? '')).join(',')),
  ].join('\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `task-center-report-${dateFrom.value}-${dateTo.value}.csv`
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
  reportMessage.value = t('已导出当前报表 CSV')
}

const applyFilters = async (successMessage = '报表筛选已应用') => {
  if (dateFrom.value > dateTo.value) {
    reportMessage.value = t('开始日期不能晚于结束日期')
    return
  }
  reportMessage.value = ''
  reportBusy.value = true
  try {
    await refreshReports()
    reportMessage.value = t(successMessage)
  } finally {
    reportBusy.value = false
  }
}
</script>

<template>
  <AppShell>
    <PageHeader
      :title="t('历史与报表')"
      :description="t('查看指定时间范围内的真实签到任务趋势、完成率和按站点汇总结果')"
      :eyebrow="t('任务中心')"
    >
      <template #actions>
        <div class="button-row">
          <button type="button" class="button button--secondary" :disabled="reportBusy" @click="applyFilters('报表筛选已应用')">
            {{ reportBusy ? t('筛选中') : t('应用筛选') }}
          </button>
          <button type="button" class="button button--secondary" :disabled="reportBusy" @click="exportReport">{{ t('导出报表 CSV') }}</button>
          <button type="button" class="button button--secondary" :disabled="reportBusy" @click="applyFilters('报表已刷新')">
            {{ reportBusy ? t('刷新中') : t('刷新报表') }}
          </button>
        </div>
      </template>
    </PageHeader>
    <div class="reports-filter-shell">
      <div class="reports-quick-ranges" role="group" :aria-label="t('快捷时间范围')">
        <button type="button" class="button button--secondary" :disabled="reportBusy" @click="setQuickRange(7)">
          {{ t('最近7天') }}
        </button>
        <button type="button" class="button button--secondary" :disabled="reportBusy" @click="setQuickRange(30)">
          {{ t('最近30天') }}
        </button>
      </div>
      <div class="panel-grid panel-grid--two reports-filters">
        <FieldBlock for-id="reports-date-from" :label="t('开始日期')" :description="t('定义报表统计起点')">
          <input id="reports-date-from" v-model="dateFrom" class="input input--code" type="date">
        </FieldBlock>
        <FieldBlock for-id="reports-date-to" :label="t('结束日期')" :description="t('定义报表统计终点')">
          <input id="reports-date-to" v-model="dateTo" class="input input--code" type="date">
        </FieldBlock>
        <FieldBlock for-id="reports-site-filter" :label="t('站点筛选')" :description="t('按站点聚焦汇总结果')">
          <AppSelect
            id="reports-site-filter"
            :model-value="siteFilter"
            :options="siteOptions"
            @update:model-value="siteFilter = String($event || 'all')"
          />
        </FieldBlock>
        <FieldBlock for-id="reports-date-range" :label="t('统计区间')" :description="t('当前报表请求的日期边界')">
          <input
            id="reports-date-range"
            class="input input--code"
            :value="`${reportsResponse?.date_from || dateFrom} ~ ${reportsResponse?.date_to || dateTo}`"
            readonly
          >
        </FieldBlock>
        <FieldBlock for-id="reports-show-empty-days" :label="t('趋势展示')" :description="t('筛选后只展示存在任务的日期，减少报表噪音')">
          <AppSelect
            id="reports-show-empty-days"
            :model-value="showEmptyDays ? 'all' : 'active'"
            :options="[
              { label: t('仅看有任务的日期'), value: 'active' },
              { label: t('显示空白日期'), value: 'all' },
            ]"
            @update:model-value="showEmptyDays = $event === 'all'"
          />
        </FieldBlock>
      </div>
    </div>
    <p v-if="reportMessage" class="status-note" aria-live="polite">{{ reportMessage }}</p>
    <div class="stat-grid reports-summary-grid">
      <section class="card surface-card stat-card">
        <div class="stat-card__head"><p class="stat-card__label">{{ t('累计任务数') }}</p><span class="stat-card__icon"><AppIcon name="jobs" :size="16" /></span></div>
        <div class="stat-card__value">{{ totals.totalTasks }}</div>
      </section>
      <section class="card surface-card stat-card">
        <div class="stat-card__head"><p class="stat-card__label">{{ t('综合完成率') }}</p><span class="stat-card__icon"><AppIcon name="dashboard" :size="16" /></span></div>
        <div class="stat-card__value">{{ successRate }}</div>
      </section>
      <section class="card surface-card stat-card">
        <div class="stat-card__head"><p class="stat-card__label">{{ t('累计奖励额度') }}</p><span class="stat-card__icon"><AppIcon name="checkin" :size="16" /></span></div>
        <div class="stat-card__value">{{ totals.totalQuota }}</div>
      </section>
      <section class="card surface-card stat-card">
        <div class="stat-card__head"><p class="stat-card__label">{{ t('阻塞与失败') }}</p><span class="stat-card__icon"><AppIcon name="settings" :size="16" /></span></div>
        <div class="stat-card__value">{{ totals.blockedTasks + totals.failedTasks }}</div>
      </section>
    </div>
    <div class="panel-grid panel-grid--two">
      <section class="card surface-card">
        <div class="section-head">
          <h2 class="card__title">{{ t('结果分布') }}</h2>
          <StatusBadge :label="`${reportsResponse?.date_from || dateFrom} ~ ${reportsResponse?.date_to || dateTo}`" state="info" :dot="false" />
        </div>
        <div class="status-list">
          <StatusBadge :label="t('成功 {count}', { count: totals.successTasks })" :state="totals.successTasks ? 'success' : 'neutral'" />
          <StatusBadge :label="t('跳过 {count}', { count: totals.skippedTasks })" :state="totals.skippedTasks ? 'disabled' : 'neutral'" />
          <StatusBadge :label="t('阻塞 {count}', { count: totals.blockedTasks })" :state="totals.blockedTasks ? 'failed' : 'neutral'" />
          <StatusBadge :label="t('失败 {count}', { count: totals.failedTasks })" :state="totals.failedTasks ? 'failed' : 'neutral'" />
        </div>
      </section>
      <section class="card surface-card report-site-summary-card">
        <div class="section-head">
          <h2 class="card__title">{{ t('站点汇总') }}</h2>
          <StatusBadge :label="t('筛选结果 {count}', { count: visibleSiteSummaries.length })" state="info" :dot="false" />
        </div>
        <div v-if="visibleSiteSummaries.length" class="report-site-rows">
          <article v-for="site in visibleSiteSummaries" :key="site.site_id" class="report-site-row">
            <strong>{{ site.site_name }}</strong>
            <span>{{ t('任务 {count}', { count: site.total_tasks }) }}</span>
            <span>{{ t('成功 {count}', { count: site.success_tasks }) }}</span>
            <span>{{ t('跳过 {count}', { count: site.skipped_tasks }) }}</span>
            <span>{{ t('阻塞 {count}', { count: site.blocked_tasks }) }}</span>
            <span>{{ t('失败 {count}', { count: site.failed_tasks }) }}</span>
            <span>{{ t('额度 {count}', { count: site.total_quota_awarded }) }}</span>
          </article>
        </div>
        <div v-else class="dashboard-empty">
          <span class="dashboard-empty__icon"><AppIcon name="schedules" :size="18" /></span>
          <div class="dashboard-empty__copy">
            <strong>{{ t('当前筛选下没有站点汇总') }}</strong>
            <p class="muted">{{ t('调整时间范围或站点筛选后再查看。') }}</p>
          </div>
        </div>
      </section>
      <section class="card surface-card reports-history-card" style="grid-column: 1 / -1;">
        <div class="section-head">
          <h2 class="card__title">{{ t('每日趋势') }}</h2>
          <StatusBadge :label="t('趋势日期 {count}', { count: visibleDays.length })" state="info" :dot="false" />
        </div>
        <div v-if="visibleDays.length" class="reports-day-list">
          <article v-for="day in visibleDays" :key="day.task_date" class="reports-day-row">
            <strong>{{ formatDate(day.task_date) }}</strong>
            <span>{{ t('任务 {count}', { count: day.total_tasks }) }}</span>
            <span>{{ t('成功 {count}', { count: day.success_tasks }) }}</span>
            <span>{{ t('跳过 {count}', { count: day.skipped_tasks }) }}</span>
            <span>{{ t('阻塞 {count}', { count: day.blocked_tasks }) }}</span>
            <span>{{ t('失败 {count}', { count: day.failed_tasks }) }}</span>
            <span>{{ t('额度 {count}', { count: day.total_quota_awarded }) }}</span>
          </article>
        </div>
        <div v-else class="dashboard-empty">
          <span class="dashboard-empty__icon"><AppIcon name="dashboard" :size="18" /></span>
          <div class="dashboard-empty__copy">
            <strong>{{ t(showEmptyDays ? '暂无历史任务报表' : '当前筛选下没有趋势数据') }}</strong>
            <p class="muted">{{ t(showEmptyDays ? '生成并执行今日任务后，这里会开始累计每日趋势。' : '切换为显示空白日期，或执行今日任务后再查看趋势。') }}</p>
          </div>
          <div class="button-row dashboard-empty__actions">
            <NuxtLink class="button button--secondary" to="/today">{{ t('前往今日任务') }}</NuxtLink>
          </div>
        </div>
      </section>
    </div>
  </AppShell>
</template>
