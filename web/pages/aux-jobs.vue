<script setup lang="ts">
const api = useControlPlane()
const { formatJobStatus, t, translateRequestError } = useAppI18n()

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

const [
  { data: config996, refresh: refresh996 },
  { data: configQaq, refresh: refreshQaq },
  { data: configLinuxdo, refresh: refreshLinuxdo },
  { data: jobs, refresh: refreshJobs }
] = await Promise.all([
  useAsyncData('config-996', () => api.getConfig('checkin_996')),
  useAsyncData('config-qaq', () => api.getConfig('checkin_qaq_al')),
  useAsyncData('config-linuxdo', () => api.getConfig('linuxdo_read')),
  useAsyncData('aux-job-runs', () => api.listJobs({ limit: 30 }))
])
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
  try {
    return JSON.parse(value)
  } catch {
    throw new Error(t('JSON 格式不正确'))
  }
}

const cleanValues = (values: string[]) => values.map((item) => item.trim()).filter(Boolean)
const cleanOAuthRows = (rows: OAuthRow[]) => rows
  .map((item) => ({ username: item.username.trim(), password: item.password.trim() }))
  .filter((item) => item.username && item.password)

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
    setMessage('checkin_996', t('配置已保存'))
  } catch (error: any) {
    setMessage('checkin_996', translateRequestError(error, '配置保存失败'))
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
    setMessage('checkin_qaq_al', t('配置已保存'))
  } catch (error: any) {
    setMessage('checkin_qaq_al', translateRequestError(error, '配置保存失败'))
  }
}

const saveLinuxdo = async () => {
  setMessage('linuxdo_read', '')
  try {
    await api.saveConfig('linuxdo_read', {
      accounts: cleanOAuthRows(linuxdoAccounts.value),
      base_topic_id: linuxdoBaseTopicId.value,
      max_posts: linuxdoMaxPosts.value
    })
    await refreshLinuxdo()
    setMessage('linuxdo_read', t('配置已保存'))
  } catch (error: any) {
    setMessage('linuxdo_read', translateRequestError(error, '配置保存失败'))
  }
}

