<script setup lang="ts">
import type { TaskCenterTodayTaskView } from '../types/controlPlane'

const api = useControlPlane()
const { t, translateError, formatTrigger } = useAppI18n()
const { formatDateTime } = useUiDateTime()

const actionMessage = ref('')
const actionBusy = ref<'import' | 'generate' | 'execute' | ''>('')
const statusFilter = ref<'all' | TaskCenterTodayTaskView['status']>('all')
const siteFilter = ref('all')
const authFilter = ref<'all' | TaskCenterTodayTaskView['auth_mode']>('all')
const executorFilter = ref<'all' | TaskCenterTodayTaskView['executor_type']>('all')

const { data: todayResponse, refresh: refreshToday } = await useAsyncData(
  'task-center-today-real',
  () => api.getTaskCenterToday()
)

const today = computed(() => todayResponse.value)
const tasks = computed(() => today.value?.tasks || [])
const siteOptions = computed(() => {
  const names = [...new Set(tasks.value.map((task) => task.site_name))].sort((left, right) => left.localeCompare(right))
  return [
    { label: t('全部站点'), value: 'all' },
    ...names.map((name) => ({ label: name, value: name })),
  ]
})
const statusOptions = computed(() => [
  { label: t('全部状态'), value: 'all' },
  { label: t('pending'), value: 'pending' },
  { label: t('success'), value: 'success' },
  { label: t('skipped'), value: 'skipped' },
  { label: t('blocked'), value: 'blocked' },
  { label: t('failed'), value: 'failed' },
])
const authOptions = computed(() => [
  { label: t('全部认证方式'), value: 'all' },
  { label: t('密码登录'), value: 'password' },
  { label: t('Cookie 会话'), value: 'cookies' },
  { label: t('GitHub OAuth'), value: 'github_oauth' },
  { label: t('Linux.do OAuth'), value: 'linuxdo_oauth' },
])
const executorOptions = computed(() => [
  { label: t('全部执行链'), value: 'all' },
  { label: t('标准接口'), value: 'standard_newapi' },
  { label: t('浏览器回退'), value: 'browser_fallback' },
  { label: t('旧兼容链'), value: 'legacy_plugin' },
])

const taskState = (status: TaskCenterTodayTaskView['status']) => {
  if (status === 'success') {
    return 'success'
  }
  if (status === 'failed' || status === 'blocked') {
    return 'failed'
  }
  if (status === 'skipped') {
    return 'disabled'
  }
  if (status === 'pending') {
    return 'neutral'
  }
  return 'info'
}

const executorLabel = (executorType: TaskCenterTodayTaskView['executor_type']) => {
  if (executorType === 'legacy_plugin') {
    return t('旧兼容链')
  }
  if (executorType === 'browser_fallback') {
    return t('浏览器回退')
  }
  return t('标准接口')
}
const authModeLabel = (authMode: TaskCenterTodayTaskView['auth_mode']) => {
  if (authMode === 'cookies') {
    return t('Cookie 会话')
  }
  if (authMode === 'github_oauth') {
    return t('GitHub OAuth')
  }
  if (authMode === 'linuxdo_oauth') {
    return t('Linux.do OAuth')
  }
  return t('密码登录')
}

const executeAction = async (
  action: 'import' | 'generate' | 'execute',
  runner: () => Promise<{ task_ids?: string[]; created_count?: number; created_accounts?: number }>
) => {
  actionMessage.value = ''
  actionBusy.value = action
  try {
    const result = await runner()
    if (action === 'import') {
      actionMessage.value = t('已导入站点 {sites} 个，账号 {accounts} 个', {
        sites: (result as any).created_sites || 0,
        accounts: (result as any).created_accounts || 0,
      })
    } else if (action === 'generate') {
      actionMessage.value = t('已生成今日任务 {count} 条', { count: result.created_count || 0 })
    } else {
      actionMessage.value = t('已执行今日任务 {count} 条', { count: result.task_ids?.length || 0 })
    }
    await refreshToday()
  } catch (error: any) {
    actionMessage.value = translateError(error?.data?.message || error?.message, '任务执行失败')
  } finally {
    actionBusy.value = ''
  }
}

const importConfig = async () => {
  await executeAction('import', () => api.importMainCheckinToTaskCenter())
}

