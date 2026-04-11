<script setup lang="ts">
const api = useControlPlane()
const { formatDeployMode, formatJobType, t, translateError } = useAppI18n()

type ScheduleForm = {
  job_type: string
  enabled: boolean
  cron: string
  timezone: string
  cooldown_seconds: number
}

const scheduleOrder = ['main_checkin', 'checkin_996', 'checkin_qaq_al', 'linuxdo_read']
const scheduleForms = reactive<Record<string, ScheduleForm>>({})
const messages = reactive<Record<string, string>>({})
const enabledOptions = [
  { label: '已启用', value: true },
  { label: '已禁用', value: false },
]
const formatEnabledState = (enabled: boolean) => t(enabled ? '已启用' : '已禁用')

const { data: scheduleResponse, refresh } = await useAsyncData('all-schedules', () => api.listSchedules())
const { data: statusResponse, refresh: refreshStatus } = await useAsyncData('schedule-status', () => api.getStatus())

watchEffect(() => {
  const items = ((scheduleResponse.value as any[]) || []).sort(
    (left, right) => scheduleOrder.indexOf(left.job_type) - scheduleOrder.indexOf(right.job_type)
  )
  for (const item of items) {
    scheduleForms[item.job_type] = {
      job_type: item.job_type,
      enabled: item.enabled,
      cron: item.cron,
      timezone: item.timezone,
      cooldown_seconds: item.cooldown_seconds
    }
    messages[item.job_type] = messages[item.job_type] || ''
  }
})

const save = async (jobType: string) => {
  messages[jobType] = ''
  try {
    await api.saveSchedule(jobType, { ...scheduleForms[jobType] })
    await refresh()
    await refreshStatus()
    messages[jobType] = t('调度已保存')
  } catch (error: any) {
    messages[jobType] = translateError(error?.data?.message || error?.message, '调度保存失败')
  }
}

const scheduleItems = computed(() => scheduleOrder
  .map((jobType) => scheduleForms[jobType])
  .filter((item): item is ScheduleForm => Boolean(item)))
const scheduleCountLabel = computed(() => `${t('调度任务')} ${scheduleItems.value.length}`)
const enabledCountLabel = computed(() => `${t('已启用')} ${scheduleItems.value.filter((item) => item.enabled).length}`)
const timezoneLabel = computed(() => `${t('默认时区')} ${scheduleItems.value[0]?.timezone || '-'}`)
const deployModeLabel = computed(() => `${t('部署模式')} ${formatDeployMode(statusResponse.value?.deploy_mode)}`)
const schedulerStateLabel = computed(() => `${t('本地调度')} ${t(statusResponse.value?.scheduler_enabled ? '已启用' : '已禁用')}`)
</script>

<template>
  <AppShell>
    <PageHeader
      title="调度计划"
      description="按任务维护 Cron、时区和冷却时间"
      eyebrow="工作台"
    />
    <div class="button-row page-summary-strip">
      <StatusBadge :label="scheduleCountLabel" state="neutral" />
      <StatusBadge :label="enabledCountLabel" :state="scheduleItems.some((item) => item.enabled) ? 'enabled' : 'disabled'" />
      <StatusBadge :label="timezoneLabel" state="info" />
      <StatusBadge :label="deployModeLabel" :state="statusResponse?.deploy_mode === 'control_plane' ? 'enabled' : 'info'" />
      <StatusBadge :label="schedulerStateLabel" :state="statusResponse?.scheduler_enabled ? 'enabled' : 'failed'" />
    </div>
    <section class="card surface-card" style="margin-bottom: 24px;">
      <div class="section-head">
        <h2 class="card__title">{{ t('调度源说明') }}</h2>
        <StatusBadge :label="t('避免重复执行')" state="failed" :dot="false" />
      </div>
      <p class="muted">{{ t('请勿同时启用本地控制面调度与 GitHub Actions 定时任务，否则同一任务可能重复执行。') }}</p>
      <p class="muted">{{ t('若已使用仓库内 workflow 定时运行，请在此页面保持对应任务为已禁用。') }}</p>
      <p class="muted">{{ t('当前部署模式：{value}', { value: formatDeployMode(statusResponse?.deploy_mode) }) }}</p>
      <p v-if="statusResponse && !statusResponse.scheduler_enabled" class="muted">{{ t('当前环境已关闭本地调度，页面中的 Cron 配置仅保留为计划，不会在本机自动触发。') }}</p>
    </section>
    <div class="panel-grid panel-grid--two">
      <section
        v-for="jobType in scheduleOrder"
        :key="jobType"
        class="card surface-card schedule-card"
      >
        <div v-if="scheduleForms[jobType]" class="section-head schedule-card__head">
          <h2 class="card__title">{{ t('{job} 调度', { job: formatJobType(jobType) }) }}</h2>
          <StatusBadge :label="formatEnabledState(scheduleForms[jobType].enabled)" :state="scheduleForms[jobType].enabled ? 'enabled' : 'disabled'" />
        </div>
        <div v-if="scheduleForms[jobType]" class="stack-list">
          <FieldBlock
            :for-id="`schedule-${jobType}-enabled`"
            label="启用"
            description="关闭后保留当前配置，但不会进入自动调度"
          >
            <AppSelect
              :id="`schedule-${jobType}-enabled`"
              :model-value="scheduleForms[jobType].enabled"
              :options="enabledOptions"
              @update:model-value="scheduleForms[jobType].enabled = $event as boolean"
            />
          </FieldBlock>
          <FieldBlock
            :for-id="`schedule-${jobType}-cron`"
            label="Cron 表达式"
            description="使用五段 Cron：分 时 日 月 周"
          >
            <input :id="`schedule-${jobType}-cron`" v-model="scheduleForms[jobType].cron" class="input input--code">
          </FieldBlock>
          <FieldBlock
            :for-id="`schedule-${jobType}-timezone`"
            label="时区"
            description="推荐与部署环境保持一致，例如 Asia/Shanghai"
          >
            <input :id="`schedule-${jobType}-timezone`" v-model="scheduleForms[jobType].timezone" class="input input--code">
          </FieldBlock>
          <FieldBlock
            :for-id="`schedule-${jobType}-cooldown`"
            label="冷却秒数"
            description="限制同一任务两次自动触发之间的最小间隔"
          >
            <input
              :id="`schedule-${jobType}-cooldown`"
              v-model.number="scheduleForms[jobType].cooldown_seconds"
              class="input"
              type="number"
              min="0"
            >
          </FieldBlock>
          <div class="button-row">
            <button class="button button--primary" @click="save(jobType)">{{ t('保存调度') }}</button>
          </div>
          <p v-if="messages[jobType]" class="status-note" role="status" aria-live="polite">{{ messages[jobType] }}</p>
        </div>
      </section>
    </div>
  </AppShell>
</template>