const runJob = async (jobType: keyof typeof messages) => {
  setMessage(jobType, '')
  try {
    const result: any = await api.runJob(jobType)
    selectedRunId.value = result.id
    await refreshJobs()
    await refreshLogs()
    setMessage(jobType, t('已创建运行：{id}（{status}）', { id: result.id, status: formatJobStatus(result.status) }))
  } catch (error: any) {
    setMessage(jobType, translateRequestError(error, '任务执行失败'))
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
const hub996CountLabel = computed(() => `${t('996 hub 账号')} ${cleanValues(hub996Accounts.value).length}`)
const qaqCountLabel = computed(() => `${t('qaq.al 账号')} ${cleanValues(qaqAccounts.value).length}`)
const linuxdoCountLabel = computed(() => `${t('Linux.do 阅读账号')} ${cleanOAuthRows(linuxdoAccounts.value).length}`)
</script>

<template>
  <AppShell>
    <PageHeader
      :title="t('补充任务')"
      :description="t('管理 996 hub、qaq.al、Linux.do 等不属于主签到链路的附加任务')"
      :eyebrow="t('高级配置')"
    />
    <div class="button-row page-summary-strip">
      <StatusBadge :label="hub996CountLabel" :state="cleanValues(hub996Accounts).length ? 'configured' : 'unconfigured'" />
      <StatusBadge :label="qaqCountLabel" :state="cleanValues(qaqAccounts).length ? 'configured' : 'unconfigured'" />
      <StatusBadge :label="linuxdoCountLabel" :state="cleanOAuthRows(linuxdoAccounts).length ? 'configured' : 'unconfigured'" />
    </div>
    <div class="panel-grid aux-job-layout">
      <details class="card surface-card aux-job-cluster aux-job-cluster--fold" :open="cleanValues(hub996Accounts).length > 0">
        <summary class="aux-job-cluster__summary">
          <div class="aux-job-cluster__copy">
            <h2 class="card__title">{{ t('996 hub') }}</h2>
            <p class="muted">{{ t('维护访问令牌与代理设置') }}</p>
          </div>
          <StatusBadge :label="hub996CountLabel" :state="cleanValues(hub996Accounts).length ? 'configured' : 'unconfigured'" />
        </summary>
        <div class="panel-grid panel-grid--two aux-job-cluster__body aux-job-cluster__grid">
          <StringListCard
            v-model="hub996Accounts"
            :title="t('996 hub 账号')"
            :label="t('访问令牌')"
            placeholder="token-1"
          />
          <section class="card surface-card">
            <h3 class="card__title">{{ t('996 hub 选项') }}</h3>
            <div class="field">
              <label class="field__label" for="hub996-proxy">{{ t('代理 JSON') }}</label>
              <textarea
                id="hub996-proxy"
                v-model="hub996ProxyJson"
                class="textarea textarea--code"
                placeholder='{"server":"http://proxy.example.com:8080"}'
              />
            </div>
            <div class="button-row">
              <button class="button button--primary" @click="save996">{{ t('保存配置') }}</button>
              <button class="button button--secondary" @click="runJob('checkin_996')">{{ t('立即运行') }}</button>
            </div>
            <p v-if="messages.checkin_996" class="status-note" role="status" aria-live="polite">{{ messages.checkin_996 }}</p>
          </section>
        </div>
      </details>

      <details class="card surface-card aux-job-cluster aux-job-cluster--fold" :open="cleanValues(qaqAccounts).length > 0">
        <summary class="aux-job-cluster__summary">
          <div class="aux-job-cluster__copy">
            <h2 class="card__title">{{ t('qaq.al') }}</h2>
            <p class="muted">{{ t('维护 SID、套餐等级与代理参数') }}</p>
          </div>
          <StatusBadge :label="qaqCountLabel" :state="cleanValues(qaqAccounts).length ? 'configured' : 'unconfigured'" />
        </summary>
        <div class="panel-grid panel-grid--two aux-job-cluster__body aux-job-cluster__grid">
          <StringListCard
            v-model="qaqAccounts"
            :title="t('qaq.al 账号')"
            :label="t('SID')"
            placeholder="sid-1"
          />
          <section class="card surface-card">
            <h3 class="card__title">{{ t('qaq.al 选项') }}</h3>
            <div class="field">
              <label class="field__label" for="qaq-tier">{{ t('套餐等级') }}</label>
              <input id="qaq-tier" v-model.number="qaqTier" class="input" type="number" min="1" max="4">
            </div>
            <div class="field">
              <label class="field__label" for="qaq-proxy">{{ t('代理 JSON') }}</label>
              <textarea
                id="qaq-proxy"
                v-model="qaqProxyJson"
                class="textarea textarea--code"
                placeholder='{"server":"http://proxy.example.com:8080"}'
              />
            </div>
            <div class="button-row">
              <button class="button button--primary" @click="saveQaq">{{ t('保存配置') }}</button>
              <button class="button button--secondary" @click="runJob('checkin_qaq_al')">{{ t('立即运行') }}</button>
            </div>
            <p v-if="messages.checkin_qaq_al" class="status-note" role="status" aria-live="polite">{{ messages.checkin_qaq_al }}</p>
          </section>
        </div>
      </details>

      <details class="card surface-card aux-job-cluster aux-job-cluster--fold" :open="cleanOAuthRows(linuxdoAccounts).length > 0">
        <summary class="aux-job-cluster__summary">
          <div class="aux-job-cluster__copy">
            <h2 class="card__title">{{ t('Linux.do 阅读') }}</h2>
            <p class="muted">{{ t('维护阅读账号、主题锚点和抓取上限') }}</p>
          </div>
          <StatusBadge :label="linuxdoCountLabel" :state="cleanOAuthRows(linuxdoAccounts).length ? 'configured' : 'unconfigured'" />
        </summary>
        <div class="panel-grid panel-grid--two aux-job-cluster__body aux-job-cluster__grid">
          <OAuthAccountsCard v-model="linuxdoAccounts" :title="t('Linux.do 阅读账号')" />
          <section class="card surface-card">
            <h3 class="card__title">{{ t('Linux.do 阅读选项') }}</h3>
            <div class="field">
              <label class="field__label" for="linuxdo-base-topic-id">{{ t('基准主题 ID') }}</label>
              <input id="linuxdo-base-topic-id" v-model.number="linuxdoBaseTopicId" class="input" type="number" min="1">
            </div>
            <div class="field">
              <label class="field__label" for="linuxdo-max-posts">{{ t('最大帖子数') }}</label>
              <input id="linuxdo-max-posts" v-model.number="linuxdoMaxPosts" class="input" type="number" min="1">
            </div>
            <div class="button-row">
              <button class="button button--primary" @click="saveLinuxdo">{{ t('保存配置') }}</button>
              <button class="button button--secondary" @click="runJob('linuxdo_read')">{{ t('立即运行') }}</button>
            </div>
            <p v-if="messages.linuxdo_read" class="status-note" role="status" aria-live="polite">{{ messages.linuxdo_read }}</p>
          </section>
        </div>
      </details>

      <JobRunConsole
        :jobs="auxRuns"
        :logs="selectedLogs"
        :selected-run-id="selectedRunId"
        @select="pickRun"
      />
    </div>
  </AppShell>
</template>
