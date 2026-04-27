<script setup lang="ts">
import type { TaskCenterTodayResponse, TaskCenterTodayTaskView } from '../types/controlPlane'

type TopAction = 'import' | 'generate' | 'execute' | 'refresh' | 'check'
type TopActionResult = {
  task_ids?: string[]
  total_accounts?: number
  created_count?: number
  created_sites?: number
  created_accounts?: number
  executed_count?: number
  success_count?: number
  skipped_count?: number
  blocked_count?: number
  failed_count?: number
}
type TopActionReceipt = {
  message: string
  sequence: number
  time: string
}
type TodayStats = Pick<
  TaskCenterTodayResponse,
  | 'total_tasks'
  | 'pending_tasks'
  | 'running_tasks'
  | 'success_tasks'
  | 'skipped_tasks'
  | 'blocked_tasks'
  | 'failed_tasks'
  | 'total_quota_awarded'
>
type ActionResultState = 'changed' | 'unchanged' | 'failed'
type ActionResultPanelView = {
  title: string
  subtitle: string
  state: ActionResultState
  stateLabel: string
  items: Array<{ label: string, value: string }>
  details: string[]
}

const api = useControlPlane()
const { t, translateError, translateRequestError } = useAppI18n()
const { formatDateTime } = useUiDateTime()

const actionMessage = ref('')
const actionBusy = ref<TopAction | ''>('')
const recentAction = ref<TopAction | ''>('')
const lastActionResult = ref<ActionResultPanelView | null>(null)
const actionReceipts = reactive<Record<TopAction, TopActionReceipt | null>>({
  import: null,
  generate: null,
  execute: null,
  refresh: null,
  check: null,
})
const taskActionBusy = ref<{ taskId: string, action: 'run' | 'retry' } | null>(null)
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
const hasTasks = computed(() => (today.value?.total_tasks || 0) > 0)
const pendingTaskCount = computed(() => today.value?.pending_tasks || 0)
const operationBusy = computed(() => actionBusy.value !== '' || taskActionBusy.value !== null)
const pendingActionActive = computed(() => actionBusy.value === 'execute' || actionBusy.value === 'check')
const pendingActionRecent = computed(() => ['execute', 'check'].includes(recentAction.value))
const actionStatusMessage = computed(() => {
  if (actionBusy.value === 'import') {
    return t('正在导入旧主签到配置，请稍候')
  }
  if (actionBusy.value === 'generate') {
    return t('正在生成今日任务，请稍候')
  }
  if (actionBusy.value === 'execute') {
    return t('正在执行待处理任务，请稍候')
  }
  if (actionBusy.value === 'refresh') {
    return t('正在刷新今日任务，请稍候')
  }
  if (actionBusy.value === 'check') {
    return t('正在检查待处理任务，请稍候')
  }
  return actionMessage.value
})
const pendingActionReceipt = computed(() => {
  const executeReceipt = actionReceipts.execute
  const checkReceipt = actionReceipts.check
  if (!executeReceipt) {
    return checkReceipt
  }
  if (!checkReceipt) {
    return executeReceipt
  }
  return checkReceipt.sequence > executeReceipt.sequence ? checkReceipt : executeReceipt
})

const formatActionClock = () => {
  const now = new Date()
  const hours = String(now.getHours()).padStart(2, '0')
  const minutes = String(now.getMinutes()).padStart(2, '0')
  const seconds = String(now.getSeconds()).padStart(2, '0')
  return `${hours}:${minutes}:${seconds}`
}

const topActionStateClass = (action: TopAction) => ({
  'button--busy': actionBusy.value === action,
  'button--recent-action': recentAction.value === action && actionBusy.value === '',
})

let actionReceiptSequence = 0

const completeAction = (action: TopAction, message: string) => {
  const time = formatActionClock()
  actionMessage.value = t('最后反馈：{message}（{time}）', {
    message,
    time,
  })
  actionReceipts[action] = {
    message,
    sequence: actionReceiptSequence += 1,
    time,
  }
  recentAction.value = action
}

const actionReceiptText = (receipt?: TopActionReceipt | null) => receipt
  ? t('已响应 {time}', { time: receipt.time })
  : ''

const emptyStats = (): TodayStats => ({
  total_tasks: 0,
  pending_tasks: 0,
  running_tasks: 0,
  success_tasks: 0,
  skipped_tasks: 0,
  blocked_tasks: 0,
  failed_tasks: 0,
  total_quota_awarded: 0,
})

