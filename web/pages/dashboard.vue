<script setup lang="ts">
const api = useControlPlane()
const { locale, t, formatDeployMode } = useAppI18n()

const formatDateTime = (value: string | null | undefined) => {
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

const [
  { data: dashboardResponse, refresh: refreshDashboard },
  { data: summaryResponse, refresh: refreshSummary },
  { data: sitesResponse, refresh: refreshSites },
  { data: todayResponse, refresh: refreshToday },
] = await Promise.all([
  useAsyncData('dashboard-runtime-real', () => api.getDashboard()),
  useAsyncData('dashboard-summary-real', () => api.getTaskCenterSummary()),
  useAsyncData('dashboard-sites-real', () => api.listSites()),
  useAsyncData('dashboard-today-real', () => api.getTaskCenterToday()),
])

const status = computed(() => dashboardResponse.value?.status)
const summary = computed(() => summaryResponse.value)
const today = computed(() => summary.value?.today)
const recentAccounts = computed(() => summary.value?.recent_accounts || [])
const recentIncidents = computed(() => summary.value?.recent_incidents || [])
const sites = computed(() => sitesResponse.value || [])
const todayTasks = computed(() => todayResponse.value)
const siteNameById = computed(() => {
  return Object.fromEntries(sites.value.map((site) => [site.id, site.name]))
})

const refreshAll = async () => {
  await Promise.all([refreshDashboard(), refreshSummary(), refreshSites(), refreshToday()])
}

const cards = computed(() => [
  { label: '站点资产', value: String(today.value?.total_sites || 0), icon: 'sites' },
  { label: '启用账号', value: String(today.value?.enabled_accounts || 0), icon: 'accounts' },
  { label: '今日成功账号', value: String(today.value?.today_success || 0), icon: 'dashboard' },
  { label: '今日异常账号', value: String((today.value?.today_failed || 0) + (today.value?.today_blocked || 0)), icon: 'incidents' },
])

const homeSummary = computed(() => [
  { label: `${t('部署模式')} ${formatDeployMode(status.value?.deploy_mode)}`, state: status.value?.deploy_mode === 'control_plane' ? 'enabled' : 'info' },
  { label: `${t('本地调度')} ${t(status.value?.scheduler_enabled ? '已启用' : '已禁用')}`, state: status.value?.scheduler_enabled ? 'enabled' : 'disabled' },
  { label: `${t('今日待处理')} ${today.value?.today_pending || 0}`, state: (today.value?.today_pending || 0) > 0 ? 'info' : 'neutral' },
  { label: `${t('今日累计额度')} ${today.value?.today_quota_awarded || 0}`, state: (today.value?.today_quota_awarded || 0) > 0 ? 'configured' : 'neutral' },
])
</script>

<template>
  <AppShell>
    <PageHeader
      :title="t('首页')"
      :description="t('从今日任务、异常和收益三个视角查看多站点多账号签到系统的当前状态')"
      :eyebrow="t('任务中心')"
    >
      <template #actions>
        <div class="button-row">
          <button class="button button--secondary" @click="refreshAll()">{{ t('刷新首页') }}</button>
        </div>
      </template>
    </PageHeader>
    <div class="button-row page-summary-strip">
      <StatusBadge v-for="item in homeSummary" :key="item.label" :label="item.label" :state="item.state" />
    </div>
    <div class="stat-grid">
      <section v-for="item in cards" :key="item.label" class="card surface-card stat-card">
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
      <section class="card surface-card dashboard-panel">
        <div class="section-head">
          <h2 class="card__title">{{ t('站点概览') }}</h2>
          <StatusBadge :label="t('真实站点资产')" state="info" :dot="false" />
        </div>
        <div v-if="sites.length" class="stack-list">
          <article v-for="site in sites.slice(0, 6)" :key="site.id" class="subcard">
            <div class="section-head">
              <strong>{{ site.name }}</strong>
              <StatusBadge :label="site.enabled ? t('已启用') : t('已禁用')" :state="site.enabled ? 'configured' : 'disabled'" />
            </div>
            <p class="muted">{{ site.base_url }}</p>
            <div class="status-list">
              <StatusBadge :label="`${t('兼容等级')} ${t(site.compatibility_level)}`" state="info" />
              <StatusBadge :label="`${t('探测状态')} ${t(site.last_probe_status)}`" state="neutral" />
              <StatusBadge :label="site.checkin_enabled_detected ? t('签到已开启') : t(site.checkin_enabled_detected === false ? '签到未开启' : '签到能力待探测')" :state="site.checkin_enabled_detected ? 'success' : 'neutral'" />
            </div>
          </article>
        </div>
        <div v-else class="dashboard-empty">
          <span class="dashboard-empty__icon"><AppIcon name="sites" :size="18" /></span>
          <div class="dashboard-empty__copy">
            <strong>{{ t('暂无站点记录') }}</strong>
            <p class="muted">{{ t('请先在站点页录入 new-api 站点。') }}</p>
          </div>
        </div>
      </section>
      <section class="card surface-card dashboard-panel">
        <div class="section-head">
          <h2 class="card__title">{{ t('今日任务快照') }}</h2>
          <StatusBadge :label="t('任务日期 {value}', { value: todayTasks?.task_date || '-' })" state="info" :dot="false" />
        </div>
        <div class="status-list">
          <StatusBadge :label="t('成功 {count}', { count: todayTasks?.success_tasks || 0 })" :state="(todayTasks?.success_tasks || 0) > 0 ? 'success' : 'neutral'" />
          <StatusBadge :label="t('跳过 {count}', { count: todayTasks?.skipped_tasks || 0 })" :state="(todayTasks?.skipped_tasks || 0) > 0 ? 'disabled' : 'neutral'" />
          <StatusBadge :label="t('阻塞 {count}', { count: todayTasks?.blocked_tasks || 0 })" :state="(todayTasks?.blocked_tasks || 0) > 0 ? 'failed' : 'neutral'" />
          <StatusBadge :label="t('失败 {count}', { count: todayTasks?.failed_tasks || 0 })" :state="(todayTasks?.failed_tasks || 0) > 0 ? 'failed' : 'neutral'" />
        </div>
        <div v-if="todayTasks?.tasks?.length" class="stack-list">
          <article v-for="task in todayTasks.tasks.slice(0, 6)" :key="task.id" class="subcard">
            <div class="section-head">
              <strong>{{ task.account_display_name }}</strong>
              <StatusBadge :label="t(task.status)" :state="task.status === 'success' ? 'success' : task.status === 'failed' || task.status === 'blocked' ? 'failed' : 'neutral'" />
            </div>
            <p class="muted">{{ task.site_name }} / {{ task.username }}</p>
            <div class="status-list">
              <StatusBadge :label="t('奖励额度 {count}', { count: task.quota_awarded })" :state="task.quota_awarded ? 'configured' : 'neutral'" />
              <StatusBadge :label="t('开始 {value}', { value: formatDateTime(task.started_at) })" state="neutral" />
            </div>
          </article>
        </div>
        <div v-else class="dashboard-empty">
          <span class="dashboard-empty__icon"><AppIcon name="jobs" :size="18" /></span>
          <div class="dashboard-empty__copy">
            <strong>{{ t('今日还没有生成账号任务') }}</strong>
            <p class="muted">{{ t('请前往今日任务页导入配置并生成当天任务。') }}</p>
          </div>
        </div>
      </section>
    </div>
    <div class="panel-grid panel-grid--two dashboard-panels">
      <section class="card surface-card dashboard-panel">
        <div class="section-head">
          <h2 class="card__title">{{ t('账号动态') }}</h2>
          <StatusBadge :label="t('最近更新账号')" state="info" :dot="false" />
        </div>
        <div v-if="recentAccounts.length" class="stack-list">
          <article v-for="account in recentAccounts" :key="account.id" class="subcard">
            <div class="section-head">
              <strong>{{ account.display_name || account.username }}</strong>
              <StatusBadge :label="t(account.last_checkin_status)" :state="account.last_checkin_status === 'success' ? 'success' : account.last_checkin_status === 'failed' || account.last_checkin_status === 'blocked' ? 'failed' : 'neutral'" />
            </div>
            <p class="muted">{{ siteNameById[account.site_id] || t('未知站点') }} / {{ account.username }}</p>
            <div class="status-list">
              <StatusBadge :label="t('累计签到 {count}', { count: account.total_checkins })" state="neutral" />
              <StatusBadge :label="t('累计额度 {count}', { count: account.total_quota_awarded })" :state="account.total_quota_awarded ? 'configured' : 'neutral'" />
            </div>
          </article>
        </div>
      </section>
      <section class="card surface-card dashboard-panel">
        <div class="section-head">
          <h2 class="card__title">{{ t('最近异常') }}</h2>
          <StatusBadge :label="t('异常中心摘要')" state="info" :dot="false" />
        </div>
        <div v-if="recentIncidents.length" class="stack-list">
          <article v-for="incident in recentIncidents" :key="incident.id" class="subcard">
            <div class="section-head">
              <strong>{{ incident.display_name }}</strong>
              <StatusBadge :label="t(incident.status)" :state="incident.status === 'failed' || incident.status === 'blocked' ? 'failed' : 'neutral'" />
            </div>
            <p class="muted">{{ incident.site_name }}</p>
            <p style="margin: 0;">{{ incident.last_error_message }}</p>
            <p class="muted">{{ formatDateTime(incident.last_checkin_at || incident.last_seen_at) }}</p>
          </article>
        </div>
        <div v-else class="dashboard-empty">
          <span class="dashboard-empty__icon"><AppIcon name="incidents" :size="18" /></span>
          <div class="dashboard-empty__copy">
            <strong>{{ t('最近没有异常记录') }}</strong>
            <p class="muted">{{ t('当前账号签到链路没有失败或阻塞记录。') }}</p>
          </div>
        </div>
      </section>
    </div>
  </AppShell>
</template>
