<script setup lang="ts">
const api = useControlPlane()
const { data: status, refresh: refreshStatus } = await useAsyncData('status', () => api.getStatus())
const { data: jobs, refresh: refreshJobs } = await useAsyncData('jobs', () => api.listJobs())
const runningEntries = computed(() => Object.entries(status.value?.running_jobs || {}))
</script>

<template>
  <AppShell>
    <div class="panel-grid panel-grid--two">
      <section class="card">
        <h2 class="card__title">Runtime status</h2>
        <div class="status-list">
          <span class="status-pill">Storage mode: {{ status?.storage_mode }}</span>
          <span class="status-pill">Timezone: {{ status?.timezone }}</span>
          <span
            v-for="[jobType, running] in runningEntries"
            :key="jobType"
            class="status-pill"
          >
            {{ jobType }}: {{ running ? 'running' : 'idle' }}
          </span>
        </div>
        <div class="button-row" style="margin-top: 16px;">
          <button class="button button--secondary" @click="refreshStatus()">Refresh status</button>
        </div>
      </section>
      <section class="card">
        <h2 class="card__title">Recent runs</h2>
        <div class="job-list">
          <div v-for="job in jobs || []" :key="job.id" class="job-item">
            <strong>{{ job.job_type }}</strong>
            <div class="job-item__meta">
              <span>{{ job.status }}</span>
              <span>{{ job.trigger }}</span>
            </div>
          </div>
        </div>
        <div class="button-row" style="margin-top: 16px;">
          <button class="button button--secondary" @click="refreshJobs()">Refresh runs</button>
        </div>
      </section>
    </div>
  </AppShell>
</template>