const captureStats = (value?: TaskCenterTodayResponse | null): TodayStats => ({
  ...emptyStats(),
  ...(value || {}),
})

const currentStats = () => captureStats(todayResponse.value)

const statsChanged = (before: TodayStats, after: TodayStats) => {
  return Object.keys(emptyStats()).some((key) => {
    const statKey = key as keyof TodayStats
    return before[statKey] !== after[statKey]
  })
}

const actionLabel = (action: TopAction) => {
  if (action === 'generate') {
    return t('生成今日任务')
  }
  if (action === 'execute') {
    return t('执行待处理任务')
  }
  if (action === 'check') {
    return t('检查待处理任务')
  }
  if (action === 'import') {
    return t('导入旧主签到配置')
  }
  return t('刷新今日任务')
}

const actionResultDetails = (action: TopAction, result: TopActionResult | undefined, after: TodayStats) => {
  if (action === 'generate') {
    return t('生成结果：可用账号 {total}，新增任务 {created}，已存在 {existing}', {
      total: result?.total_accounts || 0,
      created: result?.created_count || 0,
      existing: (result as { existing_count?: number } | undefined)?.existing_count || 0,
    })
  }
  if (action === 'import') {
    return t('导入结果：新增站点 {createdSites}，更新站点 {updatedSites}，新增账号 {createdAccounts}，更新账号 {updatedAccounts}，跳过账号 {skippedAccounts}', {
      createdSites: result?.created_sites || 0,
      updatedSites: (result as { updated_sites?: number } | undefined)?.updated_sites || 0,
      createdAccounts: result?.created_accounts || 0,
      updatedAccounts: (result as { updated_accounts?: number } | undefined)?.updated_accounts || 0,
      skippedAccounts: (result as { skipped_accounts?: number } | undefined)?.skipped_accounts || 0,
    })
  }
  if (action === 'execute') {
    return t('执行结果：选中 {selected}，实际执行 {executed}，成功 {success}，跳过 {skipped}，阻塞 {blocked}，失败 {failed}', {
      selected: (result as { total_selected?: number } | undefined)?.total_selected || 0,
      executed: result?.executed_count || 0,
      success: result?.success_count || 0,
      skipped: result?.skipped_count || 0,
      blocked: result?.blocked_count || 0,
      failed: result?.failed_count || 0,
    })
  }
  if (action === 'check') {
    return t('检查结果：待处理任务 {pending} 条', { pending: after.pending_tasks })
  }
  return t('刷新结果：已重新读取服务器今日任务')
}

const recordActionResult = (
  action: TopAction,
  message: string,
  before: TodayStats,
  after: TodayStats,
  result?: TopActionResult,
  failed = false,
) => {
  const changed = statsChanged(before, after)
  lastActionResult.value = {
    title: t('本次操作结果：{action}', { action: actionLabel(action) }),
    subtitle: t('最后反馈：{message}（{time}）', {
      message,
      time: formatActionClock(),
    }),
    state: failed ? 'failed' : changed ? 'changed' : 'unchanged',
    stateLabel: failed ? t('操作失败') : changed ? t('数据已更新') : t('数据无变化'),
    items: [
      { label: t('当前任务'), value: String(after.total_tasks) },
      { label: t('待处理'), value: String(after.pending_tasks + after.running_tasks) },
      { label: t('成功'), value: String(after.success_tasks) },
      { label: t('失败或阻塞'), value: String(after.failed_tasks + after.blocked_tasks) },
      { label: t('今日额度'), value: String(after.total_quota_awarded) },
    ],
    details: [
      actionResultDetails(action, result, after),
      changed ? t('任务列表已根据服务器返回更新') : t('列表数据无变化，当前内容已是最新状态'),
    ],
  }
}

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

const batchMessage = (result: TopActionResult) => {
  if (!result.executed_count) {
    return t('当前没有待执行任务')
  }
  return t('已批量执行 {count} 条：成功 {success}，跳过 {skipped}，阻塞 {blocked}，失败 {failed}', {
    count: result.executed_count,
    success: result.success_count || 0,
    skipped: result.skipped_count || 0,
    blocked: result.blocked_count || 0,
    failed: result.failed_count || 0,
  })
}

