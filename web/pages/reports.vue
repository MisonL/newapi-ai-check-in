<script setup lang="ts">
import type { TaskCenterReportSiteView } from '../types/controlPlane'

const api = useControlPlane()
const { locale, t } = useAppI18n()

const formatDateInput = (value: Date) => {
  const year = value.getFullYear()
  const month = String(value.getMonth() + 1).padStart(2, '0')
  const day = String(value.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

const today = new Date()
const defaultDateTo = formatDateInput(today)
const defaultDateFrom = formatDateInput(new Date(today.getTime() - (29 * 24 * 60 * 60 * 1000)))

const dateFrom = ref(defaultDateFrom)
const dateTo = ref(defaultDateTo)
const siteFilter = ref('all')
const reportBusy = ref(false)
const reportMessage = ref('')

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

const formatDate = (value: string) => new Intl.DateTimeFormat(locale.value, {
  month: '2-digit',
  day: '2-digit',
}).format(new Date(value))

const applyFilters = async () => {
  if (dateFrom.value > dateTo.value) {
    reportMessage.value = t('开始日期不能晚于结束日期')
    return
  }
  reportMessage.value = ''
  reportBusy.value = true
  try {
    await refreshReports()
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
          <button class="button button--secondary" :disabled="reportBusy" @click="applyFilters">
            {{ reportBusy ? t('筛选中') : t('应用筛选') }}
          </button>
          <button class="button button--secondary" :disabled="reportBusy" @click="applyFilters">{{ t('刷新报表') }}</button>
        </div>
      </template>
    </PageHeader>
    <div class="panel-grid panel-grid--two" style="margin-bottom: 24px;">
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
    </div>
    <p v-if="reportMessage" class="status-note" aria-live="polite">{{ reportMessage }}</p>
    <div class="stat-grid">
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
      <section class="card surface-card">
        <div class="section-head">
          <h2 class="card__title">{{ t('站点汇总') }}</h2>
          <StatusBadge :label="t('筛选结果 {count}', { count: visibleSiteSummaries.length })" state="info" :dot="false" />
        </div>
        <div v-if="visibleSiteSummaries.length" class="stack-list">
          <article v-for="site in visibleSiteSummaries" :key="site.site_id" class="subcard">
            <div class="section-head">
              <strong>{{ site.site_name }}</strong>
              <StatusBadge :label="t('任务 {count}', { count: site.total_tasks })" :state="site.total_tasks ? 'configured' : 'neutral'" />
            </div>
            <div class="status-list">
              <StatusBadge :label="t('成功 {count}', { count: site.success_tasks })" :state="site.success_tasks ? 'success' : 'neutral'" />
              <StatusBadge :label="t('跳过 {count}', { count: site.skipped_tasks })" :state="site.skipped_tasks ? 'disabled' : 'neutral'" />
              <StatusBadge :label="t('阻塞 {count}', { count: site.blocked_tasks })" :state="site.blocked_tasks ? 'failed' : 'neutral'" />
              <StatusBadge :label="t('失败 {count}', { count: site.failed_tasks })" :state="site.failed_tasks ? 'failed' : 'neutral'" />
              <StatusBadge :label="t('额度 {count}', { count: site.total_quota_awarded })" :state="site.total_quota_awarded ? 'configured' : 'neutral'" />
            </div>
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
      <section class="card surface-card" style="grid-column: 1 / -1;">
        <div class="section-head">
          <h2 class="card__title">{{ t('每日趋势') }}</h2>
          <StatusBadge :label="t('真实任务汇总')" state="info" :dot="false" />
        </div>
        <div v-if="days.length" class="stack-list">
          <article v-for="day in [...days].reverse()" :key="day.task_date" class="subcard">
            <div class="section-head">
              <strong>{{ formatDate(day.task_date) }}</strong>
              <StatusBadge :label="t('任务 {count}', { count: day.total_tasks })" :state="day.total_tasks ? 'configured' : 'neutral'" />
            </div>
            <div class="status-list">
              <StatusBadge :label="t('成功 {count}', { count: day.success_tasks })" :state="day.success_tasks ? 'success' : 'neutral'" />
              <StatusBadge :label="t('跳过 {count}', { count: day.skipped_tasks })" :state="day.skipped_tasks ? 'disabled' : 'neutral'" />
              <StatusBadge :label="t('阻塞 {count}', { count: day.blocked_tasks })" :state="day.blocked_tasks ? 'failed' : 'neutral'" />
              <StatusBadge :label="t('失败 {count}', { count: day.failed_tasks })" :state="day.failed_tasks ? 'failed' : 'neutral'" />
              <StatusBadge :label="t('额度 {count}', { count: day.total_quota_awarded })" :state="day.total_quota_awarded ? 'configured' : 'neutral'" />
            </div>
          </article>
        </div>
        <div v-else class="dashboard-empty">
          <span class="dashboard-empty__icon"><AppIcon name="dashboard" :size="18" /></span>
          <div class="dashboard-empty__copy">
            <strong>{{ t('暂无历史任务报表') }}</strong>
            <p class="muted">{{ t('生成并执行今日任务后，这里会开始累计每日趋势。') }}</p>
          </div>
          <div class="button-row dashboard-empty__actions">
            <NuxtLink class="button button--secondary" to="/today">{{ t('前往今日任务') }}</NuxtLink>
          </div>
        </div>
      </section>
    </div>
  </AppShell>
</template>
