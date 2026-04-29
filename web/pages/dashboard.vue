<script setup lang="ts">
const api = useControlPlane()
const { t, translateRequestError } = useAppI18n()

const runBusy = ref(false)
const refreshBusy = ref(false)
const actionMessage = ref('')

const [
  { data: dashboardResponse, refresh: refreshDashboard },
  { data: summaryResponse, refresh: refreshSummary },
  { data: sitesResponse, refresh: refreshSites },
  { data: accountsResponse, refresh: refreshAccounts },
  { data: todayResponse, refresh: refreshToday },
] = await Promise.all([
  useAsyncData('dashboard-runtime-daily-ops', () => api.getDashboard()),
  useAsyncData('dashboard-summary-daily-ops', () => api.getTaskCenterSummary()),
  useAsyncData('dashboard-sites-daily-ops', () => api.listSites()),
  useAsyncData('dashboard-accounts-daily-ops', () => api.listAccounts()),
  useAsyncData('dashboard-today-daily-ops', () => api.getTaskCenterToday()),
])

const status = computed(() => dashboardResponse.value?.status)
const summaryEnvelope = computed(() => summaryResponse.value)
const summary = computed(() => summaryEnvelope.value?.today)
const sites = computed(() => sitesResponse.value || [])
const accounts = computed(() => accountsResponse.value || [])
const today = computed(() => todayResponse.value)
const recentAccounts = computed(() => summaryEnvelope.value?.recent_accounts || [])
const todayTasks = computed(() => today.value?.tasks || [])
const todayTaskAccountIds = computed(() => new Set(todayTasks.value.map((task) => task.account_id)))
const recentAccountAlerts = computed(() => recentAccounts.value
  .filter((account) => account.enabled)
  .filter((account) => ['failed', 'blocked'].includes(account.last_checkin_status))
  .filter((account) => !todayTaskAccountIds.value.has(account.id)))
const failedTasks = computed(() => (today.value?.failed_tasks || 0) + (today.value?.blocked_tasks || 0) + recentAccountAlerts.value.length)
const pendingTasks = computed(() => (today.value?.pending_tasks || 0) + (today.value?.running_tasks || 0))
const totalAccounts = computed(() => summary.value?.enabled_accounts || accounts.value.filter((account) => account.enabled).length)
const successAccounts = computed(() => today.value?.success_tasks || summary.value?.today_success || 0)
const quotaAwarded = computed(() => today.value?.total_quota_awarded || summary.value?.today_quota_awarded || 0)
const hasTodayTasks = computed(() => (today.value?.total_tasks || 0) > 0)

const refreshAll = async () => {
  await Promise.all([refreshDashboard(), refreshSummary(), refreshSites(), refreshAccounts(), refreshToday()])
}

const refreshWithMessage = async () => {
  refreshBusy.value = true
  actionMessage.value = ''
  try {
    await refreshAll()
    actionMessage.value = t('首页已刷新')
  } catch (error: any) {
    actionMessage.value = translateRequestError(error, '首页刷新失败')
  } finally {
    refreshBusy.value = false
  }
}

const runToday = async () => {
  if (runBusy.value) {
    return
  }
  runBusy.value = true
  actionMessage.value = ''
  try {
    await refreshToday()
    if ((todayResponse.value?.total_tasks || 0) === 0) {
      await api.generateTaskCenterToday()
      await refreshToday()
    }
    if ((todayResponse.value?.pending_tasks || 0) > 0) {
      const result = await api.executeTaskCenterToday()
      actionMessage.value = t('已执行今日签到：成功 {success}，跳过 {skipped}，阻塞 {blocked}，失败 {failed}', {
        success: result.success_count,
        skipped: result.skipped_count,
        blocked: result.blocked_count,
        failed: result.failed_count,
      })
    } else {
      actionMessage.value = t('当前没有待执行任务')
    }
    await refreshAll()
  } catch (error: any) {
    actionMessage.value = translateRequestError(error, '今日签到执行失败')
  } finally {
    runBusy.value = false
  }
}
</script>

<template>
  <AppShell>
    <PageHeader
      :title="t('今日签到运营台')"
      :description="t('面向普通用户的日常入口：先看今日状态，再执行签到，最后处理异常。')"
      :eyebrow="t('首页')"
    >
      <template #actions>
        <NuxtLink class="button button--secondary" to="/setup">{{ t('接入站点账号') }}</NuxtLink>
      </template>
    </PageHeader>
    <p v-if="actionMessage" class="status-note" aria-live="polite">{{ actionMessage }}</p>
    <DailyOpsHero
      :total-accounts="totalAccounts"
      :success-accounts="successAccounts"
      :pending-accounts="pendingTasks"
      :failed-accounts="failedTasks"
      :quota-awarded="quotaAwarded"
      :has-tasks="hasTodayTasks"
      :busy="runBusy || refreshBusy"
      @run="runToday"
      @refresh="refreshWithMessage"
    />
    <div class="daily-ops-grid">
      <DailyTaskWorkbench :tasks="today?.tasks || []" :recent-accounts="recentAccounts" />
      <div class="daily-ops-side-stack">
        <DashboardControlConsole
          :status="status"
          :sites="sites"
          :accounts="accounts"
          :today="today"
          :failed-count="failedTasks"
          :pending-count="pendingTasks"
        />
        <section class="card surface-card daily-ops-next">
          <div class="section-head">
            <h2 class="card__title">{{ t('下一步') }}</h2>
            <StatusBadge :label="t(status?.scheduler_enabled ? '自动调度已启用' : '自动调度未启用')" :state="status?.scheduler_enabled ? 'success' : 'neutral'" />
          </div>
          <div class="daily-ops-step-list">
            <NuxtLink to="/setup" class="daily-ops-step">
              <strong>{{ t('接入站点和账号') }}</strong>
              <span>{{ t('当前站点 {sites} 个，启用账号 {accounts} 个', { sites: sites.length, accounts: totalAccounts }) }}</span>
            </NuxtLink>
            <NuxtLink to="/today" class="daily-ops-step">
              <strong>{{ t('复核今日任务') }}</strong>
              <span>{{ t('今日任务 {count} 条，待处理 {pending} 条', { count: today?.total_tasks || 0, pending: pendingTasks }) }}</span>
            </NuxtLink>
            <NuxtLink to="/incidents" class="daily-ops-step">
              <strong>{{ t('处理异常账号') }}</strong>
              <span>{{ t('异常或阻塞 {count} 条', { count: failedTasks }) }}</span>
            </NuxtLink>
          </div>
        </section>
      </div>
    </div>
  </AppShell>
</template>