const generationMessage = (result: { total_accounts?: number, created_count?: number }) => {
  if (!result.total_accounts) {
    return t('没有可生成任务的启用账号')
  }
  if (!result.created_count) {
    return t('今日任务已存在，无新增任务')
  }
  return t('已生成今日任务 {count} 条', { count: result.created_count })
}

const importMessage = (result: { created_sites?: number, created_accounts?: number }) => {
  if (!result.created_sites && !result.created_accounts) {
    return t('旧配置中没有新增站点或账号')
  }
  return t('已导入站点 {sites} 个，账号 {accounts} 个', {
    sites: result.created_sites || 0,
    accounts: result.created_accounts || 0,
  })
}

const taskResultMessage = (task: { status?: TaskCenterTodayTaskView['status'], error_message?: string }) => {
  if (task.status === 'success') {
    return t('账号任务执行成功')
  }
  if (task.status === 'skipped') {
    return t('账号今日已完成，已跳过')
  }
  if (task.status === 'blocked') {
    return t('账号任务已阻塞：{reason}', {
      reason: translateError(task.error_message, '任务执行失败'),
    })
  }
  if (task.status === 'failed') {
    return t('账号任务执行失败：{reason}', {
      reason: translateError(task.error_message, '任务执行失败'),
    })
  }
  return t('账号任务状态已更新为 {status}', { status: t(task.status || 'unknown') })
}

const showStatusTasks = (status: TaskCenterTodayTaskView['status'] | 'all') => {
  if (['all', 'pending', 'success', 'skipped', 'blocked', 'failed'].includes(status)) {
    statusFilter.value = status
    return
  }
  statusFilter.value = 'all'
}

const isTaskBusy = (taskId: string, action?: 'run' | 'retry') => {
  const current = taskActionBusy.value
  if (!current) {
    return false
  }
  return current.taskId === taskId && (!action || current.action === action)
}

