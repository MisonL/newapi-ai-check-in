<script setup lang="ts">
import type { JobLogLineView, JobRunView } from '../types/controlPlane'

const props = defineProps<{
  jobs: JobRunView[]
  logs: JobLogLineView[]
  selectedRunId: string
}>()

const emit = defineEmits<{
  select: [runId: string]
}>()

const { t, formatJobStatus, formatJobType, formatTrigger } = useAppI18n()
const { formatDateTime } = useUiDateTime()
const logText = computed(() => props.logs.map((item) => `[${item.stream}] ${item.message}`).join('\n'))
</script>

<template>
  <section class="card surface-card console-card">
    <div class="section-head console-card__head">
      <h2 class="card__title">{{ t('运行与日志') }}</h2>
    </div>
    <div class="panel-grid panel-grid--two console-card__grid">
      <div class="job-list job-list--console console-card__list">
        <div v-if="!props.jobs.length" class="console-empty console-empty--list">
          <span class="console-empty__icon"><AppIcon name="jobs" :size="18" /></span>
          <div class="console-empty__copy">
            <strong>{{ t('暂无运行记录') }}</strong>
            <p class="muted">{{ t('手动运行任务后，这里会显示最近执行历史') }}</p>
          </div>
        </div>
        <button
          v-for="job in props.jobs"
          :key="job.id"
          type="button"
          class="job-item"
          :class="{ 'job-item--selected': props.selectedRunId === job.id }"
          @click="emit('select', job.id)"
        >
          <strong>{{ formatJobType(job.job_type) }}</strong>
          <div class="job-item__meta">
            <StatusBadge :label="formatJobStatus(job.status)" :state="job.status" />
            <span>{{ formatTrigger(job.trigger) }}</span>
            <span>{{ formatDateTime(job.started_at) }}</span>
          </div>
        </button>
      </div>
      <div class="console-card__output">
        <div class="console-card__toolbar">
          <StatusBadge v-if="props.selectedRunId" :label="props.selectedRunId" state="neutral" :dot="false" />
        </div>
        <pre v-if="props.logs.length" class="code-block">{{ logText }}</pre>
        <div v-else class="console-empty console-empty--output" role="status">
          <span class="console-empty__icon"><AppIcon name="dashboard" :size="18" /></span>
          <div class="console-empty__copy">
            <strong>{{ t('请选择一条运行记录') }}</strong>
            <p class="muted">{{ t('选中左侧记录后，这里会展示实时日志输出') }}</p>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
