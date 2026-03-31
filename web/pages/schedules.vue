<script setup lang="ts">
const api = useControlPlane()
const { formatJobType, t, translateError } = useAppI18n()

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

const { data: scheduleResponse, refresh } = await useAsyncData('all-schedules', () => api.listSchedules())

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
    messages[jobType] = t('调度已保存')
  } catch (error: any) {
    messages[jobType] = translateError(error?.data?.message || error?.message, '调度保存失败')
  }
}
</script>

<template>
  <AppShell>
    <div class="panel-grid panel-grid--two">
      <section
        v-for="jobType in scheduleOrder"
        :key="jobType"
        class="card"
      >
        <h2 class="card__title">{{ t('{job} 调度', { job: formatJobType(jobType) }) }}</h2>
        <div v-if="scheduleForms[jobType]" class="stack-list">
          <div class="field">
            <label class="field__label">{{ t('启用') }}</label>
            <select v-model="scheduleForms[jobType].enabled" class="select">
              <option :value="true">{{ t('已启用') }}</option>
              <option :value="false">{{ t('已禁用') }}</option>
            </select>
          </div>
          <div class="field">
            <label class="field__label">{{ t('Cron 表达式') }}</label>
            <input v-model="scheduleForms[jobType].cron" class="input">
          </div>
          <div class="field">
            <label class="field__label">{{ t('时区') }}</label>
            <input v-model="scheduleForms[jobType].timezone" class="input">
          </div>
          <div class="field">
            <label class="field__label">{{ t('冷却秒数') }}</label>
            <input
              v-model.number="scheduleForms[jobType].cooldown_seconds"
              class="input"
              type="number"
              min="0"
            >
          </div>
          <div class="button-row">
            <button class="button button--primary" @click="save(jobType)">{{ t('保存调度') }}</button>
          </div>
          <p class="muted">{{ messages[jobType] }}</p>
        </div>
      </section>
    </div>
  </AppShell>
</template>