const generateTasks = async () => {
  await executeAction('generate', () => api.generateTaskCenterToday())
}

const executeToday = async () => {
  await executeAction('execute', () => api.executeTaskCenterToday())
}

const retryTask = async (taskId: string) => {
  actionMessage.value = ''
  try {
    await api.retryTaskCenterTask(taskId)
    actionMessage.value = t('任务已重置为待执行')
    await refreshToday()
  } catch (error: any) {
    actionMessage.value = translateError(error?.data?.message || error?.message, '任务重试失败')
  }
}

const runTask = async (taskId: string) => {
  actionMessage.value = ''
  try {
    await api.executeTaskCenterTask(taskId)
    actionMessage.value = t('账号任务已执行')
    await refreshToday()
  } catch (error: any) {
    actionMessage.value = translateError(error?.data?.message || error?.message, '任务执行失败')
  }
}

const visibleTasks = computed(() => {
  return tasks.value
    .filter((task) => (statusFilter.value === 'all' ? true : task.status === statusFilter.value))
    .filter((task) => (siteFilter.value === 'all' ? true : task.site_name === siteFilter.value))
    .filter((task) => (authFilter.value === 'all' ? true : task.auth_mode === authFilter.value))
    .filter((task) => (executorFilter.value === 'all' ? true : task.executor_type === executorFilter.value))
    .sort((left, right) => {
    const leftTime = left.started_at || left.finished_at || left.task_date
    const rightTime = right.started_at || right.finished_at || right.task_date
    return String(rightTime).localeCompare(String(leftTime))
  })
})
</script>

