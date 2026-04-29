<script setup lang="ts">
import type {
  AccountRecordView,
  AppStatus,
  SiteRecordView,
  TaskCenterTodayResponse,
} from '../types/controlPlane'

type ConsoleStep = {
  title: string
  description: string
  state: string
  stateLabel: string
  actionLabel: string
  to: string
}

const props = defineProps<{
  status?: AppStatus
  sites: SiteRecordView[]
  accounts: AccountRecordView[]
  today?: TaskCenterTodayResponse | null
  failedCount: number
  pendingCount: number
}>()

const { t } = useAppI18n()

const enabledSites = computed(() => props.sites.filter((site) => site.enabled).length)
const enabledAccounts = computed(() => props.accounts.filter((account) => account.enabled).length)
const completedTasks = computed(() => (props.today?.success_tasks || 0) + (props.today?.skipped_tasks || 0))
const totalTasks = computed(() => props.today?.total_tasks || 0)
const schedulerLabel = computed(() => props.status?.scheduler_enabled ? t('自动调度已启用') : t('自动调度未启用'))
const deployModeLabel = computed(() => props.status?.deploy_mode === 'github_actions' ? t('GitHub Actions 驱动') : t('控制面调度'))

const steps = computed<ConsoleStep[]>(() => [
  {
    title: t('接入状态'),
    description: t('已启用站点 {sites} 个，启用账号 {accounts} 个', {
      sites: enabledSites.value,
      accounts: enabledAccounts.value,
    }),
    state: enabledSites.value && enabledAccounts.value ? 'success' : 'unconfigured',
    stateLabel: enabledSites.value && enabledAccounts.value ? t('可生成任务') : t('需要补全配置'),
    actionLabel: t('配置站点账号'),
    to: '/setup',
  },
  {
    title: t('今日任务'),
    description: t('今日任务 {total} 条，待处理 {pending} 条', {
      total: totalTasks.value,
      pending: props.pendingCount,
    }),
    state: totalTasks.value ? 'configured' : 'neutral',
    stateLabel: totalTasks.value ? t('任务已生成') : t('尚未生成'),
    actionLabel: t('生成或执行任务'),
    to: '/today',
  },
  {
    title: t('执行结果'),
    description: t('完成 {done}/{total}，今日额度 {quota}', {
      done: completedTasks.value,
      total: totalTasks.value,
      quota: props.today?.total_quota_awarded || 0,
    }),
    state: completedTasks.value ? 'success' : 'neutral',
    stateLabel: completedTasks.value ? t('已有结果') : t('等待执行'),
    actionLabel: t('查看今日结果'),
    to: '/reports',
  },
  {
    title: t('异常闭环'),
    description: t('失败或阻塞账号 {count} 个', { count: props.failedCount }),
    state: props.failedCount ? 'failed' : 'success',
    stateLabel: props.failedCount ? t('需要处理') : t('无待处理异常'),
    actionLabel: t('处理失败账号'),
    to: '/incidents',
  },
])
</script>

<template>
  <section class="workflow-console surface-card" data-testid="dashboard-control-console">
    <div class="section-head workflow-console__head">
      <div>
        <p class="workflow-console__eyebrow">{{ t('签到控制台') }}</p>
        <h2 class="card__title">{{ t('按真实工作流检查系统是否可用') }}</h2>
      </div>
      <div class="workflow-console__runtime">
        <StatusBadge :label="schedulerLabel" :state="props.status?.scheduler_enabled ? 'success' : 'neutral'" />
        <StatusBadge :label="deployModeLabel" state="info" />
      </div>
    </div>
    <div class="workflow-console__grid">
      <NuxtLink v-for="step in steps" :key="step.title" class="workflow-console__step" :to="step.to">
        <div class="workflow-console__step-main">
          <strong>{{ step.title }}</strong>
          <p>{{ step.description }}</p>
        </div>
        <StatusBadge :label="step.stateLabel" :state="step.state" />
        <span class="workflow-console__action">{{ step.actionLabel }}</span>
      </NuxtLink>
    </div>
  </section>
</template>
