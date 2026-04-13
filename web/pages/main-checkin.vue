<script setup lang="ts">
const api = useControlPlane()
const { formatJobStatus, t, translateError } = useAppI18n()

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

const [
  { data: configResponse, refresh: refreshConfig },
  { data: jobs, refresh: refreshJobs }
] = await Promise.all([
  useAsyncData('main-config', () => api.getConfig('main_checkin')),
  useAsyncData('main-jobs', () => api.listJobs({ jobType: 'main_checkin', limit: 20 }))
])
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

const isBlankAccountRow = (row: AccountRow) => (
  !row.name.trim()
  && !row.provider.trim()
  && !row.api_user.trim()
  && !row.cookies_json.trim()
  && row.linux_mode === 'none'
  && !row.linux_user.trim()
  && !row.linux_pass.trim()
  && row.github_mode === 'none'
  && !row.github_user.trim()
  && !row.github_pass.trim()
  && !row.proxy_json.trim()
  && !row.extra_json.trim()
)

const cleanOAuthRows = (rows: OAuthRow[]) => rows
  .map((item) => ({ username: item.username.trim(), password: item.password.trim() }))
  .filter((item) => item.username && item.password)

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
  try {
    return JSON.parse(value)
  } catch {
    throw new Error(t('JSON 格式不正确'))
  }
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
    throw new Error(t('每个账号至少要配置 cookies、linux.do 或 github 之一'))
  }
  if (account.cookies && !account.api_user) {
    throw new Error(t('使用 cookies 的账号必须填写 api_user'))
  }
  if (row.linux_mode === 'single' && (!row.linux_user || !row.linux_pass)) {
    throw new Error(t('单账号 Linux.do 模式必须填写用户名和密码'))
  }
  if (row.github_mode === 'single' && (!row.github_user || !row.github_pass)) {
    throw new Error(t('单账号 GitHub 模式必须填写用户名和密码'))
  }
  return account
}

const saveConfig = async () => {
  saveMessage.value = ''
  runMessage.value = ''
  try {
    const configuredAccounts = accounts.value.filter((row) => !isBlankAccountRow(row))
    const payload = {
      accounts: configuredAccounts.map(buildAccount),
      providers: parseObject(providersJson.value, {}),
      accounts_linux_do: cleanOAuthRows(linuxDoAccounts.value),
      accounts_github: cleanOAuthRows(githubAccounts.value),
      proxy: parseObject(proxyJson.value, null)
    }
    await api.saveConfig('main_checkin', payload)
    await refreshConfig()
    saveMessage.value = t('配置已保存')
  } catch (error: any) {
    saveMessage.value = translateError(error?.data?.message || error?.message, '配置保存失败')
  }
}

const runJob = async () => {
  saveMessage.value = ''
  try {
    const result: any = await api.runJob('main_checkin')
    runMessage.value = t('已创建运行：{id}（{status}）', {
      id: result.id,
      status: formatJobStatus(result.status),
    })
    selectedRunId.value = result.id
    await refreshJobs()
    await refreshLogs()
  } catch (error: any) {
    runMessage.value = translateError(error?.data?.message || error?.message, '任务执行失败')
  }
}

const pickRun = async (runId: string) => {
  selectedRunId.value = runId
  await refreshLogs()
}

const pageMessage = computed(() => saveMessage.value || runMessage.value)
const accountCount = computed(() => accounts.value.filter((row) => !isBlankAccountRow(row)).length)
const linuxDoCount = computed(() => cleanOAuthRows(linuxDoAccounts.value).length)
const githubCount = computed(() => cleanOAuthRows(githubAccounts.value).length)
const accountCountLabel = computed(() => `${t('账号')} ${accountCount.value}`)
const linuxDoCountLabel = computed(() => `${t('全局 Linux.do 账号')} ${linuxDoCount.value}`)
const githubCountLabel = computed(() => `${t('全局 GitHub 账号')} ${githubCount.value}`)
const mainRuns = computed(() => (jobs.value as any[]) || [])
</script>

<template>
  <AppShell>
    <PageHeader
      :title="t('主链路配置')"
      :description="t('维护旧版主签到链路的账号、共享凭据和手动执行入口')"
      :eyebrow="t('运维与高级')"
    >
      <template #actions>
        <div class="button-row">
          <button class="button button--primary" @click="saveConfig">{{ t('保存配置') }}</button>
          <button class="button button--secondary" @click="runJob">{{ t('立即运行') }}</button>
        </div>
      </template>
    </PageHeader>
    <div class="button-row page-summary-strip">
      <StatusBadge :label="accountCountLabel" :state="accountCount ? 'configured' : 'unconfigured'" />
      <StatusBadge :label="linuxDoCountLabel" :state="linuxDoCount ? 'configured' : 'unconfigured'" />
      <StatusBadge :label="githubCountLabel" :state="githubCount ? 'configured' : 'unconfigured'" />
    </div>
    <p v-if="pageMessage" class="status-note" aria-live="polite">{{ pageMessage }}</p>
    <div class="panel-grid main-checkin-layout">
      <MainCheckinAccountsCard v-model="accounts" />
      <div class="panel-grid main-checkin-side">
        <OAuthAccountsCard v-model="linuxDoAccounts" :title="t('全局 Linux.do 账号')" />
        <OAuthAccountsCard v-model="githubAccounts" :title="t('全局 GitHub 账号')" />
        <section class="card surface-card section-card section-card--editor">
          <div class="section-head">
            <h2 class="card__title">{{ t('自定义提供商') }}</h2>
            <StatusBadge label="JSON" state="info" :dot="false" />
          </div>
          <div class="field">
            <label class="field__label" for="main-checkin-providers">{{ t('自定义提供商 JSON') }}</label>
            <textarea id="main-checkin-providers" v-model="providersJson" autocomplete="off" class="textarea textarea--code" spellcheck="false" />
          </div>
        </section>
        <section class="card surface-card section-card section-card--editor">
          <div class="section-head">
            <h2 class="card__title">{{ t('全局代理') }}</h2>
            <StatusBadge label="JSON" state="info" :dot="false" />
          </div>
          <div class="field">
            <label class="field__label" for="main-checkin-proxy">{{ t('代理 JSON') }}</label>
            <textarea
              id="main-checkin-proxy"
              v-model="proxyJson"
              autocomplete="off"
              class="textarea textarea--code"
              placeholder='{"server":"http://proxy.example.com:8080"}'
              spellcheck="false"
            />
          </div>
        </section>
        <JobRunConsole
          :jobs="mainRuns"
          :logs="logs || []"
          :selected-run-id="selectedRunId"
          @select="pickRun"
        />
      </div>
    </div>
  </AppShell>
</template>