const executeAction = async (
  action: Exclude<TopAction, 'refresh' | 'check'>,
  runner: () => Promise<TopActionResult>
) => {
  if (operationBusy.value) {
    return
  }
  const before = currentStats()
  actionMessage.value = ''
  actionBusy.value = action
  try {
    const result = await runner()
    let message = ''
    if (action === 'import') {
      message = importMessage(result)
    } else if (action === 'generate') {
      message = generationMessage(result)
      if (result.created_count) {
        showStatusTasks('pending')
      }
    } else {
      message = batchMessage(result)
      if (result.executed_count) {
        showStatusTasks('all')
      }
    }
    await refreshToday()
    completeAction(action, message)
    recordActionResult(action, message, before, currentStats(), result)
  } catch (error: any) {
    const message = translateRequestError(error, '任务执行失败')
    completeAction(action, message)
    recordActionResult(action, message, before, currentStats(), undefined, true)
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

const checkPendingTasks = async () => {
  if (operationBusy.value) {
    return
  }
  const before = currentStats()
  actionMessage.value = ''
  actionBusy.value = 'check'
  try {
    await refreshToday()
    const after = currentStats()
    const refreshedPendingCount = todayResponse.value?.pending_tasks || 0
    let message = ''
    if (refreshedPendingCount > 0) {
      showStatusTasks('pending')
      message = t('已发现待处理任务 {count} 条，可点击执行', { count: refreshedPendingCount })
      completeAction('check', message)
      recordActionResult('check', message, before, after)
      return
    }
    showStatusTasks('all')
    message = t('当前没有待执行任务')
    completeAction('check', message)
    recordActionResult('check', message, before, after)
  } catch (error: any) {
    const message = translateRequestError(error, '今日任务刷新失败')
    completeAction('check', message)
    recordActionResult('check', message, before, currentStats(), undefined, true)
  } finally {
    actionBusy.value = ''
  }
}

const handlePendingAction = async () => {
  if (pendingTaskCount.value === 0) {
    await checkPendingTasks()
    return
  }
  await executeToday()
}

const refreshTodayWithMessage = async () => {
  if (operationBusy.value) {
    return
  }
  const before = currentStats()
  actionMessage.value = ''
  actionBusy.value = 'refresh'
  try {
    await refreshToday()
    const message = t('今日任务已刷新')
    completeAction('refresh', message)
    recordActionResult('refresh', message, before, currentStats())
  } catch (error: any) {
    const message = translateRequestError(error, '今日任务刷新失败')
    completeAction('refresh', message)
    recordActionResult('refresh', message, before, currentStats(), undefined, true)
  } finally {
    actionBusy.value = ''
  }
}

const retryTask = async (taskId: string) => {
  if (operationBusy.value) {
    return
  }
  actionMessage.value = ''
  taskActionBusy.value = { taskId, action: 'retry' }
  try {
    await api.retryTaskCenterTask(taskId)
    showStatusTasks('pending')
    actionMessage.value = t('最后反馈：{message}（{time}）', {
      message: t('任务已重置为待执行，可点击执行账号任务'),
      time: formatActionClock(),
    })
    await refreshToday()
  } catch (error: any) {
    actionMessage.value = t('最后反馈：{message}（{time}）', {
      message: translateRequestError(error, '任务重试失败'),
      time: formatActionClock(),
    })
  } finally {
    taskActionBusy.value = null
  }
}

const runTask = async (taskId: string) => {
  if (operationBusy.value) {
    return
  }
  actionMessage.value = ''
  taskActionBusy.value = { taskId, action: 'run' }
  try {
    const result = await api.executeTaskCenterTask(taskId) as { status?: TaskCenterTodayTaskView['status'], error_message?: string }
    actionMessage.value = t('最后反馈：{message}（{time}）', {
      message: taskResultMessage(result),
      time: formatActionClock(),
    })
    showStatusTasks(result.status || 'all')
    await refreshToday()
  } catch (error: any) {
    actionMessage.value = t('最后反馈：{message}（{time}）', {
      message: translateRequestError(error, '任务执行失败'),
      time: formatActionClock(),
    })
  } finally {
    taskActionBusy.value = null
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
        <div class="today-action-board" role="group" :aria-label="t('今日任务操作')">
          <div class="today-action-command">
            <button
              type="button"
              class="button"
              :class="[hasTasks ? 'button--secondary' : 'button--primary', topActionStateClass('generate')]"
              :disabled="operationBusy"
              :aria-busy="actionBusy === 'generate'"
              data-testid="today-action-generate"
              @click="generateTasks"
            >
              {{ actionBusy === 'generate' ? t('生成中') : t('生成今日任务') }}
            </button>
            <span
              v-if="actionReceipts.generate"
              class="today-action-receipt"
              data-testid="today-action-generate-receipt"
              :title="actionReceipts.generate.message"
            >
              {{ actionReceiptText(actionReceipts.generate) }}
            </span>
          </div>
          <div class="today-action-command">
            <button
              type="button"
              class="button"
              :class="[
                pendingTaskCount > 0 ? 'button--primary' : 'button--secondary',
                {
                  'button--busy': pendingActionActive,
                  'button--recent-action': pendingActionRecent && actionBusy === '',
                },
              ]"
              :disabled="operationBusy"
              :aria-busy="actionBusy === 'execute' || actionBusy === 'check'"
              data-testid="today-action-execute"
              @click="handlePendingAction"
            >
              {{
                actionBusy === 'execute'
                  ? t('执行中')
                  : actionBusy === 'check'
                    ? t('检查中')
                    : pendingTaskCount === 0
                      ? t('检查待处理任务')
                      : t('执行待处理任务')
              }}
            </button>
            <span
              v-if="pendingActionReceipt"
              class="today-action-receipt"
              data-testid="today-action-execute-receipt"
              :title="pendingActionReceipt.message"
            >
              {{ actionReceiptText(pendingActionReceipt) }}
            </span>
          </div>
          <div class="today-action-command">
            <button
              type="button"
              class="button button--secondary"
              :class="topActionStateClass('import')"
              :disabled="operationBusy"
              :aria-busy="actionBusy === 'import'"
              data-testid="today-action-import"
              @click="importConfig"
            >
              {{ actionBusy === 'import' ? t('导入中') : t('导入旧主签到配置') }}
            </button>
            <span
              v-if="actionReceipts.import"
              class="today-action-receipt"
              data-testid="today-action-import-receipt"
              :title="actionReceipts.import.message"
            >
              {{ actionReceiptText(actionReceipts.import) }}
            </span>
          </div>
          <div class="today-action-command">
            <button
              type="button"
              class="button button--secondary"
              :class="topActionStateClass('refresh')"
              :disabled="operationBusy"
              :aria-busy="actionBusy === 'refresh'"
              data-testid="today-action-refresh"
              @click="refreshTodayWithMessage"
            >
              {{ actionBusy === 'refresh' ? t('刷新中') : t('刷新今日任务') }}
            </button>
            <span
              v-if="actionReceipts.refresh"
              class="today-action-receipt"
              data-testid="today-action-refresh-receipt"
              :title="actionReceipts.refresh.message"
            >
              {{ actionReceiptText(actionReceipts.refresh) }}
            </span>
          </div>
        </div>
      </template>
    </PageHeader>
    <p v-if="actionStatusMessage" id="today-action-status" class="status-note status-note--action" role="status" aria-live="polite">
      {{ actionStatusMessage }}
    </p>
    <ActionResultPanel
      v-if="lastActionResult"
      :title="lastActionResult.title"
      :subtitle="lastActionResult.subtitle"
      :state="lastActionResult.state"
      :state-label="lastActionResult.stateLabel"
      :items="lastActionResult.items"
      :details="lastActionResult.details"
    />
    <div class="button-row page-summary-strip">
      <StatusBadge :label="t('今日任务 {count}', { count: today?.total_tasks || 0 })" :state="(today?.total_tasks || 0) > 0 ? 'configured' : 'unconfigured'" />
      <StatusBadge :label="t('待处理 {count}', { count: (today?.pending_tasks || 0) + (today?.running_tasks || 0) })" :state="((today?.pending_tasks || 0) + (today?.running_tasks || 0)) > 0 ? 'info' : 'neutral'" />
      <StatusBadge :label="t('成功 {count}', { count: today?.success_tasks || 0 })" :state="(today?.success_tasks || 0) > 0 ? 'success' : 'neutral'" />
      <StatusBadge :label="t('阻塞 {count}', { count: today?.blocked_tasks || 0 })" :state="(today?.blocked_tasks || 0) > 0 ? 'failed' : 'neutral'" />
      <StatusBadge :label="t('失败 {count}', { count: today?.failed_tasks || 0 })" :state="(today?.failed_tasks || 0) > 0 ? 'failed' : 'neutral'" />
      <StatusBadge :label="t('今日额度 {count}', { count: today?.total_quota_awarded || 0 })" :state="(today?.total_quota_awarded || 0) > 0 ? 'configured' : 'neutral'" />
    </div>
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
      <div v-if="visibleTasks.length" class="task-table">
        <article v-for="task in visibleTasks" :key="task.id" class="task-row">
          <div class="task-row__main">
            <strong>{{ task.account_display_name }}</strong>
            <p class="muted">{{ task.site_name }} / {{ task.username }}</p>
          </div>
          <div class="task-row__meta">
            <StatusBadge :label="t(task.status)" :state="taskState(task.status)" />
            <StatusBadge :label="`${t('执行链')} ${executorLabel(task.executor_type)}`" state="info" />
            <StatusBadge :label="t('奖励额度 {count}', { count: task.quota_awarded })" :state="task.quota_awarded > 0 ? 'configured' : 'neutral'" />
          </div>
          <div class="task-row__time muted">
            {{ t('开始 {value}', { value: formatDateTime(task.started_at) }) }} /
            {{ t('结束 {value}', { value: formatDateTime(task.finished_at) }) }}
          </div>
          <div class="task-row__actions">
            <button
              v-if="task.status === 'pending'"
              type="button"
              class="button button--primary"
              :disabled="operationBusy"
              @click="runTask(task.id)"
            >
              {{ isTaskBusy(task.id, 'run') ? t('执行中') : t('执行账号任务') }}
            </button>
            <button
              v-if="task.status === 'failed' || task.status === 'blocked'"
              type="button"
              class="button button--secondary"
              :disabled="operationBusy"
              @click="retryTask(task.id)"
            >
              {{ isTaskBusy(task.id, 'retry') ? t('重置中') : t('重置后重试') }}
            </button>
          </div>
          <p v-if="task.error_message" class="task-row__error">{{ translateError(task.error_message, '任务执行失败') }}</p>
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
          <p class="muted">{{ t('已有启用账号时可直接生成今日任务；如果还保留旧主链路配置，可先导入旧配置。') }}</p>
        </div>
      </div>
    </section>
  </AppShell>
</template>
