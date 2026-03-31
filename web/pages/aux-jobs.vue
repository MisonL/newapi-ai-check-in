<script setup lang="ts">
const api = useControlPlane()

type OAuthRow = { username: string; password: string }

const selectedRunId = ref('')
const messages = reactive({
  checkin_996: '',
  checkin_qaq_al: '',
  linuxdo_read: ''
})

const hub996Accounts = ref<string[]>([''])
const hub996ProxyJson = ref('')
const qaqAccounts = ref<string[]>([''])
const qaqProxyJson = ref('')
const qaqTier = ref(4)
const linuxdoAccounts = ref<OAuthRow[]>([])
const linuxdoBaseTopicId = ref<number | null>(null)
const linuxdoMaxPosts = ref(100)

const { data: config996, refresh: refresh996 } = await useAsyncData('config-996', () => api.getConfig('checkin_996'))
const { data: configQaq, refresh: refreshQaq } = await useAsyncData('config-qaq', () => api.getConfig('checkin_qaq_al'))
const { data: configLinuxdo, refresh: refreshLinuxdo } = await useAsyncData('config-linuxdo', () => api.getConfig('linuxdo_read'))
const { data: jobs, refresh: refreshJobs } = await useAsyncData('aux-job-runs', () => api.listJobs())
const { data: logs, refresh: refreshLogs } = await useAsyncData(
  'aux-job-logs',
  () => selectedRunId.value ? api.getJobLogs(selectedRunId.value) : Promise.resolve([])
)

watchEffect(() => {
  const payload996 = config996.value?.payload || {}
  hub996Accounts.value = payload996.accounts?.length ? [...payload996.accounts] : ['']
  hub996ProxyJson.value = payload996.proxy ? JSON.stringify(payload996.proxy, null, 2) : ''

  const payloadQaq = configQaq.value?.payload || {}
  qaqAccounts.value = payloadQaq.accounts?.length ? [...payloadQaq.accounts] : ['']
  qaqProxyJson.value = payloadQaq.proxy ? JSON.stringify(payloadQaq.proxy, null, 2) : ''
  qaqTier.value = payloadQaq.tier ?? 4

  const payloadLinuxdo = configLinuxdo.value?.payload || {}
  linuxdoAccounts.value = (payloadLinuxdo.accounts || []).map((item: any) => ({
    username: item.username || '',
    password: item.password || ''
  }))
  if (!linuxdoAccounts.value.length) {
    linuxdoAccounts.value = [{ username: '', password: '' }]
  }
  linuxdoBaseTopicId.value = payloadLinuxdo.base_topic_id ?? null
  linuxdoMaxPosts.value = payloadLinuxdo.max_posts ?? 100
})

const parseObject = (value: string) => {
  if (!value.trim()) {
    return null
  }
  return JSON.parse(value)
}

const cleanValues = (values: string[]) => values.map((item) => item.trim()).filter(Boolean)

const setMessage = (jobType: keyof typeof messages, value: string) => {
  messages[jobType] = value
}

const save996 = async () => {
  setMessage('checkin_996', '')
  try {
    await api.saveConfig('checkin_996', {
      accounts: cleanValues(hub996Accounts.value),
      proxy: parseObject(hub996ProxyJson.value)
    })
    await refresh996()
    setMessage('checkin_996', 'Config saved')
  } catch (error: any) {
    setMessage('checkin_996', error?.data?.message || error?.message || 'Config save failed')
  }
}

const saveQaq = async () => {
  setMessage('checkin_qaq_al', '')
  try {
    await api.saveConfig('checkin_qaq_al', {
      accounts: cleanValues(qaqAccounts.value),
      proxy: parseObject(qaqProxyJson.value),
      tier: qaqTier.value
    })
    await refreshQaq()
    setMessage('checkin_qaq_al', 'Config saved')
  } catch (error: any) {
    setMessage('checkin_qaq_al', error?.data?.message || error?.message || 'Config save failed')
  }
}

