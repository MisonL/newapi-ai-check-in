<script setup lang="ts">
const api = useControlPlane()
const { t, formatJobStatus, formatJobType, formatTrigger } = useAppI18n()

const formatRunningState = (running: boolean) => t(running ? '运行中' : '空闲中')

const { data: status, refresh: refreshStatus } = await useAsyncData('status', () => api.getStatus())
const { data: jobs, refresh: refreshJobs } = await useAsyncData('jobs', () => api.listJobs())
const runningEntries = computed(() => Object.entries(status.value?.running_jobs || {}))
</script>

<template>
  <AppShell>
    <div class="panel-grid panel-grid--two">
      <section class="card">
        <h2 class="card__title">{{ t('运行状态') }}</h2>
        <div class="status-list">
          <span class="status-pill">{{ t('存储模式：{value}', { value: status?.storage_mode || '-' }) }}</span>
          <span class="status-pill">{{ t('时区：{value}', { value: status?.timezone || '-' }) }}</span>
          <span
            v-for="[jobType, running] in runningEntries"
            :key="jobType"
            class="status-pill"
          >
            {{ t('{job}：{status}', { job: formatJobType(jobType), status: formatRunningState(Boolean(running)) }) }}
          </span>
        </div>
        <div class="button-row" style="margin-top: 16px;">
          <button class="button button--secondary" @click="refreshStatus()">{{ t('刷新状态') }}</button>
        </div>
      </section>
      <section class="card">
        <h2 class="card__title">{{ t('最近运行') }}</h2>
        <div class="job-list">
          <div v-for="job in jobs || []" :key="job.id" class="job-item">
            <strong>{{ formatJobType(job.job_type) }}</strong>
            <div class="job-item__meta">
              <span>{{ formatJobStatus(job.status) }}</span>
              <span>{{ formatTrigger(job.trigger) }}</span>
            </div>
          </div>
        </div>
        <div class="button-row" style="margin-top: 16px;">
          <button class="button button--secondary" @click="refreshJobs()">{{ t('刷新运行') }}</button>
        </div>
      </section>
    </div>
  </AppShell>
</template>
