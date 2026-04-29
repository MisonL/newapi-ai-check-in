<script setup lang="ts">
const props = defineProps<{
  totalAccounts: number
  successAccounts: number
  pendingAccounts: number
  failedAccounts: number
  quotaAwarded: number
  hasTasks: boolean
  busy: boolean
}>()

const emit = defineEmits<{
  run: []
  refresh: []
}>()

const { t } = useAppI18n()

const completionText = computed(() => {
  if (props.totalAccounts === 0) {
    return t('还没有启用账号')
  }
  return `${props.successAccounts}/${props.totalAccounts}`
})

const stateText = computed(() => {
  if (props.busy) {
    return t('正在同步今日签到')
  }
  if (props.failedAccounts > 0) {
    return t('有账号需要处理')
  }
  if (props.pendingAccounts > 0) {
    return t('还有账号待签到')
  }
  if (props.successAccounts > 0) {
    return t('今日已完成')
  }
  return props.hasTasks ? t('今日任务已准备') : t('需要生成今日任务')
})
</script>

<template>
  <section class="daily-ops-hero surface-card">
    <div class="daily-ops-hero__copy">
      <p class="daily-ops-hero__eyebrow">{{ t('日常运营驾驶舱') }}</p>
      <h2>{{ t('今天只需要关注签到是否完成') }}</h2>
      <p>{{ t('系统会基于真实站点和账号生成今日任务，执行后把失败账号集中到异常页。') }}</p>
      <div class="daily-ops-hero__actions">
        <button
          type="button"
          class="button button--primary"
          data-testid="daily-ops-primary-action"
          :disabled="props.busy"
          :aria-busy="props.busy"
          @click="emit('run')"
        >
          {{ props.busy ? t('执行中') : t('一键执行今日签到') }}
        </button>
        <button
          type="button"
          class="button button--secondary"
          data-testid="daily-ops-refresh-action"
          :disabled="props.busy"
          @click="emit('refresh')"
        >
          {{ t('刷新') }}
        </button>
        <NuxtLink
          v-if="props.failedAccounts > 0"
          class="button button--secondary daily-ops-hero__incident-action"
          data-testid="daily-ops-incident-action"
          to="/incidents"
        >
          {{ t('处理异常') }}
        </NuxtLink>
      </div>
      <p
        v-if="props.busy"
        class="daily-ops-hero__sync"
        data-testid="daily-ops-sync-status"
        role="status"
        aria-live="polite"
      >
        {{ t('正在同步今日签到') }}
      </p>
    </div>
    <div class="daily-ops-hero__panel">
      <div class="daily-ops-hero__state">
        <span>{{ t('今日状态') }}</span>
        <strong>{{ stateText }}</strong>
      </div>
      <div class="daily-ops-hero__metrics">
        <div class="daily-ops-hero__metric">
          <span>{{ t('完成账号') }}</span>
          <strong>{{ completionText }}</strong>
        </div>
        <div class="daily-ops-hero__metric">
          <span>{{ t('待处理') }}</span>
          <strong>{{ props.pendingAccounts }}</strong>
        </div>
        <div
          class="daily-ops-hero__metric"
          :class="{ 'daily-ops-hero__metric--alert': props.failedAccounts > 0 }"
          data-testid="daily-ops-failed-metric"
        >
          <span>{{ t('异常') }}</span>
          <strong>{{ props.failedAccounts }}</strong>
        </div>
        <div class="daily-ops-hero__metric">
          <span>{{ t('今日额度') }}</span>
          <strong>{{ props.quotaAwarded }}</strong>
        </div>
      </div>
    </div>
  </section>
</template>