const saveLinuxdo = async () => {
  setMessage('linuxdo_read', '')
  try {
    await api.saveConfig('linuxdo_read', {
      accounts: linuxdoAccounts.value.filter((item) => item.username && item.password),
      base_topic_id: linuxdoBaseTopicId.value,
      max_posts: linuxdoMaxPosts.value
    })
    await refreshLinuxdo()
    setMessage('linuxdo_read', 'Config saved')
  } catch (error: any) {
    setMessage('linuxdo_read', error?.data?.message || error?.message || 'Config save failed')
  }
}

const runJob = async (jobType: keyof typeof messages) => {
  setMessage(jobType, '')
  try {
    const result: any = await api.runJob(jobType)
    selectedRunId.value = result.id
    await refreshJobs()
    await refreshLogs()
    setMessage(jobType, `Run created: ${result.id} (${result.status})`)
  } catch (error: any) {
    setMessage(jobType, error?.data?.message || error?.message || 'Run failed')
  }
}

const pickRun = async (runId: string) => {
  selectedRunId.value = runId
  await refreshLogs()
}

const auxRuns = computed(() => {
  const jobTypes = new Set(['checkin_996', 'checkin_qaq_al', 'linuxdo_read'])
  return ((jobs.value as any[]) || []).filter((job) => jobTypes.has(job.job_type))
})
const selectedLogs = computed(() => (logs.value as any[]) || [])
</script>

<template>
  <AppShell>
    <div class="panel-grid">
      <div class="panel-grid panel-grid--two">
        <StringListCard
          v-model="hub996Accounts"
          title="996 hub accounts"
          label="Access token"
          placeholder="token-1"
        />
        <section class="card">
          <h2 class="card__title">996 hub options</h2>
          <div class="field">
            <label class="field__label">Proxy JSON</label>
            <textarea
              v-model="hub996ProxyJson"
              class="textarea"
              placeholder='{"server":"http://proxy.example.com:8080"}'
            />
          </div>
          <div class="button-row">
            <button class="button button--primary" @click="save996">Save config</button>
            <button class="button button--secondary" @click="runJob('checkin_996')">Run now</button>
          </div>
          <p class="muted">{{ messages.checkin_996 }}</p>
        </section>
      </div>

      <div class="panel-grid panel-grid--two">
        <StringListCard
          v-model="qaqAccounts"
          title="qaq.al accounts"
          label="SID"
          placeholder="sid-1"
        />
        <section class="card">
          <h2 class="card__title">qaq.al options</h2>
          <div class="field">
            <label class="field__label">Tier</label>
            <input v-model.number="qaqTier" class="input" type="number" min="1" max="4">
          </div>
          <div class="field">
            <label class="field__label">Proxy JSON</label>
            <textarea
              v-model="qaqProxyJson"
              class="textarea"
              placeholder='{"server":"http://proxy.example.com:8080"}'
            />
          </div>
          <div class="button-row">
            <button class="button button--primary" @click="saveQaq">Save config</button>
            <button class="button button--secondary" @click="runJob('checkin_qaq_al')">Run now</button>
          </div>
          <p class="muted">{{ messages.checkin_qaq_al }}</p>
        </section>
      </div>

      <div class="panel-grid panel-grid--two">
        <OAuthAccountsCard v-model="linuxdoAccounts" title="Linux.do read accounts" />
        <section class="card">
          <h2 class="card__title">Linux.do read options</h2>
          <div class="field">
            <label class="field__label">Base topic ID</label>
            <input v-model.number="linuxdoBaseTopicId" class="input" type="number" min="1">
          </div>
          <div class="field">
            <label class="field__label">Max posts</label>
            <input v-model.number="linuxdoMaxPosts" class="input" type="number" min="1">
          </div>
          <div class="button-row">
            <button class="button button--primary" @click="saveLinuxdo">Save config</button>
            <button class="button button--secondary" @click="runJob('linuxdo_read')">Run now</button>
          </div>
          <p class="muted">{{ messages.linuxdo_read }}</p>
        </section>
      </div>

      <JobRunConsole
        :jobs="auxRuns"
        :logs="selectedLogs"
        :selected-run-id="selectedRunId"
        @select="pickRun"
      />
    </div>
  </AppShell>
</template>