<template>
  <AppShell>
    <PageHeader
      :title="t('今日任务')"
      :description="t('直接管理今天的站点账号签到任务，包括导入、生成、批量执行和单账号重试')"
      :eyebrow="t('任务中心')"
    >
      <template #actions>
        <div class="button-row">
          <button class="button button--secondary" :disabled="actionBusy !== ''" @click="importConfig">
            {{ actionBusy === 'import' ? t('导入中') : t('导入主签到配置') }}
          </button>
          <button class="button button--secondary" :disabled="actionBusy !== ''" @click="generateTasks">
            {{ actionBusy === 'generate' ? t('生成中') : t('生成今日任务') }}
          </button>
          <button class="button button--primary" :disabled="actionBusy !== ''" @click="executeToday">
            {{ actionBusy === 'execute' ? t('执行中') : t('执行待处理任务') }}
          </button>
          <button class="button button--secondary" :disabled="actionBusy !== ''" @click="refreshToday()">{{ t('刷新今日任务') }}</button>
        </div>
      </template>
    </PageHeader>
    <div class="button-row page-summary-strip">
      <StatusBadge :label="t('今日任务 {count}', { count: today?.total_tasks || 0 })" :state="(today?.total_tasks || 0) > 0 ? 'configured' : 'unconfigured'" />
      <StatusBadge :label="t('待处理 {count}', { count: (today?.pending_tasks || 0) + (today?.running_tasks || 0) })" :state="((today?.pending_tasks || 0) + (today?.running_tasks || 0)) > 0 ? 'info' : 'neutral'" />
      <StatusBadge :label="t('成功 {count}', { count: today?.success_tasks || 0 })" :state="(today?.success_tasks || 0) > 0 ? 'success' : 'neutral'" />
      <StatusBadge :label="t('阻塞 {count}', { count: today?.blocked_tasks || 0 })" :state="(today?.blocked_tasks || 0) > 0 ? 'failed' : 'neutral'" />
      <StatusBadge :label="t('失败 {count}', { count: today?.failed_tasks || 0 })" :state="(today?.failed_tasks || 0) > 0 ? 'failed' : 'neutral'" />
      <StatusBadge :label="t('今日额度 {count}', { count: today?.total_quota_awarded || 0 })" :state="(today?.total_quota_awarded || 0) > 0 ? 'configured' : 'neutral'" />
    </div>
    <p v-if="actionMessage" class="status-note" aria-live="polite">{{ actionMessage }}</p>
    <section class="card surface-card">
      <div class="section-head">
        <h2 class="card__title">{{ t('账号任务列表') }}</h2>
        <StatusBadge :label="t('筛选结果 {count}', { count: visibleTasks.length })" state="info" :dot="false" />
      </div>
      <div class="panel-grid panel-grid--two" style="margin-bottom: 16px;">
        <FieldBlock for-id="today-status-filter" :label="t('状态筛选')" :description="t('只看待处理、成功、阻塞或失败账号')">
          <AppSelect
            id="today-status-filter"
            :model-value="statusFilter"
            :options="statusOptions"
            @update:model-value="statusFilter = ($event as typeof statusFilter.value)"
          />
        </FieldBlock>
        <FieldBlock for-id="today-site-filter" :label="t('站点筛选')" :description="t('按站点缩小今天的账号任务列表')">
          <AppSelect
            id="today-site-filter"
            :model-value="siteFilter"
            :options="siteOptions"
            @update:model-value="siteFilter = String($event || 'all')"
          />
        </FieldBlock>
        <FieldBlock for-id="today-auth-filter" :label="t('认证方式筛选')" :description="t('按密码、Cookie 或 OAuth 方式筛选账号任务')">
          <AppSelect
            id="today-auth-filter"
            :model-value="authFilter"
            :options="authOptions"
            @update:model-value="authFilter = ($event as typeof authFilter.value)"
          />
        </FieldBlock>
        <FieldBlock for-id="today-executor-filter" :label="t('执行链筛选')" :description="t('区分标准接口、浏览器回退和旧链路执行')">
          <AppSelect
            id="today-executor-filter"
            :model-value="executorFilter"
            :options="executorOptions"
            @update:model-value="executorFilter = ($event as typeof executorFilter.value)"
          />
        </FieldBlock>
      </div>
      <div v-if="visibleTasks.length" class="stack-list">
        <article v-for="task in visibleTasks" :key="task.id" class="subcard">
          <div class="section-head">
            <strong>{{ task.account_display_name }}</strong>
            <StatusBadge :label="t(task.status)" :state="taskState(task.status)" />
          </div>
          <p class="muted">{{ task.site_name }} / {{ task.username }}</p>
          <div class="status-list">
            <StatusBadge :label="`${t('认证方式')} ${authModeLabel(task.auth_mode)}`" state="neutral" />
            <StatusBadge :label="`${t('触发方式')} ${formatTrigger(task.trigger_type)}`" state="neutral" />
            <StatusBadge :label="`${t('执行链')} ${executorLabel(task.executor_type)}`" state="info" />
            <StatusBadge :label="t('尝试次数 {count}', { count: task.attempt_count })" state="neutral" />
            <StatusBadge :label="t('奖励额度 {count}', { count: task.quota_awarded })" :state="task.quota_awarded > 0 ? 'configured' : 'neutral'" />
          </div>
          <p class="muted">
            {{ t('开始 {value}', { value: formatDateTime(task.started_at) }) }} /
            {{ t('结束 {value}', { value: formatDateTime(task.finished_at) }) }}
          </p>
          <p v-if="task.error_message" style="margin: 0;">{{ translateError(task.error_message, '任务执行失败') }}</p>
          <div class="button-row">
            <button
              v-if="task.status === 'pending'"
              class="button button--primary"
              @click="runTask(task.id)"
            >
              {{ t('执行账号任务') }}
            </button>
            <button
              v-if="task.status === 'failed' || task.status === 'blocked'"
              class="button button--secondary"
              @click="retryTask(task.id)"
            >
              {{ t('重置后重试') }}
            </button>
          </div>
        </article>
      </div>
      <div v-else-if="tasks.length" class="dashboard-empty">
        <span class="dashboard-empty__icon"><AppIcon name="jobs" :size="18" /></span>
        <div class="dashboard-empty__copy">
          <strong>{{ t('当前筛选下没有账号任务') }}</strong>
          <p class="muted">{{ t('放宽筛选条件后可查看其他站点或认证方式的任务。') }}</p>
        </div>
      </div>
      <div v-else class="dashboard-empty">
        <span class="dashboard-empty__icon"><AppIcon name="jobs" :size="18" /></span>
        <div class="dashboard-empty__copy">
          <strong>{{ t('今日还没有生成账号任务') }}</strong>
          <p class="muted">{{ t('先导入主签到配置，再生成今日任务，最后批量执行待处理账号。') }}</p>
        </div>
      </div>
    </section>
  </AppShell>
</template>
