<script setup lang="ts">
const api = useControlPlane()

type AccountMode = 'none' | 'global' | 'single'
type AccountRow = {
  name: string
  provider: string
  api_user: string
  cookies_json: string
  linux_mode: AccountMode
  linux_user: string
  linux_pass: string
  github_mode: AccountMode
  github_user: string
  github_pass: string
  proxy_json: string
  extra_json: string
}

type OAuthRow = { username: string; password: string }

const providersJson = ref('{}')
const proxyJson = ref('')
const accounts = ref<AccountRow[]>([])
const linuxDoAccounts = ref<OAuthRow[]>([])
const githubAccounts = ref<OAuthRow[]>([])
const selectedRunId = ref('')
const saveMessage = ref('')
const runMessage = ref('')

const { data: configResponse, refresh: refreshConfig } = await useAsyncData('main-config', () => api.getConfig('main_checkin'))
const { data: jobs, refresh: refreshJobs } = await useAsyncData('main-jobs', () => api.listJobs())
const { data: logs, refresh: refreshLogs } = await useAsyncData(
  'main-logs',
  () => selectedRunId.value ? api.getJobLogs(selectedRunId.value) : Promise.resolve([])
)

const createAccount = (): AccountRow => ({
  name: '',
  provider: '',
  api_user: '',
  cookies_json: '',
  linux_mode: 'none',
  linux_user: '',
  linux_pass: '',
  github_mode: 'none',
  github_user: '',
  github_pass: '',
  proxy_json: '',
  extra_json: ''
})

watchEffect(() => {
  const payload = configResponse.value?.payload || {}
  providersJson.value = JSON.stringify(payload.providers || {}, null, 2)
  proxyJson.value = payload.proxy ? JSON.stringify(payload.proxy, null, 2) : ''
  accounts.value = (payload.accounts || []).map((item: any) => {
    const extra = { ...item }
    delete extra.name
    delete extra.provider
    delete extra.api_user
    delete extra.cookies
    delete extra['linux.do']
    delete extra.github
    delete extra.proxy
    const linuxConfig = item['linux.do']
    const githubConfig = item.github
    return {
      name: item.name || '',
      provider: item.provider || '',
      api_user: item.api_user || '',
      cookies_json: item.cookies ? JSON.stringify(item.cookies, null, 2) : '',
      linux_mode: linuxConfig === true ? 'global' : (linuxConfig ? 'single' : 'none'),
      linux_user: linuxConfig && linuxConfig !== true ? linuxConfig.username || '' : '',
      linux_pass: linuxConfig && linuxConfig !== true ? linuxConfig.password || '' : '',
      github_mode: githubConfig === true ? 'global' : (githubConfig ? 'single' : 'none'),
      github_user: githubConfig && githubConfig !== true ? githubConfig.username || '' : '',
      github_pass: githubConfig && githubConfig !== true ? githubConfig.password || '' : '',
      proxy_json: item.proxy ? JSON.stringify(item.proxy, null, 2) : '',
      extra_json: Object.keys(extra).length ? JSON.stringify(extra, null, 2) : ''
    }
  })
  linuxDoAccounts.value = (payload.accounts_linux_do || []).map((item: any) => ({
    username: item.username || '',
    password: item.password || ''
  }))
  githubAccounts.value = (payload.accounts_github || []).map((item: any) => ({
    username: item.username || '',
    password: item.password || ''
  }))
  if (!accounts.value.length) {
    accounts.value = [createAccount()]
  }
})

const parseObject = (value: string, emptyValue: any = undefined) => {
  if (!value.trim()) {
    return emptyValue
  }
  return JSON.parse(value)
}

