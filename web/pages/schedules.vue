<script setup lang="ts">
const api = useControlPlane()
const { formatDeployMode, formatJobType, t, translateRequestError } = useAppI18n()

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
const enabledOptions = computed(() => [
  { label: t('已启用'), value: true },
  { label: t('已禁用'), value: false },
])
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
    messages[jobType] = translateRequestError(error, '调度保存失败')
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
      :title="t('执行计划')"
      :description="t('只在需要调整自动执行时间、冷却规则或部署边界时修改')"
      :eyebrow="t('高级配置')"
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
      <details
        v-for="item in scheduleItems"
        :key="item.job_type"
        class="card surface-card schedule-card schedule-card--fold"
        :open="item.enabled || item.job_type === 'main_checkin'"
      >
        <summary class="schedule-card__summary">
          <h2 class="card__title">{{ t('{job} 调度', { job: formatJobType(item.job_type) }) }}</h2>
          <StatusBadge :label="formatEnabledState(item.enabled)" :state="item.enabled ? 'enabled' : 'disabled'" />
        </summary>
        <div class="schedule-card__body stack-list">
          <FieldBlock
            :for-id="`schedule-${item.job_type}-enabled`"
            :label="t('启用')"
            :description="t('关闭后保留当前配置，但不会进入自动调度')"
          >
            <AppSelect
              :id="`schedule-${item.job_type}-enabled`"
              :model-value="item.enabled"
              :options="enabledOptions"
              @update:model-value="item.enabled = $event as boolean"
            />
          </FieldBlock>
          <FieldBlock
            :for-id="`schedule-${item.job_type}-cron`"
            :label="t('Cron 表达式')"
            :description="t('使用五段 Cron：分 时 日 月 周')"
          >
            <input :id="`schedule-${item.job_type}-cron`" v-model="item.cron" class="input input--code">
          </FieldBlock>
          <FieldBlock
            :for-id="`schedule-${item.job_type}-timezone`"
            :label="t('时区')"
            :description="t('推荐与部署环境保持一致，例如 Asia/Shanghai')"
          >
            <input :id="`schedule-${item.job_type}-timezone`" v-model="item.timezone" class="input input--code">
          </FieldBlock>
          <FieldBlock
            :for-id="`schedule-${item.job_type}-cooldown`"
            :label="t('冷却秒数')"
            :description="t('限制同一任务两次自动触发之间的最小间隔')"
          >
            <input
              :id="`schedule-${item.job_type}-cooldown`"
              v-model.number="item.cooldown_seconds"
              class="input"
              type="number"
              min="0"
            >
          </FieldBlock>
          <div class="button-row">
            <button class="button button--primary" @click="save(item.job_type)">{{ t('保存调度') }}</button>
          </div>
          <p v-if="messages[item.job_type]" class="status-note" role="status" aria-live="polite">{{ messages[item.job_type] }}</p>
        </div>
      </details>
    </div>
  </AppShell>
</template>
