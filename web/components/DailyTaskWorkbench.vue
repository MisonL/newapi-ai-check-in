<script setup lang="ts">
import type { AccountRecordView, TaskCenterTodayTaskView } from '../types/controlPlane'

type LaneTone = 'attention' | 'active' | 'done'
type Lane = {
  id: LaneTone
  title: string
  description: string
  emptyText: string
  tasks: TaskCenterTodayTaskView[]
}

const props = defineProps<{
  tasks: TaskCenterTodayTaskView[]
  recentAccounts?: AccountRecordView[]
}>()

const { t, translateError } = useAppI18n()
const { formatDateTime } = useUiDateTime()

const attentionStatuses = new Set<TaskCenterTodayTaskView['status']>(['failed', 'blocked'])
const activeStatuses = new Set<TaskCenterTodayTaskView['status']>(['pending', 'probing', 'logging_in', 'checking', 'checking_in'])

const orderedTasks = computed(() => {
  const priority = (task: TaskCenterTodayTaskView) => {
    if (attentionStatuses.has(task.status)) {
      return 0
    }
    if (activeStatuses.has(task.status)) {
      return 1
    }
    return 2
  }
  return [...props.tasks].sort((left, right) => {
    const rank = priority(left) - priority(right)
    if (rank !== 0) {
      return rank
    }
    const leftTime = left.finished_at || left.started_at || left.task_date
    const rightTime = right.finished_at || right.started_at || right.task_date
    return String(rightTime).localeCompare(String(leftTime))
  })
})

const taskAccountIds = computed(() => new Set(props.tasks.map((task) => task.account_id)))

const attentionAccountAlerts = computed(() => (props.recentAccounts || [])
  .filter((account) => account.enabled)
  .filter((account) => ['failed', 'blocked'].includes(account.last_checkin_status))
  .filter((account) => !taskAccountIds.value.has(account.id))
  .slice(0, 4))

const lanes = computed<Lane[]>(() => [
  {
    id: 'attention',
    title: t('先处理异常'),
    description: t('失败或阻塞账号会影响今日完成度'),
    emptyText: t('当前没有需要处理的异常账号'),
    tasks: orderedTasks.value.filter((task) => attentionStatuses.has(task.status)),
  },
  {
    id: 'active',
    title: t('等待执行'),
    description: t('待执行和进行中的账号任务'),
    emptyText: t('当前没有待执行账号'),
    tasks: orderedTasks.value.filter((task) => activeStatuses.has(task.status)),
  },
  {
    id: 'done',
    title: t('已完成'),
    description: t('成功或已跳过的账号任务'),
    emptyText: t('完成后会在这里形成今日记录'),
    tasks: orderedTasks.value.filter((task) => !attentionStatuses.has(task.status) && !activeStatuses.has(task.status)),
  },
])

const laneState = (lane: Lane) => {
  const count = lane.id === 'attention' ? lane.tasks.length + attentionAccountAlerts.value.length : lane.tasks.length
  if (lane.id === 'attention') {
    return count ? 'failed' : 'success'
  }
  if (lane.id === 'active') {
    return count ? 'info' : 'neutral'
  }
  return count ? 'success' : 'neutral'
}

const laneCount = (lane: Lane) => {
  if (lane.id === 'attention') {
    return lane.tasks.length + attentionAccountAlerts.value.length
  }
  return lane.tasks.length
}

const cardState = (task: TaskCenterTodayTaskView) => {
  if (attentionStatuses.has(task.status)) {
    return 'failed'
  }
  if (activeStatuses.has(task.status)) {
    return task.status === 'pending' ? 'neutral' : 'running'
  }
  return task.status === 'success' ? 'success' : 'skipped'
}

const taskTarget = (task: TaskCenterTodayTaskView) => {
  if (attentionStatuses.has(task.status)) {
    return '/incidents'
  }
  return '/today'
}

const taskDetail = (task: TaskCenterTodayTaskView) => {
  if (task.error_message) {
    return translateError(task.error_message, '任务执行失败')
  }
  if (task.finished_at || task.started_at) {
    return formatDateTime(task.finished_at || task.started_at)
  }
  return t('等待系统执行')
}

const accountDetail = (account: AccountRecordView) => {
  if (account.last_error_message) {
    return translateError(account.last_error_message, '任务执行失败')
  }
  if (account.last_checkin_at) {
    return formatDateTime(account.last_checkin_at)
  }
  return t('账号需要处理')
}
</script>

<template>
  <section class="daily-task-workbench surface-card" data-testid="daily-task-workbench">
    <div class="section-head daily-task-workbench__head">
      <div>
        <p class="daily-task-workbench__eyebrow">{{ t('任务收件箱') }}</p>
        <h2 class="card__title">{{ t('按处理顺序查看今天的账号任务') }}</h2>
      </div>
      <NuxtLink class="button button--secondary" to="/today">{{ t('查看今日任务') }}</NuxtLink>
    </div>
    <div class="daily-task-lanes">
      <section
        v-for="lane in lanes"
        :key="lane.id"
        class="daily-task-lane"
        :class="`daily-task-lane--${lane.id}`"
        :data-testid="`daily-task-lane-${lane.id}`"
      >
        <div class="daily-task-lane__head">
          <div>
            <strong>{{ lane.title }}</strong>
            <p>{{ lane.description }}</p>
          </div>
          <StatusBadge :label="String(laneCount(lane))" :state="laneState(lane)" :dot="false" />
        </div>
        <div v-if="lane.tasks.length || (lane.id === 'attention' && attentionAccountAlerts.length)" class="daily-task-card-list">
          <NuxtLink
            v-for="task in lane.tasks.slice(0, 4)"
            :key="task.id"
            :to="taskTarget(task)"
            class="daily-task-card"
            :class="`daily-task-card--${lane.id}`"
          >
            <div class="daily-task-card__main">
              <strong>{{ task.account_display_name }}</strong>
              <span>{{ task.site_name }} / {{ task.username }}</span>
            </div>
            <StatusBadge :label="t(task.status)" :state="cardState(task)" />
            <p>{{ taskDetail(task) }}</p>
          </NuxtLink>
          <NuxtLink
            v-for="account in lane.id === 'attention' ? attentionAccountAlerts : []"
            :key="`account-${account.id}`"
            to="/incidents"
            class="daily-task-card daily-task-card--attention"
          >
            <div class="daily-task-card__main">
              <strong>{{ account.display_name || account.username }}</strong>
              <span>{{ account.username }}</span>
            </div>
            <StatusBadge :label="t(account.last_checkin_status)" state="failed" />
            <p>{{ accountDetail(account) }}</p>
          </NuxtLink>
        </div>
        <div v-else class="daily-task-lane__empty">
          {{ lane.emptyText }}
        </div>
      </section>
    </div>
  </section>
</template>