const buildAccount = (row: AccountRow) => {
  const account: Record<string, any> = {
    provider: row.provider || 'anyrouter'
  }
  if (row.name) {
    account.name = row.name
  }
  if (row.api_user) {
    account.api_user = row.api_user
  }
  const cookies = parseObject(row.cookies_json, undefined)
  if (cookies) {
    account.cookies = cookies
  }
  if (row.linux_mode === 'global') {
    account['linux.do'] = true
  } else if (row.linux_mode === 'single') {
    account['linux.do'] = { username: row.linux_user, password: row.linux_pass }
  }
  if (row.github_mode === 'global') {
    account.github = true
  } else if (row.github_mode === 'single') {
    account.github = { username: row.github_user, password: row.github_pass }
  }
  const proxy = parseObject(row.proxy_json, undefined)
  if (proxy) {
    account.proxy = proxy
  }
  const extra = parseObject(row.extra_json, {})
  if (extra && typeof extra === 'object' && !Array.isArray(extra)) {
    Object.assign(account, extra)
  }
  if (!account.cookies && !account['linux.do'] && !account.github) {
    throw new Error('Each account must contain cookies, linux.do, or github authentication')
  }
  if (account.cookies && !account.api_user) {
    throw new Error('Accounts using cookies must set api_user')
  }
  if (row.linux_mode === 'single' && (!row.linux_user || !row.linux_pass)) {
    throw new Error('Single linux.do mode requires username and password')
  }
  if (row.github_mode === 'single' && (!row.github_user || !row.github_pass)) {
    throw new Error('Single github mode requires username and password')
  }
  return account
}

const saveConfig = async () => {
  saveMessage.value = ''
  runMessage.value = ''
  try {
    const payload = {
      accounts: accounts.value.map(buildAccount),
      providers: parseObject(providersJson.value, {}),
      accounts_linux_do: linuxDoAccounts.value.filter((item) => item.username && item.password),
      accounts_github: githubAccounts.value.filter((item) => item.username && item.password),
      proxy: parseObject(proxyJson.value, null)
    }
    await api.saveConfig('main_checkin', payload)
    await refreshConfig()
    saveMessage.value = 'Config saved'
  } catch (error: any) {
    saveMessage.value = error?.data?.message || error?.message || 'Config save failed'
  }
}

const runJob = async () => {
  saveMessage.value = ''
  try {
    const result: any = await api.runJob('main_checkin')
    runMessage.value = `Run created: ${result.id} (${result.status})`
    selectedRunId.value = result.id
    await refreshJobs()
    await refreshLogs()
  } catch (error: any) {
    runMessage.value = error?.data?.message || error?.message || 'Run failed'
  }
}

const pickRun = async (runId: string) => {
  selectedRunId.value = runId
  await refreshLogs()
}
</script>

<template>
  <AppShell>
    <div class="panel-grid">
      <MainCheckinAccountsCard v-model="accounts" />
      <div class="panel-grid panel-grid--two">
        <OAuthAccountsCard v-model="linuxDoAccounts" title="Global Linux.do accounts" />
        <OAuthAccountsCard v-model="githubAccounts" title="Global GitHub accounts" />
      </div>
      <div class="panel-grid panel-grid--two">
        <section class="card">
          <h2 class="card__title">Providers</h2>
          <div class="field">
            <label class="field__label">Custom providers JSON</label>
            <textarea v-model="providersJson" class="textarea" />
          </div>
        </section>
        <section class="card">
          <h2 class="card__title">Global proxy</h2>
          <div class="field">
            <label class="field__label">Proxy JSON</label>
            <textarea v-model="proxyJson" class="textarea" placeholder='{"server":"http://proxy.example.com:8080"}' />
          </div>
          <div class="button-row">
            <button class="button button--primary" @click="saveConfig">Save config</button>
            <button class="button button--secondary" @click="runJob">Run now</button>
          </div>
          <p class="muted">{{ saveMessage || runMessage }}</p>
        </section>
      </div>
      <section class="card">
        <h2 class="card__title">Runs and logs</h2>
        <div class="panel-grid panel-grid--two">
          <div class="job-list">
            <button
              v-for="job in jobs || []"
              :key="job.id"
              class="job-item"
              :class="{ 'job-item--selected': selectedRunId === job.id }"
              @click="pickRun(job.id)"
            >
              <strong>{{ job.job_type }} / {{ job.status }}</strong>
              <div class="job-item__meta">
                <span>{{ job.trigger }}</span>
                <span>{{ job.started_at }}</span>
              </div>
            </button>
          </div>
          <pre class="code-block">{{ (logs || []).map((item: any) => `[${item.stream}] ${item.message}`).join('\n') }}</pre>
        </div>
      </section>
    </div>
  </AppShell>
</template>
