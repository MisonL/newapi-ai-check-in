<script setup lang="ts">
const props = defineProps<{
  jobs: Array<any>
  logs: Array<any>
  selectedRunId: string
}>()

const emit = defineEmits<{
  select: [runId: string]
}>()
</script>

<template>
  <section class="card">
    <h2 class="card__title">Runs and logs</h2>
    <div class="panel-grid panel-grid--two">
      <div class="job-list">
        <button
          v-for="job in props.jobs"
          :key="job.id"
          class="job-item"
          :class="{ 'job-item--selected': props.selectedRunId === job.id }"
          @click="emit('select', job.id)"
        >
          <strong>{{ job.job_type }} / {{ job.status }}</strong>
          <div class="job-item__meta">
            <span>{{ job.trigger }}</span>
            <span>{{ job.started_at }}</span>
          </div>
        </button>
      </div>
      <pre class="code-block">{{ props.logs.map((item: any) => `[${item.stream}] ${item.message}`).join('\n') }}</pre>
    </div>
  </section>
</template>
